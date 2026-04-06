"""Tests for persistent agent pool — agents survive across Orchestrator sessions."""

from __future__ import annotations

import pytest

from zhihuiti.agents import AgentManager
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState
from tests.conftest import make_stub_llm


def _make_memory() -> Memory:
    return Memory(":memory:")


def _make_manager(memory: Memory | None = None) -> AgentManager:
    mem = memory or _make_memory()
    return AgentManager(llm=make_stub_llm(), memory=mem)


# ---------------------------------------------------------------------------
# checkpoint_agent
# ---------------------------------------------------------------------------

class TestCheckpointAgent:
    def test_checkpoint_writes_budget_to_db(self):
        mem = _make_memory()
        mgr = _make_manager(mem)

        agent = AgentState(
            config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt=""),
            budget=100.0,
        )
        mgr.agents[agent.id] = agent

        # Simulate earning a reward
        agent.budget = 133.7
        agent.scores.append(0.85)
        mgr.checkpoint_agent(agent)

        row = mem.conn.execute(
            "SELECT budget, avg_score, alive FROM agents WHERE id = ?",
            (agent.id,),
        ).fetchone()

        assert row is not None
        assert row["budget"] == pytest.approx(133.7)
        assert row["alive"] == 1

    def test_checkpoint_updates_avg_score(self):
        mem = _make_memory()
        mgr = _make_manager(mem)

        # First save at spawn with default 0.5
        agent = AgentState(
            config=AgentConfig(role=AgentRole.ANALYST, system_prompt=""),
            budget=100.0,
        )
        mem.save_agent(
            agent_id=agent.id, role="analyst", budget=100.0,
            depth=0, avg_score=0.5, alive=True,
        )

        agent.scores = [0.9, 0.85]
        mgr.checkpoint_agent(agent)

        row = mem.conn.execute(
            "SELECT avg_score FROM agents WHERE id = ?", (agent.id,)
        ).fetchone()
        assert row["avg_score"] == pytest.approx(agent.avg_score, abs=0.01)

    def test_checkpoint_marks_dead_agent(self):
        mem = _make_memory()
        mgr = _make_manager(mem)

        agent = AgentState(
            config=AgentConfig(role=AgentRole.CUSTOM, system_prompt=""),
            budget=0.0,
        )
        agent.alive = False
        mgr.checkpoint_agent(agent)

        row = mem.conn.execute(
            "SELECT alive FROM agents WHERE id = ?", (agent.id,)
        ).fetchone()
        assert row["alive"] == 0


# ---------------------------------------------------------------------------
# Pool restoration — agents from DB loaded into bidding pool on startup
# ---------------------------------------------------------------------------

class TestPoolRestoration:
    def test_alive_agents_restored_from_db(self):
        from zhihuiti.bidding import BiddingHouse

        mem = _make_memory()
        # Manually insert an alive agent record into DB
        mem.save_agent(
            agent_id="test-agent-abc",
            role="researcher",
            budget=75.0,
            depth=0,
            avg_score=0.82,
            alive=True,
        )

        bh = BiddingHouse(llm=make_stub_llm(), memory=mem)
        pool_ids = [a.id for a in bh.pool.get_all_alive()]
        assert "test-agent-abc" in pool_ids

    def test_dead_agents_not_restored(self):
        from zhihuiti.bidding import BiddingHouse

        mem = _make_memory()
        mem.save_agent(
            agent_id="dead-agent-xyz",
            role="analyst",
            budget=0.0,
            depth=0,
            avg_score=0.3,
            alive=False,
        )

        bh = BiddingHouse(llm=make_stub_llm(), memory=mem)
        pool_ids = [a.id for a in bh.pool.get_all_alive()]
        assert "dead-agent-xyz" not in pool_ids

    def test_restored_agent_has_correct_budget(self):
        from zhihuiti.bidding import BiddingHouse

        mem = _make_memory()
        mem.save_agent(
            agent_id="funded-agent-999",
            role="coder",
            budget=142.5,
            depth=0,
            avg_score=0.9,
            alive=True,
        )

        bh = BiddingHouse(llm=make_stub_llm(), memory=mem)
        agent = bh.pool.get("funded-agent-999")
        assert agent is not None
        assert agent.budget == pytest.approx(142.5)


# ---------------------------------------------------------------------------
# Orchestrator startup syncs pool → agent_manager
# ---------------------------------------------------------------------------

class TestOrchestratorStartupSync:
    def test_prior_session_agents_in_agent_manager(self):
        """Agents saved to DB in a prior session appear in agent_manager on next startup."""
        from zhihuiti.agents import AgentManager
        from zhihuiti.bidding import BiddingHouse
        from zhihuiti.economy import Economy
        from zhihuiti.bloodline import Bloodline
        from zhihuiti.realms import RealmManager

        mem = _make_memory()
        llm = make_stub_llm()

        # Simulate prior session: agent saved with good budget
        mem.save_agent(
            agent_id="prior-session-agent",
            role="researcher",
            budget=88.0,
            depth=0,
            avg_score=0.8,
            alive=True,
        )

        # Build the sub-systems as Orchestrator.__init__ does
        economy = Economy(mem)
        bloodline = Bloodline(mem)
        realm_manager = RealmManager(mem)
        agent_manager = AgentManager(llm, mem, economy, bloodline, realm_manager)
        bidding = BiddingHouse(llm, mem, economy)

        # Simulate the sync loop from Orchestrator.__init__
        for agent in bidding.pool.get_all_alive():
            if agent.id not in agent_manager.agents:
                agent_manager.agents[agent.id] = agent

        assert "prior-session-agent" in agent_manager.agents
        restored = agent_manager.agents["prior-session-agent"]
        assert restored.budget == pytest.approx(88.0)
