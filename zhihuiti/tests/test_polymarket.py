"""Focused tests for deterministic Polymarket paper copying."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from zhihuiti.polymarket.client import PolymarketClient, parse_book_payload
from zhihuiti.polymarket.config import PolymarketConfig
from zhihuiti.polymarket.copy_engine import DeterministicCopyEngine
from zhihuiti.polymarket.models import (
    CopyDecision,
    DecisionStatus,
    FeeSchedule,
    MarketMetadata,
    Side,
    SimulatedFill,
)
from zhihuiti.polymarket.normalize import normalize_trades
from zhihuiti.polymarket.paper_ledger import PaperLedger
from zhihuiti.polymarket.runner import LeaderTradePoller
from zhihuiti.polymarket.simulator import OrderBookFillSimulator


WALLET = "0x1111111111111111111111111111111111111111"
FIXTURE = Path(__file__).parent / "fixtures" / "polymarket" / "replay.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(), parse_float=Decimal)


def config(**overrides) -> PolymarketConfig:
    values = {
        "leader_wallets": (WALLET,),
        "starting_cash": Decimal("100"),
        "copy_ratio": Decimal("1"),
        "simulated_latency_ms": 1000,
        "max_slippage": Decimal("0.03"),
        "max_trade_notional": Decimal("100"),
        "max_market_exposure": Decimal("100"),
        "stale_after_seconds": 60,
    }
    values.update(overrides)
    return PolymarketConfig(**values)


def test_config_from_environment_and_no_live_credentials():
    cfg = PolymarketConfig.from_env(
        {
            "POLYMARKET_LEADER_WALLETS": WALLET.upper(),
            "POLYMARKET_COPY_RATIO": "0.125",
        }
    )
    assert cfg.leader_wallets == (WALLET,)
    assert cfg.copy_ratio == Decimal("0.125")
    assert not any("key" in name or "live" in name for name in cfg.__dataclass_fields__)


def test_client_paginates_and_requests_maker_fills():
    fake = MagicMock()
    responses = [
        MagicMock(text=json.dumps([{"id": 1}, {"id": 2}])),
        MagicMock(text=json.dumps([{"id": 3}])),
    ]
    for response in responses:
        response.raise_for_status.return_value = None
    fake.request.side_effect = responses
    client = PolymarketClient(client=fake, retries=0)
    rows = client.fetch_trades(WALLET, start=100, end=200, page_size=2)
    assert [row["id"] for row in rows] == [1, 2, 3]
    first_params = fake.request.call_args_list[0].kwargs["params"]
    second_params = fake.request.call_args_list[1].kwargs["params"]
    assert first_params["takerOnly"] == "false"
    assert (first_params["offset"], second_params["offset"]) == (0, 2)
    assert (first_params["start"], first_params["end"]) == (100, 200)


def test_client_does_not_retry_non_retryable_http_error():
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(400, request=request)
    fake = MagicMock()
    fake.request.side_effect = httpx.HTTPStatusError(
        "bad", request=request, response=response
    )
    client = PolymarketClient(client=fake, retries=3, sleep=lambda _: None)
    with pytest.raises(httpx.HTTPStatusError):
        client.fetch_trades(WALLET)
    assert fake.request.call_count == 1


def test_normalization_preserves_identical_same_second_occurrences():
    payloads = load_fixture()["trades"]
    trades = normalize_trades(payloads, expected_wallet=WALLET)
    assert len(trades) == 2
    assert {trade.occurrence for trade in trades} == {0, 1}
    assert len({trade.fingerprint for trade in trades}) == 2
    assert all(trade.price == Decimal("0.5") for trade in trades)
    assert all(trade.raw for trade in trades)


def test_book_walk_sorts_levels_and_partially_fills_with_fee():
    fixture = load_fixture()
    trade = normalize_trades(fixture["trades"][:1])[0]
    book = parse_book_payload(fixture["books"]["yes-token"], "yes-token")
    fill = OrderBookFillSimulator().simulate(
        trade,
        Decimal("3"),
        book,
        max_slippage=Decimal("0.03"),
        fee_schedule=FeeSchedule(rate=Decimal("0.05")),
    )
    assert fill.filled_size == Decimal("3")
    assert [level.price for level in fill.levels] == [Decimal("0.50"), Decimal("0.51")]
    assert fill.notional == Decimal("1.52")
    assert fill.fee == Decimal("0.03749")

    partial = OrderBookFillSimulator().simulate(
        trade,
        Decimal("200"),
        book,
        max_slippage=Decimal("0.03"),
    )
    assert partial.filled_size == Decimal("101")
    assert partial.partial


def test_risk_rejections_for_staleness_inventory_and_exposure():
    trade = normalize_trades(load_fixture()["trades"][:1])[0]
    engine = DeterministicCopyEngine(config())
    stale = engine.decide(
        trade,
        now_timestamp=trade.timestamp + 61,
        cash=Decimal("100"),
        inventory=Decimal("0"),
        market_exposure=Decimal("0"),
    )
    assert stale.reason == "stale_source_trade"

    sell = trade.__class__(**{**trade.__dict__, "side": Side.SELL})
    no_inventory = engine.decide(
        sell,
        now_timestamp=trade.timestamp,
        cash=Decimal("100"),
        inventory=Decimal("0"),
        market_exposure=Decimal("0"),
    )
    assert no_inventory.reason == "insufficient_inventory"

    capped = engine.decide(
        trade,
        now_timestamp=trade.timestamp,
        cash=Decimal("100"),
        inventory=Decimal("0"),
        market_exposure=Decimal("100"),
    )
    assert capped.reason == "market_exposure_cap"


def make_fill(trade, side: Side, size: str, price: str, fee: str = "0") -> SimulatedFill:
    quantity = Decimal(size)
    execution_price = Decimal(price)
    return SimulatedFill(
        source_fingerprint=trade.fingerprint,
        side=side,
        token_id=trade.token_id,
        condition_id=trade.condition_id,
        requested_size=quantity,
        filled_size=quantity,
        average_price=execution_price,
        notional=quantity * execution_price,
        fee=Decimal(fee),
        book_timestamp_ms=trade.timestamp * 1000,
        book_hash="test",
    )


def accepted(trade, size: str) -> CopyDecision:
    return CopyDecision(
        source_fingerprint=trade.fingerprint,
        status=DecisionStatus.ACCEPTED,
        reason="accepted",
        requested_size=Decimal(size),
        approved_size=Decimal(size),
    )


def test_buy_sell_accounting_fees_restart_and_settlement(tmp_path):
    db = tmp_path / "paper.db"
    buy = normalize_trades(load_fixture()["trades"][:1])[0]
    with PaperLedger(db, Decimal("100")) as ledger:
        assert ledger.apply(buy, accepted(buy, "10"), make_fill(buy, Side.BUY, "10", "0.5", "0.1"))
        assert not ledger.apply(buy, accepted(buy, "10"), make_fill(buy, Side.BUY, "10", "0.5", "0.1"))
        snapshot = ledger.snapshot()
        assert snapshot.cash == Decimal("94.9")
        assert snapshot.positions[0].cost_basis == Decimal("5.1")

    sell_payload = {**load_fixture()["trades"][0], "side": "SELL", "transactionHash": "0xbbb", "timestamp": 1700000001}
    sell = normalize_trades([sell_payload])[0]
    with PaperLedger(db, Decimal("999")) as ledger:
        assert ledger.snapshot().cash == Decimal("94.9")
        ledger.apply(sell, accepted(sell, "4"), make_fill(sell, Side.SELL, "4", "0.6", "0.05"))
        snapshot = ledger.snapshot()
        assert snapshot.cash == Decimal("97.25")
        assert snapshot.positions[0].shares == Decimal("6")
        assert snapshot.positions[0].cost_basis == Decimal("3.06")
        assert snapshot.realized_pnl == Decimal("0.31")
        assert ledger.settle_market("condition-1", {"yes-token"}) == 1
        settled = ledger.snapshot()
        assert settled.cash == Decimal("103.25")
        assert settled.realized_pnl == Decimal("3.25")
        assert ledger.settle_market("condition-1", {"yes-token"}) == 0


def test_runner_replay_is_deterministic_and_idempotent(tmp_path):
    fixture = load_fixture()
    trades = normalize_trades(fixture["trades"], expected_wallet=WALLET)
    book = parse_book_payload(fixture["books"]["yes-token"], "yes-token")
    market = MarketMetadata(
        condition_id="condition-1",
        tokens={"yes-token": "Yes", "no-token": "No"},
        fee=FeeSchedule(rate=Decimal("0.05")),
    )
    client = MagicMock()
    cfg = config(database_path=tmp_path / "replay.db")
    with PaperLedger(cfg.database_path, cfg.starting_cash) as ledger:
        runner = LeaderTradePoller(cfg, client, ledger, clock=lambda: 1700000010.0, sleep=lambda _: None)
        first = runner.process_trades(
            trades,
            now_timestamp=1700000010,
            book_lookup=lambda _: book,
            market_lookup=lambda _: market,
        )
        before = ledger.snapshot()
        second = runner.process_trades(
            trades,
            now_timestamp=1700000010,
            book_lookup=lambda _: book,
            market_lookup=lambda _: market,
        )
        after = ledger.snapshot()
    assert first == {"observed": 2, "processed": 2, "duplicates": 0}
    assert second == {"observed": 2, "processed": 0, "duplicates": 2}
    assert before == after
