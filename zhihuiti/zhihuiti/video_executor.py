"""Resumable wave executor for ``agent-plan.json`` video plans."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from zhihuiti.video_factory import WorkflowError


TaskHandler = Callable[[dict[str, Any], Path], None]


@dataclass(frozen=True)
class TaskRun:
    task_id: str
    status: str
    reason: str = ""
    output_hashes: dict[str, str] | None = None


class PlanExecutor:
    """Execute ready plan tasks while stopping at unapproved human gates.

    Handlers must produce the outputs declared by their task. The executor
    validates and hashes those outputs before marking work complete.
    """

    def __init__(self, handlers: dict[str, TaskHandler] | None = None, *, max_workers: int = 4):
        self.handlers = handlers or {}
        self.max_workers = max(1, max_workers)

    def run(
        self,
        plan_path: str | Path,
        *,
        execute: bool = False,
        approved_gates: set[str] | None = None,
        paid_budget: int = 0,
    ) -> dict[str, Any]:
        path = Path(plan_path)
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowError(f"cannot read agent plan: {exc}") from exc
        episode = Path(plan["episode_dir"])
        approved = approved_gates or set()
        tasks = {task["id"]: task for task in plan.get("tasks", [])}
        if not tasks:
            raise WorkflowError("agent plan contains no tasks")

        completed = self._completed_from_artifacts(tasks, episode)
        results: dict[str, TaskRun] = {}
        paid_used = 0
        for wave in plan.get("waves", []):
            runnable: list[dict[str, Any]] = []
            for task_id in wave:
                task = tasks[task_id]
                if task_id in completed:
                    results[task_id] = TaskRun(task_id, "skipped", "validated outputs already exist", completed[task_id])
                    continue
                missing = [dep for dep in task["dependencies"] if dep not in completed]
                if missing:
                    results[task_id] = TaskRun(task_id, "blocked", f"dependencies incomplete: {', '.join(missing)}")
                    continue
                if task.get("gate") and task_id not in approved:
                    results[task_id] = TaskRun(task_id, "human_required", "explicit approval not supplied")
                    continue
                if task.get("gate"):
                    hashes = self._output_hashes(task, episode)
                    if len(hashes) != len(task["outputs"]):
                        results[task_id] = TaskRun(task_id, "human_required", "approval artifact is missing")
                        continue
                    completed[task_id] = hashes
                    results[task_id] = TaskRun(task_id, "approved", "explicit approval supplied", hashes)
                    continue
                if execute and task_id not in self.handlers:
                    results[task_id] = TaskRun(task_id, "handler_required", "no executor registered")
                    continue
                if task.get("paid"):
                    if paid_used >= paid_budget:
                        results[task_id] = TaskRun(task_id, "budget_required", "paid task budget exhausted")
                        continue
                    paid_used += 1
                if not execute:
                    results[task_id] = TaskRun(task_id, "ready", "dry run")
                    continue
                runnable.append(task)

            if runnable:
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(runnable))) as pool:
                    futures = {pool.submit(self._execute_task, task, episode): task for task in runnable}
                    for future in as_completed(futures):
                        task = futures[future]
                        try:
                            hashes = future.result()
                            completed[task["id"]] = hashes
                            results[task["id"]] = TaskRun(task["id"], "completed", output_hashes=hashes)
                        except Exception as exc:
                            results[task["id"]] = TaskRun(task["id"], "failed", str(exc))

        report = {
            "schema_version": 1,
            "episode": plan.get("episode"),
            "plan": str(path.resolve()),
            "mode": "execute" if execute else "plan",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "paid_budget": paid_budget,
            "paid_slots_used": paid_used,
            "summary": {
                status: sum(result.status == status for result in results.values())
                for status in ("completed", "approved", "skipped", "ready", "blocked", "human_required", "budget_required", "handler_required", "failed")
            },
            "tasks": [asdict(results[task_id]) for task_id in tasks if task_id in results],
        }
        _atomic_json(episode / "agent-run.json", report)
        return report

    def _execute_task(self, task: dict[str, Any], episode: Path) -> dict[str, str]:
        before = self._input_snapshot(task, episode)
        self.handlers[task["id"]](task, episode)
        after = self._input_snapshot(task, episode)
        if before != after:
            raise WorkflowError("task inputs changed during execution")
        hashes = self._output_hashes(task, episode)
        if len(hashes) != len(task["outputs"]):
            missing = [name for name in task["outputs"] if name not in hashes]
            raise WorkflowError(f"handler did not produce outputs: {', '.join(missing)}")
        return hashes

    @classmethod
    def _completed_from_artifacts(cls, tasks: dict[str, dict[str, Any]], episode: Path) -> dict[str, dict[str, str]]:
        completed: dict[str, dict[str, str]] = {}
        for task_id, task in tasks.items():
            if task.get("gate"):
                continue
            hashes = cls._output_hashes(task, episode)
            if task.get("outputs") and len(hashes) == len(task["outputs"]):
                completed[task_id] = hashes
        return completed

    @staticmethod
    def _input_snapshot(task: dict[str, Any], episode: Path) -> dict[str, str]:
        return {name: _hash_path(episode / name) for name in task["inputs"] if (episode / name).exists()}

    @staticmethod
    def _output_hashes(task: dict[str, Any], episode: Path) -> dict[str, str]:
        return {name: _hash_path(episode / name) for name in task["outputs"] if (episode / name).exists()}


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(str(child.relative_to(path)).encode())
            digest.update(child.read_bytes())
    else:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".agent-run-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
