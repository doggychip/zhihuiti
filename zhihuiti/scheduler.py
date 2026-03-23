"""Monitor scheduler — runs goals on a recurring interval.

Usage:
    scheduler.add("check PRs on owner/repo", interval_seconds=7200)  # every 2h
    scheduler.start(orchestrator)  # runs in background thread
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.memory import Memory
    from zhihuiti.orchestrator import Orchestrator

console = Console()

POLL_INTERVAL = 30  # seconds between scheduler checks


class MonitorScheduler:
    """Runs scheduled goals in a background thread."""

    def __init__(self, memory: Memory):
        self.memory = memory
        self._running = False
        self._thread: threading.Thread | None = None

    def add(self, goal: str, interval_seconds: int) -> str:
        """Add a new monitor. Returns the monitor ID."""
        monitor_id = uuid.uuid4().hex[:12]
        next_run = (datetime.utcnow() + timedelta(seconds=interval_seconds)).isoformat()
        self.memory.save_monitor(
            monitor_id=monitor_id,
            goal=goal,
            interval_seconds=interval_seconds,
            next_run=next_run,
        )
        console.print(
            f"  [green]📋 Monitor added:[/green] {monitor_id} "
            f"— \"{goal[:50]}\" every {_fmt_interval(interval_seconds)}"
        )
        return monitor_id

    def remove(self, monitor_id: str) -> None:
        self.memory.delete_monitor(monitor_id)
        console.print(f"  [red]Removed monitor {monitor_id}[/red]")

    def pause(self, monitor_id: str) -> None:
        self.memory.toggle_monitor(monitor_id, enabled=False)
        console.print(f"  [yellow]Paused monitor {monitor_id}[/yellow]")

    def resume(self, monitor_id: str) -> None:
        self.memory.toggle_monitor(monitor_id, enabled=True)
        console.print(f"  [green]Resumed monitor {monitor_id}[/green]")

    def list_monitors(self) -> list[dict]:
        return self.memory.list_monitors()

    def print_monitors(self) -> None:
        monitors = self.list_monitors()
        if not monitors:
            console.print("  [dim]No monitors configured.[/dim]")
            return

        table = Table(title="Monitors")
        table.add_column("ID", style="dim")
        table.add_column("Goal", max_width=40)
        table.add_column("Interval")
        table.add_column("Last Run")
        table.add_column("Status")

        for m in monitors:
            status = "[green]active[/green]" if m["enabled"] else "[yellow]paused[/yellow]"
            last = m["last_run"][:16] if m["last_run"] else "—"
            table.add_row(
                m["id"], m["goal"][:40],
                _fmt_interval(m["interval_seconds"]),
                last, status,
            )
        console.print(table)

    def start(self, orchestrator: Orchestrator) -> None:
        """Start the scheduler in a background daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, args=(orchestrator,), daemon=True,
        )
        self._thread.start()
        console.print("  [dim]📅 Monitor scheduler started[/dim]")

    def stop(self) -> None:
        self._running = False

    def _run_loop(self, orchestrator: Orchestrator) -> None:
        import time
        while self._running:
            try:
                self._check_and_run(orchestrator)
            except Exception as e:
                console.print(f"  [red]Scheduler error:[/red] {e}")
            time.sleep(POLL_INTERVAL)

    def _check_and_run(self, orchestrator: Orchestrator) -> None:
        due = self.memory.get_due_monitors()
        for monitor in due:
            console.print(
                f"\n[bold magenta]📋 Monitor firing:[/bold magenta] {monitor['goal'][:60]}"
            )
            now = datetime.utcnow()
            next_run = (now + timedelta(seconds=monitor["interval_seconds"])).isoformat()
            self.memory.update_monitor_run(monitor["id"], now.isoformat(), next_run)

            try:
                orchestrator.execute_goal(monitor["goal"])
            except Exception as e:
                console.print(f"  [red]Monitor {monitor['id']} failed:[/red] {e}")


def _fmt_interval(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400}d"
    if seconds >= 3600:
        return f"{seconds // 3600}h"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def parse_interval(s: str) -> int:
    """Parse a human interval string like '2h', '30m', '1d' to seconds."""
    s = s.strip().lower()
    if s.endswith("d"):
        return int(s[:-1]) * 86400
    if s.endswith("h"):
        return int(s[:-1]) * 3600
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("s"):
        return int(s[:-1])
    return int(s)  # assume seconds
