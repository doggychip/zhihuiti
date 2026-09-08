"""Resumable image generation for video shot manifests.

The default operation is a cost-free plan. Network calls only happen when the
operator explicitly passes ``execute=True`` and supplies an API key.
"""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from zhihuiti.video_factory import WorkflowError


SUPPORTED_RATIOS = {"16:9": "1536x1024", "3:2": "1536x1024", "1:1": "1024x1024", "9:16": "1024x1536"}
IMAGE_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"RIFF")
CONFLICT_COPY = re.compile(r"^(?P<stem>.+) \d+\.(?:png|jpe?g|webp)$", re.IGNORECASE)


@dataclass(frozen=True)
class Shot:
    id: str
    prompt: str
    filename: str
    aspect_ratio: str = "16:9"


@dataclass(frozen=True)
class ImageResult:
    shot_id: str
    filename: str
    status: str
    reason: str = ""


class ImageProvider(Protocol):
    def generate(self, *, prompt: str, size: str, quality: str) -> bytes: ...


class OpenAIImageProvider:
    """Small Images API client with no SDK dependency."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-image-1",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 180.0,
    ):
        if not api_key:
            raise WorkflowError("OPENAI_API_KEY is required for image generation")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout)

    def generate(self, *, prompt: str, size: str, quality: str) -> bytes:
        response = self.client.post(
            f"{self.base_url}/images/generations",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": 1,
                "response_format": "b64_json",
            },
        )
        response.raise_for_status()
        payload = response.json()
        try:
            item = payload["data"][0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"], validate=True)
            if item.get("url"):
                download = self.client.get(item["url"])
                download.raise_for_status()
                return download.content
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise WorkflowError("image provider returned an invalid response") from exc
        raise WorkflowError("image provider returned neither image bytes nor a URL")

    def close(self) -> None:
        self.client.close()


def load_shots(path: str | Path) -> list[Shot]:
    """Load shots from a list or from an object containing a ``shots`` list."""
    manifest_path = Path(path)
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot read shot manifest: {exc}") from exc
    raw_shots = value.get("shots") if isinstance(value, dict) else value
    if not isinstance(raw_shots, list) or not raw_shots:
        raise WorkflowError("shot manifest must contain a non-empty shots list")

    shots: list[Shot] = []
    seen: set[str] = set()
    seen_filenames: set[str] = set()
    for index, raw in enumerate(raw_shots, start=1):
        if not isinstance(raw, dict):
            raise WorkflowError(f"shot {index} must be an object")
        shot_id = str(
            raw.get("id") or raw.get("shot_id") or raw.get("scene_id")
            or raw.get("scene") or f"{index:03d}"
        ).strip()
        prompt = str(raw.get("image_prompt") or raw.get("prompt") or "").strip()
        ratio = str(raw.get("aspect_ratio") or "16:9")
        if not prompt:
            raise WorkflowError(f"shot {shot_id} has no prompt")
        if shot_id in seen or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in shot_id):
            raise WorkflowError(f"shot id is duplicate or unsafe: {shot_id}")
        if ratio not in SUPPORTED_RATIOS:
            raise WorkflowError(f"shot {shot_id} has unsupported aspect ratio: {ratio}")
        filename = str(
            raw.get("filename") or raw.get("output_file")
            or raw.get("output") or f"shot_{shot_id}.png"
        )
        if Path(filename).name != filename or Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise WorkflowError(f"shot {shot_id} has an unsafe image filename")
        if filename.casefold() in seen_filenames:
            raise WorkflowError(f"duplicate image filename: {filename}")
        seen.add(shot_id)
        seen_filenames.add(filename.casefold())
        shots.append(Shot(shot_id, prompt, filename, ratio))
    return shots


class ImageBatch:
    """Plan or execute a resumable, bounded image batch."""

    def __init__(self, provider: ImageProvider | None = None, *, attempts: int = 3, retry_delay: float = 1.0):
        self.provider = provider
        self.attempts = max(1, attempts)
        self.retry_delay = max(0.0, retry_delay)

    def run(
        self,
        shots: list[Shot],
        output_dir: str | Path,
        *,
        execute: bool = False,
        limit: int | None = None,
        overwrite: bool = False,
        quality: str = "medium",
    ) -> list[ImageResult]:
        if execute and self.provider is None:
            raise WorkflowError("an image provider is required with execute=True")
        if limit is not None and limit < 1:
            raise WorkflowError("limit must be at least 1")
        selected = shots[:limit] if limit is not None else shots
        output = Path(output_dir)
        results: list[ImageResult] = []
        if not execute:
            return [ImageResult(shot.id, shot.filename, "planned") for shot in selected]

        output.mkdir(parents=True, exist_ok=True)
        with OutputLock(output):
            conflicts = find_conflict_copies(output, shots)
            if conflicts:
                names = ", ".join(path.name for path in conflicts)
                raise WorkflowError(f"conflicting image copies require human review: {names}")
            for shot in selected:
                destination = output / shot.filename
                if destination.exists() and not overwrite:
                    issue = validate_image(destination)
                    if issue:
                        results.append(ImageResult(shot.id, shot.filename, "failed", issue))
                    else:
                        results.append(ImageResult(shot.id, shot.filename, "skipped", "valid image already exists"))
                    continue
                last_error = ""
                for attempt in range(self.attempts):
                    try:
                        content = self.provider.generate(
                            prompt=shot.prompt,
                            size=SUPPORTED_RATIOS[shot.aspect_ratio],
                            quality=quality,
                        )
                        if not _has_image_signature(content, destination.suffix):
                            raise WorkflowError("provider returned invalid image bytes")
                        _atomic_bytes_write(destination, content)
                        results.append(ImageResult(shot.id, shot.filename, "generated"))
                        break
                    except (httpx.HTTPError, WorkflowError, OSError) as exc:
                        last_error = str(exc)
                        if attempt + 1 < self.attempts:
                            time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    results.append(ImageResult(shot.id, shot.filename, "failed", last_error))
        return results


def build_openai_batch(*, model: str, base_url: str | None = None) -> ImageBatch:
    provider = OpenAIImageProvider(
        os.environ.get("OPENAI_API_KEY", ""),
        model=model,
        base_url=base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    return ImageBatch(provider)


def _atomic_bytes_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".image-")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def validate_image(path: Path) -> str:
    """Return an issue instead of trusting a directory entry or cloud placeholder."""
    try:
        with path.open("rb") as stream:
            header = stream.read(12)
        if not _has_image_signature(header, path.suffix):
            return "existing file is empty, unavailable, or not a recognized image"
    except OSError as exc:
        return f"existing image is unavailable: {exc}"
    return ""


def _has_image_signature(content: bytes, suffix: str) -> bool:
    suffix = suffix.lower()
    if suffix == ".png":
        return content.startswith(IMAGE_SIGNATURES[0])
    if suffix in {".jpg", ".jpeg"}:
        return content.startswith(IMAGE_SIGNATURES[1])
    if suffix == ".webp":
        return content.startswith(IMAGE_SIGNATURES[2]) and content[8:12] == b"WEBP"
    return False


def find_conflict_copies(output: Path, shots: list[Shot]) -> list[Path]:
    """Detect iCloud/Finder-style ``name 2.png`` copies of expected shots."""
    expected_stems = {Path(shot.filename).stem.casefold() for shot in shots}
    conflicts: list[Path] = []
    try:
        candidates = list(output.iterdir())
    except OSError as exc:
        raise WorkflowError(f"cannot inspect image output directory: {exc}") from exc
    for path in candidates:
        match = CONFLICT_COPY.match(path.name)
        if match and match.group("stem").casefold() in expected_stems:
            conflicts.append(path)
    return sorted(conflicts)


class OutputLock:
    """Fail-fast process lock preventing two agents from writing one image set."""

    def __init__(self, output: Path):
        self.path = output / ".image-batch.lock"
        self.acquired = False

    def __enter__(self) -> "OutputLock":
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            try:
                owner = self.path.read_text(encoding="utf-8").strip()
            except OSError:
                owner = "unknown"
            raise WorkflowError(f"image output is locked by another process ({owner})") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()} created_at={time.time()}\n")
        self.acquired = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
