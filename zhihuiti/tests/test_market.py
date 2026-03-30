"""Tests for the TradingMarket (交易市场) module."""

from __future__ import annotations

import pytest

from zhihuiti.market import TradingMarket, MarketOrder, TradeRecord, OrderType, OrderStatus
from zhihuiti.models import AgentState, AgentConfig, AgentRole
from zhihuiti.memory import Memory


def _make_memory() -> Memory:
    return Memory(":memory:")


def _make_agent(budget: float = 100.0) -> AgentState:
    return AgentState(
        config=AgentConfig(role=AgentRole.CODER, system_prompt=""),
        budget=budget,
    )


def _make_market() -> tuple[TradingMarket, Memory]:
    mem = _make_memory()
    market = TradingMarket(mem)
    return market, mem


# ---------------------------------------------------------------------------
# Order placement
# ---------------------------------------------------------------------------

class TestPlaceOrder:
    def test_place_buy_order_success(self):
        market, _ = _make_market()
        agent = _make_agent(budget=100.0)
        order = market.place_order(agent, OrderType.BUY, "coder", price=10.0)
        assert order is not None
        assert order.order_type == OrderType.BUY
        assert order.service_role == "coder"
        assert order.price == 10.0
        assert order.status == OrderStatus.OPEN

    def test_place_sell_order_success(self):
        market, _ = _make_market()
        agent = _make_agent()
        order = market.place_order(agent, OrderType.SELL, "coder", price=5.0)
        assert order is not None
        assert order.order_type == OrderType.SELL

    def test_reject_price_below_minimum(self):
        market, _ = _make_market()
        agent = _make_agent()
        order = market.place_order(agent, OrderType.BUY, "coder", price=0.5)
        assert order is None

    def test_reject_buy_insufficient_budget(self):
        market, _ = _make_market()
        agent = _make_agent(budget=5.0)
        order = market.place_order(agent, OrderType.BUY, "coder", price=10.0)
        assert order is None

    def test_reject_dead_agent(self):
        market, _ = _make_market()
        agent = _make_agent()
        agent.alive = False
        order = market.place_order(agent, OrderType.BUY, "coder", price=5.0)
        assert order is None

    def test_sell_does_not_check_budget(self):
        """Sellers don't need budget — they're offering a service."""
        market, _ = _make_market()
        agent = _make_agent(budget=0.0)
        agent.budget = 0.5  # Below cost but selling
        order = market.place_order(agent, OrderType.SELL, "coder", price=1.0)
        assert order is not None


# ---------------------------------------------------------------------------
# Order cancellation
# ---------------------------------------------------------------------------

class TestCancelOrder:
    def test_cancel_own_order(self):
        market, _ = _make_market()
        agent = _make_agent()
        order = market.place_order(agent, OrderType.BUY, "coder", price=5.0)
        result = market.cancel_order(order.id, agent.id)
        assert result is True
        assert order.status == OrderStatus.CANCELLED

    def test_cannot_cancel_others_order(self):
        market, _ = _make_market()
        agent1 = _make_agent()
        agent2 = _make_agent()
        order = market.place_order(agent1, OrderType.BUY, "coder", price=5.0)
        result = market.cancel_order(order.id, agent2.id)
        assert result is False
        assert order.status == OrderStatus.OPEN

    def test_cannot_cancel_nonexistent_order(self):
        market, _ = _make_market()
        result = market.cancel_order("nonexistent", "some_agent")
        assert result is False


# ---------------------------------------------------------------------------
# Order matching
# ---------------------------------------------------------------------------

class TestMatchOrders:
    def test_basic_match(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=100.0)
        seller = _make_agent()

        market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        market.place_order(seller, OrderType.SELL, "coder", price=8.0)

        pairs = market.match_orders("coder")
        assert len(pairs) == 1
        assert pairs[0][0].order_type == OrderType.BUY
        assert pairs[0][1].order_type == OrderType.SELL

    def test_no_match_when_buy_below_sell(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=100.0)
        seller = _make_agent()

        market.place_order(buyer, OrderType.BUY, "coder", price=5.0)
        market.place_order(seller, OrderType.SELL, "coder", price=10.0)

        pairs = market.match_orders("coder")
        assert len(pairs) == 0

    def test_no_self_trade(self):
        market, _ = _make_market()
        agent = _make_agent(budget=100.0)

        market.place_order(agent, OrderType.BUY, "coder", price=10.0)
        market.place_order(agent, OrderType.SELL, "coder", price=8.0)

        pairs = market.match_orders("coder")
        assert len(pairs) == 0

    def test_multiple_matches(self):
        market, _ = _make_market()
        buyer1 = _make_agent(budget=100.0)
        buyer2 = _make_agent(budget=100.0)
        seller1 = _make_agent()
        seller2 = _make_agent()

        market.place_order(buyer1, OrderType.BUY, "analyst", price=15.0)
        market.place_order(buyer2, OrderType.BUY, "analyst", price=12.0)
        market.place_order(seller1, OrderType.SELL, "analyst", price=8.0)
        market.place_order(seller2, OrderType.SELL, "analyst", price=9.0)

        pairs = market.match_orders("analyst")
        assert len(pairs) == 2


