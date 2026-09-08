"""Auditable workflow primitives for human-approved video production.

This module deliberately does not generate or publish content.  It owns the
durable state and release boundary that agents, renderers, and a human editor
coordinate through.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class EpisodeState(str, Enum):
    DISCOVERED = "discovered"
    PITCHED = "pitched"
    BRIEF_APPROVED = "brief_approved"
    RESEARCHED = "researched"
    SCRIPTED = "scripted"
    VERIFIED = "verified"
    RENDERED = "rendered"
    QC_PASSED = "qc_passed"
    RELEASE_APPROVED = "release_approved"
    UPLOADED_UNLISTED = "uploaded_unlisted"
    PUBLISHED = "published"
    MEASURED = "measured"
    CHANGES_REQUESTED = "changes_requested"


PRODUCTION_FLOW = (
    EpisodeState.DISCOVERED,
    EpisodeState.PITCHED,
    EpisodeState.BRIEF_APPROVED,
    EpisodeState.RESEARCHED,
    EpisodeState.SCRIPTED,
    EpisodeState.VERIFIED,
    EpisodeState.RENDERED,
    EpisodeState.QC_PASSED,
    EpisodeState.RELEASE_APPROVED,
    EpisodeState.UPLOADED_UNLISTED,
    EpisodeState.PUBLISHED,
    EpisodeState.MEASURED,
)

HUMAN_GATES = {EpisodeState.BRIEF_APPROVED, EpisodeState.RELEASE_APPROVED}
REQUIRED_RELEASE_ARTIFACTS = (
    "render/master.mp4",
    "render/captions.srt",
    "script.md",
    "claims.json",
    "assets.json",
    "compliance.json",
    "qc.json",
)


class WorkflowError(ValueError):
    """Raised when an episode attempts an unsafe state transition."""


@dataclass(frozen=True)
class Approval:
    reviewer: str
    approved_at: str
    artifact_hashes: dict[str, str]


@dataclass
class Episode:
    id: str
    slug: str
    title: str
    state: EpisodeState = EpisodeState.DISCOVERED
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())
    approval: Approval | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["state"] = self.state.value
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Episode":
        data = dict(value)
        data["state"] = EpisodeState(data["state"])
        if data.get("approval"):
            data["approval"] = Approval(**data["approval"])
        return cls(**data)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".episode-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class VideoFactory:
    """Filesystem-backed episode workflow with explicit human gates."""

    def __init__(self, root: str | Path = "episodes"):
        self.root = Path(root)

    def create(self, slug: str, title: str) -> Episode:
        safe_slug = slug.strip().lower()
        if not safe_slug or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in safe_slug):
            raise WorkflowError("slug may contain only lowercase letters, numbers, '-' and '_'")
        episode_id = f"{datetime.now(timezone.utc):%Y-%m-%d}-{safe_slug}"
        episode_dir = self.root / episode_id
        if episode_dir.exists():
            raise WorkflowError(f"episode already exists: {episode_id}")
        episode_dir.mkdir(parents=True)
        episode = Episode(id=episode_id, slug=safe_slug, title=title.strip())
        episode.history.append({"at": episode.created_at, "event": "created", "to": episode.state.value})
        self.save(episode)
        return episode

    def directory(self, episode: Episode | str) -> Path:
        episode_id = episode.id if isinstance(episode, Episode) else episode
        return self.root / episode_id

    def load(self, episode_id: str) -> Episode:
        path = self.directory(episode_id) / "episode.json"
        if not path.is_file():
            raise WorkflowError(f"unknown episode: {episode_id}")
        return Episode.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, episode: Episode) -> None:
        _atomic_json_write(self.directory(episode) / "episode.json", episode.to_dict())

    def transition(
        self,
        episode_id: str,
        target: EpisodeState,
        *,
        actor: str,
        human: bool = False,
    ) -> Episode:
        episode = self.load(episode_id)
        if target == EpisodeState.CHANGES_REQUESTED:
            return self._move(episode, target, actor)
        if episode.state == EpisodeState.CHANGES_REQUESTED:
            raise WorkflowError("changes_requested must be resumed to a named prior state")
        current_index = PRODUCTION_FLOW.index(episode.state)
        if current_index + 1 >= len(PRODUCTION_FLOW) or PRODUCTION_FLOW[current_index + 1] != target:
            raise WorkflowError(f"invalid transition: {episode.state.value} -> {target.value}")
        if target in HUMAN_GATES and not human:
            raise WorkflowError(f"{target.value} requires a human actor")
        if target == EpisodeState.RELEASE_APPROVED:
            raise WorkflowError("use approve_release() to bind approval to artifact hashes")
        if target in (EpisodeState.UPLOADED_UNLISTED, EpisodeState.PUBLISHED):
            if not self.approval_is_current(episode_id):
                raise WorkflowError("approved artifacts changed; release approval is invalid")
        return self._move(episode, target, actor)

    def request_changes(self, episode_id: str, *, actor: str, reason: str) -> Episode:
        if not reason.strip():
            raise WorkflowError("a change request requires a reason")
        episode = self.load(episode_id)
        previous = episode.state
        episode.approval = None
        self._move(episode, EpisodeState.CHANGES_REQUESTED, actor, reason=reason)
        episode.history[-1]["from"] = previous.value
        self.save(episode)
        return episode

    def resume(self, episode_id: str, target: EpisodeState, *, actor: str) -> Episode:
        episode = self.load(episode_id)
        if episode.state != EpisodeState.CHANGES_REQUESTED:
            raise WorkflowError("only changes_requested episodes can be resumed")
        if target not in PRODUCTION_FLOW[: PRODUCTION_FLOW.index(EpisodeState.QC_PASSED) + 1]:
            raise WorkflowError("resume target must be at or before qc_passed")
        return self._move(episode, target, actor)

    def release_issues(self, episode_id: str) -> list[str]:
        episode = self.load(episode_id)
        base = self.directory(episode)
        issues = [f"missing artifact: {name}" for name in REQUIRED_RELEASE_ARTIFACTS if not (base / name).is_file()]
        issues.extend(self._json_gate_issues(base))
        return issues

    def approve_release(self, episode_id: str, *, reviewer: str) -> Episode:
        episode = self.load(episode_id)
        if episode.state != EpisodeState.QC_PASSED:
            raise WorkflowError("release approval requires qc_passed state")
        if not reviewer.strip():
            raise WorkflowError("reviewer identity is required")
        issues = self.release_issues(episode_id)
        if issues:
            raise WorkflowError("release blocked: " + "; ".join(issues))
        base = self.directory(episode)
        hashes = {name: hash_file(base / name) for name in REQUIRED_RELEASE_ARTIFACTS}
        episode.approval = Approval(reviewer.strip(), _now(), hashes)
        return self._move(episode, EpisodeState.RELEASE_APPROVED, reviewer)

    def approval_is_current(self, episode_id: str) -> bool:
        episode = self.load(episode_id)
        if not episode.approval:
            return False
        base = self.directory(episode)
        return all((base / name).is_file() and hash_file(base / name) == digest
                   for name, digest in episode.approval.artifact_hashes.items())

    def _move(self, episode: Episode, target: EpisodeState, actor: str, **details: Any) -> Episode:
        previous = episode.state
        episode.state = target
        episode.updated_at = _now()
        episode.history.append({
            "at": episode.updated_at,
            "event": "transition",
            "from": previous.value,
            "to": target.value,
            "actor": actor,
            **details,
        })
        self.save(episode)
        return episode

    @staticmethod
    def _json_gate_issues(base: Path) -> list[str]:
        issues: list[str] = []
        for name in ("claims.json", "assets.json", "compliance.json", "qc.json"):
            path = base / name
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                issues.append(f"invalid {name}: {exc}")
                continue
            if not isinstance(data, dict) or data.get("passed") is not True:
                issues.append(f"{name} has not passed")
        return issues
