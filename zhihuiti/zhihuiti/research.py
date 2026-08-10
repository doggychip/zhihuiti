"""Project-specific, inspection-gated public agent research."""

from __future__ import annotations

import json
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

RESEARCH_SCHEMA_VERSION = 2
RESEARCH_REQUIRED_FIELDS = {
    "role",
    "work_status",
    "work_performed",
    "finding",
    "evidence",
    "checks",
    "success_criteria",
    "uncertainties",
    "stop_condition",
}
ROTATION_ROLE_CONTRACTS = {
    AgentRole.RESEARCHER: {
        "execution_mode": "telemetry_research",
        "responsibility": "Inventory supplied evidence, distinguish known facts from gaps, and synthesize only supported findings.",
    },
    AgentRole.ANALYST: {
        "execution_mode": "telemetry_analysis",
        "responsibility": "Analyze compatible telemetry fields, state assumptions, and avoid comparisons across different units.",
    },
    AgentRole.AUDITOR: {
        "execution_mode": "evidence_audit",
        "responsibility": "Test whether a claim is supported by the supplied evidence and fail closed when required proof is absent.",
    },
}
METRIC_DEFINITIONS = {
    "historical_agents": "cumulative count of agent identities ever spawned; count, not quality",
    "active_agents": "currently live agent identities; count",
    "qualified_agents": "agents with inspection-approved, deterministically validated public research; count",
    "published_outputs": "inspection-approved, deterministically validated public research outputs; count",
    "total_tasks": "persisted task records; count",
    "average_task_score": "mean task score on a unitless 0-to-1 scale",
    "treasury_balance": "simulated tokens currently held by the shared Treasury",
    "money_supply": "simulated tokens across Treasury, agents, and other ledger accounts",
    "auto_mint_remaining_today": "remaining simulated mint allowance for the current UTC day",
    "cumulative_target": "target for cumulative historical agent identities; count",
    "deployment_commit": "immutable source commit reported by the running service",
    "snapshot_at": "UTC timestamp when the supplied telemetry was assembled",
    "service_profile": "runtime capability profile such as core_oracle or agent_only",
}


