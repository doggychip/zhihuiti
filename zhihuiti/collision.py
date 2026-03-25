"""Theory Collision Engine — run the same goal under competing strategies and compare.

Theories:
  - darwinian: Pure competition. No messaging, no lending, aggressive culling.
  - mutualist: Full cooperation. Messaging enabled, lending active, no culling.
  - hybrid: Default zhihuiti behavior (both forces active).
  - elitist: Only the top performers survive — extreme selection pressure.

The engine runs the same goal under two theories, scores both, and declares a winner.

Extended features:
  - Temporal dynamics: track how collision outcomes evolve over repeated runs.
  - Collision narratives: auto-generated natural language explanations.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.orchestrator import Orchestrator

console = Console()


THEORIES = {
    "darwinian": {
        "label": "🧬 Darwinian Selection",
        "description": "Survival of the fittest — pure competition, aggressive culling",
        "cull_threshold": 0.5,     # higher bar → more culling
        "promote_threshold": 0.8,
        "messaging": False,
        "lending": False,
        # Attention allocation: budget ratios for the three realms
        # (research, execution, central) — must sum to 1.0
        "attention": {"research": 0.40, "execution": 0.50, "central": 0.10},
    },
    "mutualist": {
        "label": "🤝 Symbiotic Mutualism",
        "description": "Cooperation amplifies both — messaging, lending, gentle culling",
        "cull_threshold": 0.1,     # very forgiving
        "promote_threshold": 0.7,  # easier to promote
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.55, "execution": 0.30, "central": 0.15},
    },
    "hybrid": {
        "label": "⚡ Hybrid Equilibrium",
        "description": "Default zhihuiti — competition + cooperation",
        "cull_threshold": 0.3,
        "promote_threshold": 0.8,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.50, "execution": 0.35, "central": 0.15},
    },
    "elitist": {
        "label": "👑 Elite Meritocracy",
        "description": "Only the top performers survive — extreme selection pressure",
        "cull_threshold": 0.6,
        "promote_threshold": 0.9,
        "messaging": False,
        "lending": False,
        "attention": {"research": 0.35, "execution": 0.55, "central": 0.10},
    },
    "ecosystem": {
        "label": "🌿 Ecosystem Dynamics",
        "description": "Agents form niches — specialists thrive, generalists adapt, diversity matters",
        "cull_threshold": 0.25,
        "promote_threshold": 0.75,
        "messaging": True,
        "lending": True,
        "attention": {"research": 0.45, "execution": 0.40, "central": 0.15},
    },
    "social_contract": {
        "label": "📜 Social Contract",
        "description": "Collective agreement — agents vote on norms, defectors face sanctions",
        "cull_threshold": 0.35,
        "promote_threshold": 0.85,
        "messaging": True,
        "lending": False,
        "attention": {"research": 0.40, "execution": 0.40, "central": 0.20},
    },
}


@dataclass
class CollisionResult:
    """Result of a theory collision experiment."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    theory_a: str = ""
    theory_b: str = ""
    result_a: dict = field(default_factory=dict)
    result_b: dict = field(default_factory=dict)

    @property
    def score_a(self) -> float:
        tasks = self.result_a.get("tasks", [])
        scores = [t["score"] for t in tasks if t.get("score", 0) > 0]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def score_b(self) -> float:
        tasks = self.result_b.get("tasks", [])
        scores = [t["score"] for t in tasks if t.get("score", 0) > 0]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def winner(self) -> str:
        if self.score_a > self.score_b + 0.01:
            return self.theory_a
        if self.score_b > self.score_a + 0.01:
            return self.theory_b
        return "tie"

    @property
    def narrative(self) -> str:
        """Auto-generated natural language explanation of the collision outcome."""
        return generate_narrative(self)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "theory_a": self.theory_a,
            "theory_b": self.theory_b,
            "score_a": round(self.score_a, 3),
            "score_b": round(self.score_b, 3),
            "winner": self.winner,
            "tasks_a": len(self.result_a.get("tasks", [])),
            "tasks_b": len(self.result_b.get("tasks", [])),
            "narrative": self.narrative,
        }


