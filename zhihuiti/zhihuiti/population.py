"""Guarded cumulative-agent population rotation.

The normal bidding pool intentionally reuses a small set of live agents.  This
module supports a separate, operator-triggered rotation that can grow the
historical population while keeping the active pool bounded and evaluated.
"""

from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from zhihuiti.models import AgentRole, TaskStatus
from zhihuiti.research import (
    AgentResearchPublisher,
    ROTATION_ROLE_CONTRACTS,
    build_research_task,
    public_research_stats,
)


STATE_KEY = "population_rotation"
SAFE_DEFAULT_ROLES = (
    AgentRole.ANALYST,
    AgentRole.RESEARCHER,
    AgentRole.AUDITOR,
)
def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class PopulationConfig:
    target: int
    batch_size: int
    daily_limit: int
    min_interval_seconds: int
    agent_budget: float
    retain_active: int
    min_per_role: int
    roles: tuple[AgentRole, ...]

    @property
    def enabled(self) -> bool:
        return self.target > 0

    @classmethod
    def from_env(cls) -> "PopulationConfig":
        target = _bounded_int("ZHIHUITI_CUMULATIVE_AGENT_TARGET", 0, 0, 100_000)
        role_names = os.environ.get(
            "ZHIHUITI_ROTATION_ROLES",
            ",".join(role.value for role in SAFE_DEFAULT_ROLES),
        )
        roles: list[AgentRole] = []
        for name in role_names.split(","):
            try:
                role = AgentRole(name.strip())
            except ValueError:
                continue
            if role in ROTATION_ROLE_CONTRACTS and role not in roles:
                roles.append(role)
        if not roles:
            roles = list(SAFE_DEFAULT_ROLES)

        max_active = _bounded_int("ZHIHUITI_MAX_ACTIVE_AGENTS", 36, 1, 10_000)
        retain_active = _bounded_int(
            "ZHIHUITI_RETAIN_ACTIVE_AGENTS", min(24, max_active), 1, max_active,
        )
        return cls(
            target=target,
            batch_size=_bounded_int("ZHIHUITI_ROTATION_BATCH_SIZE", 2, 1, 10),
            daily_limit=_bounded_int("ZHIHUITI_ROTATION_DAILY_LIMIT", 10, 1, 100),
            min_interval_seconds=_bounded_int(
                "ZHIHUITI_ROTATION_MIN_INTERVAL_SECONDS", 14_400, 300, 86_400,
            ),
            agent_budget=_bounded_float("ZHIHUITI_ROTATION_AGENT_BUDGET", 25.0, 5.0, 100.0),
            retain_active=retain_active,
            min_per_role=_bounded_int("ZHIHUITI_ROTATION_MIN_PER_ROLE", 1, 0, 10),
            roles=tuple(roles),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "target": self.target,
            "target_basis": "cumulative_historical_agents",
            "batch_size": self.batch_size,
            "daily_limit": self.daily_limit,
            "min_interval_seconds": self.min_interval_seconds,
            "agent_budget": self.agent_budget,
            "retain_active": self.retain_active,
            "roles": [role.value for role in self.roles],
            "role_contracts": {
                role.value: ROTATION_ROLE_CONTRACTS[role]
                for role in self.roles
            },
            "unsupported_rotation_roles": sorted(
                role.value for role in AgentRole
                if role not in ROTATION_ROLE_CONTRACTS
            ),
        }


