"""Tests for Orchestrator — goal decomposition and execution pipeline."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from zhihuiti.memory import Memory
from zhihuiti.models import TaskStatus
from tests.conftest import make_stub_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INSPECTION_PASS = {"score": 0.8, "reasoning": "good", "pass": True}
SUBTASK_LIST = [
    {"description": "Research the topic", "role": "researcher"},
    {"description": "Summarize findings", "role": "analyst"},
]


def _make_orchestrator(llm=None):
    """Build an Orchestrator backed by in-memory SQLite and a stub LLM."""
    from zhihuiti.orchestrator import Orchestrator

    mem = Memory(":memory:")

    # Patch Orchestrator to inject our in-memory DB and stub LLM
    orch = Orchestrator.__new__(Orchestrator)

    stub = llm or make_stub_llm()
    orch.llm = stub

    from zhihuiti.economy import Economy
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.realms import RealmManager
    from zhihuiti.agents import AgentManager
    from zhihuiti.judge import Judge
    from zhihuiti.circuit_breaker import CircuitBreaker
    from zhihuiti.behavior import BehaviorDetector
    from zhihuiti.relationships import LendingSystem, RelationshipGraph
    from zhihuiti.arbitration import ArbitrationBureau
    from zhihuiti.market import TradingMarket
    from zhihuiti.futures import FuturesMarket
    from zhihuiti.factory import Factory
    from zhihuiti.bidding import BiddingHouse

    orch.memory = mem
    orch.economy = Economy(mem)
    orch.bloodline = Bloodline(mem)
    orch.realm_manager = RealmManager(mem)
    orch.agent_manager = AgentManager(stub, mem, orch.economy, orch.bloodline, orch.realm_manager)
    orch.judge = Judge(stub, mem, orch.agent_manager)
    orch.circuit_breaker = CircuitBreaker(mem, interactive=False)
    orch.behavior = BehaviorDetector(mem, stub)
    orch.rel_graph = RelationshipGraph(mem)
    orch.lending = LendingSystem(mem, orch.rel_graph)
    orch.arbitration = ArbitrationBureau(mem)
    orch.market = TradingMarket(mem)
    orch.futures = FuturesMarket(mem)
    orch.factory = Factory(llm=stub, memory=mem)
    orch.bidding = BiddingHouse(stub, mem, orch.economy)
    from zhihuiti.messaging import MessageBoard
    from zhihuiti.metacognition import MetacognitionEngine
    from zhihuiti.consolidation import ConsolidationEngine
    from zhihuiti.prediction import PredictionEngine
    from zhihuiti.causal import CausalGraph
    orch.messages = MessageBoard(mem)
    orch.causal_graph = CausalGraph()
    orch.metacognition = MetacognitionEngine(mem)
    orch.consolidation = ConsolidationEngine(mem)
    orch.prediction = PredictionEngine(mem, causal_graph=orch.causal_graph)
    orch.tasks = {}
    orch.max_workers = 4
    orch.max_retries = 0
    orch.tools_enabled = False

    # Sync pool → agent_manager (mirrors Orchestrator.__init__)
    for agent in orch.bidding.pool.get_all_alive():
        if agent.id not in orch.agent_manager.agents:
            orch.agent_manager.agents[agent.id] = agent

    orch.realm_manager.allocate_budgets(orch.economy.treasury.balance * 0.5)

    return orch


def _inspection_side_effect(*args, **kwargs):
    """chat_json always returns a passing inspection score."""
    return INSPECTION_PASS


# ---------------------------------------------------------------------------
# decompose_goal
# ---------------------------------------------------------------------------

class TestDecomposeGoal:
    def test_returns_tasks(self):
        orch = _make_orchestrator()
        orch.llm.chat_json.return_value = SUBTASK_LIST
        tasks = orch.decompose_goal("research and summarize topic X")
        assert len(tasks) == 2

    def test_task_descriptions_match(self):
        orch = _make_orchestrator()
        orch.llm.chat_json.return_value = SUBTASK_LIST
        tasks = orch.decompose_goal("goal")
        descriptions = [t.description for t in tasks]
        assert "Research the topic" in descriptions
        assert "Summarize findings" in descriptions

    def test_tasks_registered_in_orch(self):
        orch = _make_orchestrator()
        orch.llm.chat_json.return_value = SUBTASK_LIST
        tasks = orch.decompose_goal("goal")
        for t in tasks:
            assert t.id in orch.tasks

    def test_single_dict_wrapped_in_list(self):
        """LLM returning a single dict (not list) is handled gracefully."""
        orch = _make_orchestrator()
        orch.llm.chat_json.return_value = {"description": "single task", "role": "researcher"}
        tasks = orch.decompose_goal("goal")
        assert len(tasks) == 1

    def test_metadata_stores_role(self):
        orch = _make_orchestrator()
        orch.llm.chat_json.return_value = [{"description": "t", "role": "analyst"}]
        tasks = orch.decompose_goal("goal")
        assert tasks[0].metadata["requested_role"] == "analyst"


# ---------------------------------------------------------------------------
# execute_goal — full pipeline
# ---------------------------------------------------------------------------

class TestExecuteGoal:
    def _make_llm_for_execute(self, task_output: str = "task completed") -> MagicMock:
        """LLM stub that handles all call patterns in execute_goal."""
        llm = MagicMock()
        # chat_json: decompose returns subtask list; inspection layers return pass scores
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            # First call is goal decomposition
            if call_count[0] == 1:
                return [{"description": "do the thing", "role": "researcher"}]
            # All subsequent calls are inspection layers
            return INSPECTION_PASS

        llm.chat_json.side_effect = chat_json_side_effect
        # chat() is called for actual task execution and bidding
        llm.chat.return_value = task_output
        return llm

    def test_execute_returns_dict_with_goal(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        assert result["goal"] == "do something"

    def test_execute_returns_tasks_list(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        assert isinstance(result["tasks"], list)
        assert len(result["tasks"]) >= 1

    def test_execute_task_status_completed(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        assert result["tasks"][0]["status"] == "completed"

    def test_execute_includes_score(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        score = result["tasks"][0]["score"]
        assert 0.0 <= score <= 1.0

    def test_execute_includes_economy_report(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        assert "money_supply" in result["economy"]

    def test_execute_includes_memory_stats(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        assert "total_tasks" in result["stats"]

    def test_reward_paid_to_agent(self):
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")
        reward = result["tasks"][0]["reward"]
        # Score of 0.8 → reward should be paid
        assert reward["paid"] is True
        assert reward["net"] > 0

    def test_multiple_tasks_all_run(self):
        llm = MagicMock()
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [
                    {"description": "task one", "role": "researcher"},
                    {"description": "task two", "role": "analyst"},
                ]
            return INSPECTION_PASS

        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.return_value = "output"

        orch = _make_orchestrator(llm)
        result = orch.execute_goal("two tasks goal")
        assert len(result["tasks"]) == 2
        statuses = {r["status"] for r in result["tasks"]}
        assert statuses == {"completed"}

    def test_agent_checkpointed_after_reward(self):
        """After execute_goal, winning agent's budget is saved to DB."""
        llm = self._make_llm_for_execute()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("do something")

        agent_id = result["tasks"][0]["agent_id"]
        row = orch.memory.conn.execute(
            "SELECT budget FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
        assert row is not None
        # Budget in DB should reflect the reward paid
        agent = orch.agent_manager.agents.get(agent_id)
        if agent:
            assert row["budget"] == pytest.approx(agent.budget, abs=0.1)


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_does_not_raise(self):
        orch = _make_orchestrator()
        orch.close()  # Should not raise
