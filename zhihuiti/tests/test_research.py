"""Tests for project-specific, inspection-gated public agent research."""

from __future__ import annotations

import json

import pytest

from zhihuiti.knowledge import KnowledgeBase
from zhihuiti.inspection import InspectionLayer, InspectionResult, LayerResult
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, KnowledgeChunk, Task, TaskStatus
from zhihuiti.research import (
    AgentResearchPublisher,
    build_research_task,
    public_research_outputs,
    public_research_stats,
    select_assignment,
    validate_research_payload,
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


def _valid_research(*evidence_fields: str) -> str:
    fields = evidence_fields or ("total_tasks", "historical_agents")
    return json.dumps({
        "role": "analyst",
        "work_status": "completed",
        "work_performed": [{
            "action": "Compared compatible canonical telemetry fields.",
            "evidence_fields": list(fields),
        }],
        "finding": "The supplied runtime evidence supports adding an explicit quality gate before publication.",
        "evidence": [
            {"field": field, "interpretation": "This canonical runtime value is used only within its defined unit."}
            for field in fields
        ],
        "checks": [
            "Reject outputs whose evidence field is absent from telemetry.",
            "Render canonical values instead of accepting model supplied numbers.",
            "Record the deterministic validation result with every output.",
        ],
        "success_criteria": ["Every published claim has a known telemetry field."],
        "uncertainties": ["Runtime telemetry does not prove source-code behavior."],
        "stop_condition": "Stop publication whenever deterministic validation reports any error.",
    })


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
        AgentRole.ANALYST,
        sequence=0,
        telemetry={"total_tasks": 5, "historical_agents": 14},
    )

    assert assignment.key == "test-coverage"
    assert "total_tasks: 5" in task.description
    assert "Do not claim that you inspected source code" in task.description
    assert task.metadata["disable_delegation"] is True
    assert task.metadata["telemetry_snapshot"] == {
        "total_tasks": 5, "historical_agents": 14,
    }
    assert task.metadata["role_contract"]["execution_mode"] == "telemetry_analysis"


def test_rotation_task_rejects_roles_without_an_execution_contract():
    with pytest.raises(ValueError, match="no safe population execution contract"):
        build_research_task(
            "Software Supply Chain",
            AgentRole.CODER,
            sequence=0,
            telemetry={"total_tasks": 5, "historical_agents": 14},
        )


def test_only_accepted_research_is_published(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_RESEARCH_PUBLISH_MIN_SCORE", "0.80")
    memory = Memory(":memory:")
    publisher = AgentResearchPublisher(memory)
    assignment = select_assignment("Zhihuiti-Core", 0)
    content = _valid_research("total_tasks", "historical_agents")

    rejected_task = _completed_task(content)
    rejected = publisher.publish_if_accepted(
        "Zhihuiti-Core", assignment, rejected_task, _agent(),
        _inspection(rejected_task, (0.79, 0.79, 0.79, 0.79)),
    )
    accepted_task = _completed_task(content)
    accepted_task.metadata["telemetry_snapshot"] = {
        "total_tasks": 7,
        "historical_agents": 14,
    }
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
    assert outputs[0]["telemetry_snapshot"] == {
        "total_tasks": 7,
        "historical_agents": 14,
    }
    assert outputs[0]["inspection"]["accepted"] is True
    assert outputs[0]["inspection"]["scores"]["safety"] == 0.84
    assert outputs[0]["validation"]["schema_version"] == 2
    assert outputs[0]["work_status"] == "validated"
    assert "`total_tasks` = `7`" in outputs[0]["content"]
    assert public_research_stats(memory)["qualified_agents"] == 1


def test_deterministic_validation_rejects_incompatible_units():
    payload = json.loads(
        _valid_research("average_task_score", "cumulative_target")
    )
    payload["finding"] = (
        "The average_task_score is three orders below the cumulative_target, "
        "which indicates a serious performance shortfall."
    )

    validated, errors = validate_research_payload(
        json.dumps(payload),
        {"average_task_score": 0.8, "cumulative_target": 1000},
    )

    assert validated is None
    assert "incompatible_metric_comparison" in errors


def test_deterministic_validation_rejects_false_treasury_reconciliation():
    payload = json.loads(
        _valid_research("treasury_balance", "money_supply")
    )
    payload["finding"] = (
        "The treasury_balance and money_supply difference is an unexplained "
        "discrepancy that represents unaccounted tokens."
    )

    validated, errors = validate_research_payload(
        json.dumps(payload),
        {"treasury_balance": 6.7, "money_supply": 9974.0},
    )

    assert validated is None
    assert "unsupported_treasury_reconciliation" in errors


def test_deterministic_validation_rejects_role_mismatch_and_unperformed_work():
    payload = json.loads(_valid_research("total_tasks", "historical_agents"))
    payload["role"] = "researcher"
    payload["work_performed"][0]["evidence_fields"] = ["source_code"]

    validated, errors = validate_research_payload(
        json.dumps(payload),
        {"total_tasks": 7, "historical_agents": 14},
        expected_role=AgentRole.ANALYST,
    )

    assert validated is None
    assert "role_mismatch" in errors
    assert "work_0_unknown_evidence" in errors


def test_research_stats_are_not_capped_at_feed_limit():
    memory = Memory(":memory:")
    rows = [
        (
            f"research-{index}",
            "agent_research",
            json.dumps({
                "public": True,
                "agent_id": f"agent-{index}",
                "validation": {"deterministic": True, "errors": []},
            }),
        )
        for index in range(501)
    ]
    memory.conn.executemany(
        "INSERT INTO knowledge_chunks (id, content, chunk_type, metadata) "
        "VALUES (?, '', ?, ?)",
        rows,
    )
    memory.conn.commit()

    stats = public_research_stats(memory)

    assert stats["qualified_agents"] == 501
    assert stats["published_outputs"] == 501
    assert stats["legacy_published_outputs"] == 0
    memory.close()


def test_legacy_outputs_do_not_count_as_qualified_agents():
    memory = Memory(":memory:")
    KnowledgeBase(memory).store(KnowledgeChunk(
        id="legacy-public",
        source="agent-research:test",
        title="Legacy output",
        content="Published before deterministic validation existed.",
        chunk_type="agent_research",
        metadata={"public": True, "agent_id": "legacy-agent"},
    ))

    stats = public_research_stats(memory)

    assert stats["qualified_agents"] == 0
    assert stats["published_outputs"] == 0
    assert stats["legacy_published_outputs"] == 1
    assert public_research_outputs(memory)[0]["validation"] is None
    memory.close()


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
