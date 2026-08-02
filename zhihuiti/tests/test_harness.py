from __future__ import annotations

import http.client
import json
import threading
from http.server import HTTPServer
from types import SimpleNamespace
from unittest.mock import patch

from zhihuiti.agents import AgentManager
from zhihuiti.dashboard import DashboardHandler, _gather_data
from zhihuiti.harness import (
    DEFAULT_EVAL_CASES,
    HarnessObservation,
    HarnessPolicy,
    SelfImprovementHarness,
)
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole
from zhihuiti.orchestrator import Orchestrator
from zhihuiti.oracle_server import OracleHandler


def _config(prompt: str, *, temperature: float = 0.7) -> AgentConfig:
    return AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt=prompt,
        temperature=temperature,
        model="test-model",
    )


def _harness(tmp_path, **policy_overrides) -> SelfImprovementHarness:
    policy = HarnessPolicy(**policy_overrides) if policy_overrides else HarnessPolicy()
    return SelfImprovementHarness(Memory(str(tmp_path / "harness.db")), policy)


def _propose(harness: SelfImprovementHarness) -> str:
    return harness.propose_candidate(
        _config("candidate prompt"), incumbent=_config("incumbent prompt"),
        mutation_rate=0.2,
    )


def test_default_suite_is_frozen_and_persistent(tmp_path):
    db_path = tmp_path / "harness.db"
    first = SelfImprovementHarness(Memory(str(db_path)))
    first_status = first.get_status()

    second = SelfImprovementHarness(Memory(str(db_path)))
    second_status = second.get_status()

    assert len(first.get_suite()) == len(DEFAULT_EVAL_CASES) == 8
    assert first_status["suite"]["frozen_hash"] == second_status["suite"]["frozen_hash"]
    assert second_status["autonomous_production_evolution"] is False


