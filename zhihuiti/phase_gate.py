"""Phase gates between DAG waves (inspired by agency-agents' NEXUS pipeline).

Before advancing from Wave N to Wave N+1, a quality gate checks:
1. Minimum acceptance rate — did enough tasks in this wave pass inspection?
2. Average score threshold — is the wave's quality sufficient to build on?
3. No critical failures — were any circuit breakers tripped?

If the gate fails, the orchestrator can:
- Retry failed tasks in the current wave before proceeding
- Warn but continue (soft gate)
- Halt execution (hard gate, for safety-critical pipelines)

This prevents bad outputs from propagating to downstream tasks that
depend on them — a key pattern from agency-agents' phase gating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class GateMode(str, Enum):
    """How strictly to enforce the gate."""
    HARD = "hard"    # Halt if gate fails
    SOFT = "soft"    # Warn but continue
    OFF = "off"      # Skip gate checks


# Default thresholds (can be overridden per-orchestrator)
DEFAULT_MIN_ACCEPTANCE_RATE = 0.5   # At least 50% of wave tasks must pass
DEFAULT_MIN_AVG_SCORE = 0.4         # Average score must be above this
DEFAULT_NO_FUSE_TRIPS = True        # No circuit breaker trips allowed


@dataclass
class GateResult:
    """Result of a phase gate evaluation."""
    wave_idx: int
    passed: bool
    acceptance_rate: float
    avg_score: float
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    fuse_trips: int
    issues: list[str] = field(default_factory=list)


class PhaseGate:
    """Quality gate between DAG waves.

    Evaluates wave results against configurable thresholds
    before allowing execution to proceed to the next wave.
    """

    def __init__(
        self,
        mode: GateMode = GateMode.SOFT,
        min_acceptance_rate: float = DEFAULT_MIN_ACCEPTANCE_RATE,
        min_avg_score: float = DEFAULT_MIN_AVG_SCORE,
        block_on_fuse: bool = DEFAULT_NO_FUSE_TRIPS,
    ):
        self.mode = mode
        self.min_acceptance_rate = min_acceptance_rate
        self.min_avg_score = min_avg_score
        self.block_on_fuse = block_on_fuse
        self.history: list[GateResult] = []

    def evaluate(self, wave_idx: int, wave_results: list[dict]) -> GateResult:
        """Evaluate whether a completed wave passes the quality gate.

        Args:
            wave_idx: Index of the completed wave
            wave_results: List of task result dicts from execute_goal

        Returns:
            GateResult with pass/fail and details
        """
        if not wave_results:
            result = GateResult(
                wave_idx=wave_idx, passed=True,
                acceptance_rate=1.0, avg_score=0.0,
                total_tasks=0, passed_tasks=0, failed_tasks=0, fuse_trips=0,
            )
            self.history.append(result)
            return result

        total = len(wave_results)
        passed = sum(
            1 for r in wave_results
            if r.get("status") in ("completed", "accepted_with_issues")
        )
        failed = total - passed
        fuse_trips = sum(1 for r in wave_results if r.get("status") == "fuse_tripped")

        scores = [r.get("score", 0.0) for r in wave_results if r.get("score", 0) > 0]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        acceptance_rate = passed / total if total > 0 else 0.0

        issues = []
        gate_passed = True

        # Check acceptance rate
        if acceptance_rate < self.min_acceptance_rate:
            issues.append(
                f"Acceptance rate {acceptance_rate:.0%} below threshold "
                f"{self.min_acceptance_rate:.0%}"
            )
            gate_passed = False

        # Check average score
        if avg_score < self.min_avg_score:
            issues.append(
                f"Average score {avg_score:.2f} below threshold {self.min_avg_score:.2f}"
            )
            gate_passed = False

        # Check for circuit breaker trips
        if self.block_on_fuse and fuse_trips > 0:
            issues.append(f"{fuse_trips} circuit breaker trip(s) in this wave")
            gate_passed = False

        result = GateResult(
            wave_idx=wave_idx,
            passed=gate_passed,
            acceptance_rate=acceptance_rate,
            avg_score=avg_score,
            total_tasks=total,
            passed_tasks=passed,
            failed_tasks=failed,
            fuse_trips=fuse_trips,
            issues=issues,
        )
        self.history.append(result)

        # Display gate result
        self._print_gate(result)

        return result

    def _print_gate(self, result: GateResult) -> None:
        """Print the gate evaluation result."""
        if result.passed:
            console.print(
                f"\n  [bold green]✓ Phase Gate (Wave {result.wave_idx}):[/bold green] "
                f"PASSED — {result.passed_tasks}/{result.total_tasks} tasks accepted, "
                f"avg score {result.avg_score:.2f}"
            )
        else:
            severity = "red" if self.mode == GateMode.HARD else "yellow"
            action = "HALTING" if self.mode == GateMode.HARD else "WARNING (continuing)"
            console.print(
                f"\n  [bold {severity}]✗ Phase Gate (Wave {result.wave_idx}):[/bold {severity}] "
                f"FAILED — {action}"
            )
            for issue in result.issues:
                console.print(f"    [dim]- {issue}[/dim]")

    def should_continue(self, result: GateResult) -> bool:
        """Whether execution should continue to the next wave."""
        if self.mode == GateMode.OFF:
            return True
        if self.mode == GateMode.SOFT:
            return True  # Always continue, but logged the warning
        # HARD mode: only continue if gate passed
        return result.passed

    def print_report(self) -> None:
        """Print summary of all phase gate evaluations."""
        if not self.history:
            return

        table = Table(title="Phase Gate Report")
        table.add_column("Wave", justify="center")
        table.add_column("Tasks", justify="center")
        table.add_column("Passed", justify="center")
        table.add_column("Avg Score", justify="center")
        table.add_column("Gate", justify="center")

        for r in self.history:
            score_color = "green" if r.avg_score >= 0.7 else "yellow" if r.avg_score >= 0.4 else "red"
            gate_str = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            table.add_row(
                str(r.wave_idx),
                str(r.total_tasks),
                f"{r.passed_tasks}/{r.total_tasks}",
                f"[{score_color}]{r.avg_score:.2f}[/{score_color}]",
                gate_str,
            )

        console.print(Panel(table))
