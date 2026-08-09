"""Tests for project-specific, inspection-gated public agent research."""

from __future__ import annotations

from zhihuiti.knowledge import KnowledgeBase
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


def test_assignment_selection_is_project_specific():
    core = select_assignment("Zhihuiti-Core", 0)
    software = select_assignment("Software Supply Chain", 0)

    assert core.key == "population-quality"
    assert software.key == "data-freshness"


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


def test_only_accepted_research_is_published(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_RESEARCH_PUBLISH_MIN_SCORE", "0.80")
    memory = Memory(":memory:")
    publisher = AgentResearchPublisher(memory)
    assignment = select_assignment("Zhihuiti-Core", 0)
    content = "Finding grounded in runtime telemetry. " * 12

    rejected = publisher.publish_if_accepted(
        "Zhihuiti-Core", assignment, _completed_task(content), _agent(), 0.79,
    )
    accepted_task = _completed_task(content)
    accepted = publisher.publish_if_accepted(
        "Zhihuiti-Core", assignment, accepted_task, _agent(), 0.84,
    )

    assert rejected["published"] is False
    assert rejected["reason"] == "score_below_threshold"
    assert accepted["published"] is True
    outputs = public_research_outputs(memory)
    assert len(outputs) == 1
    assert outputs[0]["score"] == 0.84
    assert outputs[0]["project"] == "Zhihuiti-Core"
    assert outputs[0]["evidence_scope"] == "runtime_telemetry_only"


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
