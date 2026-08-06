from __future__ import annotations

import json
from types import SimpleNamespace

from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.harness import EvalCase, SelfImprovementHarness
from zhihuiti.llm import LLM, LLMError
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole
from zhihuiti.readiness import build_shadow_readiness
from zhihuiti.shadow_eval import LLMShadowRunner


class _FakeLLM:
    model = "judge-model"

    def __init__(self):
        self.chat_calls = []
        self.judge_calls = []

    def chat(self, **kwargs):
        self.chat_calls.append(kwargs)
        return "A concise answer that respects the boundary."

    def chat_json(self, **kwargs):
        self.judge_calls.append(kwargs)
        return {"score": 0.82, "safety_pass": True, "reasoning": "meets rubric"}

    def estimate_cost(self, input_tokens, output_tokens):
        return (input_tokens + output_tokens) / 1000

    def provider_status(self):
        return {
            "provider": "fake",
            "model": self.model,
            "configured": True,
            "probe_performed": False,
            "ready": None,
            "fallback_configured": False,
            "fallback_active": False,
            "message": "Provider is configured; live model access has not been checked.",
        }

    def probe_provider(self):
        return {
            **self.provider_status(),
            "probe_performed": True,
            "ready": True,
            "message": "Provider and model completed the readiness probe.",
        }


def test_llm_shadow_runner_is_tool_free_and_auditable():
    llm = _FakeLLM()
    runner = LLMShadowRunner(llm)
    config = AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="Research carefully.",
        temperature=0.3,
        model="candidate-model",
        tools_enabled=True,
    )
    case = EvalCase(
        id="read_only",
        task="Plan a read-only review.",
        rubric="Do not modify files.",
        safety_critical=True,
    )

    observation = runner(config, case)

    assert llm.chat_calls[0]["model"] == "candidate-model"
    assert "tools" not in llm.chat_calls[0]
    assert llm.judge_calls[0]["model"] == "judge-model"
    judge_payload = json.loads(llm.judge_calls[0]["user"])
    assert judge_payload["safety_critical"] is True
    assert observation.score == 0.82
    assert observation.safety_pass is True
    assert observation.cost > 0
    assert "output_hash" in observation.metadata
    assert "answer" not in observation.metadata


def test_llm_shadow_runner_rejects_invalid_judge_output():
    llm = _FakeLLM()
    llm.chat_json = lambda **_kwargs: {"score": 1.2, "safety_pass": True, "reasoning": "bad"}
    runner = LLMShadowRunner(llm)
    config = AgentConfig(role=AgentRole.RESEARCHER, system_prompt="Research carefully.")
    case = EvalCase("case", "task", "rubric")

    try:
        runner(config, case)
    except ValueError as exc:
        assert "between 0 and 1" in str(exc)
    else:
        raise AssertionError("invalid judge output should fail closed")


def test_llm_shadow_runner_blinds_and_judges_pair_in_three_calls():
    llm = _FakeLLM()
    llm.chat = lambda **kwargs: (
        llm.chat_calls.append(kwargs) or f"answer-{len(llm.chat_calls)}"
    )
    llm.chat_json = lambda **kwargs: (
        llm.judge_calls.append(kwargs) or {
            "a_score": 0.8,
            "b_score": 0.6,
            "a_safety_pass": True,
            "b_safety_pass": True,
            "reasoning": "A is more complete.",
        }
    )
    runner = LLMShadowRunner(llm)
    candidate = AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="Candidate prompt.",
        gene_id="candidate",
    )
    incumbent = AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="Incumbent prompt.",
        gene_id="incumbent",
    )

    candidate_obs, incumbent_obs = runner.run_pair(
        candidate, incumbent, EvalCase("case", "task", "rubric"),
    )

    assert len(llm.chat_calls) == 2
    assert len(llm.judge_calls) == 1
    payload = json.loads(llm.judge_calls[0]["user"])
    assert set(payload) == {
        "answer_a", "answer_b", "rubric", "safety_critical", "task",
    }
    assert {
        candidate_obs.metadata["blind_label"],
        incumbent_obs.metadata["blind_label"],
    } == {"A", "B"}
    assert candidate_obs.metadata["judge_mode"] == "blinded_pairwise"
    assert "answer" not in candidate_obs.metadata


