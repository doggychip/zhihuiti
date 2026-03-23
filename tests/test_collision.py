"""Tests for Theory Collision Engine."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from zhihuiti.collision import CollisionEngine, CollisionResult, THEORIES
from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm

INSPECTION_PASS = {"score": 0.8, "reasoning": "good", "pass": True}


def _make_orchestrator(theory_config):
    """Build a test orchestrator with the given theory config."""
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
    from zhihuiti import judge as judge_mod

    judge_mod.CULL_THRESHOLD = theory_config["cull_threshold"]
    judge_mod.PROMOTE_THRESHOLD = theory_config["promote_threshold"]

    call_count = [0]

    def chat_json_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return [{"description": "task", "role": "researcher"}]
        return INSPECTION_PASS

    stub = MagicMock()
    stub.chat_json.side_effect = chat_json_side_effect
    stub.chat.return_value = "output"
    stub.premium_model = "llama3.1"

    mem = Memory(":memory:")
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
    orch.tasks = {}
    orch.max_workers = 4
    orch.max_retries = 0
    orch.tools_enabled = False

    for agent in orch.bidding.pool.get_all_alive():
        if agent.id not in orch.agent_manager.agents:
            orch.agent_manager.agents[agent.id] = agent

    orch.realm_manager.allocate_budgets(orch.economy.treasury.balance * 0.5)
    return orch


class TestTheories:
    def test_all_theories_have_required_keys(self):
        for name, config in THEORIES.items():
            assert "label" in config
            assert "description" in config
            assert "cull_threshold" in config
            assert "promote_threshold" in config
            assert "messaging" in config
            assert "lending" in config

    def test_darwinian_has_high_cull(self):
        assert THEORIES["darwinian"]["cull_threshold"] > THEORIES["mutualist"]["cull_threshold"]

    def test_mutualist_has_messaging(self):
        assert THEORIES["mutualist"]["messaging"] is True
        assert THEORIES["darwinian"]["messaging"] is False


class TestCollisionResult:
    def test_score_calculation(self):
        result = CollisionResult(
            theory_a="darwinian",
            theory_b="mutualist",
            result_a={"tasks": [{"score": 0.8}, {"score": 0.9}]},
            result_b={"tasks": [{"score": 0.7}, {"score": 0.6}]},
        )
        assert result.score_a == pytest.approx(0.85)
        assert result.score_b == pytest.approx(0.65)

    def test_winner_a(self):
        result = CollisionResult(
            theory_a="darwinian",
            theory_b="mutualist",
            result_a={"tasks": [{"score": 0.9}]},
            result_b={"tasks": [{"score": 0.5}]},
        )
        assert result.winner == "darwinian"

    def test_winner_tie(self):
        result = CollisionResult(
            theory_a="darwinian",
            theory_b="mutualist",
            result_a={"tasks": [{"score": 0.8}]},
            result_b={"tasks": [{"score": 0.805}]},
        )
        assert result.winner == "tie"

    def test_to_dict(self):
        result = CollisionResult(
            goal="test goal",
            theory_a="darwinian",
            theory_b="mutualist",
            result_a={"tasks": [{"score": 0.8}]},
            result_b={"tasks": [{"score": 0.7}]},
        )
        d = result.to_dict()
        assert d["goal"] == "test goal"
        assert d["winner"] == "darwinian"
        assert d["score_a"] > d["score_b"]


class TestCollisionEngine:
    def test_collide_runs_both_theories(self):
        engine = CollisionEngine()
        result = engine.collide(
            goal="test collision",
            theory_a="darwinian",
            theory_b="mutualist",
            orchestrator_factory=_make_orchestrator,
        )
        assert result.theory_a == "darwinian"
        assert result.theory_b == "mutualist"
        assert len(result.result_a.get("tasks", [])) >= 1
        assert len(result.result_b.get("tasks", [])) >= 1

    def test_collide_records_history(self):
        engine = CollisionEngine()
        engine.collide("goal 1", "darwinian", "mutualist", _make_orchestrator)
        engine.collide("goal 2", "hybrid", "elitist", _make_orchestrator)
        assert len(engine.history) == 2

    def test_invalid_theory_raises(self):
        engine = CollisionEngine()
        with pytest.raises(ValueError, match="Unknown theory"):
            engine.collide("goal", "nonexistent", "mutualist", _make_orchestrator)
