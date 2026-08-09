"""Project-specific, inspection-gated public agent research."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from zhihuiti.inspection import InspectionLayer, InspectionResult
from zhihuiti.knowledge import KnowledgeBase
from zhihuiti.models import AgentRole, AgentState, KnowledgeChunk, Task, TaskStatus


CORE_ASSIGNMENTS = (
    (
        "population-quality",
        "Population quality and retention",
        "Assess whether cumulative growth is preserving a strong, diverse active agent pool.",
    ),
    (
        "economy-sustainability",
        "Agent-economy sustainability",
        "Assess treasury, mint-cap, spawn-cost, and burn dynamics for sustainable growth.",
    ),
    (
        "inspection-quality",
        "Inspection and output quality",
        "Identify measurable ways to improve agent output quality without weakening safety gates.",
    ),
    (
        "knowledge-integrity",
        "Research knowledge integrity",
        "Design checks that keep published agent research traceable, current, and uncertainty-aware.",
    ),
    (
        "scheduler-reliability",
        "Rotation scheduler reliability",
        "Assess quota, interval, retry, and stop-condition behavior for reliable unattended rotation.",
    ),
)

SOFTWARE_ASSIGNMENTS = (
    (
        "data-freshness",
        "Data freshness and fail-closed behavior",
        "Define checks for stale earnings, prices, dates, and unavailable upstream data.",
    ),
    (
        "source-traceability",
        "Source coverage and traceability",
        "Define how every assessment claim should expose source, timestamp, and coverage gaps.",
    ),
    (
        "browser-runtime",
        "Browser runtime integrity",
        "Prioritize browser checks that catch rendering and interaction failures missed by static tests.",
    ),
    (
        "test-coverage",
        "Engineering test coverage",
        "Propose a small, high-value test plan for data trust, edge cases, and deployment regressions.",
    ),
    (
        "deployment-proof",
        "Deployment and production proof",
        "Define evidence required to prove that a tested change is the version serving production.",
    ),
    (
        "backlog-priority",
        "Engineering backlog priority",
        "Rank the next reliability improvements by user impact, confidence, and implementation effort.",
    ),
)

AI_SUPPLY_CHAIN_ASSIGNMENTS = (
    (
        "issuer-provenance",
        "Issuer source provenance",
        "Define checks that keep SEC issuer facts primary and secondary market data explicitly reconciled.",
    ),
    (
        "universe-integrity",
        "Company-universe integrity",
        "Assess taxonomy, symbol mapping, exclusions, and curated-universe coverage without inventing companies.",
    ),
    (
        "filing-freshness",
        "Filing and reporting freshness",
        "Define fail-closed checks for stale, malformed, future-dated, or unavailable reporting periods.",
    ),
    (
        "financial-reconciliation",
        "Financial-data reconciliation",
        "Prioritize period, currency, unit, and accounting-concept checks across issuer and market sources.",
    ),
    (
        "browser-runtime",
        "Browser runtime integrity",
        "Prioritize browser checks for rendering and interaction failures missed by static tests.",
    ),
    (
        "vendor-integrity",
        "Vendored dependency integrity",
        "Define provenance and regression checks for vendored dashboard code and runtime dependencies.",
    ),
)

GENERIC_ASSIGNMENTS = (
    (
        "reliability",
        "Project reliability",
        "Identify the highest-value reliability check supported by the supplied telemetry.",
    ),
    (
        "quality",
        "Output quality",
        "Define measurable checks for accurate, useful, and safe agent output.",
    ),
)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project"


def _publish_threshold() -> float:
    try:
        value = float(os.environ.get("ZHIHUITI_RESEARCH_PUBLISH_MIN_SCORE", "0.80"))
    except ValueError:
        value = 0.80
    return max(0.70, min(0.95, value))


def _max_public_chars() -> int:
    try:
        value = int(os.environ.get("ZHIHUITI_RESEARCH_MAX_CHARS", "8000"))
    except ValueError:
        value = 8000
    return max(1000, min(20_000, value))


@dataclass(frozen=True)
class ResearchAssignment:
    key: str
    title: str
    description: str


def select_assignment(project: str, sequence: int) -> ResearchAssignment:
    normalized = _slug(project)
    if "ai-supply-chain" in normalized:
        assignments = AI_SUPPLY_CHAIN_ASSIGNMENTS
    elif "software-supply-chain" in normalized:
        assignments = SOFTWARE_ASSIGNMENTS
    elif "zhihuiti" in normalized:
        assignments = CORE_ASSIGNMENTS
    else:
        assignments = GENERIC_ASSIGNMENTS
    key, title, description = assignments[sequence % len(assignments)]
    return ResearchAssignment(key=key, title=title, description=description)


def build_research_task(
    project: str,
    role: AgentRole,
    sequence: int,
    telemetry: dict[str, Any],
) -> tuple[Task, ResearchAssignment]:
    """Build one read-only assignment grounded only in supplied telemetry."""
    assignment = select_assignment(project, sequence)
    verified = "\n".join(f"- {key}: {value}" for key, value in telemetry.items())
    description = (
        f"Public read-only agent research for {project}.\n\n"
        f"Assignment: {assignment.title}\n{assignment.description}\n\n"
        f"Verified runtime telemetry:\n{verified}\n\n"
        "Produce: (1) a two-sentence finding, (2) evidence tied to the telemetry field names, "
        "(3) three prioritized engineering or research checks, (4) measurable success criteria, "
        "(5) uncertainty and missing evidence, and (6) one stop condition. "
        "Do not claim that you inspected source code, external sources, or production systems beyond "
        "the telemetry above. Do not use tools, trade, deploy, message anyone, or take external actions."
    )
    return Task(
        description=description,
        metadata={
            "requested_role": role.value,
            "population_rotation": True,
            "public_research_candidate": True,
            "assignment_key": assignment.key,
            "disable_delegation": True,
            "telemetry_snapshot": dict(telemetry),
        },
    ), assignment


class AgentResearchPublisher:
    """Publish only completed, sufficiently scored rotation research."""

    def __init__(self, memory) -> None:
        self.knowledge = KnowledgeBase(memory)

    def publish_if_accepted(
        self,
        project: str,
        assignment: ResearchAssignment,
        task: Task,
        agent: AgentState,
        inspection: InspectionResult | None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        threshold = _publish_threshold()
        if task.status != TaskStatus.COMPLETED:
            return {"published": False, "reason": "task_not_completed", "threshold": threshold}
        if inspection is None:
            return {"published": False, "reason": "inspection_missing", "threshold": threshold}
        if inspection.task_id != task.id:
            return {"published": False, "reason": "inspection_task_mismatch", "threshold": threshold}

        required_layers = {layer.value for layer in InspectionLayer}
        completed_layers = [layer.layer.value for layer in inspection.layers]
        if len(completed_layers) != len(required_layers) or set(completed_layers) != required_layers:
            return {"published": False, "reason": "inspection_incomplete", "threshold": threshold}
        if any(layer.reasoning.startswith("Inspection error:") for layer in inspection.layers):
            return {"published": False, "reason": "inspection_error", "threshold": threshold}
        if not inspection.accepted or not inspection.passed_all:
            return {"published": False, "reason": "inspection_rejected", "threshold": threshold}

        score = inspection.final_score
        if score < threshold:
            return {"published": False, "reason": "score_below_threshold", "threshold": threshold}
        content = task.result.strip()
        if len(content) < 200:
            return {"published": False, "reason": "output_too_short", "threshold": threshold}

        now = now or datetime.now(timezone.utc)
        project_slug = _slug(project)
        chunk = KnowledgeChunk(
            id=f"research-{task.id}",
            source=f"agent-research:{project_slug}",
            title=f"[{project}] {assignment.title}",
            content=content[:_max_public_chars()],
            chunk_type="agent_research",
            tags=["agent-research", project_slug, agent.config.role.value, assignment.key],
            confidence=round(score, 3),
            metadata={
                "public": True,
                "project": project,
                "project_slug": project_slug,
                "assignment_key": assignment.key,
                "agent_id": agent.id,
                "role": agent.config.role.value,
                "task_id": task.id,
                "score": round(score, 3),
                "published_at": now.isoformat(),
                "evidence_scope": "runtime_telemetry_only",
                "telemetry_snapshot": task.metadata.get("telemetry_snapshot", {}),
                "inspection": {
                    "accepted": inspection.accepted,
                    "failed_at": (
                        inspection.failed_at.value if inspection.failed_at else None
                    ),
                    "scores": inspection.scores_by_layer,
                },
            },
        )
        self.knowledge.store(chunk)
        return {
            "published": True,
            "knowledge_id": chunk.id,
            "title": chunk.title,
            "threshold": threshold,
        }


def public_research_outputs(
    memory,
    query: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return public agent research only; private knowledge is never included."""
    limit = max(1, min(50, int(limit)))
    kb = KnowledgeBase(memory)
    if query.strip():
        chunks = kb.query(
            query.strip(), top_k=limit, chunk_type="agent_research", public_only=True,
        )
    else:
        chunks = kb.recent(
            limit=limit, chunk_type="agent_research", public_only=True,
        )
    return [
        {
            "id": chunk.id,
            "title": chunk.title,
            "content": chunk.content,
            "source": chunk.source,
            "confidence": chunk.confidence,
            "score": chunk.metadata.get("score", chunk.confidence),
            "project": chunk.metadata.get("project", ""),
            "role": chunk.metadata.get("role", ""),
            "assignment_key": chunk.metadata.get("assignment_key", ""),
            "created_at": chunk.metadata.get("published_at", chunk.created_at),
            "evidence_scope": chunk.metadata.get("evidence_scope", ""),
            "telemetry_snapshot": chunk.metadata.get("telemetry_snapshot", {}),
            "inspection": chunk.metadata.get("inspection", {}),
        }
        for chunk in chunks
    ]
