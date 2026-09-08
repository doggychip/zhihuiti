"""Opt-in operator operations with durable at-most-once model dispatch.

Uses existing economy_state storage; no schema migration. A crash leaves the
reservation unresolved, intentionally blocking new work until operator review.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone

from zhihuiti.agents import TASK_COST
from zhihuiti.env import env_enabled
from zhihuiti.models import AgentLifeState, TaskStatus
from zhihuiti.research import (
    ROTATION_ROLE_CONTRACTS, build_research_task, validate_research_payload,
)


STATE_KEY = "controlled_operations"
REQUEST_PREFIX = "controlled_request:"
REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{8,80}")
PROBE_TTL = 600


class ControlledError(Exception):
    def __init__(self, reason: str, status: int = 409):
        super().__init__(reason)
        self.status = status


class ControlledOperations:
    def __init__(self, orch, active_work=lambda: False):
        self.orch = orch
        self.memory = orch.memory
        self.active_work = active_work

    def get(self, request_id):
        if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
            raise ControlledError("invalid_request_id", 400)
        return self.memory.get_economy_state(REQUEST_PREFIX + request_id)

    def busy(self):
        return bool((self.memory.get_economy_state(STATE_KEY) or {}).get("active_id"))

    def _gates(self):
        if not env_enabled("ZHIHUITI_CONTROLLED_OPERATIONS"):
            raise ControlledError("controlled_operations_disabled", 503)
        if env_enabled("ZHIHUITI_AUTO_EVOLVE") or self.orch.tools_enabled:
            raise ControlledError("unsafe_runtime")
        if self.active_work() or self.memory._query_one(
            "SELECT id FROM tasks WHERE status IN ('pending', 'running') LIMIT 1"
        ):
            raise ControlledError("other_work_unresolved")
        alive = [a for a in self.orch.agent_manager.agents.values() if a.alive]
        if len(alive) > 30:
            raise ControlledError("active_agent_limit")
        status = self.orch.llm.provider_status()
        if (
            status.get("provider") != "deepseek"
            or status.get("model") != "deepseek-chat"
            or status.get("configured") is not True
            or status.get("fallback_active") is not False
        ):
            raise ControlledError("bounded_provider_not_supported", 503)
        return status

    def _claim(self, request_id, kind, agent_id, now):
        """Serialize admission across connections, including process restarts."""
        with self.memory._lock:
            conn = self.memory.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                prior = self.get(request_id)
                if prior:
                    if prior["kind"] != kind or prior.get("agent_id") != agent_id:
                        raise ControlledError("request_id_conflict")
                    conn.commit()
                    return prior, False
                self._gates()
                state = self.memory.get_economy_state(STATE_KEY) or {}
                if state.get("active_id"):
                    raise ControlledError("controlled_request_unresolved")
                if state.get("day") != now.date().isoformat():
                    state.update(day=now.date().isoformat(), readiness_count=0, task_count=0)
                count_key = kind + "_count"
                if state.get(count_key, 0) >= (24 if kind == "readiness" else 6):
                    raise ControlledError("daily_request_limit", 429)
                last = state.get(kind + "_started_at")
                interval = 60 if kind == "readiness" else 14400
                if last and (now - datetime.fromisoformat(last)).total_seconds() < interval:
                    raise ControlledError("request_interval", 429)
                if kind == "task":
                    probe = state.get("readiness", {})
                    age = (now - datetime.fromisoformat(probe["checked_at"])).total_seconds() if probe else -1
                    current = self.orch.llm.provider_status()
                    if (
                        probe.get("ready") is not True or not 0 <= age <= PROBE_TTL
                        or current.get("ready") is not True
                        or current.get("last_call_at") != probe.get("last_call_at")
                        or self.orch.llm.total_calls != probe.get("call_sequence")
                    ):
                        raise ControlledError("fresh_readiness_required")
                record = {
                    "request_id": request_id, "kind": kind, "agent_id": agent_id,
                    "status": "running", "started_at": now.isoformat(),
                    "max_model_calls": 1, "retries": 0, "fallback": False,
                }
                state.update(active_id=request_id)
                state[count_key] = state.get(count_key, 0) + 1
                state[kind + "_started_at"] = now.isoformat()
                self._put(conn, REQUEST_PREFIX + request_id, record)
                self._put(conn, STATE_KEY, state)
                conn.commit()
                return record, True
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def _put(conn, key, value):
        conn.execute(
            "INSERT OR REPLACE INTO economy_state (entity, state, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, json.dumps(value)),
        )

    def _finish(self, record, provider=None):
        with self.memory._lock:
            conn = self.memory.conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                state = self.memory.get_economy_state(STATE_KEY) or {}
                if state.get("active_id") != record["request_id"]:
                    raise ControlledError("reservation_changed")
                record["completed_at"] = datetime.now(timezone.utc).isoformat()
                state["active_id"] = None
                if provider is not None:
                    state["readiness"] = provider
                    population = self.memory.get_economy_state("population_rotation") or {}
                    population["llm_gate"] = provider
                    population["last_llm_probe_at"] = provider["checked_at"]
                    self._put(conn, "population_rotation", population)
                self._put(conn, STATE_KEY, state)
                self._put(conn, REQUEST_PREFIX + record["request_id"], record)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return record

    def run(self, kind, body):
        expected = {"request_id"} if kind == "readiness" else {"request_id", "agent_id"}
        if not isinstance(body, dict) or set(body) != expected:
            raise ControlledError("unexpected_or_missing_fields", 400)
        request_id = body["request_id"]
        prior = self.get(request_id)
        agent_id = body.get("agent_id")
        if kind == "task" and (not isinstance(agent_id, str) or not agent_id):
            raise ControlledError("invalid_agent_id", 400)
        # Replays do not depend on today's budget, readiness, or runtime switches.
        if prior:
            if prior["kind"] != kind or prior.get("agent_id") != agent_id:
                raise ControlledError("request_id_conflict")
            return prior
        agent = task = None
        if kind == "task":
            agent = self.orch.agent_manager.agents.get(agent_id)
            if (
                agent is None or not agent.alive
                or agent.life_state != AgentLifeState.ACTIVE
                or agent.config.role not in ROTATION_ROLE_CONTRACTS
                or agent.config.tools_enabled
            ):
                raise ControlledError("eligible_existing_agent_required")
            if not math.isfinite(agent.budget) or agent.budget < TASK_COST:
                raise ControlledError("insufficient_agent_budget")
            stats = self.memory.get_stats()
            task, _ = build_research_task(
                project="Zhihuiti Core", role=agent.config.role,
                sequence=stats["total_tasks"],
                telemetry={
                    "historical_agents": stats["total_agents"],
                    "active_agents": sum(a.alive for a in self.orch.agent_manager.agents.values()),
                    "total_tasks": stats["total_tasks"],
                    "snapshot_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            task.description = task.description.replace("Public read-only", "Private read-only", 1)
            task.metadata.update(
                population_rotation=False, public_research_candidate=False,
                controlled_request_id=request_id, max_model_calls=1,
                tools_enabled=False, disable_delegation=True,
            )
        record, claimed = self._claim(
            request_id, kind, agent_id, datetime.now(timezone.utc),
        )
        if not claimed:
            return record
        if kind == "readiness":
            return self._readiness(record)
        return self._task(record, agent, task)

    def _readiness(self, record):
        ready = False
        self.orch.llm._probe_performed = True
        try:
            ready = self.orch.llm.chat_once(
                "Reply with exactly OK.", "Readiness check.", max_tokens=3,
            ).strip() == "OK"
        except Exception:
            pass
        status = self.orch.llm.provider_status()
        provider = {
            "ready": ready, "provider": "deepseek", "model": "deepseek-chat",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "last_call_at": status.get("last_call_at"),
            "call_sequence": self.orch.llm.total_calls,
            "last_error_category": None if ready else status.get("last_error_category") or "probe_failed",
            "source": "controlled_readiness", "request_id": record["request_id"],
        }
        record.update(status="completed" if ready else "failed", readiness=provider)
        return self._finish(record, provider)

    def _save_task(self, task, agent, work_status, reason):
        task.metadata["role_execution"] = {
            "assigned_role": agent.config.role.value,
            "execution_mode": task.metadata["role_contract"]["execution_mode"],
            "work_status": work_status, "evidence_scope": "runtime_telemetry_only",
            "validation_reason": reason,
            "validation_scope": "deterministic_schema_and_evidence_fields_only",
            "provider": "deepseek",
            "live_model_succeeded": task.status == TaskStatus.COMPLETED,
            "completed_at": None if work_status == "running" else datetime.now(timezone.utc).isoformat(),
        }
        self.memory.save_task(
            task.id, task.description, task.status.value, result=task.result,
            agent_id=agent.id, metadata=task.metadata,
        )

    def _task(self, record, agent, task):
        # Persist before dispatch; a crash must not make this request retryable.
        record["task_id"] = task.id
        self.memory.save_economy_state(REQUEST_PREFIX + record["request_id"], record)
        task.assigned_agent_id = agent.id
        task.status = TaskStatus.RUNNING
        self._save_task(task, agent, "running", "validation_pending")
        if not agent.deduct_budget(TASK_COST):
            raise ControlledError("agent_budget_changed")
        self.orch.agent_manager.checkpoint_agent(agent)
        self.orch.economy.record_task_fee(agent.id, TASK_COST)
        try:
            task.result = self.orch.llm.chat_once(
                "Analyze only the supplied runtime telemetry. Return the required JSON. "
                "No delegation, tools, trading, or external actions.",
                task.description,
            )
        except Exception:
            task.status = TaskStatus.FAILED
            task.result = "The bounded model request failed; it will not be retried automatically."
            work_status, reason = "failed", "model_request_failed"
        else:
            task.status = TaskStatus.COMPLETED
            try:
                payload, errors = validate_research_payload(
                    task.result, task.metadata["telemetry_snapshot"], agent.config.role,
                )
            except (TypeError, ValueError, KeyError):
                payload, errors = None, ["malformed_evidence"]
            work_status = "validated" if payload is not None else "rejected"
            reason = "deterministic_pass" if payload is not None else ",".join(errors)
        self._save_task(task, agent, work_status, reason)
        agent.task_ids.append(task.id)
        record.update(
            status=task.status.value, work_status=work_status,
            validation_reason=reason, output=task.result,
            published=False, simulated_task_fee=TASK_COST,
            validation_scope="deterministic_schema_and_evidence_fields_only",
        )
        if task.status == TaskStatus.FAILED:
            status = self.orch.llm.provider_status()
            return self._finish(record, {
                "ready": False, "provider": "deepseek", "model": "deepseek-chat",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "last_call_at": status.get("last_call_at"),
                "call_sequence": self.orch.llm.total_calls,
                "last_error_category": status.get("last_error_category") or "request_failed",
                "source": "controlled_task", "request_id": record["request_id"],
            })
        return self._finish(record)
