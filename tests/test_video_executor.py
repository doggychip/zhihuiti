import json

from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.video_executor import PlanExecutor


def write_plan(tmp_path, tasks, waves):
    episode = tmp_path / "episode"
    episode.mkdir()
    plan = episode / "agent-plan.json"
    plan.write_text(json.dumps({
        "episode": "episode", "episode_dir": str(episode), "tasks": tasks, "waves": waves,
    }), encoding="utf-8")
    return episode, plan


def task(task_id, *, deps=(), inputs=(), outputs=(), gate=False, paid=False):
    return {
        "id": task_id, "dependencies": list(deps), "inputs": list(inputs),
        "outputs": list(outputs), "gate": gate, "paid": paid,
    }


def test_executor_runs_dependencies_and_hashes_outputs(tmp_path):
    tasks = [task("one", outputs=("one.json",)), task("two", deps=("one",), inputs=("one.json",), outputs=("two.json",))]
    episode, plan = write_plan(tmp_path, tasks, [["one"], ["two"]])

    def one(_, directory):
        (directory / "one.json").write_text('{"one": 1}', encoding="utf-8")

    def two(_, directory):
        (directory / "two.json").write_text('{"two": 2}', encoding="utf-8")

    report = PlanExecutor({"one": one, "two": two}).run(plan, execute=True)
    assert report["summary"]["completed"] == 2
    assert all(item["output_hashes"] for item in report["tasks"])
    assert (episode / "agent-run.json").is_file()


def test_executor_resumes_without_calling_handler(tmp_path):
    tasks = [task("one", outputs=("one.json",))]
    episode, plan = write_plan(tmp_path, tasks, [["one"]])
    (episode / "one.json").write_text("done", encoding="utf-8")
    calls = []
    report = PlanExecutor({"one": lambda *_: calls.append(1)}).run(plan, execute=True)
    assert report["summary"]["skipped"] == 1
    assert calls == []


def test_human_gate_blocks_dependants_without_approval(tmp_path):
    tasks = [
        task("gate", outputs=("approval.json",), gate=True),
        task("after", deps=("gate",), outputs=("after.json",)),
    ]
    _, plan = write_plan(tmp_path, tasks, [["gate"], ["after"]])
    report = PlanExecutor().run(plan)
    statuses = {item["task_id"]: item["status"] for item in report["tasks"]}
    assert statuses == {"gate": "human_required", "after": "blocked"}


def test_explicit_gate_approval_requires_receipt_and_unlocks_dependant(tmp_path):
    tasks = [
        task("gate", outputs=("approval.json",), gate=True),
        task("after", deps=("gate",), outputs=("after.json",)),
    ]
    episode, plan = write_plan(tmp_path, tasks, [["gate"], ["after"]])
    (episode / "approval.json").write_text('{"reviewer": "Ryan"}', encoding="utf-8")
    report = PlanExecutor().run(plan, approved_gates={"gate"})
    statuses = {item["task_id"]: item["status"] for item in report["tasks"]}
    assert statuses == {"gate": "approved", "after": "ready"}


def test_paid_task_requires_budget(tmp_path):
    tasks = [task("paid", outputs=("image.png",), paid=True)]
    _, plan = write_plan(tmp_path, tasks, [["paid"]])
    report = PlanExecutor().run(plan)
    assert report["tasks"][0]["status"] == "budget_required"


def test_missing_handler_does_not_consume_paid_budget(tmp_path):
    tasks = [task("paid", outputs=("image.png",), paid=True)]
    _, plan = write_plan(tmp_path, tasks, [["paid"]])
    report = PlanExecutor().run(plan, execute=True, paid_budget=1)
    assert report["tasks"][0]["status"] == "handler_required"
    assert report["paid_slots_used"] == 0


def test_cli_plan_mode_writes_report(tmp_path):
    _, plan = write_plan(tmp_path, [task("one", outputs=("one.json",))], [["one"]])
    result = CliRunner().invoke(main, ["video", "run-plan", str(plan)])
    assert result.exit_code == 0
    assert json.loads(result.output)["summary"]["ready"] == 1
