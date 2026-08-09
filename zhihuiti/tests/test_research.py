"""Tests for project-specific, inspection-gated public agent research."""

from __future__ import annotations

from zhihuiti.knowledge import KnowledgeBase
from zhihuiti.inspection import InspectionLayer, InspectionResult, LayerResult
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, KnowledgeChunk, Task, TaskStatus
from zhihuiti.research import (
    AgentResearchPublisher,
    build_research_task,
    public_research_outputs,
    select_assignment,
)


def _completed_task(result: str) -> Task:
    return Task(
        description="Research assignment",
        status=TaskStatus.COMPLETED,
        result=result,
    )


def _agent() -> AgentState:
    return AgentState(
        id="agent-1",
        config=AgentConfig(role=AgentRole.ANALYST, system_prompt="test"),
    )


def _inspection(task: Task, scores: tuple[float, float, float, float]) -> InspectionResult:
    layers = [
        LayerResult(layer=layer, score=score, passed=score >= threshold)
        for layer, score, threshold in zip(
            InspectionLayer,
            scores,
            (0.4, 0.5, 0.6, 0.4),
        )
    ]
    final_score = round(sum(
        layer.score * weight for layer, weight in zip(layers, (0.25, 0.35, 0.25, 0.15))
    ), 3)
    failed = next((layer.layer for layer in layers if not layer.passed), None)
    return InspectionResult(
        task_id=task.id,
        agent_id="agent-1",
        layers=layers,
        final_score=final_score,
        accepted=failed is None,
        failed_at=failed,
    )


def test_assignment_selection_is_project_specific():
    core = select_assignment("Zhihuiti-Core", 0)
    software = select_assignment("Software Supply Chain", 0)
    ai_supply_chain = select_assignment("AI Supply Chain", 0)

    assert core.key == "population-quality"
    assert software.key == "data-freshness"
    assert ai_supply_chain.key == "issuer-provenance"


def test_research_task_is_grounded_and_cannot_delegate():
    task, assignment = build_research_task(
        "Software Supply Chain",
        AgentRole.CODER,
        sequence=0,
        telemetry={"total_tasks": 5, "historical_agents": 14},
    )

    assert assignment.key == "data-freshness"
    assert "total_tasks: 5" in task.description
    assert "Do not claim that you inspected source code" in task.description
    assert task.metadata["disable_delegation"] is True
    assert task.metadata["telemetry_snapshot"] == {
        "total_tasks": 5, "historical_agents": 14,
    }


def test_only_accepted_research_is_published(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_RESEARCH_PUBLISH_MIN_SCORE", "0.80")
    memory = Memory(":memory:")
    publisher = AgentResearchPublisher(memory)
    assignment = select_assignment("Zhihuiti-Core", 0)
    content = "Finding grounded in runtime telemetry. " * 12

    rejected_task = _completed_task(content)
    rejected = publisher.publish_if_accepted(
        "Zhihuiti-Core", assignment, rejected_task, _agent(),
        _inspection(rejected_task, (0.79, 0.79, 0.79, 0.79)),
    )
    accepted_task = _completed_task(content)
    accepted_task.metadata["telemetry_snapshot"] = {"total_tasks": 7}
    accepted = publisher.publish_if_accepted(
        "Zhihuiti-Core", assignment, accepted_task, _agent(),
        _inspection(accepted_task, (0.84, 0.84, 0.84, 0.84)),
    )

    assert rejected["published"] is False
    assert rejected["reason"] == "score_below_threshold"
    assert accepted["published"] is True
    outputs = public_research_outputs(memory)
    assert len(outputs) == 1
    assert outputs[0]["score"] == 0.84
    assert outputs[0]["project"] == "Zhihuiti-Core"
    assert outputs[0]["evidence_scope"] == "runtime_telemetry_only"
    assert outputs[0]["telemetry_snapshot"] == {"total_tasks": 7}
    assert outputs[0]["inspection"]["accepted"] is True
    assert outputs[0]["inspection"]["scores"]["safety"] == 0.84


def test_high_average_never_overrides_safety_rejection():
    memory = Memory(":memory:")
    publisher = AgentResearchPublisher(memory)
    task = _completed_task("Finding grounded in supplied telemetry. " * 12)
    inspection = _inspection(task, (1.0, 1.0, 0.59, 1.0))

    result = publisher.publish_if_accepted(
        "AI Supply Chain", select_assignment("AI Supply Chain", 0),
        task, _agent(), inspection,
    )

    assert inspection.final_score > 0.80
    assert result["published"] is False
    assert result["reason"] == "inspection_rejected"
    assert public_research_outputs(memory) == []


def test_incomplete_or_erroring_inspection_never_publishes():
    memory = Memory(":memory:")
    publisher = AgentResearchPublisher(memory)
    assignment = select_assignment("AI Supply Chain", 0)
    task = _completed_task("Finding grounded in supplied telemetry. " * 12)
    incomplete = InspectionResult(
        task_id=task.id,
        layers=[LayerResult(InspectionLayer.RELEVANCE, 1.0, True)],
        final_score=1.0,
        accepted=True,
    )

    result = publisher.publish_if_accepted(
        "AI Supply Chain", assignment, task, _agent(), incomplete,
    )

    assert result["published"] is False
    assert result["reason"] == "inspection_incomplete"


def test_public_feed_never_returns_private_knowledge():
    memory = Memory(":memory:")
    kb = KnowledgeBase(memory)
    kb.store(KnowledgeChunk(
        id="private",
        source="internal",
        title="Private agent note",
        content="private reliability note",
        chunk_type="agent_research",
        confidence=0.9,
        metadata={"public": False},
    ))
    kb.store(KnowledgeChunk(
        id="other-type",
        source="internal",
        title="Public but unrelated",
        content="public reliability note",
        chunk_type="text",
        confidence=0.9,
        metadata={"public": True},
    ))

    assert public_research_outputs(memory, query="reliability") == []