class CollisionEngine:
    """Runs the same goal under two competing theories and compares results."""

    def __init__(self, metacognition=None):
        self.history: list[CollisionResult] = []
        self.metacognition = metacognition  # MetacognitionEngine for auto-learning
        self.dynamics: dict[tuple[str, str], TemporalDynamics] = {}

    def collide(
        self,
        goal: str,
        theory_a: str,
        theory_b: str,
        orchestrator_factory,
    ) -> CollisionResult:
        """Run a goal under two theories and compare.

        orchestrator_factory: callable(theory_config) -> Orchestrator
            Creates a fresh orchestrator configured for the given theory.
        """
        config_a = THEORIES.get(theory_a)
        config_b = THEORIES.get(theory_b)
        if not config_a or not config_b:
            raise ValueError(f"Unknown theory. Available: {list(THEORIES.keys())}")

        console.print(Panel(
            f"[bold]Goal:[/bold] {goal}\n\n"
            f"[bold magenta]Theory A:[/bold magenta] {config_a['label']}\n"
            f"  {config_a['description']}\n\n"
            f"[bold cyan]Theory B:[/bold cyan] {config_b['label']}\n"
            f"  {config_b['description']}",
            title="💥 Theory Collision Engine",
            border_style="magenta",
        ))

        # Run Theory A
        console.print(f"\n[bold magenta]━━━ Running Theory A: {config_a['label']} ━━━[/bold magenta]\n")
        orch_a = orchestrator_factory(config_a)
        try:
            result_a = orch_a.execute_goal(goal)
        finally:
            orch_a.close()

        # Run Theory B
        console.print(f"\n[bold cyan]━━━ Running Theory B: {config_b['label']} ━━━[/bold cyan]\n")
        orch_b = orchestrator_factory(config_b)
        try:
            result_b = orch_b.execute_goal(goal)
        finally:
            orch_b.close()

        # Compare
        collision = CollisionResult(
            goal=goal,
            theory_a=theory_a,
            theory_b=theory_b,
            result_a=result_a,
            result_b=result_b,
        )
        self.history.append(collision)

        # Brain Intelligence: record collision for metacognition auto-learning
        if self.metacognition:
            self.metacognition.record_collision(
                goal=goal,
                theory_a=theory_a,
                theory_b=theory_b,
                score_a=collision.score_a,
                score_b=collision.score_b,
                winner=collision.winner,
                tasks_a=len(collision.result_a.get("tasks", [])),
                tasks_b=len(collision.result_b.get("tasks", [])),
            )

        # Track temporal dynamics for this theory pair
        key = _pair_key(theory_a, theory_b)
        if key not in self.dynamics:
            self.dynamics[key] = TemporalDynamics(theory_a=key[0], theory_b=key[1])
        self.dynamics[key].record(collision)

        self._print_result(collision, config_a, config_b)
        return collision

    def _print_result(self, c: CollisionResult, config_a: dict, config_b: dict) -> None:
        console.print()
        table = Table(title="💥 Collision Result", border_style="magenta")
        table.add_column("", style="bold")
        table.add_column(config_a["label"], justify="center")
        table.add_column(config_b["label"], justify="center")

        sa, sb = c.score_a, c.score_b
        style_a = "bold green" if sa > sb else "dim"
        style_b = "bold green" if sb > sa else "dim"

        table.add_row("Avg Score", f"[{style_a}]{sa:.3f}[/{style_a}]", f"[{style_b}]{sb:.3f}[/{style_b}]")

        tasks_a = c.result_a.get("tasks", [])
        tasks_b = c.result_b.get("tasks", [])
        table.add_row("Tasks", str(len(tasks_a)), str(len(tasks_b)))

        completed_a = sum(1 for t in tasks_a if t.get("status") == "completed")
        completed_b = sum(1 for t in tasks_b if t.get("status") == "completed")
        table.add_row("Completed", str(completed_a), str(completed_b))

        reward_a = sum(t.get("reward", {}).get("net", 0) for t in tasks_a)
        reward_b = sum(t.get("reward", {}).get("net", 0) for t in tasks_b)
        table.add_row("Total Rewards", f"{reward_a:.1f} ◆", f"{reward_b:.1f} ◆")

        econ_a = c.result_a.get("economy", {})
        econ_b = c.result_b.get("economy", {})
        table.add_row("Treasury", f"{econ_a.get('treasury_balance', 0):.0f} ◆", f"{econ_b.get('treasury_balance', 0):.0f} ◆")

        console.print(table)

        # Winner
        winner = c.winner
        if winner == "tie":
            console.print("\n[bold yellow]Result: TIE — both theories performed equally[/bold yellow]")
        else:
            winner_config = config_a if winner == c.theory_a else config_b
            margin = abs(sa - sb)
            console.print(
                f"\n[bold green]Winner: {winner_config['label']}[/bold green] "
                f"(margin: {margin:.3f})"
            )

    def get_temporal_dynamics(self, theory_a: str, theory_b: str) -> TemporalDynamics:
        """Get the temporal dynamics for a specific theory pair."""
        key = _pair_key(theory_a, theory_b)
        if key not in self.dynamics:
            self.dynamics[key] = TemporalDynamics(theory_a=key[0], theory_b=key[1])
        return self.dynamics[key]

    def print_dynamics(self) -> None:
        """Print temporal dynamics for all tracked theory pairs."""
        if not self.dynamics:
            console.print("  [dim]No temporal dynamics yet.[/dim]")
            return
        for dyn in self.dynamics.values():
            dyn.print_summary()

    def print_history(self) -> None:
        if not self.history:
            console.print("  [dim]No collisions yet.[/dim]")
            return

        table = Table(title="Collision History")
        table.add_column("Goal", max_width=30)
        table.add_column("Theory A")
        table.add_column("Score A", justify="center")
        table.add_column("Theory B")
        table.add_column("Score B", justify="center")
        table.add_column("Winner")

        for c in self.history:
            ca = THEORIES.get(c.theory_a, {})
            cb = THEORIES.get(c.theory_b, {})
            winner_label = THEORIES.get(c.winner, {}).get("label", c.winner)
            table.add_row(
                c.goal[:30],
                ca.get("label", c.theory_a),
                f"{c.score_a:.3f}",
                cb.get("label", c.theory_b),
                f"{c.score_b:.3f}",
                winner_label,
            )
        console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPORAL DYNAMICS — track how collision outcomes evolve over repeated runs
