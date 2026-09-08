import json

from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.video_daily import DailyVideoRun, discover_episodes, inspect_episode


PNG = b"\x89PNG\r\n\x1a\nvalid"


def make_episode(root, name="ep001_v4", *, status="active", with_script=True):
    episode = root / name
    episode.mkdir(parents=True)
    (episode / "episode.json").write_text(json.dumps({"status": status}), encoding="utf-8")
    (episode / "shots.json").write_text(json.dumps({"shots": [
        {"scene": "scene_01", "prompt": "one", "filename": "scene_01.png"},
        {"scene": "scene_02", "prompt": "two", "filename": "scene_02.png"},
    ]}), encoding="utf-8")
    if with_script:
        (episode / "script.md").write_text("script", encoding="utf-8")
    return episode


def test_discovers_only_episode_folders(tmp_path):
    live = make_episode(tmp_path)
    (tmp_path / "random").mkdir()
    assert discover_episodes(tmp_path) == [live]


def test_doctor_reports_missing_placeholder_and_conflict(tmp_path):
    episode = make_episode(tmp_path)
    images = episode / "images"
    images.mkdir()
    (images / "scene_01.png").write_bytes(b"")
    (images / "scene_01 2.png").write_bytes(PNG)
    health = inspect_episode(episode)
    assert health.expected_images == 2
    assert health.valid_images == 0
    assert health.missing_images == ["scene_02.png"]
    assert "scene_01.png" in health.invalid_images
    assert any("conflicting image copies" in blocker for blocker in health.blockers)
    assert not health.ready_for_render


def test_doctor_marks_complete_episode_ready(tmp_path):
    episode = make_episode(tmp_path)
    images = episode / "images"
    images.mkdir()
    (images / "scene_01.png").write_bytes(PNG)
    (images / "scene_02.png").write_bytes(PNG)
    assert inspect_episode(episode).ready_for_render


def test_daily_plan_skips_retired_and_does_not_write(tmp_path):
    live = make_episode(tmp_path, "ep_live")
    make_episode(tmp_path, "ep_retired", status="retired")
    result = DailyVideoRun(tmp_path).run()
    assert result["mode"] == "plan"
    assert result["episodes_found"] == 2
    assert len(result["episodes"][0]["images"]) == 2
    assert result["episodes"][1]["images"] == []
    assert not (live / "images").exists()


def test_daily_cli_outputs_machine_readable_report(tmp_path):
    make_episode(tmp_path)
    result = CliRunner().invoke(main, ["video", "daily", str(tmp_path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["episodes_found"] == 1
    assert payload["episodes"][0]["before"]["missing_images"] == ["scene_01.png", "scene_02.png"]
