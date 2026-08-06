"""Secret-free readiness and budget reporting for shadow evaluations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from zhihuiti.models import AgentConfig, AgentRole
from zhihuiti.prompts import get_prompt
from zhihuiti.shadow_eval import JUDGE_SYSTEM_PROMPT, LLMShadowRunner


PREFLIGHT_FRESH_SECONDS = 600
RESPONSE_MAX_TOKENS = 512
JUDGE_MAX_TOKENS = 256


def _age_seconds(created_at: str | None) -> float | None:
    if not created_at:
        return None
    try:
        checked = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None
    return max(0.0, (datetime.now(timezone.utc) - checked).total_seconds())


def _shadow_plan(harness, llm, role: str) -> dict[str, Any]:
    try:
        cases = harness.get_suite()
        config = harness.get_active_config(role)
    except (RuntimeError, ValueError):
        return {
            "suite_ready": False,
            "suite_id": getattr(harness, "DEFAULT_SUITE_ID", None),
            "paired_cases": 0,
            "expected_llm_calls": 0,
            "estimated_input_tokens": 0,
            "estimated_max_output_tokens": 0,
            "estimated_max_cost_units": 0.0,
        }

    if not cases:
        return {
            "suite_ready": False,
            "suite_id": getattr(harness, "DEFAULT_SUITE_ID", None),
            "paired_cases": len(cases),
            "expected_llm_calls": len(cases) * 4,
            "estimated_input_tokens": 0,
            "estimated_max_output_tokens": len(cases) * 2 * (
                RESPONSE_MAX_TOKENS + JUDGE_MAX_TOKENS
            ),
            "estimated_max_cost_units": 0.0,
        }

    if config is None:
        try:
            config = AgentConfig(
                role=AgentRole(role),
                system_prompt=get_prompt(role),
            )
        except ValueError:
            return {
                "suite_ready": False,
                "suite_id": getattr(harness, "DEFAULT_SUITE_ID", None),
                "paired_cases": len(cases),
                "expected_llm_calls": len(cases) * 4,
                "estimated_input_tokens": 0,
                "estimated_max_output_tokens": len(cases) * 2 * (
                    RESPONSE_MAX_TOKENS + JUDGE_MAX_TOKENS
                ),
                "estimated_max_cost_units": 0.0,
            }

    estimated_input_tokens = 0
    answer_placeholder = "x" * (RESPONSE_MAX_TOKENS * 4)
    for case in cases:
        judge_payload = json.dumps({
            "task": case.task,
            "rubric": case.rubric,
            "safety_critical": case.safety_critical,
            "answer": answer_placeholder,
        }, sort_keys=True)
        per_config_input = LLMShadowRunner._estimated_tokens(
            config.system_prompt,
            case.task,
            JUDGE_SYSTEM_PROMPT,
            judge_payload,
        )
        estimated_input_tokens += per_config_input * 2

    estimated_max_output_tokens = len(cases) * 2 * (
        RESPONSE_MAX_TOKENS + JUDGE_MAX_TOKENS
    )
    return {
        "suite_ready": True,
        "suite_id": getattr(harness, "DEFAULT_SUITE_ID", None),
        "paired_cases": len(cases),
        "expected_llm_calls": len(cases) * 4,
        "estimated_input_tokens": estimated_input_tokens,
        "estimated_max_output_tokens": estimated_max_output_tokens,
        "estimated_max_cost_units": round(
            llm.estimate_cost(estimated_input_tokens, estimated_max_output_tokens),
            3,
        ),
    }


def build_shadow_readiness(orch, role: str = "researcher", *, probe: bool = False) -> dict[str, Any]:
    """Build readiness state; only ``probe=True`` performs a provider call."""
    provider = orch.llm.probe_provider() if probe else orch.llm.provider_status()
    plan = _shadow_plan(orch.harness, orch.llm, role)
    last_checked_at = None
    probe_fresh = False
    matching_probe_stale = False

    if probe:
        details = {
            key: provider.get(key)
            for key in (
                "provider", "model", "configured", "probe_performed", "ready",
                "fallback_configured", "fallback_active", "message",
            )
        }
        orch.harness.record_provider_preflight(role, details)
    else:
        last = orch.harness.get_latest_provider_preflight(role)
        if last:
            last_checked_at = last["created_at"]
            age = _age_seconds(last_checked_at)
            probe_fresh = age is not None and age <= PREFLIGHT_FRESH_SECONDS
            previous = last["details"]
            same_target = (
                previous.get("provider") == provider.get("provider")
                and previous.get("model") == provider.get("model")
            )
            if probe_fresh and same_target:
                provider = {**provider, **previous}
            elif same_target:
                matching_probe_stale = True
                outcome = "passed" if previous.get("ready") is True else "failed"
                provider = {
                    **provider,
                    "message": (
                        f"The last readiness probe {outcome}, but it is no longer fresh. "
                        "Run a fresh probe before starting a shadow evaluation."
                    ),
                }

    ready = bool(provider.get("ready") and plan["suite_ready"])
    failed_fresh_probe = (
        provider.get("probe_performed") is True
        and provider.get("ready") is False
        and (probe or probe_fresh)
    )
    if provider.get("configured") is False or failed_fresh_probe:
        status = "blocked"
    elif ready:
        status = "ready"
    elif matching_probe_stale:
        status = "stale"
    else:
        status = "not_checked"

    return {
        "role": role,
        "status": status,
        **provider,
        **plan,
        "last_checked_at": last_checked_at,
        "probe_fresh": probe_fresh if not probe else True,
        "tools_enabled": False,
        "candidate_created": False,
        "canary_enabled": False,
    }


def get_harness_status(orch) -> dict[str, Any]:
    """Return harness status with readiness when the orchestrator exposes an LLM."""
    status = orch.harness.get_status()
    if not hasattr(orch, "llm"):
        return status
    return {**status, "shadow_readiness": build_shadow_readiness(orch)}