# ─────────────────────────────────────────────────────────────────────────────

def _pair_key(a: str, b: str) -> tuple[str, str]:
    """Canonical key for a theory pair (sorted for consistency)."""
    return (min(a, b), max(a, b))


@dataclass
class TemporalSnapshot:
    """A single point in the temporal evolution of a collision pair."""
    tick: int
    score_a: float
    score_b: float
    winner: str
    margin: float


@dataclass
class TemporalDynamics:
    """Tracks how a theory pair's collision outcomes evolve over time.

    Records score trajectories, detects convergence/divergence,
    and identifies regime shifts (when dominance flips).
    """
    theory_a: str
    theory_b: str
    snapshots: list[TemporalSnapshot] = field(default_factory=list)

    def record(self, result: CollisionResult) -> None:
        tick = len(self.snapshots) + 1
        self.snapshots.append(TemporalSnapshot(
            tick=tick,
            score_a=result.score_a,
            score_b=result.score_b,
            winner=result.winner,
            margin=abs(result.score_a - result.score_b),
        ))

    @property
    def num_runs(self) -> int:
        return len(self.snapshots)

    @property
    def dominant_theory(self) -> str:
        """Which theory wins most often across all runs."""
        if not self.snapshots:
            return "none"
        wins: dict[str, int] = {}
        for s in self.snapshots:
            wins[s.winner] = wins.get(s.winner, 0) + 1
        return max(wins, key=wins.get)  # type: ignore[arg-type]

    @property
    def dominance_ratio(self) -> float:
        """Fraction of runs won by the dominant theory (0.5 = even, 1.0 = total)."""
        if not self.snapshots:
            return 0.5
        wins: dict[str, int] = {}
        for s in self.snapshots:
            wins[s.winner] = wins.get(s.winner, 0) + 1
        return max(wins.values()) / len(self.snapshots)

    @property
    def regime_shifts(self) -> int:
        """Count how many times the winning theory flipped."""
        if len(self.snapshots) < 2:
            return 0
        shifts = 0
        for i in range(1, len(self.snapshots)):
            prev = self.snapshots[i - 1].winner
            curr = self.snapshots[i].winner
            if prev != curr and prev != "tie" and curr != "tie":
                shifts += 1
        return shifts

    @property
    def convergence_rate(self) -> float:
        """How quickly the margin between theories is shrinking.

        Negative = converging (gap closing), positive = diverging.
        Returns slope of margin over time via linear regression.
        """
        if len(self.snapshots) < 3:
            return 0.0
        margins = [s.margin for s in self.snapshots[-20:]]
        n = len(margins)
        x_mean = (n - 1) / 2.0
        y_mean = sum(margins) / n
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(margins))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den == 0:
            return 0.0
        return num / den

    def score_trajectory(self, theory: str) -> list[float]:
        """Get the score trajectory for a specific theory."""
        if theory == self.theory_a:
            return [s.score_a for s in self.snapshots]
        elif theory == self.theory_b:
            return [s.score_b for s in self.snapshots]
        return []

    def to_dict(self) -> dict:
        return {
            "theory_a": self.theory_a,
            "theory_b": self.theory_b,
            "num_runs": self.num_runs,
            "dominant_theory": self.dominant_theory,
            "dominance_ratio": round(self.dominance_ratio, 3),
            "regime_shifts": self.regime_shifts,
            "convergence_rate": round(self.convergence_rate, 4),
            "trajectory_a": [round(s.score_a, 3) for s in self.snapshots],
            "trajectory_b": [round(s.score_b, 3) for s in self.snapshots],
        }

    def print_summary(self) -> None:
        la = THEORIES.get(self.theory_a, {}).get("label", self.theory_a)
        lb = THEORIES.get(self.theory_b, {}).get("label", self.theory_b)

        table = Table(title=f"Temporal Dynamics: {la} vs {lb}", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="center")

        dom = THEORIES.get(self.dominant_theory, {}).get("label", self.dominant_theory)
        conv = self.convergence_rate
        conv_label = "converging" if conv < -0.005 else "diverging" if conv > 0.005 else "stable"

        table.add_row("Runs", str(self.num_runs))
        table.add_row("Dominant", dom)
        table.add_row("Dominance Ratio", f"{self.dominance_ratio:.1%}")
        table.add_row("Regime Shifts", str(self.regime_shifts))
        table.add_row("Convergence", f"{conv:+.4f} ({conv_label})")

        console.print(Panel(table))


