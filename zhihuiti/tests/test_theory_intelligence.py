"""Tests for production theory-data resolution."""

from __future__ import annotations

import json

import zhihuiti.theory_intelligence as theory_intelligence


class _Response:
    def __init__(self, payload):
        self.content = json.dumps(payload).encode()

    def raise_for_status(self):
        return None

    def json(self):
        return json.loads(self.content)


def test_downloads_pinned_graph_into_persistent_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        theory_intelligence, "_BUNDLED_DATA_DIR", tmp_path / "missing",
    )
    monkeypatch.setenv("ZHIHUITI_DATA", str(tmp_path / "data"))
    payloads = {
        "theories.json": {"nash": {"name": "Nash", "domain": "Economics"}},
        "collisions.json": [],
        "skeletons.json": [],
        "historical.json": [],
    }

    def fake_get(url, **_kwargs):
        filename = url.rsplit("/", 1)[-1]
        assert theory_intelligence._DATA_REVISION in url
        return _Response(payloads[filename])

    monkeypatch.setattr("httpx.get", fake_get)

    resolved = theory_intelligence._resolve_data_dir()

    assert resolved == tmp_path / "data" / "theory_graph"
    assert all((resolved / filename).exists() for filename in payloads)
    assert theory_intelligence.TheoryGraph(resolved).get_stats()["theories"] == 1
