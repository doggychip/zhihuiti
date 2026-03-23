"""Theory Collision Engine — run the same goal under competing strategies and compare.

Theories:
  - darwinian: Pure competition. No messaging, no lending, aggressive culling.
  - mutualist: Full cooperation. Messaging enabled, lending active, no culling.
  - hybrid: Default zhihuiti behavior (both forces active).

The engine runs the same goal under two theories, scores both, and declares a winner.
"""

from __future__ import annotations

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
    },
    "mutualist": {
        "label": "🤝 Symbiotic Mutualism",
        "description": "Cooperation amplifies both — messaging, lending, gentle culling",
        "cull_threshold": 0.1,     # very forgiving
        "promote_threshold": 0.7,  # easier to promote
        "messaging": True,
        "lending": True,
    },
    "hybrid": {
        "label": "⚡ Hybrid Equilibrium",
        "description": "Default zhihuiti — competition + cooperation",
        "cull_threshold": 0.3,
        "promote_threshold": 0.8,
        "messaging": True,
        "lending": True,
    },
    "elitist": {
        "label": "👑 Elite Meritocracy",
        "description": "Only the top performers survive — extreme selection pressure",
        "cull_threshold": 0.6,
        "promote_threshold": 0.9,
        "messaging": False,
        "lending": False,
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
        }


class CollisionEngine:
    """Runs the same goal under two competing theories and compares results."""

    def __init__(self):
        self.history: list[CollisionResult] = []

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
