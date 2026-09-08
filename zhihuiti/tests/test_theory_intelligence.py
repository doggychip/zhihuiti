"""Release catalog integrity: no silent fallback to an old persistent cache."""
import json
import shutil

import pytest
import zhihuiti.theory_intelligence as theory_intelligence


def test_bundled_catalog_matches_manifest_and_references():
    graph = theory_intelligence.TheoryGraph()
    stats = graph.get_stats()
    assert stats["theories"] == stats["catalog"]["theories"] == 352
    assert stats["collisions"] == stats["catalog"]["collisions"] == 401
    pairs = set()
    for collision in graph.collisions:
        assert collision["a"] in graph.theories
        assert collision["b"] in graph.theories
        pair = tuple(sorted([collision["a"], collision["b"]]))
        assert pair not in pairs
        pairs.add(pair)
    assert sum(t.get("provenance") == "curated" for t in graph.theories.values()) == 58


def test_missing_bundle_does_not_reuse_old_cache(tmp_path, monkeypatch):
    cache = tmp_path / "theory_graph"
    cache.mkdir()
    for name, shape in theory_intelligence._DATA_FILES.items():
        (cache / name).write_text(json.dumps(shape()))
    monkeypatch.setenv("ZHIHUITI_DATA", str(tmp_path))
    monkeypatch.setattr(theory_intelligence, "_BUNDLED_DATA_DIR", tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        theory_intelligence._resolve_data_dir()


def test_mismatched_bundle_fails_closed(tmp_path, monkeypatch):
    shutil.copytree(theory_intelligence._BUNDLED_DATA_DIR, tmp_path / "bundle")
    (tmp_path / "bundle" / "theories.json").write_text("{}")
    monkeypatch.setattr(theory_intelligence, "_BUNDLED_DATA_DIR", tmp_path / "bundle")
    with pytest.raises(ValueError, match="checksum mismatch"):
        theory_intelligence._resolve_data_dir()
