"""Integration tests for the Daemon — long-running orchestrator loop."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zhihuiti.daemon import Daemon


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_daemon(tmp_path: Path, **kwargs) -> Daemon:
    """Create a Daemon with temp paths to avoid polluting the real filesystem."""
    defaults = dict(
        goal="test goal: analyze BTC",
        db_path=str(tmp_path / "test.db"),
        max_rounds=2,
        max_tokens=0,
        checkpoint_interval=1,
        report_interval=1,
        report_dir=str(tmp_path / "reports"),
    )
    defaults.update(kwargs)
    return defaults


def _mock_orchestrator(scores: list[float] | None = None):
    """Create a mock Orchestrator that returns controlled results."""
    if scores is None:
        scores = [0.8, 0.9]

    orch = MagicMock()
    call_count = [0]

    def fake_execute_goal(goal: str) -> dict:
        idx = min(call_count[0], len(scores) - 1)
        result = {
            "goal": goal,
            "tasks": [
                {"task": f"sub-task-{call_count[0]}", "score": scores[idx], "result": "ok"},
            ],
        }
        call_count[0] += 1
        return result

    orch.execute_goal.side_effect = fake_execute_goal
    orch.llm = MagicMock()
    orch.llm.total_tokens = 0
    orch.memory = MagicMock()
    orch.memory.checkpoint.return_value = f"snap_{call_count[0]}"
    orch.close = MagicMock()
    return orch


# ── Initialization ────────────────────────────────────────────────────────

class TestDaemonInit:
    def test_default_values(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path))
        assert d.goal == "test goal: analyze BTC"
        assert d.max_rounds == 2
        assert d.current_round == 0
        assert d.total_tokens_used == 0
        assert d.round_results == []
        assert d._stop_event is not None

    def test_custom_values(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path, max_rounds=50, max_tokens=10000))
        assert d.max_rounds == 50
        assert d.max_tokens == 10000


# ── Build Summary ─────────────────────────────────────────────────────────

class TestBuildSummary:
    def test_empty_results(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path))
        summary = d._build_summary()
        assert summary["rounds_completed"] == 0
        assert summary["total_tasks"] == 0
        assert summary["avg_score"] == 0.0
        assert summary["failed_rounds"] == 0

    def test_with_results(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path))
        d.current_round = 3
        d.round_results = [
            {"goal": "g1", "tasks": [{"score": 0.8}, {"score": 0.6}]},
            {"goal": "g2", "tasks": [{"score": 0.9}]},
            {"goal": "g3", "tasks": [], "error": "boom"},
        ]
        summary = d._build_summary()
        assert summary["rounds_completed"] == 3
        assert summary["total_tasks"] == 3
        assert abs(summary["avg_score"] - (0.8 + 0.6 + 0.9) / 3) < 0.001
        assert summary["failed_rounds"] == 1

    def test_with_none_scores(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path))
        d.round_results = [
            {"goal": "g1", "tasks": [{"score": None}, {"score": 0.5}]},
        ]
        summary = d._build_summary()
        assert summary["avg_score"] == 0.5
        assert summary["total_tasks"] == 2


# ── State persistence ─────────────────────────────────────────────────────

class TestStatePersistence:
    def test_save_and_load_state(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))

        d = Daemon(**_make_daemon(tmp_path))
        d.current_round = 5
        d.total_tokens_used = 1234
        d._started_at = "2026-03-30T00:00:00Z"
        d.round_results = [
            {"goal": "g1", "tasks": [{"score": 0.8}], "_daemon_meta": {"round": 1}},
        ]
        d._save_state()

        assert state_file.exists()
        loaded = json.loads(state_file.read_text())
        assert loaded["current_round"] == 5
        assert loaded["total_tokens_used"] == 1234
        assert loaded["goal"] == "test goal: analyze BTC"

    def test_load_missing_state(self, tmp_path, monkeypatch):
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(tmp_path / "missing.json"))
        d = Daemon(**_make_daemon(tmp_path))
        assert d._load_state() is None

    def test_load_corrupt_state(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        state_file.write_text("not valid json{{{")
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))
        d = Daemon(**_make_daemon(tmp_path))
        assert d._load_state() is None


# ── Report generation ─────────────────────────────────────────────────────

class TestReportGeneration:
    def test_write_report_creates_file(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path))
        d.current_round = 2
        d._started_at = "2026-03-30T00:00:00Z"
        d.round_results = [
            {
                "goal": "g1",
                "tasks": [{"score": 0.8, "task": "t1"}],
                "_daemon_meta": {"round": 1, "elapsed_s": 5.0, "tokens_this_round": 100},
            },
            {
                "goal": "g2",
                "tasks": [],
                "error": "timeout",
                "_daemon_meta": {"round": 2, "elapsed_s": 30.0, "tokens_this_round": 50},
            },
        ]

        report_path = d._write_report()
        assert Path(report_path).exists()

        content = Path(report_path).read_text()
        assert "# Daemon Progress Report" in content
        assert "test goal: analyze BTC" in content
        assert "Round 1" in content
        assert "Round 2" in content
        assert "ERROR" in content
        assert "timeout" in content

    def test_report_with_no_rounds(self, tmp_path):
        d = Daemon(**_make_daemon(tmp_path))
        d._started_at = "2026-03-30T00:00:00Z"
        report_path = d._write_report()
        assert Path(report_path).exists()
        content = Path(report_path).read_text()
        assert "Rounds completed | 0" in content


# ── Full loop with mock orchestrator ──────────────────────────────────────

class TestDaemonLoop:
    def test_runs_to_completion(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))

        orch = _mock_orchestrator([0.8, 0.9])

        with patch("zhihuiti.orchestrator.Orchestrator", return_value=orch), \
             patch.dict("sys.modules", {"zhihuiti.orchestrator": MagicMock(Orchestrator=MagicMock(return_value=orch))}):
            d = Daemon(**_make_daemon(tmp_path, max_rounds=2))
            summary = d.start()

        assert summary["rounds_completed"] == 2
        assert summary["total_tasks"] == 2
        assert orch.execute_goal.call_count == 2
        assert orch.close.called

    def test_stop_mid_loop(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))

        orch = _mock_orchestrator([0.7])

        d = Daemon(**_make_daemon(tmp_path, max_rounds=10))

        def stop_after_first(goal):
            result = {"goal": goal, "tasks": [{"score": 0.7}]}
            d._stop_event.set()  # Signal stop after first round
            return result

        orch.execute_goal.side_effect = stop_after_first

        with patch.dict("sys.modules", {"zhihuiti.orchestrator": MagicMock(Orchestrator=MagicMock(return_value=orch))}):
            summary = d.start()

        # Should stop after 1 round, not 10
        assert summary["rounds_completed"] <= 2

    def test_token_budget_enforcement(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))

        orch = _mock_orchestrator([0.8, 0.8, 0.8, 0.8, 0.8])
        # Simulate token usage growing each round
        token_counter = [0]
        orig_execute = orch.execute_goal.side_effect

        def counting_execute(goal):
            token_counter[0] += 600
            orch.llm.total_tokens = token_counter[0]
            return orig_execute(goal)

        orch.execute_goal.side_effect = counting_execute

        with patch.dict("sys.modules", {"zhihuiti.orchestrator": MagicMock(Orchestrator=MagicMock(return_value=orch))}):
            d = Daemon(**_make_daemon(tmp_path, max_rounds=10, max_tokens=1000))
            summary = d.start()

        # Should stop before 10 rounds due to token budget
        assert summary["rounds_completed"] < 10

    def test_handles_orchestrator_error(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))

        orch = _mock_orchestrator()
        orch.execute_goal.side_effect = RuntimeError("LLM API down")

        with patch.dict("sys.modules", {"zhihuiti.orchestrator": MagicMock(Orchestrator=MagicMock(return_value=orch))}):
            d = Daemon(**_make_daemon(tmp_path, max_rounds=2))
            summary = d.start()

        assert summary["failed_rounds"] == 2
        assert summary["total_tasks"] == 0


# ── get_status class method ───────────────────────────────────────────────

class TestGetStatus:
    def test_returns_none_when_no_state(self, tmp_path, monkeypatch):
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(tmp_path / "nope.json"))
        assert Daemon.get_status() is None

    def test_returns_state_when_exists(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".zhihuiti_daemon.json"
        state_file.write_text(json.dumps({"daemon_id": "abc123", "current_round": 5}))
        monkeypatch.setattr("zhihuiti.daemon._STATE_FILE", str(state_file))

        status = Daemon.get_status()
        assert status is not None
        assert status["daemon_id"] == "abc123"
        assert status["current_round"] == 5
