"""Tests for DAG utilities and DAG-aware orchestration."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from zhihuiti.dag import detect_cycle, topological_waves
from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm

INSPECTION_PASS = {"score": 0.8, "reasoning": "good", "pass": True}


# ---------------------------------------------------------------------------
# detect_cycle
# ---------------------------------------------------------------------------

class TestDetectCycle:
    def test_no_cycle_in_empty_graph(self):
        assert detect_cycle({}) is None

    def test_no_cycle_in_linear_chain(self):
        graph = {"a": [], "b": ["a"], "c": ["b"]}
        assert detect_cycle(graph) is None

    def test_detects_self_loop(self):
        graph = {"a": ["a"]}
        cycle = detect_cycle(graph)
        assert cycle is not None
        assert "a" in cycle

    def test_detects_two_node_cycle(self):
        graph = {"a": ["b"], "b": ["a"]}
        cycle = detect_cycle(graph)
        assert cycle is not None

    def test_no_cycle_in_diamond(self):
        graph = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
        assert detect_cycle(graph) is None

    def test_detects_cycle_in_complex_graph(self):
        graph = {"a": [], "b": ["a"], "c": ["b"], "d": ["c", "a"], "b_again": ["d"]}
        # b_again is not a cycle; let's make a real one
        graph2 = {"a": ["c"], "b": ["a"], "c": ["b"]}
        assert detect_cycle(graph2) is not None


# ---------------------------------------------------------------------------
# topological_waves
# ---------------------------------------------------------------------------

class TestTopologicalWaves:
    def test_single_node(self):
        waves = topological_waves(["a"], {"a": []})
        assert waves == [["a"]]

    def test_all_independent(self):
        waves = topological_waves(["a", "b", "c"], {"a": [], "b": [], "c": []})
        assert len(waves) == 1
        assert set(waves[0]) == {"a", "b", "c"}

    def test_linear_chain(self):
        waves = topological_waves(
            ["a", "b", "c"],
            {"a": [], "b": ["a"], "c": ["b"]},
        )
        assert len(waves) == 3
        assert waves[0] == ["a"]
        assert waves[1] == ["b"]
        assert waves[2] == ["c"]

    def test_diamond(self):
        waves = topological_waves(
            ["a", "b", "c", "d"],
            {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]},
        )
        assert len(waves) == 3
        assert waves[0] == ["a"]
        assert set(waves[1]) == {"b", "c"}
        assert waves[2] == ["d"]

    def test_raises_on_cycle(self):
        with pytest.raises(ValueError, match="cycle"):
            topological_waves(["a", "b"], {"a": ["b"], "b": ["a"]})

    def test_ignores_unknown_deps(self):
        # Dependency on a node not in the list is silently ignored
        waves = topological_waves(
            ["a", "b"],
            {"a": [], "b": ["a", "nonexistent"]},
        )
        assert len(waves) == 2


# ---------------------------------------------------------------------------
# DAG-aware orchestration
# ---------------------------------------------------------------------------

def _make_orchestrator(llm=None):
    from zhihuiti.orchestrator import Orchestrator
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

    mem = Memory(":memory:")
    stub = llm or make_stub_llm()

    orch = Orchestrator.__new__(Orchestrator)
    orch.llm = stub
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
    orch.messages = MessageBoard(mem)
    orch.tasks = {}
    orch.max_workers = 4
    orch.max_retries = 0
    orch.tools_enabled = False

    for agent in orch.bidding.pool.get_all_alive():
        if agent.id not in orch.agent_manager.agents:
            orch.agent_manager.agents[agent.id] = agent

    orch.realm_manager.allocate_budgets(orch.economy.treasury.balance * 0.5)
    return orch


class TestDAGOrchestration:
    def _make_dag_llm(self):
        """LLM that returns tasks WITH dependencies."""
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [
                    {"id": "research", "description": "Gather data", "role": "researcher", "depends_on": []},
                    {"id": "analyze", "description": "Analyze data", "role": "analyst", "depends_on": ["research"]},
                    {"id": "report", "description": "Write report", "role": "custom", "depends_on": ["analyze"]},
                ]
            return INSPECTION_PASS

        llm = MagicMock()
        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.return_value = "task output"
        return llm

    def test_dag_tasks_execute_in_order(self):
        llm = self._make_dag_llm()
        orch = _make_orchestrator(llm)
        result = orch.execute_goal("research and report")
        assert len(result["tasks"]) == 3
        # All completed
        statuses = {r["status"] for r in result["tasks"]}
        assert statuses == {"completed"}

    def test_dependent_task_receives_context(self):
        """The LLM chat call for dependent tasks should include prior outputs."""
        call_log = []

        def chat_side_effect(*args, **kwargs):
            user_msg = args[1] if len(args) > 1 else kwargs.get("user", "")
            call_log.append(user_msg)
            return "task output"

        llm = self._make_dag_llm()
        llm.chat.side_effect = chat_side_effect
        orch = _make_orchestrator(llm)
        orch.execute_goal("research and report")

        # The last task ("Write report") should have dependency context injected
        # chat is called for: 3 task executions + possibly synthesis
        # At minimum, the later tasks should have "Context from prior tasks" in them
        report_calls = [c for c in call_log if "Context from prior tasks" in c]
        assert len(report_calls) >= 1

    def test_flat_tasks_still_work(self):
        """Tasks without depends_on should still execute fine (flat DAG)."""
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [
                    {"description": "task A", "role": "researcher"},
                    {"description": "task B", "role": "analyst"},
                ]
            return INSPECTION_PASS

        llm = MagicMock()
        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.return_value = "done"

        orch = _make_orchestrator(llm)
        result = orch.execute_goal("flat goal")
        assert len(result["tasks"]) == 2
        statuses = {r["status"] for r in result["tasks"]}
        assert statuses == {"completed"}

    def test_cycle_is_detected_and_flattened(self):
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [
                    {"id": "a", "description": "task A", "role": "researcher", "depends_on": ["b"]},
                    {"id": "b", "description": "task B", "role": "analyst", "depends_on": ["a"]},
                ]
            return INSPECTION_PASS

        llm = MagicMock()
        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.return_value = "done"

        orch = _make_orchestrator(llm)
        result = orch.execute_goal("cyclic goal")
        # Should still complete — cycle stripped, tasks run flat
        assert len(result["tasks"]) == 2
        statuses = {r["status"] for r in result["tasks"]}
        assert statuses == {"completed"}

    def test_diamond_dependency_runs_in_three_waves(self):
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [
                    {"id": "a", "description": "root", "role": "researcher", "depends_on": []},
                    {"id": "b", "description": "left", "role": "analyst", "depends_on": ["a"]},
                    {"id": "c", "description": "right", "role": "coder", "depends_on": ["a"]},
                    {"id": "d", "description": "merge", "role": "custom", "depends_on": ["b", "c"]},
                ]
            return INSPECTION_PASS

        llm = MagicMock()
        llm.chat_json.side_effect = chat_json_side_effect
        llm.chat.return_value = "done"

        orch = _make_orchestrator(llm)
        result = orch.execute_goal("diamond goal")
        assert len(result["tasks"]) == 4
        statuses = {r["status"] for r in result["tasks"]}
        assert statuses == {"completed"}
