import json

import pytest
from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.video_architect import (
    AGENTS, TASKS, AgentSpec, PlanTask, VideoAgentArchitect, WorkerType,
    validate_architecture,
)
from zhihuiti.video_factory import WorkflowError


def episode(tmp_path):
    path = tmp_path / "ep001_v4"
    path.mkdir()
    return path


def test_default_architecture_has_human_gates_and_no_agent_publish_access():
    validate_architecture()
    gates = {task.id for task in TASKS if task.gate}
    assert gates == {"approve_brief", "approve_release"}
    assert all(not agent.may_publish for agent in AGENTS if agent.worker_type == WorkerType.AGENT)


def test_research_and_counter_research_share_parallel_wave(tmp_path):
    plan = VideoAgentArchitect().build(episode(tmp_path))
    assert any({"research", "counter_research"}.issubset(set(wave)) for wave in plan["waves"])
    assert plan["policy"]["auto_publish"] is False


def test_existing_artifacts_are_visible_but_human_gate_is_not_auto_completed(tmp_path):
    path = episode(tmp_path)
    (path / "script.md").write_text("approved script", encoding="utf-8")
    (path / "claims.json").write_text("{}", encoding="utf-8")
    (path / "approval.json").write_text("{}", encoding="utf-8")
    plan = VideoAgentArchitect().build(path)
    statuses = {task["id"]: task["status"] for task in plan["tasks"]}
    assert statuses["script"] == "artifact_present"
    assert statuses["approve_release"] == "human_required"


def test_rejects_multiple_writers_for_one_artifact():
    agents = (AgentSpec("one", "one", WorkerType.AGENT, "test"),)
    tasks = (
        PlanTask("a", "one", "a", (), (), ("same.json",)),
        PlanTask("b", "one", "b", (), (), ("same.json",)),
    )
    with pytest.raises(WorkflowError, match="multiple writers"):
        validate_architecture(agents, tasks)


def test_cli_writes_machine_readable_plan(tmp_path):
    path = episode(tmp_path)
    result = CliRunner().invoke(main, ["video", "architect", str(path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    plan_path = path / "agent-plan.json"
    assert payload["plan_path"] == str(plan_path)
    saved = json.loads(plan_path.read_text(encoding="utf-8"))
    assert saved["episode"] == "ep001_v4"
    assert len(saved["agents"]) == len(AGENTS)
