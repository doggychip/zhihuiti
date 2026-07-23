"""Polling, replay, delayed book lookup, and reconciliation."""

from __future__ import annotations

import signal
import threading
import time
from dataclasses import replace
from decimal import Decimal, ROUND_DOWN
from typing import Callable, Iterable

from zhihuiti.polymarket.client import PolymarketClient
from zhihuiti.polymarket.config import PolymarketConfig
from zhihuiti.polymarket.copy_engine import DeterministicCopyEngine
from zhihuiti.polymarket.models import (
    DecisionStatus,
    MarketMetadata,
    OrderBook,
    SourceTrade,
)
from zhihuiti.polymarket.normalize import normalize_trades
from zhihuiti.polymarket.paper_ledger import PaperLedger
from zhihuiti.polymarket.simulator import OrderBookFillSimulator


class LeaderTradePoller:
    def __init__(
        self,
        config: PolymarketConfig,
        client: PolymarketClient,
        ledger: PaperLedger,
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.client = client
        self.ledger = ledger
        self.engine = DeterministicCopyEngine(config)
        self.simulator = OrderBookFillSimulator()
        self.clock = clock
        self.sleep = sleep
        self.stop_event = threading.Event()

    def run_cycle(self) -> dict[str, int]:
        totals = {"observed": 0, "processed": 0, "duplicates": 0}
        end = int(self.clock())
        for wallet in self.config.leader_wallets:
            cursor = self.ledger.get_cursor(wallet)
            start = max(0, cursor - self.config.polling_overlap_seconds) if cursor else None
            payloads = self.client.fetch_trades(
                wallet,
                start=start,
                end=end,
                page_size=self.config.page_size,
            )
            trades = normalize_trades(payloads, expected_wallet=wallet)
            result = self.process_trades(trades, now_timestamp=end)
            for key in totals:
                totals[key] += result[key]
            if trades:
                # This is deliberately last: any exception leaves the overlap
                # cursor unchanged so the entire window is retried.
                self.ledger.advance_cursor(wallet, max(trade.timestamp for trade in trades))
        self.reconcile()
        return totals

    def process_trades(
        self,
        trades: Iterable[SourceTrade],
        *,
        now_timestamp: int | None = None,
        book_lookup: Callable[[str], OrderBook] | None = None,
        market_lookup: Callable[[str], MarketMetadata] | None = None,
    ) -> dict[str, int]:
        now = int(self.clock()) if now_timestamp is None else now_timestamp
        book_lookup = book_lookup or self.client.fetch_book
        market_lookup = market_lookup or self.client.fetch_market
        counts = {"observed": 0, "processed": 0, "duplicates": 0}
        for trade in sorted(trades, key=lambda item: (item.timestamp, item.fingerprint)):
            counts["observed"] += 1
            if self.ledger.has_decision(trade.fingerprint):
                counts["duplicates"] += 1
                continue
            cash, inventory, exposure = self.ledger.account_state(
                trade.token_id, trade.condition_id
            )
            decision = self.engine.decide(
                trade,
                now_timestamp=now,
                cash=cash,
                inventory=inventory,
                market_exposure=exposure,
            )
            fill = None
            if decision.status is DecisionStatus.ACCEPTED:
                market = market_lookup(trade.condition_id)
                if market.closed or not market.accepting_orders:
                    decision = replace(
                        decision,
                        status=DecisionStatus.REJECTED,
                        reason="market_not_tradable",
                        approved_size=Decimal("0"),
                    )
                elif trade.token_id not in market.tokens:
                    decision = replace(
                        decision,
                        status=DecisionStatus.REJECTED,
                        reason="unknown_market_token",
                        approved_size=Decimal("0"),
                    )
                else:
                    if trade.side.value == "BUY":
                        worst_price = min(
                            Decimal("1"),
                            trade.price * (Decimal("1") + self.config.max_slippage),
                        )
                        fee_per_share = market.fee.fee(Decimal("1"), worst_price)
                        affordable = cash / (worst_price + fee_per_share)
                        if affordable < decision.approved_size:
                            approved = max(Decimal("0"), affordable).quantize(
                                Decimal("0.000001"), rounding=ROUND_DOWN
                            )
                            if approved <= 0:
                                decision = replace(
                                    decision,
                                    status=DecisionStatus.REJECTED,
                                    reason="insufficient_cash_with_fees",
                                    approved_size=Decimal("0"),
                                )
                            else:
                                decision = replace(
                                    decision,
                                    reason="accepted_cash_and_fee_limited",
                                    approved_size=approved,
                                )
                    if decision.status is DecisionStatus.REJECTED:
                        self.ledger.apply(trade, decision)
                        counts["processed"] += 1
                        continue
                    arrival_wait = decision.arrival_timestamp_ms / 1000 - self.clock()
                    if arrival_wait > 0:
                        self.sleep(arrival_wait)
                    book = book_lookup(trade.token_id)
                    if book.timestamp_ms and (
                        decision.arrival_timestamp_ms - book.timestamp_ms
                        > self.config.stale_after_seconds * 1000
                    ):
                        decision = replace(
                            decision,
                            status=DecisionStatus.REJECTED,
                            reason="stale_order_book",
                            approved_size=Decimal("0"),
                        )
                    else:
                        fill = self.simulator.simulate(
                            trade,
                            decision.approved_size,
                            book,
                            max_slippage=self.config.max_slippage,
                            fee_schedule=market.fee,
                        )
                        if fill.filled_size == 0:
                            decision = replace(decision, reason="accepted_no_executable_depth")
                        elif fill.partial:
                            decision = replace(decision, reason="accepted_partial_depth")
            if self.ledger.apply(trade, decision, fill):
                counts["processed"] += 1
            else:
                counts["duplicates"] += 1
        return counts

    def reconcile(self) -> int:
        snapshot = self.ledger.snapshot()
        condition_ids = {
            position.condition_id for position in snapshot.positions if position.shares > 0
        }
        settled = 0
        for condition_id in condition_ids:
            market = self.client.fetch_market(condition_id)
            if market.resolved:
                settled += self.ledger.settle_market(condition_id, set(market.winners))
        return settled

    def watch(self, on_cycle: Callable[[dict[str, int]], None] | None = None) -> None:
        previous_handlers: dict[int, object] = {}

        def stop(*_: object) -> None:
            self.stop_event.set()

        if threading.current_thread() is threading.main_thread():
            for number in (signal.SIGINT, signal.SIGTERM):
                previous_handlers[number] = signal.getsignal(number)
                signal.signal(number, stop)
        try:
            while not self.stop_event.is_set():
                result = self.run_cycle()
                if on_cycle:
                    on_cycle(result)
                self.stop_event.wait(float(self.config.polling_interval_seconds))
        finally:
            for number, handler in previous_handlers.items():
                signal.signal(number, handler)
