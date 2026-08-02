from __future__ import annotations

import json

from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.harness import EvalCase
from zhihuiti.models import AgentConfig, AgentRole
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


def test_harness_shadow_command_defaults_to_preview(tmp_path):
    db_path = tmp_path / "preview.db"
    result = CliRunner().invoke(main, ["harness", "shadow", "--db", str(db_path)])

    assert result.exit_code == 0
    assert "No candidate or trial records have been created" in result.output
    assert "Production canary: disabled" in result.output
    assert not db_path.exists()


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
    result = CliRunner().invoke(main, [
        "harness", "shadow",
        "--db", str(tmp_path / "shadow.db"),
        "--execute",
    ])

    assert result.exit_code == 0
    assert state == {"run": True, "closed": True, "tools_enabled": False}
    assert '"canary_started": false' in result.output
    assert '"candidate_status": "shadow_passed"' in result.output
