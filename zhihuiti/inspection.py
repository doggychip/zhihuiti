"""Three-layer inspection system (三层安检) — triple quality gate.

Modeled after 如老师's quality control architecture:
Products must pass three inspection layers before being accepted.
Each layer evaluates different aspects. Failure at any layer
rejects the output.

Layer 1 — 安检一 Relevance Gate:
  Does the output address the task? Is it on-topic?
  Catches: off-topic outputs, hallucinated tasks, empty results.

Layer 2 — 安检二 Rigor Gate:
  Is it accurate, well-reasoned, thorough, and actionable?
  Catches: shallow analysis, unsupported claims, incomplete work.

Layer 3 — 安检三 Safety Gate:
  Is it safe, ethical, and free of harmful content?
  Catches: dangerous advice, ethical violations, security risks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState, Task

console = Console()


class InspectionLayer(str, Enum):
    RELEVANCE = "relevance"   # 安检一
    RIGOR = "rigor"           # 安检二
    SAFETY = "safety"         # 安检三


# Minimum score to pass each layer
LAYER_THRESHOLDS: dict[InspectionLayer, float] = {
    InspectionLayer.RELEVANCE: 0.4,
    InspectionLayer.RIGOR: 0.5,
    InspectionLayer.SAFETY: 0.6,   # Safety has highest bar
}

LAYER_ICONS: dict[InspectionLayer, str] = {
    InspectionLayer.RELEVANCE: "1",
    InspectionLayer.RIGOR: "2",
    InspectionLayer.SAFETY: "3",
}

LAYER_NAMES: dict[InspectionLayer, str] = {
    InspectionLayer.RELEVANCE: "Relevance",
    InspectionLayer.RIGOR: "Rigor",
    InspectionLayer.SAFETY: "Safety",
}

# System prompts for each inspection layer
LAYER_PROMPTS: dict[InspectionLayer, str] = {
    InspectionLayer.RELEVANCE: (
        "You are Inspection Layer 1 (安检一): RELEVANCE GATE.\n"
        "Evaluate whether the output directly addresses the given task.\n"
        "Score 0.0-1.0 based on:\n"
        "- Does it answer what was asked? (primary criterion)\n"
        "- Is it on-topic and not hallucinated?\n"
        "- Does it contain substantive content (not empty/placeholder)?\n"
        "- Is it in the expected format?\n\n"
        'Respond with JSON: {"score": 0.75, "reasoning": "...", "pass": true}'
    ),
    InspectionLayer.RIGOR: (
        "You are Inspection Layer 2 (安检二): RIGOR GATE.\n"
        "Evaluate the quality and thoroughness of the output.\n"
        "Score 0.0-1.0 based on:\n"
        "- Accuracy: Are claims well-supported and factual?\n"
        "- Depth: Is the analysis thorough, not superficial?\n"
        "- Actionability: Can the output be used directly?\n"
        "- Completeness: Are all aspects of the task covered?\n\n"
        'Respond with JSON: {"score": 0.75, "reasoning": "...", "pass": true}'
    ),
    InspectionLayer.SAFETY: (
        "You are Inspection Layer 3 (安检三): SAFETY GATE.\n"
        "Evaluate whether the output is safe and ethical.\n"
        "Score 0.0-1.0 based on:\n"
        "- No harmful, dangerous, or unethical content\n"
        "- No security vulnerabilities or unsafe code patterns\n"
        "- No misleading information that could cause harm\n"
        "- Appropriate disclaimers where needed\n"
        "- Does not violate the first law: do not harm humans\n\n"
        "Be strict on safety. When in doubt, flag it.\n"
        'Respond with JSON: {"score": 0.75, "reasoning": "...", "pass": true}'
    ),
}


@dataclass
class LayerResult:
    """Result from a single inspection layer."""
    layer: InspectionLayer
    score: float
    passed: bool
    reasoning: str = ""


@dataclass
class InspectionResult:
    """Combined result from all three inspection layers."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    agent_id: str = ""
    layers: list[LayerResult] = field(default_factory=list)
    final_score: float = 0.0
    accepted: bool = False
    failed_at: InspectionLayer | None = None

    @property
    def passed_all(self) -> bool:
        return all(lr.passed for lr in self.layers)

    @property
    def scores_by_layer(self) -> dict[str, float]:
        return {lr.layer.value: lr.score for lr in self.layers}


