"""Tests for the InspectionGate (三层安检) module."""

from __future__ import annotations

import pytest

from zhihuiti.inspection import (
    InspectionGate, InspectionLayer, InspectionResult, LayerResult,
    LAYER_THRESHOLDS,
)
from zhihuiti.models import AgentState, AgentConfig, AgentRole, Task, TaskStatus
from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm


def _make_memory() -> Memory:
    return Memory(":memory:")


def _make_agent() -> AgentState:
    return AgentState(
        config=AgentConfig(role=AgentRole.ANALYST, system_prompt=""),
    )


def _make_task(result: str = "Sample output", description: str = "Do analysis") -> Task:
    task = Task(description=description, result=result, status=TaskStatus.COMPLETED)
    return task


def _make_gate(pass_score: float = 0.8) -> InspectionGate:
    mem = _make_memory()
    llm = make_stub_llm({"score": pass_score, "reasoning": "acceptable", "pass": True})
    return InspectionGate(llm=llm, memory=mem)


# ---------------------------------------------------------------------------
# LayerResult
# ---------------------------------------------------------------------------

class TestLayerResult:
    def test_layer_result_pass(self):
        lr = LayerResult(layer=InspectionLayer.RELEVANCE, score=0.8, passed=True)
        assert lr.passed is True
        assert lr.score == 0.8

    def test_layer_result_fail(self):
        lr = LayerResult(layer=InspectionLayer.RIGOR, score=0.3, passed=False,
                         reasoning="Output is too shallow.")
        assert lr.passed is False
        assert lr.reasoning == "Output is too shallow."


# ---------------------------------------------------------------------------
# InspectionResult
# ---------------------------------------------------------------------------

class TestInspectionResult:
    def test_passed_all_when_all_passed(self):
        result = InspectionResult()
        result.layers = [
            LayerResult(InspectionLayer.RELEVANCE, 0.8, True),
            LayerResult(InspectionLayer.RIGOR, 0.7, True),
            LayerResult(InspectionLayer.SAFETY, 0.9, True),
        ]
        assert result.passed_all is True
        assert result.accepted is False  # Only set when full_inspection runs

    def test_passed_all_false_if_any_fail(self):
        result = InspectionResult()
        result.layers = [
            LayerResult(InspectionLayer.RELEVANCE, 0.8, True),
            LayerResult(InspectionLayer.RIGOR, 0.2, False),
        ]
        assert result.passed_all is False

    def test_scores_by_layer(self):
        result = InspectionResult()
        result.layers = [
            LayerResult(InspectionLayer.RELEVANCE, 0.8, True),
            LayerResult(InspectionLayer.RIGOR, 0.7, True),
        ]
        scores = result.scores_by_layer
        assert scores["relevance"] == 0.8
        assert scores["rigor"] == 0.7


# ---------------------------------------------------------------------------
# Empty/error result handling (no LLM needed)
# ---------------------------------------------------------------------------

class TestInspectLayerEdgeCases:
    def test_empty_result_auto_fails(self):
        # Empty result is caught before calling LLM — no API key needed
        gate = _make_gate(pass_score=0.8)
        agent = _make_agent()
        task = _make_task(result="")  # Empty output

        lr = gate.inspect_layer(InspectionLayer.RELEVANCE, task, agent)
        assert lr.passed is False
        assert lr.score <= 0.2

    def test_error_result_auto_fails(self):
        gate = _make_gate(pass_score=0.8)
        agent = _make_agent()
        task = _make_task(result="Error: connection timeout")

        lr = gate.inspect_layer(InspectionLayer.RELEVANCE, task, agent)
        assert lr.passed is False

    def test_full_inspection_empty_result(self):
        gate = _make_gate(pass_score=0.8)
        agent = _make_agent()
        task = _make_task(result="")

        result = gate.full_inspection(task, agent)
        assert result.accepted is False
        assert result.failed_at == InspectionLayer.RELEVANCE
        # Only one layer run (early stop)
        assert len(result.layers) == 1


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_empty(self):
        gate = _make_gate(pass_score=0.8)
        stats = gate.get_stats()
        assert stats["total_inspections"] == 0
        assert stats["accepted"] == 0
        assert stats["rejected"] == 0
        assert stats["acceptance_rate"] == 0.0

    def test_stats_after_failed_inspection(self):
        gate = _make_gate(pass_score=0.8)
        agent = _make_agent()

        # Empty output will fail at layer 1
        task = _make_task(result="")
        gate.full_inspection(task, agent)

        stats = gate.get_stats()
        assert stats["total_inspections"] == 1
        assert stats["rejected"] == 1
        assert stats["failures_by_layer"].get("relevance", 0) == 1

    def test_history_grows(self):
        gate = _make_gate(pass_score=0.8)
        agent = _make_agent()

        for i in range(3):
            gate.full_inspection(_make_task(result=""), agent)

        assert len(gate.history) == 3


# ---------------------------------------------------------------------------
# Layer thresholds
# ---------------------------------------------------------------------------

class TestThresholds:
    def test_safety_has_highest_threshold(self):
        """Safety layer threshold should be the strictest."""
        assert LAYER_THRESHOLDS[InspectionLayer.SAFETY] > LAYER_THRESHOLDS[InspectionLayer.RELEVANCE]
        assert LAYER_THRESHOLDS[InspectionLayer.SAFETY] >= LAYER_THRESHOLDS[InspectionLayer.RIGOR]

    def test_all_thresholds_in_range(self):
        for layer, threshold in LAYER_THRESHOLDS.items():
            assert 0.0 <= threshold <= 1.0, f"{layer} threshold out of range: {threshold}"
