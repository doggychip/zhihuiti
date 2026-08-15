import json

import pytest
from click.testing import CliRunner

from zhihuiti.cli import main
from zhihuiti.video_factory import EpisodeState, REQUIRED_RELEASE_ARTIFACTS, VideoFactory, WorkflowError


def make_factory(tmp_path):
    return VideoFactory(tmp_path / "episodes")


def advance_to_qc(factory, episode_id):
    steps = [
        EpisodeState.PITCHED,
        EpisodeState.BRIEF_APPROVED,
        EpisodeState.RESEARCHED,
        EpisodeState.SCRIPTED,
        EpisodeState.VERIFIED,
        EpisodeState.RENDERED,
        EpisodeState.QC_PASSED,
    ]
    for state in steps:
        factory.transition(
            episode_id,
            state,
            actor="editor" if state == EpisodeState.BRIEF_APPROVED else "agent",
            human=state == EpisodeState.BRIEF_APPROVED,
        )


def write_release_artifacts(factory, episode_id):
    base = factory.directory(episode_id)
    for relative in REQUIRED_RELEASE_ARTIFACTS:
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text(json.dumps({"passed": True}), encoding="utf-8")
        else:
            path.write_text("approved content", encoding="utf-8")


def test_create_persists_episode(tmp_path):
    factory = make_factory(tmp_path)
    episode = factory.create("rates-explained", "Rates explained")
    loaded = factory.load(episode.id)
    assert loaded.state == EpisodeState.DISCOVERED
    assert loaded.title == "Rates explained"
    assert loaded.history[0]["event"] == "created"


def test_rejects_skipped_state_and_automated_human_gate(tmp_path):
    factory = make_factory(tmp_path)
    episode = factory.create("rates", "Rates")
    with pytest.raises(WorkflowError, match="invalid transition"):
        factory.transition(episode.id, EpisodeState.RESEARCHED, actor="agent")
    factory.transition(episode.id, EpisodeState.PITCHED, actor="agent")
    with pytest.raises(WorkflowError, match="requires a human"):
        factory.transition(episode.id, EpisodeState.BRIEF_APPROVED, actor="agent")


def test_release_requires_artifacts_that_pass(tmp_path):
    factory = make_factory(tmp_path)
    episode = factory.create("rates", "Rates")
    advance_to_qc(factory, episode.id)
    with pytest.raises(WorkflowError, match="missing artifact"):
        factory.approve_release(episode.id, reviewer="Ryan")
    write_release_artifacts(factory, episode.id)
    (factory.directory(episode) / "qc.json").write_text('{"passed": false}', encoding="utf-8")
    with pytest.raises(WorkflowError, match="qc.json has not passed"):
        factory.approve_release(episode.id, reviewer="Ryan")


def test_approval_binds_exact_artifact_hashes(tmp_path):
    factory = make_factory(tmp_path)
    episode = factory.create("rates", "Rates")
    advance_to_qc(factory, episode.id)
    write_release_artifacts(factory, episode.id)
    approved = factory.approve_release(episode.id, reviewer="Ryan")
    assert approved.state == EpisodeState.RELEASE_APPROVED
    assert approved.approval.reviewer == "Ryan"
    assert factory.approval_is_current(episode.id)
    (factory.directory(episode) / "script.md").write_text("changed", encoding="utf-8")
    assert not factory.approval_is_current(episode.id)
    with pytest.raises(WorkflowError, match="approval is invalid"):
        factory.transition(episode.id, EpisodeState.UPLOADED_UNLISTED, actor="publisher")


def test_change_request_clears_approval_and_can_resume(tmp_path):
    factory = make_factory(tmp_path)
    episode = factory.create("rates", "Rates")
    advance_to_qc(factory, episode.id)
    write_release_artifacts(factory, episode.id)
    factory.approve_release(episode.id, reviewer="Ryan")
    changed = factory.request_changes(episode.id, actor="Ryan", reason="Chart label is unclear")
    assert changed.state == EpisodeState.CHANGES_REQUESTED
    assert changed.approval is None
    resumed = factory.resume(episode.id, EpisodeState.RENDERED, actor="producer")
    assert resumed.state == EpisodeState.RENDERED


def test_cli_creates_and_reports_episode(tmp_path):
    runner = CliRunner()
    root = tmp_path / "episodes"
    created = runner.invoke(main, ["video", "create", "rates", "Rates explained", "--root", str(root)])
    assert created.exit_code == 0
    episode_id = json.loads(created.output)["id"]
    status = runner.invoke(main, ["video", "status", episode_id, "--root", str(root)])
    assert status.exit_code == 0
    assert json.loads(status.output)["state"] == "discovered"
