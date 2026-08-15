import json

import pytest
from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.video_factory import WorkflowError
from zhihuiti.video_images import ImageBatch, load_shots


PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png"


class FakeProvider:
    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return PNG


def manifest(tmp_path, shots=None):
    path = tmp_path / "shots.json"
    path.write_text(json.dumps({"shots": shots or [
        {"id": "001", "image_prompt": "Archival portrait in soft window light"},
        {"id": "002", "prompt": "Close-up of handwritten notes", "aspect_ratio": "1:1"},
    ]}), encoding="utf-8")
    return path


def test_loads_both_prompt_spellings_and_default_filenames(tmp_path):
    shots = load_shots(manifest(tmp_path))
    assert [shot.filename for shot in shots] == ["shot_001.png", "shot_002.png"]
    assert shots[1].prompt == "Close-up of handwritten notes"


def test_loads_existing_scene_and_output_field_names(tmp_path):
    path = manifest(tmp_path, [{
        "scene": "scene_01", "image_prompt": "Historical room", "output_file": "scene_01.png",
    }])
    shot = load_shots(path)[0]
    assert shot.id == "scene_01"
    assert shot.filename == "scene_01.png"


def test_rejects_path_traversal_filename(tmp_path):
    path = manifest(tmp_path, [{"id": "1", "prompt": "test", "filename": "../secret.png"}])
    with pytest.raises(WorkflowError, match="unsafe image filename"):
        load_shots(path)


def test_rejects_duplicate_filenames(tmp_path):
    path = manifest(tmp_path, [
        {"id": "1", "prompt": "one", "filename": "same.png"},
        {"id": "2", "prompt": "two", "filename": "SAME.png"},
    ])
    with pytest.raises(WorkflowError, match="duplicate image filename"):
        load_shots(path)


def test_plan_does_not_create_directory_or_require_key(tmp_path):
    output = tmp_path / "images"
    results = ImageBatch().run(load_shots(manifest(tmp_path)), output)
    assert [item.status for item in results] == ["planned", "planned"]
    assert not output.exists()


def test_execute_is_bounded_and_resumable(tmp_path):
    output = tmp_path / "images"
    provider = FakeProvider()
    shots = load_shots(manifest(tmp_path))
    first = ImageBatch(provider).run(shots, output, execute=True, limit=1)
    assert first[0].status == "generated"
    assert (output / "shot_001.png").read_bytes() == PNG
    second = ImageBatch(provider).run(shots, output, execute=True)
    assert [item.status for item in second] == ["skipped", "generated"]
    assert len(provider.calls) == 2
    assert provider.calls[1]["size"] == "1024x1024"


def test_existing_cloud_placeholder_is_not_silently_skipped(tmp_path):
    output = tmp_path / "images"
    output.mkdir()
    (output / "shot_001.png").write_bytes(b"")
    provider = FakeProvider()
    results = ImageBatch(provider).run(load_shots(manifest(tmp_path)), output, execute=True, limit=1)
    assert results[0].status == "failed"
    assert "not a recognized image" in results[0].reason
    assert provider.calls == []


def test_conflict_copy_blocks_batch_before_generation(tmp_path):
    output = tmp_path / "images"
    output.mkdir()
    (output / "shot_001 2.png").write_bytes(PNG)
    provider = FakeProvider()
    with pytest.raises(WorkflowError, match="conflicting image copies"):
        ImageBatch(provider).run(load_shots(manifest(tmp_path)), output, execute=True)
    assert provider.calls == []


def test_existing_process_lock_blocks_second_writer(tmp_path):
    output = tmp_path / "images"
    output.mkdir()
    (output / ".image-batch.lock").write_text("pid=123", encoding="utf-8")
    with pytest.raises(WorkflowError, match="locked by another process"):
        ImageBatch(FakeProvider()).run(load_shots(manifest(tmp_path)), output, execute=True)


def test_cli_defaults_to_cost_free_plan(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, [
        "video", "images", str(manifest(tmp_path)), "--output", str(tmp_path / "images"), "--limit", "1",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["summary"]["planned"] == 1
    assert not (tmp_path / "images").exists()