class PopulationRotator:
    """Run serialized, persistent, evaluated population rotations."""

    def __init__(self, orchestrator, config: PopulationConfig | None = None):
        self.orch = orchestrator
        self.config = config or PopulationConfig.from_env()
        self._lock = threading.Lock()

    def status(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        state = self._state_for_day(now)
        total = self.orch.memory.get_stats()["total_agents"]
        active = len([a for a in self.orch.agent_manager.agents.values() if a.alive])
        target = self.config.target
        progress = round(total / target, 4) if target else 0.0
        research = public_research_stats(self.orch.memory)
        last_rotation_at = state.get("last_rotation_at")
        next_eligible_at = None
        retry_after_seconds = 0
        if last_rotation_at:
            try:
                next_eligible = datetime.fromisoformat(last_rotation_at) + timedelta(
                    seconds=self.config.min_interval_seconds,
                )
                next_eligible_at = next_eligible.isoformat()
                retry_after_seconds = max(0, int((next_eligible - now).total_seconds()))
            except ValueError:
                next_eligible_at = None
        remaining = max(0, target - total)
        return {
            **self.config.public_dict(),
            "total_agents": total,
            "active_agents": active,
            "remaining": remaining,
            "progress": min(1.0, progress),
            **research,
            "qualified_progress": (
                min(1.0, round(research["qualified_agents"] / target, 4))
                if target else 0.0
            ),
            "day": state["day"],
            "spawned_today": state["spawned_today"],
            "daily_remaining": max(0, self.config.daily_limit - state["spawned_today"]),
            "last_rotation_at": last_rotation_at,
            "next_eligible_at": next_eligible_at,
            "retry_after_seconds": retry_after_seconds,
            "estimated_days_remaining": (
                math.ceil(remaining / self.config.daily_limit)
                if self.config.daily_limit and remaining else 0
            ),
            "evaluated_since_tracking": int(state.get("evaluated_total", 0)),
            "rejected_since_tracking": int(state.get("rejected_total", 0)),
            "failed_since_tracking": int(state.get("failed_total", 0)),
            "last_rotation_result": state.get("last_rotation_result"),
            "llm_gate": state.get("llm_gate"),
        }

    def rotate(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        if not self._lock.acquire(blocking=False):
            return {**self.status(now), "status": "rotation_in_progress", "spawned": []}
        try:
            return self._rotate_locked(now)
        finally:
            self._lock.release()

    def _rotate_locked(self, now: datetime) -> dict[str, Any]:
        before = self.status(now)
        if not self.config.enabled:
            return {**before, "status": "disabled", "spawned": [], "culled": []}
        if before["remaining"] <= 0:
            return {**before, "status": "target_reached", "spawned": [], "culled": []}
        if before["daily_remaining"] <= 0:
            return {**before, "status": "daily_limit_reached", "spawned": [], "culled": []}

        state = self._state_for_day(now)
        provider = self._provider_readiness(state, now)
        if provider.get("ready") is not True:
            result = {
                "status": "llm_unavailable",
                "completed_at": now.isoformat(),
                "spawned": 0,
                "qualified": 0,
                "rejected": 0,
                "failed": 0,
                "culled": 0,
                "reason": provider.get("last_error_category") or "provider_not_ready",
            }
            state["last_rotation_result"] = result
            state["llm_gate"] = {
                "ready": False,
                "provider": provider.get("provider"),
                "last_error_category": provider.get("last_error_category"),
                "action_required": provider.get("action_required"),
                "checked_at": now.isoformat(),
            }
            self._save_state(state)
            return {
                **self.status(now),
                "status": "llm_unavailable",
                "spawned": [],
                "culled": [],
                "errors": [],
            }

        last_rotation = before.get("last_rotation_at")
        if last_rotation:
            try:
                elapsed = (now - datetime.fromisoformat(last_rotation)).total_seconds()
            except ValueError:
                elapsed = self.config.min_interval_seconds
            if elapsed < self.config.min_interval_seconds:
                return {
                    **before,
                    "status": "interval_not_elapsed",
                    "retry_after_seconds": int(self.config.min_interval_seconds - elapsed),
                    "spawned": [],
                    "culled": [],
                }

        count = min(
            self.config.batch_size,
            before["remaining"],
            before["daily_remaining"],
        )
        state["last_rotation_at"] = now.isoformat()
        state["llm_gate"] = {
            "ready": True,
            "provider": provider.get("provider"),
            "checked_at": now.isoformat(),
        }
        self._save_state(state)

        spawned: list[dict[str, Any]] = []
        culled: list[dict[str, Any]] = []
        errors: list[str] = []
        for _ in range(count):
            total = self.orch.memory.get_stats()["total_agents"]
            role = self.config.roles[total % len(self.config.roles)]
            try:
                record = self._spawn_and_evaluate(role, state)
                spawned.append(record)
                state["evaluated_total"] = int(state.get("evaluated_total", 0)) + 1
                qualified = bool(record.get("research", {}).get("published"))
                if qualified:
                    retired = self._trim_active_population()
                else:
                    state["rejected_total"] = int(state.get("rejected_total", 0)) + 1
                    self.orch.agent_manager.cull_agent(
                        self.orch.agent_manager.agents[record["agent_id"]],
                    )
                    retired = {
                        "agent_id": record["agent_id"],
                        "role": record["role"],
                        "score": record.get("score", 0.0),
                        "reason": "research_not_qualified",
                    }
                if retired:
                    culled.append(retired)
                self._save_state(state)
                # One rejected candidate closes the batch so unattended runs
                # cannot amplify low-quality output or spend.
                if not qualified:
                    break
            except Exception as exc:
                errors.append(str(exc))
                state["failed_total"] = int(state.get("failed_total", 0)) + 1
                self._save_state(state)
                break

        self.orch.realm_manager.reconcile_counts(self.orch.agent_manager.agents)
        after = self.status(now)
        qualified_count = sum(
            1 for record in spawned if record.get("research", {}).get("published")
        )
        status = (
            "rotated"
            if qualified_count
            else "quality_gate_blocked"
            if spawned
            else "blocked"
        )
        if after["remaining"] == 0 and qualified_count:
            status = "target_reached"
        state["last_rotation_result"] = {
            "status": status,
            "completed_at": now.isoformat(),
            "spawned": len(spawned),
            "qualified": qualified_count,
            "rejected": len(spawned) - qualified_count,
            "failed": len(errors),
            "culled": len(culled),
        }
        self._save_state(state)
        after = self.status(now)
        return {
            **after,
            "status": status,
            "spawned": spawned,
            "culled": culled,
            "errors": errors,
        }

    def _spawn_and_evaluate(
        self, role: AgentRole, state: dict[str, Any],
    ) -> dict[str, Any]:
        config = self.orch.agent_manager.get_best_config(role)
        agent = self.orch.agent_manager.spawn(
            role=role,
            depth=0,
            config=config,
            budget=self.config.agent_budget,
            allow_realm_replenishment=True,
        )
        self.orch.bidding.pool.add(agent)
        # Persist the quota immediately after the historical population grows,
        # before any LLM evaluation that could fail or time out.
        state["spawned_today"] += 1
        self._save_state(state)
        project = os.environ.get("ZHIHUITI_PROJECT_NAME", "this project").strip()
        memory_stats = self.orch.memory.get_stats()
        economy = self.orch.economy.get_report()
        research_stats = public_research_stats(self.orch.memory)
        explicit_profile = os.environ.get("ZHIHUITI_SERVICE_PROFILE", "").strip().lower()
        scan_enabled = os.environ.get("ZHIHUITI_ORACLE_SCAN", "0").strip().lower() in {
            "1", "true", "yes", "on",
        }
        service_profile = (
            explicit_profile
            if explicit_profile in {"core_oracle", "agent_only"}
            else "core_oracle" if scan_enabled else "agent_only"
        )
        task, assignment = build_research_task(
            project=project,
            role=role,
            sequence=memory_stats["total_agents"],
            telemetry={
                "historical_agents": memory_stats["total_agents"],
                "active_agents": len([
                    current for current in self.orch.agent_manager.agents.values()
                    if current.alive
                ]),
                "qualified_agents": research_stats["qualified_agents"],
                "published_outputs": research_stats["published_outputs"],
                "total_tasks": memory_stats["total_tasks"],
                "average_task_score": memory_stats["avg_task_score"],
                "treasury_balance": economy["treasury_balance"],
                "money_supply": economy["money_supply"],
                "auto_mint_remaining_today": economy["auto_mint"]["remaining_today"],
                "cumulative_target": self.config.target,
                "deployment_commit": os.environ.get(
                    "ZEABUR_GIT_COMMIT_SHA",
                    os.environ.get("ZHIHUITI_COMMIT_SHA", "unknown"),
                ),
                "snapshot_at": datetime.now(timezone.utc).isoformat(),
                "service_profile": service_profile,
            },
        )
        record: dict[str, Any] = {
            "agent_id": agent.id,
            "role": role.value,
        }
        try:
            output = self.orch.agent_manager.execute_task(agent, task)
            score = self.orch.judge.score_task(task, agent)
            inspection = self.orch.judge.inspection.history[-1]
            self.orch.realm_manager.on_task_complete(
                agent, score, task.status == TaskStatus.COMPLETED,
            )
            publication = AgentResearchPublisher(
                self.orch.memory,
            ).publish_if_accepted(
                project, assignment, task, agent, inspection,
            )
            work_status = "validated" if publication.get("published") else "rejected"
            task.metadata["role_execution"] = {
                "assigned_role": role.value,
                "execution_mode": task.metadata.get("role_contract", {}).get("execution_mode"),
                "work_status": work_status,
                "evidence_scope": "runtime_telemetry_only",
                "validation_reason": publication.get("reason", "deterministic_pass"),
                "provider": self.orch.llm.provider_status().get("provider"),
                "live_model_succeeded": self.orch.llm.provider_status().get("ready") is True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            self.orch.memory.save_task(
                task_id=task.id,
                description=task.description,
                status=task.status.value,
                result=task.result,
                score=task.score,
                agent_id=agent.id,
                parent_task_id=task.parent_task_id,
                metadata=task.metadata,
            )
            record.update({
                "score": round(score, 3),
                "task_status": task.status.value,
                "output_preview": output[:160],
                "research": publication,
                "work_status": work_status,
            })
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.result = f"Population evaluation error: {exc}"
            task.metadata["role_execution"] = {
                "assigned_role": role.value,
                "execution_mode": task.metadata.get("role_contract", {}).get("execution_mode"),
                "work_status": "failed",
                "evidence_scope": "runtime_telemetry_only",
                "validation_reason": "execution_error",
                "provider": self.orch.llm.provider_status().get("provider"),
                "live_model_succeeded": False,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            agent.scores.append(0.1)
            self.orch.memory.save_task(
                task_id=task.id,
                description=task.description,
                status=task.status.value,
                result=task.result,
                score=0.1,
                agent_id=agent.id,
                metadata=task.metadata,
            )
            record.update({
                "score": 0.1,
                "task_status": task.status.value,
                "evaluation_error": str(exc),
                "work_status": "failed",
            })
        self.orch.agent_manager.checkpoint_agent(agent)
        return record

    def _trim_active_population(self) -> dict[str, Any] | None:
        alive = [a for a in self.orch.agent_manager.agents.values() if a.alive]
        if len(alive) <= self.config.retain_active:
            return None

        role_counts: dict[AgentRole, int] = {}
        for agent in alive:
            role_counts[agent.config.role] = role_counts.get(agent.config.role, 0) + 1
        candidates = [
            agent for agent in alive
            if role_counts[agent.config.role] > self.config.min_per_role
        ]
        if not candidates:
            return None
        candidate = min(candidates, key=lambda agent: (agent.avg_score, agent.id))
        record = {
            "agent_id": candidate.id,
            "role": candidate.config.role.value,
            "score": round(candidate.avg_score, 3),
        }
        self.orch.agent_manager.cull_agent(candidate)
        return record

    def _state_for_day(self, now: datetime) -> dict[str, Any]:
        day = now.astimezone(timezone.utc).date().isoformat()
        state = self.orch.memory.get_economy_state(STATE_KEY) or {}
        if state.get("day") != day:
            state = {
                "day": day,
                "spawned_today": 0,
                "last_rotation_at": state.get("last_rotation_at"),
                "evaluated_total": state.get("evaluated_total", 0),
                "rejected_total": state.get("rejected_total", 0),
                "failed_total": state.get("failed_total", 0),
                "last_rotation_result": state.get("last_rotation_result"),
                "last_llm_probe_at": state.get("last_llm_probe_at"),
                "llm_gate": state.get("llm_gate"),
            }
        state["spawned_today"] = max(0, int(state.get("spawned_today", 0)))
        return state

    def _save_state(self, state: dict[str, Any]) -> None:
        self.orch.memory.save_economy_state(STATE_KEY, state)

    def _provider_readiness(
        self, state: dict[str, Any], now: datetime,
    ) -> dict[str, Any]:
        status = self.orch.llm.provider_status()
        if status.get("ready") is True:
            return status
        last_probe = state.get("last_llm_probe_at")
        if last_probe and status.get("ready") is False:
            try:
                elapsed = (now - datetime.fromisoformat(last_probe)).total_seconds()
            except ValueError:
                elapsed = 1_800
            if elapsed < 1_800:
                return status
        status = self.orch.llm.probe_provider()
        state["last_llm_probe_at"] = now.isoformat()
        self._save_state(state)
        return status