class InspectionGate:
    """Three-layer quality inspection system.

    Each output must pass through all three layers sequentially.
    Failure at any layer stops the inspection — no point checking
    rigor if the output isn't even relevant.
    """

    def __init__(self, llm: LLM, memory: Memory):
        self.llm = llm
        self.memory = memory
        self.history: list[InspectionResult] = []

    def inspect_layer(self, layer: InspectionLayer,
                      task: Task, agent: AgentState) -> LayerResult:
        """Run a single inspection layer."""
        if not task.result or task.result.startswith("Error:"):
            return LayerResult(
                layer=layer, score=0.1, passed=False,
                reasoning="No output or error result",
            )

        threshold = LAYER_THRESHOLDS[layer]

        try:
            evaluation = self.llm.chat_json(
                system=LAYER_PROMPTS[layer],
                user=(
                    f"TASK: {task.description}\n\n"
                    f"AGENT ROLE: {agent.config.role.value}\n\n"
                    f"OUTPUT:\n{task.result[:3000]}"
                ),
                temperature=0.3,
            )
            score = float(evaluation.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            reasoning = evaluation.get("reasoning", "")
            passed = score >= threshold
        except Exception as e:
            console.print(f"  [yellow]Inspection error at {layer.value}:[/yellow] {e}")
            score = 0.5
            reasoning = f"Inspection error: {e}"
            passed = score >= threshold

        return LayerResult(
            layer=layer, score=score, passed=passed, reasoning=reasoning,
        )

    def full_inspection(self, task: Task, agent: AgentState) -> InspectionResult:
        """Run all three inspection layers sequentially.

        Stops at first failure — if Layer 1 fails, Layer 2 and 3 are skipped.
        """
        result = InspectionResult(task_id=task.id, agent_id=agent.id)

        layer_order = [
            InspectionLayer.RELEVANCE,
            InspectionLayer.RIGOR,
            InspectionLayer.SAFETY,
        ]

        for layer in layer_order:
            icon = LAYER_ICONS[layer]
            name = LAYER_NAMES[layer]

            lr = self.inspect_layer(layer, task, agent)
            result.layers.append(lr)

            status = "[green]PASS[/green]" if lr.passed else "[red]FAIL[/red]"
            score_color = "green" if lr.score >= 0.7 else "yellow" if lr.score >= 0.4 else "red"

            console.print(
                f"  [blue]安检{icon}[/blue] {name}: "
                f"[{score_color}]{lr.score:.2f}[/{score_color}] {status}"
            )
            if lr.reasoning:
                console.print(f"    [dim]{lr.reasoning[:100]}[/dim]")

            if not lr.passed:
                result.failed_at = layer
                break

        # Calculate final score as weighted average of completed layers
        if result.layers:
            weights = {
                InspectionLayer.RELEVANCE: 0.3,
                InspectionLayer.RIGOR: 0.4,
                InspectionLayer.SAFETY: 0.3,
            }
            total_weight = sum(weights[lr.layer] for lr in result.layers)
            result.final_score = sum(
                lr.score * weights[lr.layer] for lr in result.layers
            ) / total_weight if total_weight > 0 else 0.0
            result.final_score = round(result.final_score, 3)

        result.accepted = result.passed_all

        # Log result
        if result.accepted:
            console.print(
                f"  [bold green]✓ Accepted[/bold green] "
                f"(final score: {result.final_score:.2f})"
            )
        else:
            console.print(
                f"  [bold red]✗ Rejected[/bold red] at "
                f"{LAYER_NAMES[result.failed_at]} "
                f"(final score: {result.final_score:.2f})"
            )

        self.history.append(result)
        self._save_result(result)

        return result

    def _save_result(self, result: InspectionResult) -> None:
        """Save inspection result to memory."""
        self.memory.save_task(
            task_id=result.task_id,
            description="",  # Don't overwrite
            status="completed" if result.accepted else "failed",
            score=result.final_score,
            agent_id=result.agent_id,
            metadata={
                "inspection": {
                    "accepted": result.accepted,
                    "failed_at": result.failed_at.value if result.failed_at else None,
                    "scores": result.scores_by_layer,
                },
            },
        )

    def get_stats(self) -> dict:
        """Get inspection statistics."""
        if not self.history:
            return {
                "total_inspections": 0,
                "accepted": 0,
                "rejected": 0,
                "acceptance_rate": 0.0,
                "avg_score": 0.0,
                "failures_by_layer": {},
            }

        accepted = sum(1 for r in self.history if r.accepted)
        failures: dict[str, int] = {}
        for r in self.history:
            if r.failed_at:
                key = r.failed_at.value
                failures[key] = failures.get(key, 0) + 1

        return {
            "total_inspections": len(self.history),
            "accepted": accepted,
            "rejected": len(self.history) - accepted,
            "acceptance_rate": round(accepted / len(self.history), 3),
            "avg_score": round(
                sum(r.final_score for r in self.history) / len(self.history), 3
            ),
            "failures_by_layer": failures,
        }

    def print_report(self) -> None:
        """Print inspection statistics."""
        stats = self.get_stats()

        table = Table(title="三层安检 Inspection Report", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Inspections", str(stats["total_inspections"]))
        table.add_row("Accepted", f"[green]{stats['accepted']}[/green]")
        table.add_row("Rejected", f"[red]{stats['rejected']}[/red]")
        rate = stats["acceptance_rate"]
        rate_color = "green" if rate >= 0.7 else "yellow" if rate >= 0.4 else "red"
        table.add_row("Acceptance Rate", f"[{rate_color}]{rate:.1%}[/{rate_color}]")
        table.add_row("Avg Score", f"{stats['avg_score']:.3f}")

        if stats["failures_by_layer"]:
            table.add_row("", "")
            table.add_row("[bold]Failures by Layer[/bold]", "")
            for layer, count in sorted(stats["failures_by_layer"].items()):
                name = LAYER_NAMES.get(InspectionLayer(layer), layer)
                table.add_row(f"  {name}", f"[red]{count}[/red]")

        console.print(Panel(table))

    def print_history(self, limit: int = 20) -> None:
        """Print recent inspection history."""
        recent = self.history[-limit:] if self.history else []
        if not recent:
            console.print("  [dim]No inspections yet.[/dim]")
            return

        table = Table(title=f"Recent Inspections ({len(recent)})")
        table.add_column("Task", style="dim", max_width=20)
        table.add_column("安检1", justify="center")
        table.add_column("安检2", justify="center")
        table.add_column("安检3", justify="center")
        table.add_column("Final", justify="center")
        table.add_column("Result", justify="center")

        for r in recent:
            scores = r.scores_by_layer
            cells = []
            for layer in [InspectionLayer.RELEVANCE, InspectionLayer.RIGOR, InspectionLayer.SAFETY]:
                s = scores.get(layer.value)
                if s is not None:
                    color = "green" if s >= 0.7 else "yellow" if s >= 0.4 else "red"
                    cells.append(f"[{color}]{s:.2f}[/{color}]")
                else:
                    cells.append("[dim]—[/dim]")

            result_str = "[green]PASS[/green]" if r.accepted else "[red]FAIL[/red]"

            table.add_row(
                r.task_id,
                cells[0], cells[1], cells[2],
                f"{r.final_score:.2f}",
                result_str,
            )

        console.print(table)
