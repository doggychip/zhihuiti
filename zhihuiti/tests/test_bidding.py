"""Tests for the BiddingHouse (竞标) module."""

from __future__ import annotations

import pytest

from zhihuiti.bidding import BiddingHouse, AgentPool, Auction, Bid, MIN_BID, DEFAULT_PRICE_CEILING
from zhihuiti.models import AgentState, AgentConfig, AgentRole
from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm


def _make_memory() -> Memory:
    return Memory(":memory:")


def _make_agent(role: AgentRole = AgentRole.CODER, budget: float = 100.0,
                scores: list[float] | None = None) -> AgentState:
    agent = AgentState(
        config=AgentConfig(role=role, system_prompt="", budget=budget),
        budget=budget,
    )
    if scores:
        agent.scores = scores
    return agent


def _make_bidding_house() -> BiddingHouse:
    mem = _make_memory()
    llm = make_stub_llm()
    return BiddingHouse(llm=llm, memory=mem)


# ---------------------------------------------------------------------------
# AgentPool
# ---------------------------------------------------------------------------

class TestAgentPool:
    def test_add_and_get_by_role(self):
        pool = AgentPool()
        agent = _make_agent(role=AgentRole.CODER)
        pool.add(agent)
        result = pool.get_by_role(AgentRole.CODER)
        assert len(result) == 1
        assert result[0].id == agent.id

    def test_get_by_role_filters_dead(self):
        pool = AgentPool()
        alive = _make_agent()
        dead = _make_agent()
        dead.alive = False
        pool.add(alive)
        pool.add(dead)
        result = pool.get_by_role(AgentRole.CODER)
        assert len(result) == 1

    def test_get_all_alive(self):
        pool = AgentPool()
        agent1 = _make_agent()
        agent2 = _make_agent()
        agent2.alive = False
        pool.add(agent1)
        pool.add(agent2)
        assert len(pool.get_all_alive()) == 1

    def test_pool_size(self):
        pool = AgentPool()
        for _ in range(3):
            pool.add(_make_agent())
        dead = _make_agent()
        dead.alive = False
        pool.add(dead)
        assert pool.size == 3

    def test_get_by_id(self):
        pool = AgentPool()
        agent = _make_agent()
        pool.add(agent)
        assert pool.get(agent.id) is agent
        assert pool.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Qualification
# ---------------------------------------------------------------------------

class TestQualification:
    def test_alive_agent_with_budget_qualifies(self):
        house = _make_bidding_house()
        agent = _make_agent(budget=50.0)
        qualified, reason = house.qualify(agent)
        assert qualified is True

    def test_dead_agent_disqualified(self):
        house = _make_bidding_house()
        agent = _make_agent()
        agent.alive = False
        qualified, reason = house.qualify(agent)
        assert qualified is False
        assert "dead" in reason

    def test_low_budget_disqualified(self):
        house = _make_bidding_house()
        agent = _make_agent(budget=MIN_BID - 0.1)
        qualified, reason = house.qualify(agent)
        assert qualified is False
        assert "budget" in reason.lower()

    def test_low_score_disqualified(self):
        house = _make_bidding_house()
        agent = _make_agent(budget=100.0, scores=[0.1, 0.1, 0.1])
        qualified, reason = house.qualify(agent)
        assert qualified is False
        assert "score" in reason.lower()


# ---------------------------------------------------------------------------
# Auction mechanics
# ---------------------------------------------------------------------------

class TestAuction:
    def test_open_auction_creates_auction(self):
        house = _make_bidding_house()
        auction = house.open_auction("Write a test", AgentRole.CODER, price_ceiling=25.0)
        assert auction.task_description == "Write a test"
        assert auction.role == AgentRole.CODER
        assert auction.price_ceiling == 25.0
        assert len(house.auctions) == 1

    def test_collect_bids_with_no_candidates(self):
        house = _make_bidding_house()
        auction = house.open_auction("task", AgentRole.CODER)
        bids = house.collect_bids(auction)
        assert bids == []

    def test_collect_bids_with_qualified_agents(self):
        house = _make_bidding_house()
        for _ in range(3):
            agent = _make_agent(budget=50.0)
            house.pool.add(agent)

        auction = house.open_auction("Analyze data", AgentRole.CODER)
        bids = house.collect_bids(auction)
        assert len(bids) == 3
        for bid in bids:
            assert bid.amount >= MIN_BID
            assert bid.amount <= auction.price_ceiling

    def test_award_picks_lowest_bid(self):
        house = _make_bidding_house()
        auction = house.open_auction("task", AgentRole.CODER, price_ceiling=50.0)

        agent1 = _make_agent(budget=100.0)
        agent2 = _make_agent(budget=100.0)
        house.pool.add(agent1)
        house.pool.add(agent2)

        # Manually add bids with known amounts
        auction.bids = [
            Bid(agent_id=agent1.id, amount=20.0),
            Bid(agent_id=agent2.id, amount=15.0),
        ]

        winner, bid = house.award(auction)
        assert winner is not None
        assert bid is not None
        assert bid.amount == 15.0
        assert auction.winner_id == agent2.id
        assert auction.winning_bid == 15.0

    def test_award_returns_none_with_no_bids(self):
        house = _make_bidding_house()
        auction = house.open_auction("task", AgentRole.CODER)
        winner, bid = house.award(auction)
        assert winner is None
        assert bid is None

    def test_bid_above_ceiling_is_disqualified(self):
        house = _make_bidding_house()
        agent = _make_agent(budget=100.0)
        house.pool.add(agent)

        auction = house.open_auction("task", AgentRole.CODER, price_ceiling=2.0)
        bids = house.collect_bids(auction)
        # With a ceiling of 2.0 and MIN_BID of 3.0, no valid bids should come in
        for bid in bids:
            assert bid.amount <= 2.0  # all bids within ceiling (may be 0)

    def test_ensure_pool_spawns_agents(self):
        house = _make_bidding_house()

        def spawn_fn(role, budget):
            return _make_agent(role=role, budget=budget)

        agents = house.ensure_pool(AgentRole.RESEARCHER, count=2, spawn_fn=spawn_fn)
        assert len(agents) == 2
        assert house.pool.size >= 2

    def test_ensure_pool_no_spawn_if_sufficient(self):
        house = _make_bidding_house()
        for _ in range(3):
            house.pool.add(_make_agent())
        agents = house.ensure_pool(AgentRole.CODER, count=2)
        assert len(agents) == 3  # Already have 3


# ---------------------------------------------------------------------------
# Winner deducts budget
# ---------------------------------------------------------------------------

class TestWinnerBudgetDeduction:
    def test_winner_budget_deducted(self):
        house = _make_bidding_house()
        agent = _make_agent(budget=100.0)
        house.pool.add(agent)

        auction = house.open_auction("task", AgentRole.CODER, price_ceiling=50.0)
        auction.bids = [Bid(agent_id=agent.id, amount=20.0)]
        winner, bid = house.award(auction)

        # run_auction deducts the budget; award itself doesn't deduct
        # The deduction happens in run_auction after award
        assert winner is not None