# ---------------------------------------------------------------------------
# Trade execution
# ---------------------------------------------------------------------------

class TestExecuteTrade:
    def test_trade_transfers_tokens(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=100.0)
        seller = _make_agent(budget=0.0)

        buy_order = market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        sell_order = market.place_order(seller, OrderType.SELL, "coder", price=8.0)

        agents = {buyer.id: buyer, seller.id: seller}
        trade = market.execute_trade(buy_order, sell_order, agents)

        assert trade is not None
        # Trade executes at sell price (8.0)
        assert buyer.budget == pytest.approx(100.0 - 8.0)
        assert seller.budget == pytest.approx(8.0)
        assert trade.price == 8.0
        assert trade.total == 8.0

    def test_trade_updates_order_statuses(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=50.0)
        seller = _make_agent()

        buy_order = market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        sell_order = market.place_order(seller, OrderType.SELL, "coder", price=5.0)

        agents = {buyer.id: buyer, seller.id: seller}
        market.execute_trade(buy_order, sell_order, agents)

        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED

    def test_trade_records_history(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=100.0)
        seller = _make_agent()

        buy_order = market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        sell_order = market.place_order(seller, OrderType.SELL, "coder", price=7.0)

        agents = {buyer.id: buyer, seller.id: seller}
        market.execute_trade(buy_order, sell_order, agents)

        assert len(market.trade_history) == 1
        assert market.price_history["coder"] == [7.0]

    def test_trade_fails_if_buyer_broke(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=100.0)
        seller = _make_agent()

        buy_order = market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        sell_order = market.place_order(seller, OrderType.SELL, "coder", price=5.0)

        # Drain buyer's budget after placing order
        buyer.budget = 1.0

        agents = {buyer.id: buyer, seller.id: seller}
        trade = market.execute_trade(buy_order, sell_order, agents)
        assert trade is None


# ---------------------------------------------------------------------------
# Price discovery
# ---------------------------------------------------------------------------

class TestPriceDiscovery:
    def test_market_price_from_trades(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=200.0)
        seller = _make_agent()
        agents = {buyer.id: buyer, seller.id: seller}

        # Execute multiple trades
        for price in [10.0, 12.0, 11.0]:
            buy_order = market.place_order(buyer, OrderType.BUY, "coder", price=20.0)
            sell_order = market.place_order(seller, OrderType.SELL, "coder", price=price)
            market.execute_trade(buy_order, sell_order, agents)

        market_price = market.get_market_price("coder")
        assert market_price == pytest.approx(11.0)

    def test_market_price_none_before_trades(self):
        market, _ = _make_market()
        assert market.get_market_price("coder") is None

    def test_best_bid(self):
        market, _ = _make_market()
        agent1 = _make_agent(budget=200.0)
        agent2 = _make_agent(budget=200.0)

        market.place_order(agent1, OrderType.BUY, "coder", price=10.0)
        market.place_order(agent2, OrderType.BUY, "coder", price=15.0)

        assert market.get_best_bid("coder") == 15.0

    def test_best_ask(self):
        market, _ = _make_market()
        seller1 = _make_agent()
        seller2 = _make_agent()

        market.place_order(seller1, OrderType.SELL, "coder", price=8.0)
        market.place_order(seller2, OrderType.SELL, "coder", price=5.0)

        assert market.get_best_ask("coder") == 5.0

    def test_spread(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=200.0)
        seller = _make_agent()

        market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        market.place_order(seller, OrderType.SELL, "coder", price=12.0)

        assert market.get_spread("coder") == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_empty_market(self):
        market, _ = _make_market()
        stats = market.get_stats()
        assert stats["total_orders"] == 0
        assert stats["total_trades"] == 0
        assert stats["total_volume"] == 0.0

    def test_stats_after_trade(self):
        market, _ = _make_market()
        buyer = _make_agent(budget=100.0)
        seller = _make_agent()

        buy_order = market.place_order(buyer, OrderType.BUY, "coder", price=10.0)
        sell_order = market.place_order(seller, OrderType.SELL, "coder", price=8.0)
        agents = {buyer.id: buyer, seller.id: seller}
        market.execute_trade(buy_order, sell_order, agents)

        stats = market.get_stats()
        assert stats["total_trades"] == 1
        assert stats["total_volume"] == pytest.approx(8.0)
        assert stats["filled_orders"] == 2
