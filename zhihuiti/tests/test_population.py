"""Tests for guarded cumulative-agent population rotation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from zhihuiti.agents import AgentManager
from zhihuiti.bidding import BiddingHouse
from zhihuiti.economy import Economy
from zhihuiti.judge import Judge
from zhihuiti.memory import Memory
from zhihuiti.models import AgentRole
from zhihuiti.population import PopulationConfig, PopulationRotator
from zhihuiti.realms import RealmManager
from tests.conftest import make_stub_llm


def _valid_research() -> str:
    return json.dumps({
        "role": "analyst",
        "work_status": "completed",
        "work_performed": [{
            "action": "Compared compatible canonical telemetry fields.",
            "evidence_fields": ["total_tasks", "historical_agents"],
        }],
        "finding": "The supplied telemetry supports a deterministic gate before research is published.",
        "evidence": [
            {
                "field": "total_tasks",
                "interpretation": "The canonical task count establishes the observed runtime scope.",
            },
            {
                "field": "historical_agents",
                "interpretation": "The cumulative identity count bounds the observed population scope.",
            },
        ],
        "checks": [
            "Reject evidence fields that are absent from supplied telemetry.",
            "Use canonical values inserted by the server during rendering.",
            "Record validation metadata for every published research output.",
        ],
        "success_criteria": ["Every published claim cites supplied runtime telemetry."],
        "uncertainties": ["Runtime telemetry cannot prove unobserved source behavior."],
        "stop_condition": "Stop publication whenever deterministic validation returns an error.",
    })


def _orchestrator(task_output: str | None = None):
    memory = Memory(":memory:")
    llm = make_stub_llm()
    llm.chat.return_value = task_output if task_output is not None else _valid_research()
    llm.provider_status.return_value = {
        "provider": "test",
        "ready": True,
        "last_error_category": None,
        "action_required": None,
    }
    llm.probe_provider.return_value = llm.provider_status.return_value
    economy = Economy(memory)
    realms = RealmManager(memory)
    manager = AgentManager(llm, memory, economy=economy, realm_manager=realms)
    judge = Judge(llm, memory, manager)
    judge.inspection.llm.chat_json.return_value = {
        "score": 0.85, "reasoning": "accepted", "pass": True,
    }
    bidding = BiddingHouse(llm, memory, economy)
    return SimpleNamespace(
        llm=llm,
        memory=memory,
        economy=economy,
        realm_manager=realms,
        agent_manager=manager,
        judge=judge,
        bidding=bidding,
    )


def _config(**overrides) -> PopulationConfig:
    values = {
        "target": 2,
        "batch_size": 2,
        "daily_limit": 10,
        "min_interval_seconds": 14_400,
        "agent_budget": 25.0,
        "retain_active": 1,
        "min_per_role": 0,
        "roles": (AgentRole.ANALYST,),
    }
    values.update(overrides)
    return PopulationConfig(**values)


def test_rotation_grows_history_but_retains_bounded_active_pool():
    orch = _orchestrator()
    result = PopulationRotator(orch, _config()).rotate(
        datetime(2026, 8, 9, tzinfo=timezone.utc),
    )

    assert result["status"] == "target_reached"
    assert result["total_agents"] == 2
    assert result["active_agents"] == 1
    assert result["spawned_today"] == 2
    assert len(result["spawned"]) == 2
    assert len(result["culled"]) == 1
    assert orch.memory.get_stats()["total_tasks"] == 2


def test_rotation_replenishes_quota_only_with_treasury_backing(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_ALLOW_AUTO_MINT", "0")
    orch = _orchestrator()
    realm = orch.realm_manager.realms[
        orch.realm_manager.assign_realm(AgentRole.ANALYST)
    ]
    realm.budget_allocated = 10.0
    realm.budget_spent = 10.0
    orch.economy.treasury.balance = 0.0

    result = PopulationRotator(
        orch, _config(target=1, batch_size=1, retain_active=1),
    ).rotate(datetime(2026, 8, 9, tzinfo=timezone.utc))

    assert result["status"] == "blocked"
    assert result["total_agents"] == 0
    assert result["errors"] == ["Treasury cannot fund agent spawn"]
    assert realm.budget_allocated == 10.0


def test_rotation_never_spawns_when_provider_preflight_fails():
    orch = _orchestrator()
    orch.agent_manager.llm.provider_status.return_value = {
        "provider": "deepseek",
        "ready": None,
        "last_error_category": None,
        "action_required": None,
    }
    orch.agent_manager.llm.probe_provider.return_value = {
        "provider": "deepseek",
        "ready": False,
        "last_error_category": "insufficient_balance",
        "action_required": "Add provider credit before agent work can resume.",
    }

    result = PopulationRotator(
        orch, _config(target=1, batch_size=1, retain_active=1),
    ).rotate(datetime(2026, 8, 9, tzinfo=timezone.utc))

    assert result["status"] == "llm_unavailable"
    assert result["total_agents"] == 0
    assert result["spawned_today"] == 0
    assert result["last_rotation_result"]["reason"] == "insufficient_balance"
    assert result["llm_gate"]["ready"] is False


def test_rotation_publishes_accepted_project_research(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_PROJECT_NAME", "Software Supply Chain")
    output = _valid_research()
    orch = _orchestrator(task_output=output)
    orch.judge.inspection.llm.chat_json.return_value = {
        "score": 0.85, "reasoning": "accepted", "pass": True,
    }

    result = PopulationRotator(
        orch, _config(target=1, batch_size=1, retain_active=1),
    ).rotate(datetime(2026, 8, 9, tzinfo=timezone.utc))

    assert result["spawned"][0]["research"]["published"] is True
    row = orch.memory._query_one(
        "SELECT title, chunk_type FROM knowledge_chunks LIMIT 1"
    )
    assert row["chunk_type"] == "agent_research"
    assert "Software Supply Chain" in row["title"]


def test_rotation_never_overshoots_cumulative_target():
    orch = _orchestrator()
    for index in range(999):
        orch.memory.save_agent(
            f"historical-{index}", "analyst", 0.0, 0, 0.5, False,
        )

    result = PopulationRotator(
        orch,
        _config(target=1_000, batch_size=10, retain_active=5),
    ).rotate(datetime(2026, 8, 9, tzinfo=timezone.utc))

    assert result["total_agents"] == 1_000
    assert len(result["spawned"]) == 1
    assert result["remaining"] == 0


def test_rotation_agents_cannot_delegate_extra_spawns():
    delegated = json.dumps({
        "action": "delegate",
        "subtasks": [{"description": "spawn more", "role": "analyst"}],
    })
    orch = _orchestrator(task_output=delegated)

    result = PopulationRotator(
        orch, _config(target=1, batch_size=1, retain_active=1),
    ).rotate(datetime(2026, 8, 9, tzinfo=timezone.utc))

    assert result["total_agents"] == 1
    assert len(result["spawned"]) == 1


def test_invalid_research_culls_candidate_and_stops_batch():
    orch = _orchestrator(task_output="not valid structured research")

    result = PopulationRotator(
        orch, _config(target=3, batch_size=3, retain_active=3),
    ).rotate(datetime(2026, 8, 9, tzinfo=timezone.utc))

    assert result["status"] == "quality_gate_blocked"
    assert result["total_agents"] == 1
    assert result["active_agents"] == 0
    assert result["rejected_since_tracking"] == 1
    assert result["last_rotation_result"]["rejected"] == 1
    assert result["spawned"][0]["research"]["reason"] == "deterministic_validation_failed"


def test_rotation_enforces_daily_limit():
    orch = _orchestrator()
    rotator = PopulationRotator(
        orch,
        _config(target=10, batch_size=2, daily_limit=2, retain_active=10),
    )
    started = datetime(2026, 8, 9, tzinfo=timezone.utc)

    first = rotator.rotate(started)
    later = rotator.rotate(started + timedelta(hours=4))

    assert first["spawned_today"] == 2
    assert later["status"] == "daily_limit_reached"
    assert later["total_agents"] == 2


def test_rotation_enforces_minimum_interval():
    orch = _orchestrator()
    rotator = PopulationRotator(
        orch,
        _config(target=10, batch_size=1, daily_limit=10, retain_active=10),
    )
    started = datetime(2026, 8, 9, tzinfo=timezone.utc)

    rotator.rotate(started)
    too_soon = rotator.rotate(started + timedelta(hours=1))
    later = rotator.rotate(started + timedelta(hours=4))

    assert too_soon["status"] == "interval_not_elapsed"
    assert too_soon["retry_after_seconds"] == 10_800
    assert later["status"] == "rotated"
    assert later["total_agents"] == 2


def test_configuration_excludes_trading_roles(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_CUMULATIVE_AGENT_TARGET", "1000")
    monkeypatch.setenv(
        "ZHIHUITI_ROTATION_ROLES",
        "trader,alphaarena_trader,analyst,unknown",
    )

    config = PopulationConfig.from_env()

    assert config.target == 1_000
    assert config.roles == (AgentRole.ANALYST,)
