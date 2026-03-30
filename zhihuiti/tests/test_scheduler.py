"""Tests for MonitorScheduler — CRUD, interval parsing, due detection."""

from __future__ import annotations

import pytest

from zhihuiti.memory import Memory
from zhihuiti.scheduler import MonitorScheduler, parse_interval


def _make_scheduler() -> tuple[MonitorScheduler, Memory]:
    mem = Memory(":memory:")
    return MonitorScheduler(mem), mem


class TestParseInterval:
    def test_hours(self):
        assert parse_interval("2h") == 7200

    def test_minutes(self):
        assert parse_interval("30m") == 1800

    def test_days(self):
        assert parse_interval("1d") == 86400

    def test_seconds(self):
        assert parse_interval("60s") == 60

    def test_bare_number(self):
        assert parse_interval("3600") == 3600


class TestMonitorCRUD:
    def test_add_monitor(self):
        scheduler, mem = _make_scheduler()
        mid = scheduler.add("check PRs", 3600)
        monitors = scheduler.list_monitors()
        assert len(monitors) == 1
        assert monitors[0]["goal"] == "check PRs"
        assert monitors[0]["interval_seconds"] == 3600

    def test_remove_monitor(self):
        scheduler, mem = _make_scheduler()
        mid = scheduler.add("check PRs", 3600)
        scheduler.remove(mid)
        assert len(scheduler.list_monitors()) == 0

    def test_pause_and_resume(self):
        scheduler, mem = _make_scheduler()
        mid = scheduler.add("check issues", 7200)
        scheduler.pause(mid)
        monitors = scheduler.list_monitors()
        assert monitors[0]["enabled"] == 0

        scheduler.resume(mid)
        monitors = scheduler.list_monitors()
        assert monitors[0]["enabled"] == 1

    def test_multiple_monitors(self):
        scheduler, mem = _make_scheduler()
        scheduler.add("goal A", 3600)
        scheduler.add("goal B", 7200)
        scheduler.add("goal C", 1800)
        assert len(scheduler.list_monitors()) == 3

    def test_due_monitors_empty_initially(self):
        scheduler, mem = _make_scheduler()
        # Monitor with future next_run should not be due
        scheduler.add("future goal", 86400)
        due = mem.get_due_monitors()
        assert len(due) == 0

    def test_due_monitors_with_null_next_run(self):
        scheduler, mem = _make_scheduler()
        # Manually insert monitor with NULL next_run (should be due)
        mem.save_monitor("test-123", "null next_run goal", 3600, next_run=None)
        due = mem.get_due_monitors()
        assert len(due) == 1

    def test_paused_monitor_not_due(self):
        scheduler, mem = _make_scheduler()
        mem.save_monitor("test-paused", "paused goal", 3600, next_run=None)
        scheduler.pause("test-paused")
        due = mem.get_due_monitors()
        assert len(due) == 0
