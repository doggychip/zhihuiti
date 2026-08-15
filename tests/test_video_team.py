import json

import pytest

from zhihuiti.video_factory import WorkflowError
from zhihuiti.video_images import ImageBatch
from zhihuiti.video_team import MODEL_ROUTES, MultiModelVideoTeam


PNG = b"\x89PNG\r\n\x1a\nvalid"


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat_json(self, system, user, **kwargs):
        self.calls.append({"system": system, "user": json.loads(user), **kwargs})
        if "narration script" in system:
            return {"script": "Narration", "claims": [{"id": "C1", "text": "Fact"}]}
        if "visual scenes" in system:
            return {"shots": [{"scene": "scene_01", "prompt": "room", "filename": "scene_01.png"}]}
        return {"passed": True, "items": []}


class FakeImageProvider:
    def generate(self, **kwargs):
        return PNG


def test_routes_research_to_gemini_and_editorial_to_claude(tmp_path):
    llm = FakeLLM()
    team = MultiModelVideoTeam(llm, claude_model="claude-model", gemini_model="gemini-model")
    episode = tmp_path
    (episode / "brief.json").write_text('{"topic":"test"}', encoding="utf-8")
    research_task = {"inputs": ["brief.json"], "outputs": ["evidence-primary.json"]}
    pitch_task = {"inputs": [], "outputs": ["pitches.json"]}
    handlers = team.handlers()
    handlers["research"](research_task, episode)
    handlers["pitch"](pitch_task, episode)
    assert [call["model"] for call in llm.calls] == ["gemini-model", "claude-model"]
    assert MODEL_ROUTES["counter_research"] == "claude"


def test_script_adapter_writes_script_and_claim_ledger(tmp_path):
    llm = FakeLLM()
    team = MultiModelVideoTeam(llm, claude_model="claude", gemini_model="gemini")
    task = {"inputs": [], "outputs": ["script.md", "claims.json"]}
    team.handlers()["script"](task, tmp_path)
    assert (tmp_path / "script.md").read_text(encoding="utf-8") == "Narration"
    assert json.loads((tmp_path / "claims.json").read_text())["claims"][0]["id"] == "C1"


def test_image_worker_generates_manifest(tmp_path):
    (tmp_path / "shots.json").write_text(json.dumps({"shots": [
        {"scene": "scene_01", "prompt": "room", "filename": "scene_01.png"},
    ]}), encoding="utf-8")
    team = MultiModelVideoTeam(
        FakeLLM(), claude_model="claude", gemini_model="gemini",
        image_batch=ImageBatch(FakeImageProvider(), retry_delay=0),
    )
    team.handlers()["generate_images"]({"inputs": ["shots.json"], "outputs": ["images/manifest.json"]}, tmp_path)
    assert (tmp_path / "images" / "scene_01.png").is_file()
    manifest = json.loads((tmp_path / "images" / "manifest.json").read_text())
    assert manifest["images"][0]["status"] == "generated"


def test_requires_explicit_model_ids():
    with pytest.raises(WorkflowError, match="model IDs are required"):
        MultiModelVideoTeam(FakeLLM(), claude_model="", gemini_model="")
