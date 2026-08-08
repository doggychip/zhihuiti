from __future__ import annotations

import base64
import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "zeabur_volume_export.py"
SPEC = importlib.util.spec_from_file_location("zeabur_volume_export", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
_decode_chunk_output = MODULE._decode_chunk_output


def test_decode_chunk_ignores_cli_status_lines():
    payload = b"sqlite-backup"
    encoded = base64.b64encode(payload).decode()
    output = f"{encoded}\n\x1b[34mINFO\x1b[0m update available\n"

    assert _decode_chunk_output(output) == payload


def test_decode_chunk_rejects_empty_output():
    with pytest.raises(RuntimeError, match="empty backup chunk"):
        _decode_chunk_output("INFO no data")
