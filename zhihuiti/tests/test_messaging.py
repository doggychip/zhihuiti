"""Tests for agent-to-agent messaging and cross-goal memory."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from zhihuiti.memory import Memory
from zhihuiti.messaging import MessageBoard
from zhihuiti.models import AgentConfig, AgentRole, AgentState
from tests.conftest import make_stub_llm

INSPECTION_PASS = {"score": 0.8, "reasoning": "good", "pass": True}


def _make_agent(role=AgentRole.RESEARCHER, agent_id=None) -> AgentState:
    agent = AgentState(
        config=AgentConfig(role=role, system_prompt=""),
        budget=100.0,
    )
    if agent_id:
        agent.id = agent_id
    return agent


# ---------------------------------------------------------------------------
# MessageBoard
# ---------------------------------------------------------------------------

class TestMessageBoard:
    def test_broadcast_saves_message(self):
        mem = Memory(":memory:")
        board = MessageBoard(mem)
        agent = _make_agent(agent_id="sender-1")
        board.broadcast(agent, "Here are my findings on topic X", goal_id="goal-1")
        msgs = mem.get_unread_messages(goal_id="goal-1")
        assert len(msgs) == 1
        assert msgs[0]["sender_id"] == "sender-1"
        assert "findings" in msgs[0]["content"]

    def test_send_direct_message(self):
        mem = Memory(":memory:")
        board = MessageBoard(mem)
        sender = _make_agent(agent_id="sender-2")
        board.send(sender, receiver_id="recv-1", content="check this out", goal_id="goal-2")
        msgs = mem.get_unread_messages(receiver_id="recv-1")
        assert len(msgs) == 1

    def test_collect_context_returns_messages(self):
        mem = Memory(":memory:")
        board = MessageBoard(mem)
        sender = _make_agent(agent_id="sender-3")
        receiver = _make_agent(agent_id="recv-3")

        board.broadcast(sender, "Important finding: X is Y", goal_id="goal-3")
        ctx = board.collect_context(receiver, goal_id="goal-3")
        assert "Findings from collaborating agents" in ctx
        assert "Important finding" in ctx

    def test_collect_context_excludes_own_messages(self):
        mem = Memory(":memory:")
        board = MessageBoard(mem)
        agent = _make_agent(agent_id="self-sender")

        board.broadcast(agent, "my own output", goal_id="goal-4")
        ctx = board.collect_context(agent, goal_id="goal-4")
        assert ctx == ""  # should not see own messages

    def test_collect_context_marks_as_read(self):
        mem = Memory(":memory:")
        board = MessageBoard(mem)
        sender = _make_agent(agent_id="sender-5")
        receiver = _make_agent(agent_id="recv-5")

        board.broadcast(sender, "data point A", goal_id="goal-5")
        board.collect_context(receiver, goal_id="goal-5")

        # Second call should return empty (already read)
        ctx = board.collect_context(receiver, goal_id="goal-5")
        assert ctx == ""

    def test_multiple_broadcasts_collected(self):
        mem = Memory(":memory:")
        board = MessageBoard(mem)
        a1 = _make_agent(agent_id="agent-a")
        a2 = _make_agent(agent_id="agent-b")
        receiver = _make_agent(agent_id="agent-c")

        board.broadcast(a1, "finding alpha", goal_id="goal-6")
        board.broadcast(a2, "finding beta", goal_id="goal-6")

        ctx = board.collect_context(receiver, goal_id="goal-6")
        assert "alpha" in ctx
        assert "beta" in ctx


# ---------------------------------------------------------------------------
# Cross-goal memory (goal_history)
# ---------------------------------------------------------------------------

class TestCrossGoalMemory:
    def test_save_and_retrieve_goal(self):
        mem = Memory(":memory:")
        mem.save_goal("g1", "research AI safety", 3, 0.85, "summary here")
        goals = mem.get_recent_goals(limit=5)
        assert len(goals) == 1
        assert goals[0]["goal"] == "research AI safety"

    def test_search_similar_goals(self):
        mem = Memory(":memory:")
        mem.save_goal("g1", "research AI safety", 3, 0.85, "s1")
        mem.save_goal("g2", "research quantum computing", 2, 0.7, "s2")
        mem.save_goal("g3", "build a website", 4, 0.6, "s3")

        results = mem.get_similar_goals("research")
        assert len(results) == 2

    def test_no_match_returns_empty(self):
        mem = Memory(":memory:")
        mem.save_goal("g1", "research AI", 3, 0.85, "s")
        results = mem.get_similar_goals("cooking")
        assert len(results) == 0

    def test_goal_saved_after_execute(self):
        """execute_goal should save to goal_history."""
        def _make_orchestrator():
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
            from zhihuiti.messaging import MessageBoard

            mem = Memory(":memory:")
            call_count = [0]

            def chat_json_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return [{"description": "do thing", "role": "researcher"}]
                return INSPECTION_PASS

            stub = MagicMock()
            stub.chat_json.side_effect = chat_json_side_effect
            stub.chat.return_value = "output"

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
            orch.messages = MessageBoard(mem)
            from zhihuiti.metacognition import MetacognitionEngine
            from zhihuiti.consolidation import ConsolidationEngine
            from zhihuiti.prediction import PredictionEngine
            from zhihuiti.causal import CausalGraph
            orch.causal_graph = CausalGraph()
            orch.metacognition = MetacognitionEngine(mem)
            orch.consolidation = ConsolidationEngine(mem)
            orch.prediction = PredictionEngine(mem, causal_graph=orch.causal_graph)
            orch.tasks = {}
            orch.max_workers = 4
            orch.max_retries = 0
            orch.tools_enabled = False

            for agent in orch.bidding.pool.get_all_alive():
                if agent.id not in orch.agent_manager.agents:
                    orch.agent_manager.agents[agent.id] = agent

            orch.realm_manager.allocate_budgets(orch.economy.treasury.balance * 0.5)
            return orch, mem

        orch, mem = _make_orchestrator()
        orch.execute_goal("test goal for history")

        goals = mem.get_recent_goals()
        assert len(goals) == 1
        assert goals[0]["goal"] == "test goal for history"
        assert goals[0]["task_count"] == 1
        assert goals[0]["avg_score"] > 0


# ---------------------------------------------------------------------------
# Integration: messaging + DAG in execute_goal
# ---------------------------------------------------------------------------

class TestMessagingIntegration:
    def test_broadcast_happens_during_execute(self):
        """After task execution, agent should broadcast its output."""
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
        from zhihuiti.messaging import MessageBoard

        mem = Memory(":memory:")
        call_count = [0]

        def chat_json_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [
                    {"id": "a", "description": "task A", "role": "researcher", "depends_on": []},
                    {"id": "b", "description": "task B", "role": "analyst", "depends_on": ["a"]},
                ]
            return INSPECTION_PASS

        stub = MagicMock()
        stub.chat_json.side_effect = chat_json_side_effect
        stub.chat.return_value = "research findings here"

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
        orch.messages = MessageBoard(mem)
        from zhihuiti.metacognition import MetacognitionEngine
        from zhihuiti.consolidation import ConsolidationEngine
        from zhihuiti.prediction import PredictionEngine
        from zhihuiti.causal import CausalGraph
        orch.causal_graph = CausalGraph()
        orch.metacognition = MetacognitionEngine(mem)
        orch.consolidation = ConsolidationEngine(mem)
        orch.prediction = PredictionEngine(mem, causal_graph=orch.causal_graph)
        orch.tasks = {}
        orch.max_workers = 4
        orch.max_retries = 0
        orch.tools_enabled = False

        for agent in orch.bidding.pool.get_all_alive():
            if agent.id not in orch.agent_manager.agents:
                orch.agent_manager.agents[agent.id] = agent

        orch.realm_manager.allocate_budgets(orch.economy.treasury.balance * 0.5)

        orch.execute_goal("two step goal")

        # Messages should have been broadcast
        all_msgs = mem._query("SELECT * FROM messages")
        assert len(all_msgs) >= 2  # at least one per task
