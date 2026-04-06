"""Tests for Prediction Error Engine."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from zhihuiti.prediction import (
    Prediction,
    PredictionEngine,
    SURPRISE_THRESHOLD,
)
from zhihuiti.causal import CausalGraph
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, Task


@pytest.fixture
def mem():
    return Memory(":memory:")


@pytest.fixture
def causal_graph():
    return CausalGraph()


@pytest.fixture
def engine(mem, causal_graph):
    return PredictionEngine(mem, causal_graph=causal_graph)


def _make_agent(role: str = "researcher", avg_score: float = 0.7) -> AgentState:
    agent = AgentState(
        id="agent_test",
        config=AgentConfig(role=AgentRole(role), system_prompt="test"),
        budget=100.0,
    )
    if avg_score != 0.5:  # 0.5 is default when no scores
        agent.scores = [avg_score]
    return agent


def _make_task(desc: str = "test task") -> Task:
    return Task(description=desc)


class TestPrediction:
    def test_prediction_defaults(self):
        p = Prediction()
        assert not p.is_resolved
        assert p.surprise == 0.0
        assert not p.is_surprising

    def test_prediction_resolved(self):
        p = Prediction(predicted_score=0.7)
        p.actual_score = 0.3
        p.prediction_error = -0.4
        assert p.is_resolved
        assert p.surprise == 0.4
        assert p.is_surprising

    def test_prediction_not_surprising(self):
        p = Prediction(predicted_score=0.7)
        p.actual_score = 0.75
        p.prediction_error = 0.05
        assert not p.is_surprising

    def test_to_dict(self):
        p = Prediction(agent_id="a1", task_id="t1", predicted_score=0.6)
        d = p.to_dict()
        assert d["agent_id"] == "a1"
        assert d["predicted_score"] == 0.6


class TestHeuristicPrediction:
    def test_predict_uses_agent_history(self, engine):
        agent = _make_agent(avg_score=0.8)
        task = _make_task()
        pred = engine.predict(agent, task)
        # Should predict near agent's avg score
        assert 0.5 <= pred.predicted_score <= 1.0
        assert pred.agent_id == agent.id
        assert pred.task_id == task.id

    def test_predict_default_agent(self, engine):
        agent = _make_agent(avg_score=0.5)
        agent.scores = []  # No history
        task = _make_task()
        pred = engine.predict(agent, task)
        assert 0.1 <= pred.predicted_score <= 0.95

    def test_predict_persists_to_db(self, engine, mem):
        agent = _make_agent()
        task = _make_task()
        pred = engine.predict(agent, task)
        # Check it's in DB
        preds = mem.get_agent_predictions(agent.id, resolved=False)
        assert len(preds) == 1
        assert preds[0]["predicted_score"] == pred.predicted_score


class TestLLMPrediction:
    def test_llm_predict(self, mem, causal_graph):
        llm = MagicMock()
        llm.chat_json.return_value = {
            "predicted_score": 0.72,
            "predicted_outcome": "Should perform well on research",
            "confidence": 0.7,
        }
        engine = PredictionEngine(mem, llm=llm, causal_graph=causal_graph)
        agent = _make_agent()
        task = _make_task()
        pred = engine.predict(agent, task)
        assert pred.predicted_score == 0.72
        assert llm.chat_json.called

    def test_llm_predict_fallback_on_error(self, mem, causal_graph):
        llm = MagicMock()
        llm.chat_json.side_effect = Exception("API error")
        engine = PredictionEngine(mem, llm=llm, causal_graph=causal_graph)
        agent = _make_agent(avg_score=0.7)
        task = _make_task()
        pred = engine.predict(agent, task)
        # Should fallback to heuristic
        assert 0.1 <= pred.predicted_score <= 0.95


class TestResolve:
    def test_resolve_prediction(self, engine, mem):
        agent = _make_agent()
        task = _make_task()
        pred = engine.predict(agent, task)
        engine.resolve(pred, actual_score=0.9, actual_outcome="good result")
        assert pred.is_resolved
        assert pred.actual_score == 0.9
        assert pred.prediction_error is not None

    def test_surprising_result_logged(self, engine, mem):
        agent = _make_agent(avg_score=0.8)
        task = _make_task()
        pred = engine.predict(agent, task)
        # Force a big surprise
        engine.resolve(pred, actual_score=0.1)
        assert pred.is_surprising
        assert pred.surprise >= SURPRISE_THRESHOLD

    def test_resolve_persists(self, engine, mem):
        agent = _make_agent()
        task = _make_task()
        pred = engine.predict(agent, task)
        engine.resolve(pred, actual_score=0.85)
        # Check DB
        resolved = mem.get_agent_predictions(agent.id, resolved=True)
        assert len(resolved) == 1
        assert resolved[0]["actual_score"] == 0.85

    def test_surprise_updates_causal_graph(self, engine, causal_graph):
        agent = _make_agent(avg_score=0.8)
        task = _make_task()
        pred = engine.predict(agent, task)
        engine.resolve(pred, actual_score=0.2)  # Big surprise
        # Should have added a causal edge
        assert len(causal_graph.edges) > 0


class TestCalibration:
    def test_calibration_no_data(self, engine):
        assert engine.get_calibration_score("unknown") == 0.5

    def test_calibration_perfect(self, engine, mem):
        agent = _make_agent(avg_score=0.7)
        task = _make_task()
        # Make several well-calibrated predictions
        for _ in range(5):
            pred = engine.predict(agent, task)
            engine.resolve(pred, actual_score=pred.predicted_score)
        score = engine.get_calibration_score(agent.id)
        assert score >= 0.9  # Near perfect calibration

    def test_calibration_poor(self, engine, mem):
        agent = _make_agent(avg_score=0.8)
        task = _make_task()
        for _ in range(5):
            pred = engine.predict(agent, task)
            # Always way off
            engine.resolve(pred, actual_score=0.1)
        score = engine.get_calibration_score(agent.id)
        assert score < 0.5


class TestReporting:
    def test_print_report_no_crash(self, engine):
        engine.print_report()

    def test_print_report_with_data(self, engine):
        agent = _make_agent()
        task = _make_task()
        pred = engine.predict(agent, task)
        engine.resolve(pred, actual_score=0.5)
        engine.print_report()


class TestPredictionStats:
    def test_stats_empty(self, mem):
        stats = mem.get_prediction_stats()
        assert stats["total_predictions"] == 0
        assert stats["avg_absolute_error"] == 0.0

    def test_stats_after_predictions(self, engine, mem):
        agent = _make_agent()
        task = _make_task()
        pred = engine.predict(agent, task)
        engine.resolve(pred, actual_score=0.9)
        stats = mem.get_prediction_stats()
        assert stats["total_predictions"] == 1
        assert stats["resolved"] == 1
