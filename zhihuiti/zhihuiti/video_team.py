"""Provider-routed handlers for the multi-model video agent team."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol

from zhihuiti.video_factory import WorkflowError
from zhihuiti.video_images import ImageBatch, build_openai_batch, load_shots


class ChatBackend(Protocol):
    def chat_json(self, system: str, user: str, **kwargs: Any) -> dict | list: ...


ROLE_PROMPTS = {
    "discover": "Find dated, primary-source story candidates. Return JSON with a candidates array.",
    "pitch": "Act as an editorial architect. Rank candidates by evidence, novelty, and audience value. Return JSON with a pitches array.",
    "research": "Perform primary-source document analysis. Return JSON with claims, sources, dates, excerpts, and uncertainty.",
    "counter_research": "Find the strongest evidence against the proposed thesis. Return JSON with counterclaims and sources.",
    "script": "Write an original Chinese narration script. Separate fact, interpretation, and scenario; attach claim IDs.",
    "verify": "Independently critique and verify every script claim. Return JSON with passed, claims, failures, and required_changes.",
    "plan_scenes": "Map the verified script to visual scenes. Return JSON with a shots array containing scene, prompt, filename, and aspect_ratio.",
    "measure": "Analyze reliability and audience outcomes without rewarding unsupported sensationalism. Return JSON metrics.",
}

MODEL_ROUTES = {
    "discover": "gemini",
    "pitch": "claude",
    "research": "gemini",
    "counter_research": "claude",
    "script": "claude",
    "verify": "claude",
    "plan_scenes": "claude",
    "measure": "claude",
}


class MultiModelVideoTeam:
    """Build task handlers while keeping model routing explicit and auditable."""

    def __init__(self, llm: ChatBackend, *, claude_model: str, gemini_model: str,
                 image_batch: ImageBatch | None = None, image_quality: str = "medium"):
        if not claude_model or not gemini_model:
            raise WorkflowError("Claude and Gemini model IDs are required")
        self.llm = llm
        self.models = {"claude": claude_model, "gemini": gemini_model}
        self.image_batch = image_batch
        self.image_quality = image_quality

    @classmethod
    def from_environment(cls, llm: ChatBackend) -> "MultiModelVideoTeam":
        claude = os.environ.get("VIDEO_CLAUDE_MODEL", "")
        gemini = os.environ.get("VIDEO_GEMINI_MODEL", "")
        image_batch = None
        if os.environ.get("OPENAI_API_KEY"):
            image_batch = build_openai_batch(model=os.environ.get("VIDEO_IMAGE_MODEL", "gpt-image-1"))
        return cls(llm, claude_model=claude, gemini_model=gemini, image_batch=image_batch,
                   image_quality=os.environ.get("VIDEO_IMAGE_QUALITY", "medium"))

    def handlers(self) -> dict[str, Any]:
        handlers = {task_id: self._agent_handler(task_id) for task_id in MODEL_ROUTES}
        if self.image_batch is not None:
            handlers["generate_images"] = self._image_handler
        return handlers

    def _agent_handler(self, task_id: str):
        def handle(task: dict[str, Any], episode: Path) -> None:
            inputs = self._read_inputs(task, episode)
            route = MODEL_ROUTES[task_id]
            response = self.llm.chat_json(
                ROLE_PROMPTS[task_id],
                json.dumps({"episode": episode.name, "inputs": inputs}, ensure_ascii=False),
                model=self.models[route],
                temperature=0.2 if task_id in {"research", "counter_research", "verify"} else 0.6,
            )
            self._write_agent_outputs(task_id, task, episode, response)
        return handle

    def _image_handler(self, task: dict[str, Any], episode: Path) -> None:
        shots = load_shots(episode / "shots.json")
        results = self.image_batch.run(
            shots, episode / "images", execute=True, quality=self.image_quality,
        )
        failed = [result for result in results if result.status == "failed"]
        if failed:
            raise WorkflowError(f"{len(failed)} image(s) failed")
        manifest = {
            "provider": "openai-compatible",
            "images": [
                {"shot_id": result.shot_id, "filename": result.filename, "status": result.status}
                for result in results
            ],
        }
        _atomic_json(episode / "images" / "manifest.json", manifest)

    @staticmethod
    def _read_inputs(task: dict[str, Any], episode: Path) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for name in task["inputs"]:
            path = episode / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            try:
                inputs[name] = json.loads(text)
            except json.JSONDecodeError:
                inputs[name] = text
        return inputs

    @staticmethod
    def _write_agent_outputs(task_id: str, task: dict[str, Any], episode: Path,
                             response: dict | list) -> None:
        outputs = task["outputs"]
        if task_id == "script":
            if not isinstance(response, dict) or not response.get("script") or not isinstance(response.get("claims"), list):
                raise WorkflowError("scriptwriter response requires script and claims")
            _atomic_text(episode / "script.md", str(response["script"]))
            _atomic_json(episode / "claims.json", {"claims": response["claims"]})
            return
        if len(outputs) != 1:
            raise WorkflowError(f"no output adapter for task {task_id}")
        output = episode / outputs[0]
        if output.suffix != ".json":
            raise WorkflowError(f"agent output must be JSON for task {task_id}")
        value = response if isinstance(response, dict) else {"items": response}
        _atomic_json(output, value)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".video-team-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
