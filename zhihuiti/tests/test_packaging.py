from __future__ import annotations

import tomllib
from pathlib import Path


def test_distribution_includes_both_runtime_packages():
    config = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )

    included = config["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "zhihuiti*" in included
    assert "silicon_realms*" in included
