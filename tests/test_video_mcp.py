import json

from zhihuiti import mcp_server


def make_episode(tmp_path):
    episode = tmp_path / "ep001_v4"
    episode.mkdir()
    (episode / "episode.json").write_text('{"status":"active"}', encoding="utf-8")
    (episode / "script.md").write_text("script", encoding="utf-8")
    (episode / "shots.json").write_text(json.dumps({"shots": [
        {"scene": "scene_01", "prompt": "historical room", "filename": "scene_01.png"},
    ]}), encoding="utf-8")
    return episode


def payload(result):
    return json.loads(result["content"][0]["text"])


def test_video_tools_are_advertised():
    names = {tool["name"] for tool in mcp_server.TOOLS}
    assert {
        "zhihuiti_video_architect", "zhihuiti_video_doctor",
        "zhihuiti_video_daily_plan", "zhihuiti_video_plan_status",
    }.issubset(names)


def test_claude_can_architect_without_initializing_llm(tmp_path, monkeypatch):
    episode = make_episode(tmp_path)
    monkeypatch.setattr(mcp_server, "_get_orchestrator", lambda: (_ for _ in ()).throw(AssertionError("LLM initialized")))
    result = payload(mcp_server._handle_tool_call("zhihuiti_video_architect", {
        "episode_dir": str(episode), "write": True,
    }))
    assert result["episode"] == "ep001_v4"
    assert (episode / "agent-plan.json").is_file()


def test_claude_doctor_and_daily_plan_are_non_billing(tmp_path, monkeypatch):
    episode = make_episode(tmp_path)
    monkeypatch.setattr(mcp_server, "_get_orchestrator", lambda: (_ for _ in ()).throw(AssertionError("LLM initialized")))
    doctor = payload(mcp_server._handle_tool_call("zhihuiti_video_doctor", {"episode_dir": str(episode)}))
    daily = payload(mcp_server._handle_tool_call("zhihuiti_video_daily_plan", {"root": str(tmp_path)}))
    assert doctor["missing_images"] == ["scene_01.png"]
    assert daily["mode"] == "plan"


def test_claude_plan_status_never_executes_handlers(tmp_path):
    episode = make_episode(tmp_path)
    payload(mcp_server._handle_tool_call("zhihuiti_video_architect", {"episode_dir": str(episode)}))
    status = payload(mcp_server._handle_tool_call("zhihuiti_video_plan_status", {
        "plan": str(episode / "agent-plan.json"),
    }))
    assert status["mode"] == "plan"
    assert status["summary"]["completed"] == 0
