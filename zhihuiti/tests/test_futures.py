"""Tests for the FuturesMarket (期货/质押) module."""

from __future__ import annotations

import pytest

from zhihuiti.futures import FuturesMarket, Stake, StakeStatus, MAX_STAKE_RATIO, PAYOUT_MULTIPLIER
from zhihuiti.models import AgentState, AgentConfig, AgentRole
from zhihuiti.memory import Memory


def _make_memory() -> Memory:
    return Memory(":memory:")


def _make_agent(budget: float = 100.0) -> AgentState:
    return AgentState(
        config=AgentConfig(role=AgentRole.CODER, system_prompt=""),
        budget=budget,
    )


def _make_market() -> FuturesMarket:
    return FuturesMarket(_make_memory())


# ---------------------------------------------------------------------------
# Staking — placement validation
# ---------------------------------------------------------------------------

class TestStakePlacement:
    def test_place_stake_success(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()

        stake = market.place_stake(staker, target, amount=20.0, predicted_score_min=0.7)
        assert stake is not None
        assert stake.staker_id == staker.id
        assert stake.target_id == target.id
        assert stake.amount == 20.0
        assert stake.status == StakeStatus.ACTIVE

    def test_stake_deducts_staker_budget(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()

        market.place_stake(staker, target, amount=30.0, predicted_score_min=0.7)
        assert staker.budget == pytest.approx(70.0)

    def test_stake_exceeds_max_ratio_rejected(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()

        max_allowed = staker.budget * MAX_STAKE_RATIO  # 30.0
        stake = market.place_stake(staker, target, amount=max_allowed + 1.0)
        assert stake is None
        assert staker.budget == pytest.approx(100.0)  # not deducted

    def test_stake_zero_amount_rejected(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()
        stake = market.place_stake(staker, target, amount=0.0)
        assert stake is None

    def test_cannot_stake_on_self(self):
        market = _make_market()
        agent = _make_agent(budget=100.0)
        stake = market.place_stake(agent, agent, amount=10.0)
        assert stake is None


# ---------------------------------------------------------------------------
# Settle via evaluate_stakes
# ---------------------------------------------------------------------------

class TestEvaluateStakes:
    def test_winning_stake_pays_out(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()
        # Give target a good score history
        target.scores = [0.9, 0.8, 0.85]

        stake = market.place_stake(staker, target, amount=20.0,
                                   predicted_score_min=0.7, duration_tasks=3)
        staker_budget_after_stake = staker.budget  # 80.0

        agents = {staker.id: staker, target.id: target}
        # One call per task, pass task_counts so stake.tasks_seen increments
        settled = market.evaluate_stakes(agents, task_counts={target.id: 3})

        assert len(settled) == 1
        assert settled[0].status == StakeStatus.WON
        expected_payout = 20.0 * PAYOUT_MULTIPLIER
        assert staker.budget == pytest.approx(staker_budget_after_stake + expected_payout)

    def test_losing_stake_forfeited(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()
        # Low scores
        target.scores = [0.2, 0.15, 0.3]

        stake = market.place_stake(staker, target, amount=20.0,
                                   predicted_score_min=0.8, duration_tasks=3)
        staker_budget_after = staker.budget  # 80.0

        agents = {staker.id: staker, target.id: target}
        settled = market.evaluate_stakes(agents, task_counts={target.id: 3})

        assert len(settled) == 1
        assert settled[0].status == StakeStatus.LOST
        # No payout, budget stays same
        assert staker.budget == pytest.approx(staker_budget_after)

    def test_stake_expires_when_target_missing(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()

        stake = market.place_stake(staker, target, amount=20.0, duration_tasks=5)

        # Target removed from agents dict (culled)
        agents = {staker.id: staker}
        settled = market.evaluate_stakes(agents)

        assert len(settled) == 1
        assert settled[0].status == StakeStatus.EXPIRED

    def test_stake_not_settled_before_duration(self):
        market = _make_market()
        staker = _make_agent(budget=100.0)
        target = _make_agent()
        target.scores = [0.9]

        market.place_stake(staker, target, amount=20.0,
                           predicted_score_min=0.5, duration_tasks=5)

        agents = {staker.id: staker, target.id: target}
        # Only 2 tasks seen — not enough
        settled = market.evaluate_stakes(agents, task_counts={target.id: 2})

        assert settled == []
        assert market.stakes[0].status == StakeStatus.ACTIVE


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class TestQueries:
    def test_get_agent_stakes_placed(self):
        market = _make_market()
        staker = _make_agent(budget=200.0)
        target1 = _make_agent()
        target2 = _make_agent()

        market.place_stake(staker, target1, amount=10.0)
        market.place_stake(staker, target2, amount=15.0)

        result = market.get_agent_stakes(staker.id)
        assert len(result["placed"]) == 2
        assert len(result["received"]) == 0

    def test_get_agent_stakes_received(self):
        market = _make_market()
        staker1 = _make_agent(budget=200.0)
        staker2 = _make_agent(budget=200.0)
        target = _make_agent()

        market.place_stake(staker1, target, amount=10.0)
        market.place_stake(staker2, target, amount=15.0)

        result = market.get_agent_stakes(target.id)
        assert len(result["received"]) == 2


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_empty(self):
        market = _make_market()
        stats = market.get_stats()
        assert stats["total_stakes"] == 0
        assert stats["active"] == 0
        assert stats["total_staked"] == 0.0

    def test_stats_with_stakes(self):
        market = _make_market()
        staker = _make_agent(budget=200.0)
        target = _make_agent()

        market.place_stake(staker, target, amount=20.0)
        market.place_stake(staker, target, amount=10.0)

        stats = market.get_stats()
        assert stats["total_stakes"] == 2
        assert stats["active"] == 2
        assert stats["escrowed"] == pytest.approx(30.0)
        assert stats["total_staked"] == pytest.approx(30.0)
