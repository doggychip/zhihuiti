"""Daemon — long-running orchestrator loop with checkpointing and progress reports."""

from __future__ import annotations

import json
import os
import signal
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# State file for persistence across stop/resume
_STATE_FILE = ".zhihuiti_daemon.json"


class Daemon:
    """Runs the orchestrator in a loop with budget tracking, checkpointing,
    and periodic markdown progress reports.

    Usage::

        daemon = Daemon(goal="...", db_path="zhihuiti.db")
        daemon.start()          # blocking loop
        daemon.stop()           # graceful shutdown (called via signal or another thread)
        daemon.resume()         # pick up from last checkpoint
        daemon.report()         # generate status report without stopping
    """

    def __init__(
        self,
        goal: str,
        db_path: str = "zhihuiti.db",
        model: str | None = None,
        tools_enabled: bool = False,
        max_rounds: int = 10,
        max_tokens: int = 0,
        checkpoint_interval: int = 1,
        report_interval: int = 3,
        report_dir: str = "./reports",
    ):
        self.goal = goal
        self.db_path = db_path
        self.model = model
        self.tools_enabled = tools_enabled
        self.max_rounds = max_rounds
        self.max_tokens = max_tokens  # 0 = unlimited
        self.checkpoint_interval = checkpoint_interval
        self.report_interval = report_interval
        self.report_dir = Path(report_dir)

        # Runtime state
        self.daemon_id = uuid.uuid4().hex[:12]
        self.current_round = 0
        self.total_tokens_used = 0
        self.round_results: list[dict] = []
        self._stop_event = threading.Event()
        self._orch = None
        self._started_at: str | None = None
        self._last_checkpoint_id: str | None = None

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def start(self) -> dict:
        """Run the orchestrator in a loop up to *max_rounds*, saving
        checkpoints and writing progress reports at configured intervals.

        Returns a summary dict when done.
        """
        from zhihuiti.orchestrator import Orchestrator

        self._stop_event.clear()
        self._started_at = datetime.now(timezone.utc).isoformat()

        # Install signal handlers for graceful shutdown
        prev_sigint = signal.getsignal(signal.SIGINT)
        prev_sigterm = signal.getsignal(signal.SIGTERM)

        def _handle_signal(signum, frame):
            console.print("\n[yellow]Daemon received shutdown signal, finishing current round...[/yellow]")
            self._stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        console.print(Panel(
            f"[bold]Goal:[/bold] {self.goal}\n"
            f"[bold]Max rounds:[/bold] {self.max_rounds}  "
            f"[bold]Max tokens:[/bold] {'unlimited' if not self.max_tokens else self.max_tokens}\n"
            f"[bold]Checkpoint every:[/bold] {self.checkpoint_interval} rounds  "
            f"[bold]Report every:[/bold] {self.report_interval} rounds",
            title="Daemon Start",
            border_style="cyan",
        ))

        try:
            self._orch = Orchestrator(
                db_path=self.db_path, model=self.model,
                tools_enabled=self.tools_enabled,
            )

            while self.current_round < self.max_rounds:
                if self._stop_event.is_set():
                    console.print("[yellow]Daemon stopped by request.[/yellow]")
                    break

                # Token budget check
                if self.max_tokens and self.total_tokens_used >= self.max_tokens:
                    console.print(
                        f"[yellow]Token budget exhausted "
                        f"({self.total_tokens_used}/{self.max_tokens}).[/yellow]"
                    )
                    break

                self.current_round += 1
                console.print(
                    f"\n[bold magenta]===== Daemon Round {self.current_round}"
                    f"/{self.max_rounds} =====[/bold magenta]"
                )

                # Execute one round
                round_start = time.time()
                try:
                    result = self._orch.execute_goal(self.goal)
                except Exception as exc:
                    console.print(f"[red]Round {self.current_round} failed:[/red] {exc}")
                    result = {
                        "goal": self.goal,
                        "tasks": [],
                        "error": str(exc),
                    }
                elapsed = time.time() - round_start

                # Track token usage from LLM
                round_tokens = getattr(self._orch.llm, "total_tokens", 0)
                prev_tokens = self.total_tokens_used
                self.total_tokens_used = round_tokens  # cumulative from LLM

                result["_daemon_meta"] = {
                    "round": self.current_round,
                    "elapsed_s": round(elapsed, 1),
                    "tokens_this_round": round_tokens - prev_tokens,
                    "tokens_cumulative": round_tokens,
                }
                self.round_results.append(result)

                console.print(
                    f"  [dim]Round {self.current_round} done in {elapsed:.1f}s "
                    f"| tokens: {round_tokens - prev_tokens} this round, "
                    f"{round_tokens} total[/dim]"
                )

                # Checkpoint
                if self.current_round % self.checkpoint_interval == 0:
                    self._save_checkpoint()

                # Progress report
                if self.current_round % self.report_interval == 0:
                    self._write_report()

        finally:
            # Always save state on exit
            self._save_checkpoint()
            self._save_state()
            if self._orch:
                self._orch.close()

            # Restore original signal handlers
            signal.signal(signal.SIGINT, prev_sigint)
            signal.signal(signal.SIGTERM, prev_sigterm)

        summary = self._build_summary()
        console.print(Panel(
            f"Completed {self.current_round}/{self.max_rounds} rounds\n"
            f"Total tokens: {self.total_tokens_used}\n"
            f"Avg score: {summary.get('avg_score', 0):.3f}",
            title="Daemon Finished",
            border_style="green",
        ))
        return summary

    def stop(self) -> None:
        """Request graceful shutdown. The current round will finish first."""
        self._stop_event.set()

    def resume(self) -> dict:
        """Resume from the last saved state and continue the loop."""
        state = self._load_state()
        if not state:
            console.print("[red]No saved daemon state found to resume.[/red]")
            return {}

        self.daemon_id = state.get("daemon_id", self.daemon_id)
        self.goal = state.get("goal", self.goal)
        self.db_path = state.get("db_path", self.db_path)
        self.model = state.get("model", self.model)
        self.tools_enabled = state.get("tools_enabled", self.tools_enabled)
        self.max_rounds = state.get("max_rounds", self.max_rounds)
        self.max_tokens = state.get("max_tokens", self.max_tokens)
        self.checkpoint_interval = state.get("checkpoint_interval", self.checkpoint_interval)
        self.report_interval = state.get("report_interval", self.report_interval)
        self.current_round = state.get("current_round", 0)
        self.total_tokens_used = state.get("total_tokens_used", 0)
        self.round_results = state.get("round_results", [])
        self._last_checkpoint_id = state.get("last_checkpoint_id")

        console.print(Panel(
            f"Resuming daemon [bold]{self.daemon_id}[/bold] from round "
            f"{self.current_round}/{self.max_rounds}\n"
            f"Goal: {self.goal[:80]}",
            title="Daemon Resume",
            border_style="yellow",
        ))

        return self.start()

    def report(self) -> str:
        """Generate a current status report (markdown) without stopping.

        Returns the report path.
        """
        return self._write_report()

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def _save_checkpoint(self) -> None:
        """Save a memory checkpoint via the orchestrator's Memory."""
        if not self._orch:
            return

        try:
            snap_id = self._orch.memory.checkpoint(
                phase=f"daemon_round_{self.current_round}",
                goal_id=self.daemon_id,
                tags=["daemon", f"round_{self.current_round}", self.goal[:40]],
            )
            self._last_checkpoint_id = snap_id
            console.print(
                f"  [dim]Checkpoint saved: {snap_id} "
                f"(round {self.current_round})[/dim]"
            )
        except Exception as exc:
            console.print(f"  [yellow]Checkpoint failed:[/yellow] {exc}")

    def _save_state(self) -> None:
        """Persist daemon state to a JSON file for resume."""
        state = {
            "daemon_id": self.daemon_id,
            "goal": self.goal,
            "db_path": self.db_path,
            "model": self.model,
            "tools_enabled": self.tools_enabled,
            "max_rounds": self.max_rounds,
            "max_tokens": self.max_tokens,
            "checkpoint_interval": self.checkpoint_interval,
            "report_interval": self.report_interval,
            "current_round": self.current_round,
            "total_tokens_used": self.total_tokens_used,
            "last_checkpoint_id": self._last_checkpoint_id,
            "started_at": self._started_at,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            # Store only the metadata from round results (not full outputs)
            "round_results": [
                {
                    "goal": r.get("goal", ""),
                    "task_count": len(r.get("tasks", [])),
                    "error": r.get("error"),
                    "_daemon_meta": r.get("_daemon_meta", {}),
                    "scores": [
                        t.get("score", 0)
                        for t in r.get("tasks", [])
                        if isinstance(t, dict)
                    ],
                }
                for r in self.round_results
            ],
        }
        try:
            with open(_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as exc:
            console.print(f"  [yellow]State save failed:[/yellow] {exc}")

    def _load_state(self) -> dict | None:
        """Load daemon state from the JSON file."""
        path = Path(_STATE_FILE)
        if not path.exists():
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _write_report(self) -> str:
        """Write a markdown progress report to the reports directory.

        Returns the report file path.
        """
        self.report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.report_dir / f"daemon_{ts}.md"

        summary = self._build_summary()

        lines = [
            f"# Daemon Progress Report",
            f"",
            f"- **Daemon ID:** {self.daemon_id}",
            f"- **Goal:** {self.goal}",
            f"- **Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"- **Started:** {self._started_at or 'N/A'}",
            f"- **Round:** {self.current_round}/{self.max_rounds}",
            f"- **Tokens used:** {self.total_tokens_used}"
            + (f" / {self.max_tokens}" if self.max_tokens else ""),
            f"- **Last checkpoint:** {self._last_checkpoint_id or 'none'}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Rounds completed | {summary.get('rounds_completed', 0)} |",
            f"| Total tasks | {summary.get('total_tasks', 0)} |",
            f"| Avg score | {summary.get('avg_score', 0):.3f} |",
            f"| Failed rounds | {summary.get('failed_rounds', 0)} |",
            f"| Total tokens | {summary.get('total_tokens', 0)} |",
            f"",
            f"## Round Details",
            f"",
        ]

        for i, result in enumerate(self.round_results, 1):
            meta = result.get("_daemon_meta", {})
            error = result.get("error")
            tasks = result.get("tasks", [])
            task_count = len(tasks) if isinstance(tasks, list) else result.get("task_count", 0)

            scores = []
            if isinstance(tasks, list):
                scores = [t.get("score", 0) for t in tasks if isinstance(t, dict) and t.get("score") is not None]
            elif "scores" in result:
                scores = [s for s in result["scores"] if s is not None]

            avg = sum(scores) / len(scores) if scores else 0
            status = "ERROR" if error else "OK"

            lines.append(f"### Round {i}")
            lines.append(f"")
            lines.append(f"- Status: **{status}**")
            lines.append(f"- Tasks: {task_count}")
            lines.append(f"- Avg score: {avg:.3f}")
            lines.append(f"- Elapsed: {meta.get('elapsed_s', '?')}s")
            lines.append(f"- Tokens: {meta.get('tokens_this_round', '?')}")
            if error:
                lines.append(f"- Error: `{error[:200]}`")
            lines.append(f"")

        report_text = "\n".join(lines)
        path.write_text(report_text)

        console.print(f"  [dim]Report written: {path}[/dim]")
        return str(path)

    def _build_summary(self) -> dict:
        """Build a summary dict from accumulated round results."""
        all_scores: list[float] = []
        total_tasks = 0
        failed_rounds = 0

        for result in self.round_results:
            if result.get("error"):
                failed_rounds += 1
            tasks = result.get("tasks", [])
            if isinstance(tasks, list):
                total_tasks += len(tasks)
                for t in tasks:
                    if isinstance(t, dict) and t.get("score") is not None:
                        all_scores.append(t["score"])
            elif "scores" in result:
                scores = result["scores"]
                total_tasks += result.get("task_count", len(scores))
                all_scores.extend(s for s in scores if s is not None)

        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        return {
            "daemon_id": self.daemon_id,
            "goal": self.goal,
            "rounds_completed": self.current_round,
            "max_rounds": self.max_rounds,
            "total_tasks": total_tasks,
            "avg_score": avg_score,
            "failed_rounds": failed_rounds,
            "total_tokens": self.total_tokens_used,
            "max_tokens": self.max_tokens,
            "last_checkpoint_id": self._last_checkpoint_id,
        }

    # ------------------------------------------------------------------
    # Class-level helpers for CLI
    # ------------------------------------------------------------------

    @staticmethod
    def get_status() -> dict | None:
        """Read the saved state file and return status info, or None."""
        path = Path(_STATE_FILE)
        if not path.exists():
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None
