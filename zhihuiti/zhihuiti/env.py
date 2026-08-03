"""Environment parsing helpers."""

from __future__ import annotations

import os


def env_enabled(name: str) -> bool:
    """Return true only for explicit opt-in environment values."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
