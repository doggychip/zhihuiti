"""Deterministic multi-agent architecture for the video factory.

The architect defines ownership and dependencies; it does not pretend that an
LLM response is a completed production artifact. Human gates and deterministic
workers are represented explicitly in the same plan as creative agents.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from zhihuiti.dag import topological_waves
from zhihuiti.video_factory import WorkflowError


class WorkerType(str, Enum):
    AGENT = "agent"
    DETERMINISTIC = "deterministic"
    HUMAN = "human"


@dataclass(frozen=True)
class AgentSpec:
    id: str
    role: str
    worker_type: WorkerType
    objective: str
    may_publish: bool = False


@dataclass(frozen=True)
class PlanTask:
    id: str
    owner: str
    description: str
    dependencies: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    gate: bool = False
    paid: bool = False


AGENTS = (
    AgentSpec("scout", "source scout", WorkerType.AGENT, "Find dated primary-source story candidates."),
    AgentSpec("pitch", "pitch editor", WorkerType.AGENT, "Rank evidence-backed stories without clickbait."),
    AgentSpec("brief_editor", "editor in chief", WorkerType.HUMAN, "Approve topic, thesis, and risk budget."),
    AgentSpec("research", "primary researcher", WorkerType.AGENT, "Build the claim-level evidence pack."),
    AgentSpec("counter", "counter-thesis researcher", WorkerType.AGENT, "Find the strongest contrary evidence."),
    AgentSpec("writer", "scriptwriter", WorkerType.AGENT, "Write an original claim-linked narration script."),
    AgentSpec("factcheck", "independent fact checker", WorkerType.AGENT, "Verify script claims with isolated context."),
    AgentSpec("scenes", "scene planner", WorkerType.AGENT, "Map approved narration to visual prompts and timing."),
    AgentSpec("narration", "narration worker", WorkerType.DETERMINISTIC, "Generate and verify licensed narration."),
    AgentSpec("images", "image worker", WorkerType.DETERMINISTIC, "Generate missing manifest images idempotently."),
    AgentSpec("exposure", "exposure worker", WorkerType.DETERMINISTIC, "Normalize measured exposure without mutating sources."),
    AgentSpec("captions", "caption worker", WorkerType.DETERMINISTIC, "Align captions to narration and approved text."),
    AgentSpec("render", "render worker", WorkerType.DETERMINISTIC, "Assemble the review master reproducibly."),
    AgentSpec("qc", "audiovisual QC", WorkerType.DETERMINISTIC, "Measure render, audio, caption, and provenance invariants."),
    AgentSpec("release_editor", "release reviewer", WorkerType.HUMAN, "Review and approve exact release hashes."),
    AgentSpec("publisher", "publisher", WorkerType.DETERMINISTIC, "Upload unlisted and publish only an approved version.", True),
    AgentSpec("analytics", "performance analyst", WorkerType.AGENT, "Measure outcomes without rewarding unsupported claims."),
)


TASKS = (
    PlanTask("discover", "scout", "Collect story candidates.", (), (), ("story-candidates.json",)),
    PlanTask("pitch", "pitch", "Score and select candidate pitches.", ("discover",), ("story-candidates.json",), ("pitches.json",)),
    PlanTask("approve_brief", "brief_editor", "Approve one editorial brief.", ("pitch",), ("pitches.json",), ("brief.json",), True),
    PlanTask("research", "research", "Research the approved thesis.", ("approve_brief",), ("brief.json",), ("evidence-primary.json",)),
    PlanTask("counter_research", "counter", "Research the strongest countercase.", ("approve_brief",), ("brief.json",), ("evidence-counter.json",)),
    PlanTask("script", "writer", "Write a claim-linked script.", ("research", "counter_research"), ("brief.json", "evidence-primary.json", "evidence-counter.json"), ("script.md", "claims.json")),
    PlanTask("verify", "factcheck", "Independently verify every material claim.", ("script",), ("script.md", "claims.json"), ("verification.json",)),
    PlanTask("plan_scenes", "scenes", "Create the shot manifest.", ("verify",), ("script.md", "verification.json"), ("shots.json",)),
    PlanTask("narrate", "narration", "Produce narration segments.", ("verify",), ("script.md",), ("audio/manifest.json",), paid=True),
    PlanTask("generate_images", "images", "Produce all expected source images.", ("plan_scenes",), ("shots.json",), ("images/manifest.json",), paid=True),
    PlanTask("normalize_exposure", "exposure", "Normalize images into build outputs.", ("generate_images",), ("shots.json", "images/manifest.json"), ("build/images/manifest.json",)),
    PlanTask("caption", "captions", "Generate aligned captions.", ("narrate", "verify"), ("script.md", "audio/manifest.json"), ("build/captions.srt",)),
    PlanTask("render", "render", "Render the review master.", ("normalize_exposure", "narrate", "caption"), ("build/images/manifest.json", "audio/manifest.json", "build/captions.srt"), ("build/master.mp4",)),
    PlanTask("qc", "qc", "Run deterministic audiovisual QC.", ("render",), ("build/master.mp4", "script.md", "shots.json"), ("build/qc.json",)),
    PlanTask("approve_release", "release_editor", "Approve exact final artifacts.", ("qc",), ("build/master.mp4", "build/qc.json"), ("approval.json",), True),
    PlanTask("upload_unlisted", "publisher", "Upload the approved master as unlisted.", ("approve_release",), ("approval.json", "build/master.mp4"), ("upload.json",)),
    PlanTask("publish", "publisher", "Publish only after explicit release approval.", ("upload_unlisted",), ("approval.json", "upload.json"), ("publication.json",)),
    PlanTask("measure", "analytics", "Record audience and reliability outcomes.", ("publish",), ("publication.json",), ("metrics.json",)),
)


def validate_architecture(agents: tuple[AgentSpec, ...] = AGENTS,
                          tasks: tuple[PlanTask, ...] = TASKS) -> None:
    agent_ids = {agent.id for agent in agents}
    task_ids = {task.id for task in tasks}
    if len(agent_ids) != len(agents) or len(task_ids) != len(tasks):
        raise WorkflowError("agent and task IDs must be unique")
    for task in tasks:
        if task.owner not in agent_ids:
            raise WorkflowError(f"task {task.id} has unknown owner {task.owner}")
        unknown = set(task.dependencies) - task_ids
        if unknown:
            raise WorkflowError(f"task {task.id} has unknown dependencies: {sorted(unknown)}")
        owner = next(agent for agent in agents if agent.id == task.owner)
        if task.gate and owner.worker_type != WorkerType.HUMAN:
            raise WorkflowError(f"gate {task.id} must be owned by a human")
    output_owners: dict[str, str] = {}
    for task in tasks:
        for output in task.outputs:
            if output in output_owners:
                raise WorkflowError(f"artifact {output} has multiple writers")
            output_owners[output] = task.id
    topological_waves(list(task_ids), {task.id: list(task.dependencies) for task in tasks})


class VideoAgentArchitect:
    """Build and persist the canonical multi-agent execution plan."""

    def build(self, episode_dir: str | Path) -> dict[str, Any]:
        validate_architecture()
        directory = Path(episode_dir).expanduser().resolve()
        if not directory.is_dir():
            raise WorkflowError(f"episode directory does not exist: {directory}")
        task_map = {task.id: task for task in TASKS}
        waves = topological_waves(
            list(task_map), {task.id: list(task.dependencies) for task in TASKS},
        )
        tasks: list[dict[str, Any]] = []
        for task in TASKS:
            item = asdict(task)
            item["status"] = self._status(directory, task)
            tasks.append(item)
        return {
            "schema_version": 1,
            "episode": directory.name,
            "episode_dir": str(directory),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "policy": {
                "human_gates": [task.id for task in TASKS if task.gate],
                "auto_publish": False,
                "single_writer_per_artifact": True,
                "paid_tasks_require_budget": True,
            },
            "agents": [{**asdict(agent), "worker_type": agent.worker_type.value} for agent in AGENTS],
            "tasks": tasks,
            "waves": waves,
        }

    def write(self, episode_dir: str | Path, output: str | Path | None = None,
              *, plan: dict[str, Any] | None = None) -> Path:
        plan = plan or self.build(episode_dir)
        path = Path(output) if output else Path(episode_dir) / "agent-plan.json"
        _atomic_write(path, plan)
        return path

    @staticmethod
    def _status(directory: Path, task: PlanTask) -> str:
        if task.gate:
            return "human_required"
        if task.outputs and all((directory / output).exists() for output in task.outputs):
            return "artifact_present"
        return "pending"


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".agent-plan-")
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
