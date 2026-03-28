"""Experiment Runner — generate variant approaches, run each through the orchestrator, score and rank.

The experiment engine explores the strategy space for a given goal:
  1. `run_experiment()` generates N variant approaches via LLM, runs each through
     a fresh orchestrator instance, scores and ranks the results.
  2. `iterate()` takes the top K approaches from a previous experiment, generates
     mutations, and re-runs to refine.

Results are stored in memory for future reference and cross-experiment learning.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.llm import LLM
from zhihuiti.memory import Memory
from zhihuiti.models import ExperimentReport

console = Console()


@dataclass
class _VariantResult:
    """Internal: holds execution result for a single variant approach."""

    approach: str
    variant_id: str
    score: float
    task_results: list[dict[str, Any]]
    goal_output: dict[str, Any]


class ExperimentRunner:
    """Generates, executes, and ranks variant approaches for a goal.

    Parameters
    ----------
    db_path : str
        SQLite database path for persistent memory.
    model : str | None
        LLM model override (passed through to orchestrator).
    tools_enabled : bool
        Whether agents may use tool execution.
    """

    def __init__(
        self,
        db_path: str = "zhihuiti.db",
        model: str | None = None,
        tools_enabled: bool = False,
    ) -> None:
        self.db_path = db_path
        self.model = model
        self.tools_enabled = tools_enabled
        self.llm = LLM(model=model)
        self.memory = Memory(db_path=db_path)
        self.reports: list[ExperimentReport] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_experiment(
        self,
        goal: str,
        n_variants: int = 3,
        *,
        orchestrator_factory: Callable[..., Any] | None = None,
    ) -> ExperimentReport:
        """Generate *n_variants* approaches for *goal*, execute each, score and rank.

        Parameters
        ----------
        goal : str
            The objective to explore.
        n_variants : int
            How many variant approaches to generate (default 3).
        orchestrator_factory : callable, optional
            Factory that returns an ``Orchestrator`` instance.  When *None* a
            default factory is used that creates an in-memory orchestrator per
            variant so runs don't interfere with each other.

        Returns
        -------
        ExperimentReport
            Ranked results with the best approach highlighted.
        """
        experiment_id = uuid.uuid4().hex[:12]
        console.print(
            Panel(
                f"[bold]Goal:[/bold] {goal}\n"
                f"[bold]Variants:[/bold] {n_variants}",
                title=f"Experiment {experiment_id}",
                border_style="magenta",
            )
        )

        # 1. Generate variant approaches via LLM
        approaches = self._generate_approaches(goal, n_variants)
        console.print(f"\n[bold]Generated {len(approaches)} variant approaches:[/bold]")
        for i, a in enumerate(approaches, 1):
            console.print(f"  {i}. {a[:120]}")
        console.print()

        # 2. Execute each variant
        factory = orchestrator_factory or self._default_orchestrator_factory
        variant_results = self._execute_variants(goal, approaches, factory)

        # 3. Rank by score
        variant_results.sort(key=lambda v: v.score, reverse=True)

        rankings = [
            {
                "rank": i + 1,
                "variant_id": v.variant_id,
                "approach": v.approach,
                "score": v.score,
                "task_count": len(v.task_results),
            }
            for i, v in enumerate(variant_results)
        ]

        variants_data = [
            {
                "variant_id": v.variant_id,
                "approach": v.approach,
                "score": v.score,
                "task_results": v.task_results,
            }
            for v in variant_results
        ]

        best = variant_results[0] if variant_results else None

        report = ExperimentReport(
            experiment_id=experiment_id,
            goal=goal,
            variants=variants_data,
            rankings=rankings,
            best_score=best.score if best else 0.0,
            best_approach=best.approach if best else "",
            iteration=0,
            metadata={"n_variants": n_variants},
        )

        # 4. Store and display
        self.reports.append(report)
        self._save_report(report)
        self._print_report(report)

        return report

    def iterate(
        self,
        previous_report: ExperimentReport,
        top_k: int = 2,
        mutations_per: int = 2,
        *,
        orchestrator_factory: Callable[..., Any] | None = None,
    ) -> ExperimentReport:
        """Take top K approaches from *previous_report*, mutate, and re-run.

        Parameters
        ----------
        previous_report : ExperimentReport
            The report from a prior ``run_experiment()`` or ``iterate()`` call.
        top_k : int
            Number of top approaches to keep as seeds (default 2).
        mutations_per : int
            How many mutations to generate per seed (default 2).
        orchestrator_factory : callable, optional
            Same as ``run_experiment``.

        Returns
        -------
        ExperimentReport
            New ranked report for this iteration.
        """
        iteration = previous_report.iteration + 1
        experiment_id = uuid.uuid4().hex[:12]

        # Extract top K approaches
        top_approaches = [
            r["approach"] for r in previous_report.rankings[:top_k]
        ]

        console.print(
            Panel(
                f"[bold]Iterating from:[/bold] {previous_report.experiment_id}\n"
                f"[bold]Seeds:[/bold] {len(top_approaches)} (top {top_k})\n"
                f"[bold]Mutations per seed:[/bold] {mutations_per}\n"
                f"[bold]Iteration:[/bold] {iteration}",
                title=f"Experiment Iteration {experiment_id}",
                border_style="magenta",
            )
        )

        # Generate mutations for each seed approach
        all_approaches: list[str] = []
        for seed in top_approaches:
            mutations = self._generate_mutations(
                previous_report.goal, seed, mutations_per,
            )
            all_approaches.extend(mutations)

        # Also keep the original seeds
        all_approaches = top_approaches + all_approaches

        console.print(f"\n[bold]{len(all_approaches)} approaches (seeds + mutations):[/bold]")
        for i, a in enumerate(all_approaches, 1):
            label = "seed" if i <= len(top_approaches) else "mutation"
            console.print(f"  {i}. [{label}] {a[:120]}")
        console.print()

        # Execute all
        factory = orchestrator_factory or self._default_orchestrator_factory
        variant_results = self._execute_variants(
            previous_report.goal, all_approaches, factory,
        )

        # Rank
        variant_results.sort(key=lambda v: v.score, reverse=True)

        rankings = [
            {
                "rank": i + 1,
                "variant_id": v.variant_id,
                "approach": v.approach,
                "score": v.score,
                "task_count": len(v.task_results),
            }
            for i, v in enumerate(variant_results)
        ]

        variants_data = [
            {
                "variant_id": v.variant_id,
                "approach": v.approach,
                "score": v.score,
                "task_results": v.task_results,
            }
            for v in variant_results
        ]

        best = variant_results[0] if variant_results else None

        report = ExperimentReport(
            experiment_id=experiment_id,
            goal=previous_report.goal,
            variants=variants_data,
            rankings=rankings,
            best_score=best.score if best else 0.0,
            best_approach=best.approach if best else "",
            iteration=iteration,
            metadata={
                "parent_experiment": previous_report.experiment_id,
                "top_k": top_k,
                "mutations_per": mutations_per,
            },
        )

        self.reports.append(report)
        self._save_report(report)
        self._print_report(report)

        return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_approaches(self, goal: str, n: int) -> list[str]:
        """Ask the LLM to generate N distinct approaches for a goal."""
        prompt = (
            f"Generate exactly {n} distinct strategic approaches for the following goal. "
            f"Each approach should be a concise paragraph describing a different strategy, "
            f"methodology, or angle of attack. Number them 1 through {n}.\n\n"
            f"Goal: {goal}"
        )

        result = self.llm.chat_json(
            system=(
                "You are a strategy generator. Return a JSON array of strings, "
                "where each string is a distinct approach. No commentary, just the array."
            ),
            user=prompt,
            temperature=0.8,
        )

        if isinstance(result, list):
            approaches = [str(item) for item in result[:n]]
        elif isinstance(result, dict) and "approaches" in result:
            approaches = [str(item) for item in result["approaches"][:n]]
        else:
            # Fallback: treat as a single approach
            approaches = [str(result)]

        # Pad if LLM returned fewer than requested
        while len(approaches) < n:
            approaches.append(f"Alternative approach #{len(approaches) + 1} for: {goal}")

        return approaches[:n]

    def _generate_mutations(
        self, goal: str, seed_approach: str, n: int,
    ) -> list[str]:
        """Generate N mutations of a seed approach."""
        prompt = (
            f"Given this goal and a seed approach, generate {n} mutations. "
            f"Each mutation should modify the strategy in a meaningful way — "
            f"adjust priorities, change methodology, add/remove steps, or shift focus.\n\n"
            f"Goal: {goal}\n\n"
            f"Seed approach: {seed_approach}\n\n"
            f"Return a JSON array of {n} mutated approach strings."
        )

        result = self.llm.chat_json(
            system=(
                "You are a strategy mutator. Return a JSON array of strings, "
                "each a mutated version of the seed approach. No commentary."
            ),
            user=prompt,
            temperature=0.9,
        )

        if isinstance(result, list):
            mutations = [str(item) for item in result[:n]]
        elif isinstance(result, dict) and "mutations" in result:
            mutations = [str(item) for item in result["mutations"][:n]]
        else:
            mutations = [f"Mutation of: {seed_approach[:100]}"]

        while len(mutations) < n:
            mutations.append(
                f"Variant #{len(mutations) + 1} of seed: {seed_approach[:80]}"
            )

        return mutations[:n]

    def _execute_variants(
        self,
        goal: str,
        approaches: list[str],
        factory: Callable[..., Any],
    ) -> list[_VariantResult]:
        """Run each approach through its own orchestrator and collect scores."""
        results: list[_VariantResult] = []

        for i, approach in enumerate(approaches):
            variant_id = uuid.uuid4().hex[:8]
            console.print(
                f"\n[bold cyan]{'=' * 60}[/bold cyan]"
            )
            console.print(
                f"[bold cyan]Variant {i + 1}/{len(approaches)}[/bold cyan] "
                f"(id={variant_id})"
            )
            console.print(f"  [dim]{approach[:120]}[/dim]")
            console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")

            # Construct the enriched goal with the specific approach
            enriched_goal = (
                f"{goal}\n\n"
                f"## Approach\n"
                f"Use this specific strategy:\n{approach}"
            )

            try:
                orch = factory()
                goal_result = orch.execute_goal(enriched_goal)
                orch.close()

                # Compute aggregate score
                task_results = goal_result.get("tasks", [])
                scores = [
                    t["score"] for t in task_results
                    if t.get("score") is not None and t["score"] > 0
                ]
                avg_score = sum(scores) / len(scores) if scores else 0.0

                results.append(
                    _VariantResult(
                        approach=approach,
                        variant_id=variant_id,
                        score=avg_score,
                        task_results=task_results,
                        goal_output=goal_result,
                    )
                )

                console.print(
                    f"\n  [green]Variant {variant_id} score:[/green] {avg_score:.3f}"
                )

            except Exception as e:
                console.print(
                    f"\n  [red]Variant {variant_id} failed:[/red] {e}"
                )
                results.append(
                    _VariantResult(
                        approach=approach,
                        variant_id=variant_id,
                        score=0.0,
                        task_results=[],
                        goal_output={"error": str(e)},
                    )
                )

        return results

    def _default_orchestrator_factory(self) -> Any:
        """Create an in-memory orchestrator so variants don't interfere."""
        from zhihuiti.orchestrator import Orchestrator

        return Orchestrator(
            db_path=":memory:",
            model=self.model,
            tools_enabled=self.tools_enabled,
        )

    def _save_report(self, report: ExperimentReport) -> None:
        """Persist experiment report to memory as a goal-history entry."""
        import json

        summary = (
            f"Experiment {report.experiment_id} iter={report.iteration}: "
            f"{len(report.variants)} variants, best={report.best_score:.2f}"
        )

        self.memory.save_goal(
            goal_id=f"exp_{report.experiment_id}",
            goal=f"[experiment] {report.goal}",
            task_count=sum(
                len(v.get("task_results", [])) for v in report.variants
            ),
            avg_score=report.best_score,
            summary=summary[:500],
        )

        # Also persist full rankings as JSON in goal_history metadata
        # (using the summary field since there's no dedicated metadata column)
        rankings_json = json.dumps(report.rankings, default=str)
        if len(rankings_json) <= 500:
            self.memory.save_goal(
                goal_id=f"exp_{report.experiment_id}_rankings",
                goal=f"[experiment-rankings] {report.goal[:200]}",
                task_count=len(report.rankings),
                avg_score=report.best_score,
                summary=rankings_json[:500],
            )

    def _print_report(self, report: ExperimentReport) -> None:
        """Print a rich summary table of the experiment results."""
        console.print()

        table = Table(
            title=f"Experiment Results — {report.experiment_id} (iteration {report.iteration})",
        )
        table.add_column("Rank", justify="center", style="bold")
        table.add_column("Variant", style="dim", max_width=10)
        table.add_column("Approach", max_width=50)
        table.add_column("Score", justify="center")
        table.add_column("Tasks", justify="center")

        for r in report.rankings:
            score = r["score"]
            score_style = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
            rank_str = str(r["rank"])
            if r["rank"] == 1:
                rank_str = f"[bold green]{rank_str}[/bold green]"

            table.add_row(
                rank_str,
                r["variant_id"],
                r["approach"][:50],
                f"[{score_style}]{score:.3f}[/{score_style}]",
                str(r["task_count"]),
            )

        console.print(table)

        if report.best_approach:
            console.print(
                Panel(
                    f"[bold green]Best approach[/bold green] "
                    f"(score {report.best_score:.3f}):\n\n"
                    f"{report.best_approach}",
                    title="Winner",
                    border_style="green",
                )
            )

        console.print(f"\n[dim]{report.summary}[/dim]\n")

    def close(self) -> None:
        """Close the memory connection."""
        self.memory.close()