# ─────────────────────────────────────────────────────────────────────────────
# COLLISION NARRATIVES — auto-generated explanations
# ─────────────────────────────────────────────────────────────────────────────

def generate_narrative(result: CollisionResult) -> str:
    """Generate a natural language explanation of why a collision went the way it did.

    Analyzes score distributions, task completion patterns, reward flows,
    and theory properties to build a coherent narrative.
    """
    ca = THEORIES.get(result.theory_a, {})
    cb = THEORIES.get(result.theory_b, {})
    la = ca.get("label", result.theory_a)
    lb = cb.get("label", result.theory_b)
    sa, sb = result.score_a, result.score_b
    winner = result.winner

    tasks_a = result.result_a.get("tasks", [])
    tasks_b = result.result_b.get("tasks", [])
    completed_a = sum(1 for t in tasks_a if t.get("status") == "completed")
    completed_b = sum(1 for t in tasks_b if t.get("status") == "completed")

    parts: list[str] = []

    # Opening: what was tested
    parts.append(
        f"In this collision, {la} and {lb} competed on the goal "
        f"\"{result.goal}\"."
    )

    # Score comparison
    if winner == "tie":
        parts.append(
            f"The result was a tie — both theories scored within 1% "
            f"({sa:.3f} vs {sb:.3f}), suggesting neither approach has a clear "
            f"advantage for this type of goal."
        )
    else:
        margin = abs(sa - sb)
        winner_label = la if winner == result.theory_a else lb
        loser_label = lb if winner == result.theory_a else la
        if margin > 0.2:
            parts.append(
                f"{winner_label} won decisively (margin: {margin:.3f}), "
                f"significantly outperforming {loser_label}."
            )
        elif margin > 0.05:
            parts.append(
                f"{winner_label} won with a moderate advantage "
                f"(margin: {margin:.3f}) over {loser_label}."
            )
        else:
            parts.append(
                f"{winner_label} won narrowly (margin: {margin:.3f}), "
                f"barely edging out {loser_label}."
            )

    # Task completion analysis
    if len(tasks_a) > 0 and len(tasks_b) > 0:
        rate_a = completed_a / len(tasks_a) if tasks_a else 0
        rate_b = completed_b / len(tasks_b) if tasks_b else 0
        if abs(rate_a - rate_b) > 0.15:
            higher = la if rate_a > rate_b else lb
            parts.append(
                f"{higher} had a notably higher task completion rate, "
                f"suggesting its strategy better supports task execution."
            )

    # Theory-specific insights
    cull_a = ca.get("cull_threshold", 0)
    cull_b = cb.get("cull_threshold", 0)
    if cull_a > cull_b + 0.15 and sa > sb:
        parts.append(
            "Higher selection pressure appears to have driven better outcomes, "
            "filtering out low performers early."
        )
    elif cull_b > cull_a + 0.15 and sb > sa:
        parts.append(
            "Higher selection pressure appears to have driven better outcomes, "
            "filtering out low performers early."
        )
    elif ca.get("messaging") and not cb.get("messaging") and sa > sb:
        parts.append(
            "Inter-agent communication gave the cooperative strategy an edge, "
            "enabling knowledge sharing across the population."
        )
    elif cb.get("messaging") and not ca.get("messaging") and sb > sa:
        parts.append(
            "Inter-agent communication gave the cooperative strategy an edge, "
            "enabling knowledge sharing across the population."
        )

    return " ".join(parts)
