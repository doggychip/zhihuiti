"""Transactional, idempotent SQLite accounting for paper fills."""

from __future__ import annotations

import json
import sqlite3
import threading
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from zhihuiti.polymarket.models import (
    CopyDecision,
    PortfolioSnapshot,
    Position,
    Side,
    SimulatedFill,
    SourceTrade,
    ZERO,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cash TEXT NOT NULL,
    starting_cash TEXT NOT NULL,
    realized_pnl TEXT NOT NULL DEFAULT '0'
);
CREATE TABLE IF NOT EXISTS source_observations (
    fingerprint TEXT PRIMARY KEY,
    wallet TEXT NOT NULL,
    token_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    side TEXT NOT NULL,
    size TEXT NOT NULL,
    price TEXT NOT NULL,
    source_timestamp INTEGER NOT NULL,
    transaction_hash TEXT NOT NULL,
    occurrence INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    observed_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS source_wallet_time
    ON source_observations(wallet, source_timestamp);
CREATE TABLE IF NOT EXISTS ingestion_cursors (
    wallet TEXT PRIMARY KEY,
    source_timestamp INTEGER NOT NULL,
    updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS copy_decisions (
    source_fingerprint TEXT PRIMARY KEY REFERENCES source_observations(fingerprint),
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_size TEXT NOT NULL,
    approved_size TEXT NOT NULL,
    arrival_timestamp_ms INTEGER NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS simulated_fills (
    source_fingerprint TEXT PRIMARY KEY REFERENCES copy_decisions(source_fingerprint),
    side TEXT NOT NULL,
    token_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    requested_size TEXT NOT NULL,
    filled_size TEXT NOT NULL,
    average_price TEXT NOT NULL,
    notional TEXT NOT NULL,
    fee TEXT NOT NULL,
    book_timestamp_ms INTEGER NOT NULL,
    book_hash TEXT NOT NULL,
    levels_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_positions (
    token_id TEXT PRIMARY KEY,
    condition_id TEXT NOT NULL,
    shares TEXT NOT NULL,
    cost_basis TEXT NOT NULL,
    realized_pnl TEXT NOT NULL DEFAULT '0'
);
CREATE TABLE IF NOT EXISTS settlements (
    token_id TEXT PRIMARY KEY,
    condition_id TEXT NOT NULL,
    shares TEXT NOT NULL,
    payout_per_share TEXT NOT NULL,
    payout TEXT NOT NULL,
    realized_pnl TEXT NOT NULL,
    settled_at INTEGER NOT NULL DEFAULT (unixepoch())
);
"""


class PaperLedger:
    def __init__(self, path: str | Path, starting_cash: Decimal) -> None:
        path_string = str(path)
        if path_string != ":memory:":
            Path(path_string).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path_string, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        if path_string != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            "INSERT OR IGNORE INTO paper_account(id, cash, starting_cash, realized_pnl) "
            "VALUES (1, ?, ?, '0')",
            (str(starting_cash), str(starting_cash)),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> PaperLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_cursor(self, wallet: str) -> int | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT source_timestamp FROM ingestion_cursors WHERE wallet=?",
                (wallet.lower(),),
            ).fetchone()
            return int(row[0]) if row else None

    def advance_cursor(self, wallet: str, timestamp: int) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT INTO ingestion_cursors(wallet, source_timestamp) VALUES (?, ?) "
                "ON CONFLICT(wallet) DO UPDATE SET source_timestamp="
                "MAX(source_timestamp, excluded.source_timestamp), updated_at=unixepoch()",
                (wallet.lower(), timestamp),
            )

    def has_decision(self, fingerprint: str) -> bool:
        with self._lock:
            row = self.conn.execute(
                "SELECT 1 FROM copy_decisions WHERE source_fingerprint=?", (fingerprint,)
            ).fetchone()
            return row is not None

    def account_state(self, token_id: str, condition_id: str) -> tuple[Decimal, Decimal, Decimal]:
        """Return cash, token inventory, and total open exposure in the market."""
        with self._lock:
            account = self.conn.execute("SELECT cash FROM paper_account WHERE id=1").fetchone()
            position = self.conn.execute(
                "SELECT shares FROM paper_positions WHERE token_id=?", (token_id,)
            ).fetchone()
            rows = self.conn.execute(
                "SELECT cost_basis FROM paper_positions WHERE condition_id=? AND shares!='0'",
                (condition_id,),
            ).fetchall()
        return (
            Decimal(account[0]),
            Decimal(position[0]) if position else ZERO,
            sum((Decimal(row[0]) for row in rows), ZERO),
        )

    def apply(
        self,
        trade: SourceTrade,
        decision: CopyDecision,
        fill: SimulatedFill | None = None,
    ) -> bool:
        """Record a decision and atomically apply its fill exactly once."""
        if decision.source_fingerprint != trade.fingerprint:
            raise ValueError("decision does not belong to source trade")
        if fill and fill.source_fingerprint != trade.fingerprint:
            raise ValueError("fill does not belong to source trade")
        with self._lock, self.conn:
            self._insert_observation(trade)
            inserted = self.conn.execute(
                "INSERT OR IGNORE INTO copy_decisions("
                "source_fingerprint,status,reason,requested_size,approved_size,arrival_timestamp_ms"
                ") VALUES (?,?,?,?,?,?)",
                (
                    trade.fingerprint,
                    decision.status.value,
                    decision.reason,
                    str(decision.requested_size),
                    str(decision.approved_size),
                    decision.arrival_timestamp_ms,
                ),
            ).rowcount
            if not inserted:
                return False
            if fill is not None:
                self._insert_fill(fill)
                if fill.filled_size > ZERO:
                    self._apply_fill(fill)
            return True

    def _insert_observation(self, trade: SourceTrade) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO source_observations("
            "fingerprint,wallet,token_id,condition_id,side,size,price,source_timestamp,"
            "transaction_hash,occurrence,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                trade.fingerprint,
                trade.wallet,
                trade.token_id,
                trade.condition_id,
                trade.side.value,
                str(trade.size),
                str(trade.price),
                trade.timestamp,
                trade.transaction_hash,
                trade.occurrence,
                json.dumps(trade.raw, sort_keys=True, separators=(",", ":"), default=str),
            ),
        )

    def _insert_fill(self, fill: SimulatedFill) -> None:
        levels = [
            {"price": str(level.price), "size": str(level.size), "fee": str(level.fee)}
            for level in fill.levels
        ]
        self.conn.execute(
            "INSERT INTO simulated_fills VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                fill.source_fingerprint,
                fill.side.value,
                fill.token_id,
                fill.condition_id,
                str(fill.requested_size),
                str(fill.filled_size),
                str(fill.average_price),
                str(fill.notional),
                str(fill.fee),
                fill.book_timestamp_ms,
                fill.book_hash,
                json.dumps(levels, separators=(",", ":")),
            ),
        )

    def _apply_fill(self, fill: SimulatedFill) -> None:
        account = self.conn.execute(
            "SELECT cash, realized_pnl FROM paper_account WHERE id=1"
        ).fetchone()
        cash, total_realized = Decimal(account[0]), Decimal(account[1])
        row = self.conn.execute(
            "SELECT shares,cost_basis,realized_pnl FROM paper_positions WHERE token_id=?",
            (fill.token_id,),
        ).fetchone()
        shares = Decimal(row[0]) if row else ZERO
        basis = Decimal(row[1]) if row else ZERO
        position_realized = Decimal(row[2]) if row else ZERO

        if fill.side is Side.BUY:
            debit = fill.notional + fill.fee
            if debit > cash:
                raise ValueError("simulated fill exceeds available cash")
            cash -= debit
            shares += fill.filled_size
            basis += debit
        else:
            if fill.filled_size > shares:
                raise ValueError("simulated fill exceeds available inventory")
            removed_basis = basis * fill.filled_size / shares
            proceeds = fill.notional - fill.fee
            realized = proceeds - removed_basis
            cash += proceeds
            shares -= fill.filled_size
            basis -= removed_basis
            position_realized += realized
            total_realized += realized

        self.conn.execute(
            "UPDATE paper_account SET cash=?, realized_pnl=? WHERE id=1",
            (str(cash), str(total_realized)),
        )
        self.conn.execute(
            "INSERT INTO paper_positions(token_id,condition_id,shares,cost_basis,realized_pnl) "
            "VALUES (?,?,?,?,?) ON CONFLICT(token_id) DO UPDATE SET "
            "shares=excluded.shares,cost_basis=excluded.cost_basis,"
            "realized_pnl=excluded.realized_pnl",
            (
                fill.token_id,
                fill.condition_id,
                str(shares),
                str(basis),
                str(position_realized),
            ),
        )

    def settle_market(self, condition_id: str, winning_token_ids: set[str]) -> int:
        """Settle each still-open outcome at $1 or $0, idempotently."""
        count = 0
        with self._lock, self.conn:
            rows = self.conn.execute(
                "SELECT token_id,shares,cost_basis,realized_pnl FROM paper_positions "
                "WHERE condition_id=? AND CAST(shares AS REAL)>0",
                (condition_id,),
            ).fetchall()
            for row in rows:
                existing = self.conn.execute(
                    "SELECT 1 FROM settlements WHERE token_id=?", (row["token_id"],)
                ).fetchone()
                if existing:
                    continue
                shares = Decimal(row["shares"])
                basis = Decimal(row["cost_basis"])
                payout_per_share = Decimal("1") if row["token_id"] in winning_token_ids else ZERO
                payout = shares * payout_per_share
                realized = payout - basis
                self.conn.execute(
                    "INSERT INTO settlements(token_id,condition_id,shares,payout_per_share,payout,"
                    "realized_pnl) VALUES (?,?,?,?,?,?)",
                    (
                        row["token_id"],
                        condition_id,
                        str(shares),
                        str(payout_per_share),
                        str(payout),
                        str(realized),
                    ),
                )
                self.conn.execute(
                    "UPDATE paper_account SET cash=CAST(cash AS REAL)+?, "
                    "realized_pnl=CAST(realized_pnl AS REAL)+? WHERE id=1",
                    (str(payout), str(realized)),
                )
                self.conn.execute(
                    "UPDATE paper_positions SET shares='0',cost_basis='0',"
                    "realized_pnl=? WHERE token_id=?",
                    (str(Decimal(row["realized_pnl"]) + realized), row["token_id"]),
                )
                count += 1
        return count

    def snapshot(self, prices: Mapping[str, Decimal] | None = None) -> PortfolioSnapshot:
        prices = prices or {}
        with self._lock:
            account = self.conn.execute(
                "SELECT cash,realized_pnl FROM paper_account WHERE id=1"
            ).fetchone()
            rows = self.conn.execute(
                "SELECT * FROM paper_positions ORDER BY condition_id,token_id"
            ).fetchall()
        positions = tuple(
            Position(
                token_id=row["token_id"],
                condition_id=row["condition_id"],
                shares=Decimal(row["shares"]),
                cost_basis=Decimal(row["cost_basis"]),
                realized_pnl=Decimal(row["realized_pnl"]),
            )
            for row in rows
        )
        unrealized = sum(
            (
                position.shares * prices[position.token_id] - position.cost_basis
                for position in positions
                if position.token_id in prices
            ),
            ZERO,
        )
        return PortfolioSnapshot(
            cash=Decimal(account["cash"]),
            positions=positions,
            realized_pnl=Decimal(account["realized_pnl"]),
            unrealized_pnl=unrealized,
        )

    def counts(self) -> dict[str, int]:
        with self._lock:
            return {
                table: int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in ("source_observations", "copy_decisions", "simulated_fills", "settlements")
            }