def _strip_json_fence(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def validate_research_payload(
    content: str,
    telemetry: dict[str, Any],
    expected_role: AgentRole | str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate the machine-readable evidence contract before publication."""
    try:
        payload = json.loads(_strip_json_fence(content))
    except (json.JSONDecodeError, TypeError):
        return None, ["output_not_valid_json"]
    if not isinstance(payload, dict):
        return None, ["output_not_object"]

    errors: list[str] = []
    missing = sorted(RESEARCH_REQUIRED_FIELDS - set(payload))
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    unexpected = sorted(set(payload) - RESEARCH_REQUIRED_FIELDS)
    if unexpected:
        errors.append("unexpected_fields:" + ",".join(unexpected))

    expected_role_name = (
        expected_role.value if isinstance(expected_role, AgentRole) else expected_role
    )
    role = payload.get("role")
    if not isinstance(role, str) or role not in {
        contract_role.value for contract_role in ROTATION_ROLE_CONTRACTS
    }:
        errors.append("role_not_rotation_capable")
    elif expected_role_name and role != expected_role_name:
        errors.append("role_mismatch")
    if payload.get("work_status") != "completed":
        errors.append("work_status_not_completed")

    work_performed = payload.get("work_performed")
    if not isinstance(work_performed, list) or not work_performed:
        errors.append("work_performed_missing")
        work_performed = []
    for index, item in enumerate(work_performed):
        if not isinstance(item, dict):
            errors.append(f"work_{index}_not_object")
            continue
        action = item.get("action")
        fields = item.get("evidence_fields")
        if not isinstance(action, str) or len(action.strip()) < 10:
            errors.append(f"work_{index}_action_missing")
        if not isinstance(fields, list) or not fields:
            errors.append(f"work_{index}_evidence_missing")
        elif any(field not in telemetry for field in fields):
            errors.append(f"work_{index}_unknown_evidence")

    finding = payload.get("finding")
    if not isinstance(finding, str) or len(finding.strip()) < 40:
        errors.append("finding_too_short")

    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence_missing")
        evidence = []
    evidence_fields: set[str] = set()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"evidence_{index}_not_object")
            continue
        field = item.get("field")
        claim = item.get("interpretation")
        if field not in telemetry:
            errors.append(f"evidence_{index}_unknown_field")
        else:
            evidence_fields.add(field)
        if not isinstance(claim, str) or len(claim.strip()) < 10:
            errors.append(f"evidence_{index}_interpretation_missing")
        elif re.search(r"\b\d+(?:\.\d+)?\b", claim):
            errors.append(f"evidence_{index}_contains_numeric_literal")
    if len(evidence_fields) < 2:
        errors.append("insufficient_evidence_fields")

    for field, exact_length in (("checks", 3),):
        value = payload.get(field)
        if not isinstance(value, list) or len(value) != exact_length or not all(
            isinstance(item, str) and len(item.strip()) >= 10 for item in value
        ):
            errors.append(f"{field}_must_have_{exact_length}_items")
    for field in ("success_criteria", "uncertainties"):
        value = payload.get(field)
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and len(item.strip()) >= 10 for item in value
        ):
            errors.append(f"{field}_missing")
    stop_condition = payload.get("stop_condition")
    if not isinstance(stop_condition, str) or len(stop_condition.strip()) < 20:
        errors.append("stop_condition_too_short")

    # These two errors appeared in live outputs and can be rejected without an
    # LLM: they compare unlike units or assume Treasury must equal money supply.
    normalized = " ".join(
        [str(finding or "")]
        + [str(item.get("interpretation", "")) for item in evidence if isinstance(item, dict)]
    ).lower()
    comparative = (" gap ", " below ", " above ", " shortfall", "three orders")
    if (
        {"average_task_score", "cumulative_target"} <= evidence_fields
        and any(token in f" {normalized} " for token in comparative)
    ):
        errors.append("incompatible_metric_comparison")
    if (
        {"treasury_balance", "money_supply"} <= evidence_fields
        and any(token in normalized for token in ("unaccounted", "unexplained", "discrepancy", "missing liability"))
    ):
        errors.append("unsupported_treasury_reconciliation")

    return (payload if not errors else None), errors


def render_research_payload(
    payload: dict[str, Any],
    telemetry: dict[str, Any],
) -> str:
    """Render validated research while injecting canonical evidence values."""
    evidence = "\n".join(
        f"- `{item['field']}` = `{telemetry[item['field']]}` — {item['interpretation']}"
        for item in payload["evidence"]
    )
    checks = "\n".join(
        f"{index}. {item}" for index, item in enumerate(payload["checks"], 1)
    )
    success = "\n".join(f"- {item}" for item in payload["success_criteria"])
    uncertainties = "\n".join(f"- {item}" for item in payload["uncertainties"])
    performed = "\n".join(
        f"- {item['action']} (`{', '.join(item['evidence_fields'])}`)"
        for item in payload["work_performed"]
    )
    return (
        f"Role: `{payload['role']}` · Work state: `validated`\n\n"
        f"## Work performed\n\n{performed}\n\n"
        f"## Finding\n\n{payload['finding'].strip()}\n\n"
        f"## Verified evidence\n\n{evidence}\n\n"
        f"## Prioritized checks\n\n{checks}\n\n"
        f"## Success criteria\n\n{success}\n\n"
        f"## Uncertainty\n\n{uncertainties}\n\n"
        f"## Stop condition\n\n{payload['stop_condition'].strip()}\n\n"
        "Evidence scope: runtime telemetry only."
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


def select_assignment(
    project: str,
    sequence: int,
    role: AgentRole | None = None,
) -> ResearchAssignment:
    normalized = _slug(project)
    if "ai-supply-chain" in normalized:
        assignments = AI_SUPPLY_CHAIN_ASSIGNMENTS
    elif "software-supply-chain" in normalized:
        assignments = SOFTWARE_ASSIGNMENTS
    elif "zhihuiti" in normalized:
        assignments = CORE_ASSIGNMENTS
    else:
        assignments = GENERIC_ASSIGNMENTS
    role_keys = {
        AgentRole.RESEARCHER: {
            "knowledge-integrity", "source-traceability", "data-freshness",
            "issuer-provenance", "universe-integrity", "reliability", "quality",
        },
        AgentRole.ANALYST: {
            "population-quality", "economy-sustainability", "inspection-quality",
            "test-coverage", "backlog-priority", "financial-reconciliation",
            "quality", "reliability",
        },
        AgentRole.AUDITOR: {
            "scheduler-reliability", "browser-runtime", "deployment-proof",
            "filing-freshness", "vendor-integrity", "source-traceability",
            "reliability", "quality",
        },
    }
    eligible = (
        [assignment for assignment in assignments if assignment[0] in role_keys[role]]
        if role in role_keys else list(assignments)
    )
    if not eligible:
        eligible = list(assignments)
    key, title, description = eligible[sequence % len(eligible)]
    return ResearchAssignment(key=key, title=title, description=description)


def build_research_task(
    project: str,
    role: AgentRole,
    sequence: int,
    telemetry: dict[str, Any],
) -> tuple[Task, ResearchAssignment]:
    """Build one read-only assignment grounded only in supplied telemetry."""
    if role not in ROTATION_ROLE_CONTRACTS:
        raise ValueError(f"Role {role.value} has no safe population execution contract")
    assignment = select_assignment(project, sequence, role)
    contract = ROTATION_ROLE_CONTRACTS[role]
    verified = "\n".join(
        f"- {key}: {value} ({METRIC_DEFINITIONS.get(key, 'runtime telemetry field')})"
        for key, value in telemetry.items()
    )
    description = (
        f"Public read-only agent research for {project}.\n\n"
        f"Assignment: {assignment.title}\n{assignment.description}\n\n"
        f"Verified runtime telemetry:\n{verified}\n\n"
        f"Assigned role contract: {role.value} / {contract['execution_mode']}. "
        f"Responsibility: {contract['responsibility']}\n\n"
        "Return ONLY one valid JSON object with exactly these fields: "
        f'"role" (exactly "{role.value}"), "work_status" (exactly "completed"), '
        '"work_performed" (array of objects with "action" and "evidence_fields"), '
        '"finding" (string), "evidence" (array of objects with "field" and '
        '"interpretation"), "checks" (exactly three strings), "success_criteria" '
        '(array of strings), "uncertainties" (array of strings), and "stop_condition" '
        "(string). Evidence field names must come from the supplied telemetry; do not "
        "repeat numeric values inside interpretations because the server injects canonical values. "
        "Use at least two distinct telemetry fields. Every work_performed item must name the "
        "telemetry fields actually examined; never claim an action outside this contract. "
        "Never compare metrics with different units. Money supply is not expected to equal the "
        "Treasury because agents and other ledger accounts also hold simulated tokens. "
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
            "research_schema_version": RESEARCH_SCHEMA_VERSION,
            "role_contract": {
                "role": role.value,
                **contract,
            },
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
        telemetry = task.metadata.get("telemetry_snapshot", {})
        payload, validation_errors = validate_research_payload(
            task.result,
            telemetry,
            expected_role=agent.config.role,
        )
        if payload is None:
            return {
                "published": False,
                "reason": "deterministic_validation_failed",
                "validation_errors": validation_errors,
                "threshold": threshold,
            }
        content = render_research_payload(payload, telemetry)

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
                "validation": {
                    "schema_version": RESEARCH_SCHEMA_VERSION,
                    "deterministic": True,
                    "errors": [],
                    "role_contract": True,
                },
                "work_status": "validated",
                "execution_mode": task.metadata.get("role_contract", {}).get(
                    "execution_mode", "telemetry_research",
                ),
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
            "validation": "deterministic_pass",
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
            "validation": chunk.metadata.get("validation"),
            "work_status": chunk.metadata.get("work_status", "legacy"),
            "execution_mode": chunk.metadata.get("execution_mode", ""),
        }
        for chunk in chunks
    ]


def public_research_stats(memory) -> dict[str, Any]:
    """Return durable qualified-output counts without exposing private content."""
    rows = memory._query(
        "SELECT metadata, created_at FROM knowledge_chunks "
        "WHERE chunk_type = 'agent_research'"
    )
    agent_ids: set[str] = set()
    accepted_at: list[str] = []
    published_outputs = 0
    legacy_published_outputs = 0
    for row in rows:
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if metadata.get("public") is not True:
            continue
        validation = metadata.get("validation")
        if (
            not isinstance(validation, dict)
            or validation.get("deterministic") is not True
            or validation.get("errors")
        ):
            legacy_published_outputs += 1
            continue
        published_outputs += 1
        agent_id = str(metadata.get("agent_id", "")).strip()
        if agent_id:
            agent_ids.add(agent_id)
        accepted_at.append(str(metadata.get("published_at", row["created_at"] or "")))
    return {
        "qualified_agents": len(agent_ids),
        "published_outputs": published_outputs,
        "legacy_published_outputs": legacy_published_outputs,
        "latest_published_at": max(accepted_at) if accepted_at else None,
        "tracking_scope": "inspection_and_deterministic_validation",
    }