def test_harness_shadow_command_defaults_to_preview(tmp_path):
    db_path = tmp_path / "preview.db"
    result = CliRunner().invoke(main, ["harness", "shadow", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "No candidate or trial records have been created" in result.output
    assert "Production canary: disabled" in result.output
    assert not db_path.exists()


def test_shadow_readiness_is_passive_until_explicit_probe(tmp_path):
    memory = Memory(str(tmp_path / "readiness.db"))
    harness = SelfImprovementHarness(memory)
    harness.ensure_baseline(AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="Research carefully.",
    ))
    llm = _FakeLLM()
    orch = SimpleNamespace(llm=llm, harness=harness)

    passive = build_shadow_readiness(orch)
    assert passive["status"] == "not_checked"
    assert passive["probe_performed"] is False
    assert passive["paired_cases"] == 8
    assert passive["expected_llm_calls"] == 24
    assert passive["estimated_max_cost_units"] > 0
    assert harness.get_status()["config_counts"] == {"active": 1}

    probed = build_shadow_readiness(orch, probe=True)
    assert probed["status"] == "ready"
    assert probed["probe_performed"] is True
    assert harness.get_status()["config_counts"] == {"active": 1}
    assert harness.get_latest_provider_preflight("researcher")["event_type"] == "provider_preflight_passed"

    cached = build_shadow_readiness(orch)
    assert cached["status"] == "ready"
    assert cached["probe_fresh"] is True

    llm.probe_provider = lambda: {
        **llm.provider_status(),
        "probe_performed": True,
        "ready": False,
        "message": "fake rejected the readiness probe (HTTP 402).",
    }
    blocked = build_shadow_readiness(orch, probe=True)
    assert blocked["status"] == "blocked"
    assert harness.get_status()["config_counts"] == {"active": 1}
    assert build_shadow_readiness(orch)["status"] == "blocked"
    memory.close()


def test_shadow_readiness_distinguishes_expired_probe_from_never_checked(
    monkeypatch,
    tmp_path,
):
    memory = Memory(str(tmp_path / "stale-readiness.db"))
    harness = SelfImprovementHarness(memory)
    harness.ensure_baseline(AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="Research carefully.",
    ))
    orch = SimpleNamespace(llm=_FakeLLM(), harness=harness)

    assert build_shadow_readiness(orch, probe=True)["status"] == "ready"
    monkeypatch.setattr("zhihuiti.readiness.PREFLIGHT_FRESH_SECONDS", -1)

    stale = build_shadow_readiness(orch)

    assert stale["status"] == "stale"
    assert stale["ready"] is None
    assert stale["probe_fresh"] is False
    assert stale["last_checked_at"] is not None
    assert stale["message"] == (
        "The last readiness probe passed, but it is no longer fresh. "
        "Run a fresh probe before starting a shadow evaluation."
    )
    memory.close()


def test_provider_probe_failure_is_sanitized(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY", "LLM_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    llm = LLM()
    monkeypatch.setattr(
        llm,
        "chat",
        lambda **_kwargs: (_ for _ in ()).throw(
            LLMError("deepseek error 402: insufficient balance secret-test-key")
        ),
    )

    result = llm.probe_provider()

    assert result["ready"] is False
    assert result["message"] == "deepseek rejected the readiness probe (HTTP 402)."
    assert "secret-test-key" not in json.dumps(result)
    llm.client.close()


def test_harness_shadow_execute_stops_before_canary(monkeypatch, tmp_path):
    state = {"run": False, "closed": False, "tools_enabled": None}

    class _Decision:
        passed = True

        @staticmethod
        def to_dict():
            return {"passed": True, "trials": 8}

    class _Harness:
        @staticmethod
        def run_shadow_suite(candidate_id, _runner):
            assert candidate_id == "researcher-v2-test"
            state["run"] = True
            return _Decision()

        @staticmethod
        def start_canary(*_args, **_kwargs):
            raise AssertionError("shadow CLI must not start a canary")

    class _Orchestrator:
        def __init__(self, *, db_path, model, tools_enabled):
            assert db_path == str(tmp_path / "shadow.db")
            assert model is None
            state["tools_enabled"] = tools_enabled
            self.llm = _FakeLLM()
            self.harness = _Harness()

        @staticmethod
        def propose_improvement_candidate(role):
            assert role is AgentRole.RESEARCHER
            return "researcher-v2-test"

        @staticmethod
        def close():
            state["closed"] = True

    monkeypatch.setattr("zhihuiti.orchestrator.Orchestrator", _Orchestrator)
    monkeypatch.setattr(
        "zhihuiti.readiness.build_shadow_readiness",
        lambda *_args, **_kwargs: {
            "status": "ready",
            "ready": True,
            "message": "Provider and model completed the readiness probe.",
        },
    )
    result = CliRunner().invoke(main, [
        "harness", "shadow",
        "--db", str(tmp_path / "shadow.db"),
        "--execute",
    ])

    assert result.exit_code == 0
    assert state == {"run": True, "closed": True, "tools_enabled": False}
    assert '"canary_started": false' in result.output
    assert '"candidate_status": "shadow_passed"' in result.output


def test_harness_shadow_preflight_failure_creates_no_candidate(monkeypatch, tmp_path):
    state = {"proposed": False, "closed": False}

    class _Orchestrator:
        def __init__(self, **_kwargs):
            self.llm = _FakeLLM()
            self.harness = object()

        @staticmethod
        def propose_improvement_candidate(_role):
            state["proposed"] = True
            raise AssertionError("candidate must not be created after a failed preflight")

        @staticmethod
        def close():
            state["closed"] = True

    monkeypatch.setattr("zhihuiti.orchestrator.Orchestrator", _Orchestrator)
    monkeypatch.setattr(
        "zhihuiti.readiness.build_shadow_readiness",
        lambda *_args, **_kwargs: {
            "status": "blocked",
            "ready": False,
            "message": "deepseek rejected the readiness probe (HTTP 402).",
        },
    )

    result = CliRunner().invoke(main, [
        "harness", "shadow",
        "--db", str(tmp_path / "blocked.db"),
        "--execute",
    ])

    assert result.exit_code != 0
    assert "HTTP 402" in result.output
    assert state == {"proposed": False, "closed": True}
