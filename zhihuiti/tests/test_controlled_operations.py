"""No live provider calls: exercise real persistence and mocked HTTP transport."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from zhihuiti.controlled import ControlledError, ControlledOperations, STATE_KEY
from zhihuiti.llm import LLM, LLMError
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole, AgentState, AgentLifeState


def valid_output():
    return json.dumps({
        "role": "researcher", "work_status": "completed",
        "work_performed": [{
            "action": "Compared supplied population and task coverage.",
            "evidence_fields": ["historical_agents", "total_tasks"],
        }],
        "finding": "The supplied counts describe recorded activity but do not establish the quality of agent work.",
        "evidence": [
            {"field": "historical_agents", "interpretation": "Records cumulative population rather than demonstrated quality."},
            {"field": "total_tasks", "interpretation": "Records task volume without proving successful outcomes."},
        ],
        "checks": ["Inspect recorded task validation.", "Compare only compatible measures.", "Check freshness before drawing conclusions."],
        "success_criteria": ["Require persisted evidence of validated work."],
        "uncertainties": ["The snapshot does not establish semantic correctness."],
        "stop_condition": "Stop if evidence is missing or stale before further execution.",
    })


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret")
    monkeypatch.setenv("DEEPSEEK_FALLBACK_API_KEY", "fallback-secret")
    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    monkeypatch.setenv("ZHIHUITI_CONTROLLED_OPERATIONS", "1")
    monkeypatch.setenv("ZHIHUITI_AUTO_EVOLVE", "0")
    calls = []
    reply = {"status": 200, "output": valid_output(), "probe": "OK", "finish_reason": "stop"}

    def transport(request):
        calls.append(request)
        data = json.loads(request.content)
        output = reply["probe"] if data["max_tokens"] == 3 else reply["output"]
        return httpx.Response(reply["status"], json={
            "choices": [{"message": {"content": output}, "finish_reason": reply["finish_reason"]}],
        })

    llm = LLM()
    llm.client.close()
    llm.client = httpx.Client(transport=httpx.MockTransport(transport))
    memory = Memory(str(tmp_path / "test.db"))
    agent = AgentState(id="existing-researcher", config=AgentConfig(
        role=AgentRole.RESEARCHER, system_prompt="unused",
    ), budget=25)
    memory.save_agent(agent.id, agent.config.role.value, agent.budget, agent.depth, agent.avg_score, agent.alive)

    def checkpoint(a):
        memory.save_agent(a.id, a.config.role.value, a.budget, a.depth, a.avg_score, a.alive)

    manager = SimpleNamespace(
        agents={agent.id: agent}, spawn=Mock(), execute_task=Mock(),
        checkpoint_agent=checkpoint,
    )
    orch = SimpleNamespace(
        memory=memory, llm=llm, tools_enabled=False, agent_manager=manager,
        economy=SimpleNamespace(record_task_fee=Mock()), judge=Mock(),
    )
    controller = ControlledOperations(orch)
    yield SimpleNamespace(
        controller=controller, orch=orch, agent=agent, llm=llm,
        memory=memory, calls=calls, reply=reply,
    )
    manager.spawn.assert_not_called()
    manager.execute_task.assert_not_called()
    orch.judge.assert_not_called()
    llm.client.close()
    memory.close()


def probe(s, request_id="readiness-0001"):
    return s.controller.run("readiness", {"request_id": request_id})


def task(s, request_id="task-00000001"):
    return s.controller.run("task", {"request_id": request_id, "agent_id": s.agent.id})


def test_readiness_refreshes_only_gate_and_does_not_rotate(setup):
    s = setup
    before = {"spawned_today": 4, "last_rotation_at": "old", "llm_gate": {"ready": False}}
    s.memory.save_economy_state("population_rotation", before)
    result = probe(s)
    state = s.memory.get_economy_state("population_rotation")
    assert result["readiness"]["ready"] is True
    assert result["status"] == "completed"
    assert state["spawned_today"] == 4
    assert state["last_rotation_at"] == "old"
    assert state["llm_gate"]["ready"] is True
    assert s.memory.get_stats()["total_tasks"] == 0
    assert s.memory.get_stats()["total_agents"] == 1
    assert s.agent.budget == 25
    assert len(s.calls) == 1
    assert s.llm.provider_status()["probe_performed"] is True


def test_exactly_one_existing_agent_task_and_private_validation(setup):
    s = setup
    probe(s)
    result = task(s)
    assert len(s.calls) == 2  # one probe plus one task
    assert result["work_status"] == "validated"
    assert result["published"] is False
    assert "deterministic" in result["validation_scope"]
    assert s.agent.budget == 20
    s.orch.economy.record_task_fee.assert_called_once_with(s.agent.id, 5)
    assert s.memory.get_stats()["total_agents"] == 1
    assert s.memory.get_stats()["total_tasks"] == 1
    stored = s.memory._query_one("SELECT * FROM tasks WHERE id=?", (result["task_id"],))
    metadata = json.loads(stored["metadata"])
    assert metadata["disable_delegation"] is True
    assert metadata["public_research_candidate"] is False
    assert metadata["population_rotation"] is False
    assert metadata["role_execution"]["work_status"] == "validated"
    assert s.memory.get_latest_task_states_by_agent()[s.agent.id]["work_status"] == "validated"
    request = json.loads(s.calls[-1].content)
    assert "tools" not in request
    assert request["max_tokens"] == 1536
    assert s.calls[-1].extensions["timeout"]["read"] == 30


def test_restart_replay_is_durable_and_has_no_second_fee(setup):
    s = setup
    probe(s)
    first = task(s)
    s.controller = ControlledOperations(s.orch)
    assert task(s) == first
    assert probe(s)["status"] == "completed"
    assert len(s.calls) == 2
    assert s.agent.budget == 20
    with pytest.raises(ControlledError, match="request_id_conflict"):
        s.controller.run("readiness", {"request_id": first["request_id"]})


@pytest.mark.parametrize("status", [401, 402, 429, 500, 503])
def test_probe_failure_never_retries_or_uses_fallback(setup, status):
    s = setup
    s.reply["status"] = status
    result = probe(s)
    assert result["status"] == "failed"
    assert len(s.calls) == 1
    assert s.llm.total_retries == 0
    assert s.llm.provider_status()["fallback_active"] is False
    assert "test-secret" not in json.dumps(result)
    assert "fallback-secret" not in json.dumps(result)
    with pytest.raises(ControlledError, match="fresh_readiness_required"):
        task(s)
    assert len(s.calls) == 1


@pytest.mark.parametrize("output", ["", "NOT OK"])
def test_probe_requires_exact_acknowledgement(setup, output):
    setup.reply["probe"] = output
    assert probe(setup)["readiness"]["ready"] is False
    with pytest.raises(ControlledError, match="fresh_readiness_required"):
        task(setup)


@pytest.mark.parametrize("output", [
    "DELEGATE: spawn another researcher",
    '{"role":"researcher","evidence":[{"field":[]}]}',
    '{"role":"researcher","work_performed":[{"evidence_fields":[{}]}]}',
])
def test_bad_output_rejected_without_repair_or_delegation(setup, output):
    probe(setup)
    setup.reply["output"] = output
    result = task(setup)
    assert result["work_status"] == "rejected"
    assert len(setup.calls) == 2
    assert setup.controller.busy() is False


def test_task_failure_is_persisted_and_not_retried(setup):
    probe(setup)
    setup.reply["status"] = 402
    first = task(setup)
    assert first["work_status"] == "failed"
    assert task(setup) == first
    assert len(setup.calls) == 2
    assert setup.memory.get_latest_task_states_by_agent()[setup.agent.id]["work_status"] == "failed"
    gate = setup.memory.get_economy_state("population_rotation")["llm_gate"]
    assert gate["ready"] is False
    assert gate["last_error_category"] == "insufficient_balance"


def test_missing_stale_future_or_changed_readiness_blocks_task(setup):
    s = setup
    with pytest.raises(ControlledError, match="fresh_readiness_required"):
        task(s)
    probe(s)
    state = s.memory.get_economy_state(STATE_KEY)
    for delta in (-601, 60):
        state["readiness"]["checked_at"] = (datetime.now(timezone.utc) + timedelta(seconds=delta)).isoformat()
        s.memory.save_economy_state(STATE_KEY, state)
        with pytest.raises(ControlledError, match="fresh_readiness_required"):
            task(s)
    state["readiness"]["checked_at"] = datetime.now(timezone.utc).isoformat()
    s.memory.save_economy_state(STATE_KEY, state)
    s.llm._last_call_succeeded = None  # new process / credential restart
    with pytest.raises(ControlledError, match="fresh_readiness_required"):
        task(s)
    assert len(s.calls) == 1


@pytest.mark.parametrize("mutation", ["dead", "frozen", "tools", "trader", "budget", "nan"])
def test_ineligible_agent_never_calls_model(setup, mutation):
    s = setup
    if mutation == "dead":
        s.agent.alive = False
    elif mutation == "frozen":
        s.agent.life_state = AgentLifeState.FROZEN
    elif mutation == "tools":
        s.agent.config.tools_enabled = True
    elif mutation == "trader":
        s.agent.config.role = AgentRole.TRADER
    else:
        s.agent.budget = float("nan") if mutation == "nan" else 0
    with pytest.raises(ControlledError):
        task(s)
    assert not s.calls


def test_other_work_and_disabled_safety_gates(setup, monkeypatch):
    s = setup
    monkeypatch.setenv("ZHIHUITI_CONTROLLED_OPERATIONS", "0")
    with pytest.raises(ControlledError, match="disabled"):
        probe(s)
    monkeypatch.setenv("ZHIHUITI_CONTROLLED_OPERATIONS", "1")
    monkeypatch.setenv("ZHIHUITI_AUTO_EVOLVE", "1")
    with pytest.raises(ControlledError, match="unsafe_runtime"):
        probe(s)
    monkeypatch.setenv("ZHIHUITI_AUTO_EVOLVE", "0")
    s.controller.active_work = lambda: True
    with pytest.raises(ControlledError, match="other_work_unresolved"):
        probe(s)
    s.controller.active_work = lambda: False
    s.memory.save_task("legacy", "Existing work", "running")
    with pytest.raises(ControlledError, match="other_work_unresolved"):
        probe(s)
    assert not s.calls


def test_crash_reservation_blocks_new_requests_and_survives_restart(setup):
    s = setup
    record, _ = s.controller._claim("crashed-00001", "readiness", None, datetime.now(timezone.utc))
    other_memory = Memory(str(s.memory.db_path))
    try:
        other = ControlledOperations(SimpleNamespace(**{**vars(s.orch), "memory": other_memory}))
        assert other.run("readiness", {"request_id": "crashed-00001"}) == record
        with pytest.raises(ControlledError, match="unresolved"):
            other.run("readiness", {"request_id": "new-request-0001"})
    finally:
        other_memory.close()
    assert not s.calls


def test_interval_and_daily_caps(setup):
    s = setup
    probe(s)
    with pytest.raises(ControlledError, match="request_interval"):
        probe(s, "readiness-0002")
    state = s.memory.get_economy_state(STATE_KEY)
    state["readiness_count"] = 24
    s.memory.save_economy_state(STATE_KEY, state)
    with pytest.raises(ControlledError, match="daily_request_limit"):
        probe(s, "readiness-0003")
    assert len(s.calls) == 1


def test_same_second_intervening_call_invalidates_probe(setup):
    probe(setup)
    setup.llm.total_calls += 1  # timestamps alone have only second resolution
    with pytest.raises(ControlledError, match="fresh_readiness_required"):
        task(setup)
    assert len(setup.calls) == 1


def test_task_daily_cap_and_interval_do_not_dispatch(setup):
    probe(setup)
    state = setup.memory.get_economy_state(STATE_KEY)
    state["task_count"] = 6
    setup.memory.save_economy_state(STATE_KEY, state)
    with pytest.raises(ControlledError, match="daily_request_limit"):
        task(setup)
    state["task_count"] = 0
    state["task_started_at"] = datetime.now(timezone.utc).isoformat()
    setup.memory.save_economy_state(STATE_KEY, state)
    with pytest.raises(ControlledError, match="request_interval"):
        task(setup)
    assert len(setup.calls) == 1


def test_persisted_running_task_visible_during_model_call(setup, monkeypatch):
    probe(setup)
    original = setup.llm.chat_once

    def observe(*args, **kwargs):
        latest = setup.memory.get_latest_task_states_by_agent()[setup.agent.id]
        assert latest["work_status"] == "running"
        assert setup.controller.busy() is True
        assert setup.controller.get("task-00000001")["task_id"] == latest["task_id"]
        return original(*args, **kwargs)

    monkeypatch.setattr(setup.llm, "chat_once", observe)
    assert task(setup)["work_status"] == "validated"


def test_reservation_stays_closed_if_final_persistence_fails(setup, monkeypatch):
    probe(setup)
    original = setup.memory.save_task

    def fail_final(*args, **kwargs):
        if args[2] == "completed":
            raise OSError("simulated disk failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(setup.memory, "save_task", fail_final)
    with pytest.raises(OSError):
        task(setup)
    assert setup.controller.busy() is True
    assert task(setup)["status"] == "running"
    assert len(setup.calls) == 2


def test_runtime_tools_population_and_fallback_are_blocked(setup):
    s = setup
    s.orch.tools_enabled = True
    with pytest.raises(ControlledError, match="unsafe_runtime"):
        probe(s)
    s.orch.tools_enabled = False
    s.orch.agent_manager.agents = {str(i): s.agent for i in range(31)}
    with pytest.raises(ControlledError, match="active_agent_limit"):
        probe(s)
    s.orch.agent_manager.agents = {s.agent.id: s.agent}
    s.llm._using_fallback = True
    with pytest.raises(ControlledError, match="bounded_provider_not_supported"):
        probe(s)
    assert not s.calls


@pytest.mark.parametrize("body", [{}, [], {"request_id": "../bad"}, {"request_id": "good-id-001", "force": True}])
def test_invalid_request_has_no_side_effects(setup, body):
    with pytest.raises(ControlledError):
        setup.controller.run("readiness", body)
    assert not setup.calls
    assert setup.memory.get_economy_state(STATE_KEY) is None


def test_bounded_transport_rejects_overrides_truncation_and_timeouts(setup):
    s = setup
    for limit in (0, 1537, True):
        with pytest.raises(LLMError):
            s.llm.chat_once("s", "u", max_tokens=limit)
    with pytest.raises(LLMError):
        s.llm.chat_once("s" * 16001, "u")
    assert not s.calls
    s.reply["finish_reason"] = "length"
    with pytest.raises(LLMError):
        s.llm.chat_once("s", "u")
    assert len(s.calls) == 1
    s.llm.client.post = Mock(side_effect=httpx.ReadTimeout("sensitive upstream text"))
    with pytest.raises(LLMError, match="request_failed"):
        s.llm.chat_once("s", "u")
    s.llm.client.post.assert_called_once()


def test_http_auth_replay_polling_and_no_lazy_initialization(setup, monkeypatch):
    import zhihuiti.oracle_server as server
    from .test_oracle_server import _start_server, _post
    import http.client

    monkeypatch.setenv("ZHIHUITI_API_TOKEN", "operator-test")
    monkeypatch.setattr(server, "_orchestrator", setup.orch)
    monkeypatch.setattr(server, "_orch_goals", {})
    monkeypatch.setattr(server, "_self_loop_running", False)
    monkeypatch.setattr(server, "_population_rotator", None)
    srv, port = _start_server()
    try:
        body = {"request_id": "http-probe-001"}
        assert _post(port, "/api/operations/readiness", body, token=None)[0] == 401
        assert not setup.calls
        status, result = _post(port, "/api/operations/readiness", body, token="operator-test")
        assert status == 200 and result["readiness"]["ready"] is True
        assert _post(port, "/api/operations/readiness", body, token="operator-test")[1] == result
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        path = "/api/operations/controlled/http-probe-001"
        conn.request("GET", path)
        response = conn.getresponse()
        assert response.status == 401
        response.read()
        conn.request("GET", path, headers={"Authorization": "Bearer operator-test"})
        response = conn.getresponse()
        assert response.status == 200
        assert json.loads(response.read()) == result
        conn.close()
        assert len(setup.calls) == 1

        monkeypatch.setattr(server, "_orchestrator", None)
        init = Mock(side_effect=AssertionError("must not initialize"))
        monkeypatch.setattr(server, "_get_orchestrator", init)
        assert _post(port, "/api/operations/readiness", body, token="operator-test")[0] == 503
        init.assert_not_called()
    finally:
        srv.shutdown()
        srv.server_close()


def test_http_blocks_legacy_posts_while_controlled_work_is_unresolved(setup, monkeypatch):
    import zhihuiti.oracle_server as server
    from .test_oracle_server import _start_server, _post

    monkeypatch.setenv("ZHIHUITI_API_TOKEN", "operator-test")
    monkeypatch.setattr(server, "_orchestrator", setup.orch)
    setup.controller._claim("crash-http-001", "readiness", None, datetime.now(timezone.utc))
    srv, port = _start_server()
    try:
        for path in ("/api/tasks", "/api/goals", "/api/population/rotate"):
            status, result = _post(port, path, {"task": "do work"}, token="operator-test")
            assert status == 409
            assert result["error"] == "controlled_request_unresolved"
        status, result = _post(port, "/api/operations/readiness", {"request_id": "crash-http-001"}, token="operator-test")
        assert status == 202 and result["status"] == "running"
        assert not setup.calls
    finally:
        srv.shutdown()
        srv.server_close()
