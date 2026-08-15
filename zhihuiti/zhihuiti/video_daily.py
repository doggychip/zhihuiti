"""One-shot daily video assembly pass suitable for cron or macOS launchd."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from zhihuiti.video_factory import WorkflowError
from zhihuiti.video_images import (
    ImageBatch, build_openai_batch, find_conflict_copies, load_shots, validate_image,
)


RETIRED_STATUSES = {"retired", "archived", "cancelled", "canceled"}


@dataclass(frozen=True)
class EpisodeHealth:
    episode: str
    status: str
    expected_images: int
    valid_images: int
    missing_images: list[str]
    invalid_images: dict[str, str]
    blockers: list[str]

    @property
    def ready_for_render(self) -> bool:
        return not self.blockers and self.expected_images > 0 and self.valid_images == self.expected_images

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["ready_for_render"] = self.ready_for_render
        return result


def discover_episodes(root: str | Path) -> list[Path]:
    base = Path(root).expanduser()
    if not base.is_dir():
        raise WorkflowError(f"episode root does not exist: {base}")
    return sorted(path.parent for path in base.glob("*/episode.json") if path.is_file())


def inspect_episode(directory: str | Path, *, image_dir: str = "images") -> EpisodeHealth:
    episode_dir = Path(directory)
    blockers: list[str] = []
    try:
        metadata = json.loads((episode_dir / "episode.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return EpisodeHealth(episode_dir.name, "invalid", 0, 0, [], {}, [f"invalid episode.json: {exc}"])
    status = str(metadata.get("status") or metadata.get("state") or "active").lower()
    if status in RETIRED_STATUSES:
        return EpisodeHealth(episode_dir.name, status, 0, 0, [], {}, ["episode is retired"])

    manifest = episode_dir / "shots.json"
    try:
        shots = load_shots(manifest)
    except WorkflowError as exc:
        return EpisodeHealth(episode_dir.name, status, 0, 0, [], {}, [str(exc)])

    images = episode_dir / image_dir
    missing: list[str] = []
    invalid: dict[str, str] = {}
    valid = 0
    for shot in shots:
        path = images / shot.filename
        if not path.exists():
            missing.append(shot.filename)
            continue
        issue = validate_image(path)
        if issue:
            invalid[shot.filename] = issue
        else:
            valid += 1
    if missing:
        blockers.append(f"{len(missing)} image(s) missing")
    if invalid:
        blockers.append(f"{len(invalid)} image(s) invalid or unavailable")
    if images.is_dir():
        conflicts = find_conflict_copies(images, shots)
        if conflicts:
            blockers.append("conflicting image copies: " + ", ".join(path.name for path in conflicts))
    if not (episode_dir / "script.md").is_file():
        blockers.append("script.md missing")
    return EpisodeHealth(episode_dir.name, status, len(shots), valid, missing, invalid, blockers)


class DailyVideoRun:
    """Inspect every live episode and optionally fill its missing images."""

    def __init__(self, root: str | Path, *, image_dir: str = "images"):
        self.root = Path(root).expanduser()
        self.image_dir = image_dir

    def run(
        self,
        *,
        execute_images: bool = False,
        model: str = "gpt-image-1",
        quality: str = "medium",
    ) -> dict[str, Any]:
        directories = discover_episodes(self.root)
        batch = build_openai_batch(model=model) if execute_images else ImageBatch()
        episodes: list[dict[str, Any]] = []
        for directory in directories:
            before = inspect_episode(directory, image_dir=self.image_dir)
            record: dict[str, Any] = {"before": before.to_dict(), "images": []}
            if before.status not in RETIRED_STATUSES and before.expected_images:
                results = batch.run(
                    load_shots(directory / "shots.json"),
                    directory / self.image_dir,
                    execute=execute_images,
                    quality=quality,
                )
                record["images"] = [asdict(item) for item in results]
            record["after"] = inspect_episode(directory, image_dir=self.image_dir).to_dict()
            episodes.append(record)
        return {
            "root": str(self.root),
            "mode": "execute" if execute_images else "plan",
            "episodes_found": len(directories),
            "ready_for_render": sum(item["after"]["ready_for_render"] for item in episodes),
            "episodes": episodes,
        }