def test_candidate_passes_paired_shadow_gates(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        if config.system_prompt == "candidate prompt":
            return HarnessObservation(score=0.85, cost=1.02, safety_pass=True)
        return HarnessObservation(score=0.70, cost=1.00, safety_pass=True)

    decision = harness.run_shadow_suite(candidate_id, runner)

    assert decision.passed
    assert decision.trials == 8
    assert decision.mean_score_delta == 0.15
    assert harness._get_config_row(candidate_id)["status"] == "shadow_passed"
    evaluation = harness.get_status()["recent_shadow_evaluations"][0]
    assert evaluation == {
        "candidate_id": candidate_id,
        "role": "researcher",
        "status": "shadow_passed",
        "passed": True,
        "trials": 8,
        "mean_score_delta": 0.15,
        "win_rate_lower_bound": decision.win_rate_lower_bound,
        "candidate_cost": 8.16,
        "incumbent_cost": 8.0,
        "cost_ratio": 1.02,
        "candidate_avg_latency_ms": 0.0,
        "incumbent_avg_latency_ms": 0.0,
        "candidate_safety_failures": 0,
        "incumbent_safety_failures": 0,
        "reasons": [],
        "updated_at": evaluation["updated_at"],
    }


def test_shadow_runner_failure_does_not_persist_partial_trials(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)
    calls = 0

    def runner(_config, _case):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise RuntimeError("provider unavailable")
        return HarnessObservation(score=0.7, cost=1.0)

    with patch("zhihuiti.harness.SelfImprovementHarness.record_trial") as record_trial:
        try:
            harness.run_shadow_suite(candidate_id, runner)
        except RuntimeError as exc:
            assert str(exc) == "provider unavailable"
        else:
            raise AssertionError("shadow evaluation should fail closed")

    assert not record_trial.called
    assert harness._get_config_row(candidate_id)["status"] == "candidate"


def test_cost_regression_blocks_promotion(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        if config.system_prompt == "candidate prompt":
            return HarnessObservation(score=0.90, cost=1.25)
        return HarnessObservation(score=0.70, cost=1.00)

    decision = harness.run_shadow_suite(candidate_id, runner)

    assert not decision.passed
    assert "cost regression exceeds the allowed ratio" in decision.reasons


def test_safety_regression_blocks_promotion(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, case):
        if config.system_prompt == "candidate prompt":
            return HarnessObservation(
                score=0.90,
                cost=1.0,
                safety_pass=case.id != "unsafe_request",
            )
        return HarnessObservation(score=0.70, cost=1.0, safety_pass=True)

    decision = harness.run_shadow_suite(candidate_id, runner)

    assert not decision.passed
    assert decision.candidate_safety_failures == 1
    assert "candidate introduces a safety regression" in decision.reasons


def test_canary_promotes_after_passing_live_observations(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    assert harness.run_shadow_suite(candidate_id, runner).passed
    harness.start_canary(candidate_id, fraction=0.2)

    decision = None
    for i in range(5):
        decision = harness.record_canary_observation(
            candidate_id,
            HarnessObservation(score=0.9, cost=1.0),
            HarnessObservation(score=0.7, cost=1.0),
            case_id=f"canary-{i}",
        )

    assert decision is not None and decision.passed
    status = harness.get_status()
    role = status["roles"][0]
    assert role["active_config_id"] == candidate_id
    assert role["canary_config_id"] is None
    assert harness._get_config_row(candidate_id)["status"] == "active"


def test_canary_safety_failure_rolls_back_immediately(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    harness.run_shadow_suite(candidate_id, runner)
    harness.start_canary(candidate_id)
    harness.record_canary_observation(
        candidate_id,
        HarnessObservation(score=0.9, safety_pass=False),
        HarnessObservation(score=0.7, safety_pass=True),
    )

    status = harness.get_status()
    assert status["roles"][0]["canary_config_id"] is None
    assert harness._get_config_row(candidate_id)["status"] == "rolled_back"
    assert status["recent_events"][0]["event_type"] == "automatic_rollback"


def test_canary_cost_regression_rolls_back_at_gate(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    harness.run_shadow_suite(candidate_id, runner)
    harness.start_canary(candidate_id)
    decision = None
    for i in range(5):
        decision = harness.record_canary_observation(
            candidate_id,
            HarnessObservation(score=0.9, cost=1.25),
            HarnessObservation(score=0.7, cost=1.0),
            case_id=f"canary-{i}",
        )

    assert decision is not None and not decision.passed
    assert "cost regression exceeds the allowed ratio" in decision.reasons
    assert harness._get_config_row(candidate_id)["status"] == "rolled_back"


def test_canary_selection_is_deterministic(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    harness.run_shadow_suite(candidate_id, runner)
    harness.start_canary(candidate_id, fraction=0.5)

    selections = [
        harness.select_config("researcher", f"agent-{i}")["id"]
        for i in range(20)
    ]
    repeated = [
        harness.select_config("researcher", f"agent-{i}")["id"]
        for i in range(20)
    ]
    assert selections == repeated
    assert candidate_id in selections
    assert any(config_id != candidate_id for config_id in selections)


def test_manual_rollback_restores_previous_config(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    harness.run_shadow_suite(candidate_id, runner)
    harness.start_canary(candidate_id)
    for i in range(5):
        harness.record_canary_observation(
            candidate_id,
            HarnessObservation(score=0.9, cost=1.0),
            HarnessObservation(score=0.7, cost=1.0),
            case_id=f"canary-{i}",
        )

    assert harness.rollback("researcher", "post-promotion regression")
    state = harness.get_status()["roles"][0]
    assert state["active_config_id"] != candidate_id
    assert harness._get_config_row(candidate_id)["status"] == "rolled_back"


def test_promoted_config_rolls_back_on_production_safety_regression(tmp_path):
    harness = _harness(tmp_path)
    candidate_id = _propose(harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    harness.run_shadow_suite(candidate_id, runner)
    harness.start_canary(candidate_id)
    for i in range(5):
        harness.record_canary_observation(
            candidate_id,
            HarnessObservation(score=0.9, cost=1.0),
            HarnessObservation(score=0.7, cost=1.0),
            case_id=f"canary-{i}",
        )

    rolled_back = harness.record_active_observation(
        "researcher",
        HarnessObservation(score=0.9, safety_pass=False),
        HarnessObservation(score=0.7, safety_pass=True),
    )

    assert rolled_back
    state = harness.get_status()["roles"][0]
    assert state["active_config_id"] != candidate_id
    assert harness.get_status()["recent_events"][0]["event_type"] == "automatic_production_rollback"


class _FakeLLM:
    pass


class _FakeBloodline:
    def __init__(self):
        self.mutation_rate = None

    def breed_from_pool(self, role, mutation_rate=None):
        self.mutation_rate = mutation_rate
        return AgentConfig(role=role, system_prompt="base prompt")

    def register(self, _config, agent_id=None):
        return agent_id


class _FakeAdaptation:
    def get_mutation_rate(self, _role):
        return 0.42

    def get_evolved_prompt(self, base_prompt, _role):
        return base_prompt + "\nquality directive"


def test_agent_manager_wires_mutation_and_prompt_feedback(tmp_path):
    memory = Memory(str(tmp_path / "agents.db"))
    bloodline = _FakeBloodline()
    manager = AgentManager(_FakeLLM(), memory, bloodline=bloodline)
    manager.set_adaptation_provider(_FakeAdaptation())

    config = manager.get_best_config(AgentRole.RESEARCHER)
    assert bloodline.mutation_rate == 0.42

    agent = manager.spawn(AgentRole.RESEARCHER, config=config)
    assert agent.config.system_prompt.endswith("quality directive")


def test_governed_harness_config_overrides_dynamic_prompt(tmp_path):
    memory = Memory(str(tmp_path / "agents.db"))
    harness = SelfImprovementHarness(memory)
    candidate_id = harness.propose_candidate(
        _config("candidate prompt"), incumbent=_config("frozen incumbent"),
    )
    manager = AgentManager(_FakeLLM(), memory)
    manager.set_adaptation_provider(_FakeAdaptation())
    manager.set_improvement_harness(harness)

    agent = manager.spawn(
        AgentRole.RESEARCHER,
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="dynamic base"),
    )

    assert candidate_id
    assert agent.config.system_prompt == "frozen incumbent"


def test_first_spawn_freezes_baseline_before_dynamic_prompt_evolution(tmp_path):
    memory = Memory(str(tmp_path / "agents.db"))
    harness = SelfImprovementHarness(memory)
    manager = AgentManager(_FakeLLM(), memory)
    manager.set_adaptation_provider(_FakeAdaptation())
    manager.set_improvement_harness(harness)

    first = manager.spawn(
        AgentRole.RESEARCHER,
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="baseline"),
    )
    second = manager.spawn(
        AgentRole.RESEARCHER,
        config=AgentConfig(role=AgentRole.RESEARCHER, system_prompt="different"),
    )

    assert first.config.system_prompt == "baseline"
    assert second.config.system_prompt == "baseline"
    assert harness.get_status()["config_counts"] == {"active": 1}


def test_orchestrator_bootstraps_restored_role_baselines_once(tmp_path):
    db_path = tmp_path / "restored.db"
    memory = Memory(str(db_path))
    memory.save_agent("research-high", "researcher", 100, 0, 0.9, True)
    memory.save_agent("research-low", "researcher", 100, 0, 0.6, True)
    memory.save_agent("coder-high", "coder", 100, 0, 0.8, True)
    memory.close()

    first = Orchestrator(db_path=str(db_path))
    first.close()
    second = Orchestrator(db_path=str(db_path))
    try:
        status = second.harness.get_status()
    finally:
        second.close()

    assert status["config_counts"] == {"active": 2}
    assert [role["role"] for role in status["roles"]] == ["coder", "researcher"]
    assert [event["event_type"] for event in status["recent_events"]] == [
        "baseline_frozen",
        "baseline_frozen",
    ]


def test_restored_agents_receive_promoted_harness_config(tmp_path):
    db_path = tmp_path / "restored-promoted.db"
    memory = Memory(str(db_path))
    memory.save_agent("research-agent", "researcher", 100, 0, 0.9, True)
    memory.close()

    first = Orchestrator(db_path=str(db_path))
    candidate_id = _propose(first.harness)

    def runner(config, _case):
        score = 0.9 if config.system_prompt == "candidate prompt" else 0.7
        return HarnessObservation(score=score, cost=1.0)

    assert first.harness.run_shadow_suite(candidate_id, runner).passed
    first.harness.start_canary(candidate_id)
    for i in range(5):
        first.harness.record_canary_observation(
            candidate_id,
            HarnessObservation(score=0.9, cost=1.0),
            HarnessObservation(score=0.7, cost=1.0),
            case_id=f"canary-{i}",
        )
    first.close()

    second = Orchestrator(db_path=str(db_path))
    try:
        restored = second.agent_manager.agents["research-agent"]
        assert restored.config.system_prompt == "candidate prompt"
    finally:
        second.close()


def test_orchestrator_turns_adaptation_into_non_active_candidate(tmp_path):
    orchestrator = Orchestrator(db_path=str(tmp_path / "orchestrator.db"))

    candidate_id = orchestrator.propose_improvement_candidate(AgentRole.RESEARCHER)

    candidate = orchestrator.harness._get_config_row(candidate_id)
    status = orchestrator.harness.get_status()
    assert candidate["status"] == "candidate"
    assert candidate["mutation_rate"] is not None
    assert status["config_counts"] == {"active": 1, "candidate": 1}
    assert status["autonomous_production_evolution"] is False


def test_dashboard_data_includes_harness_status(monkeypatch):
    expected = {"mode": "guarded", "roles": []}
    orchestrator = SimpleNamespace(
        harness=SimpleNamespace(get_status=lambda: expected),
    )
    monkeypatch.setattr(
        "zhihuiti.routes.agent_routes.gather_core_data", lambda _orch: {"agents": []},
    )

    data = _gather_data(orchestrator)

    assert data["harness"] == expected


def test_dashboard_endpoints_include_harness_status(monkeypatch):
    expected = {"mode": "guarded", "roles": []}
    fake_orchestrator = SimpleNamespace(
        harness=SimpleNamespace(get_status=lambda: expected),
    )
    monkeypatch.setattr(
        "zhihuiti.routes.agent_routes.gather_core_data", lambda _orch: {"agents": []},
    )
    DashboardHandler.orchestrator = fake_orchestrator
    server = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        responses = {}
        for path in ("/api/data", "/api/harness"):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", path)
            response = connection.getresponse()
            responses[path] = (response.status, json.loads(response.read()))
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        DashboardHandler.orchestrator = None

    assert responses["/api/data"] == (200, {"agents": [], "harness": expected})
    assert responses["/api/harness"] == (200, expected)


def test_harness_status_endpoint(tmp_path):
    harness = _harness(tmp_path)
    fake_orchestrator = SimpleNamespace(harness=harness)
    server = HTTPServer(("127.0.0.1", 0), OracleHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    with (
        patch("zhihuiti.oracle_server._has_llm_key", return_value=True),
        patch("zhihuiti.oracle_server._get_orchestrator", return_value=fake_orchestrator),
    ):
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", "/api/harness")
            response = connection.getresponse()
            body = json.loads(response.read())
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    assert response.status == 200
    assert body["mode"] == "guarded"
    assert body["suite"]["id"] == "core-v1"
    assert body["autonomous_production_evolution"] is False
