"""Blood Sweat Factory (血汗工厂) — production pipeline for mass task execution.

中枢界 (Central realm) generates production orders that get decomposed into
subtasks, then piped to a factory of worker agents from the 执行界 (Execution
realm) pool for mass execution.  Completed products go through QA inspection
before shipping.

Revenue model:
  - Each shipped order earns tokens distributed to the workers who
    contributed to its completion.
  - Failed QA sends the order back for rework (up to a retry limit).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_REVENUE_PER_SUBTASK = 20.0    # Tokens earned per subtask on ship
QA_THRESHOLD = 0.5                  # Minimum quality score to pass QA
MAX_REWORK_CYCLES = 2               # Max times an order can be sent back
WORKER_SHARE = 0.70                 # 70% of revenue goes to workers
FACTORY_CUT = 0.30                  # 30% retained by the factory (treasury)


# ---------------------------------------------------------------------------
# Enums / Data models
# ---------------------------------------------------------------------------

class ProductionStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    QA_PASS = "qa_pass"
    QA_FAIL = "qa_fail"
    SHIPPED = "shipped"


@dataclass
class ProductionOrder:
    """A production order containing multiple subtasks."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    subtasks: list[str] = field(default_factory=list)
    results: dict[str, str] = field(default_factory=dict)      # task_id -> result
    assignments: dict[str, str] = field(default_factory=dict)   # task_id -> agent_id
    quality_score: float = 0.0
    status: ProductionStatus = ProductionStatus.QUEUED
    revenue: float = 0.0
    rework_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    @property
    def is_complete(self) -> bool:
        return len(self.results) == len(self.subtasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "subtasks": self.subtasks,
            "results": self.results,
            "assignments": self.assignments,
            "quality_score": self.quality_score,
            "status": self.status.value,
            "revenue": self.revenue,
            "rework_count": self.rework_count,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class Factory:
    """Blood Sweat Factory (血汗工厂) — mass production pipeline.

    Lifecycle:
        create_order -> decompose_order -> assign_workers -> process_order
        -> quality_check -> ship  (or rework on QA failure)
    """

    def __init__(self, llm: LLM, memory: Memory):
        self.llm = llm
        self.memory = memory
        self.orders: dict[str, ProductionOrder] = {}
        self.worker_earnings: dict[str, float] = {}  # agent_id -> total earned
        self.total_revenue: float = 0.0
        self.total_shipped: int = 0
        self.total_reworks: int = 0

    # ------------------------------------------------------------------
    # Order creation
    # ------------------------------------------------------------------

    def create_order(
        self, description: str, subtasks: list[str] | None = None,
    ) -> ProductionOrder:
        """Create a new production order.

        If *subtasks* is ``None``, call :meth:`decompose_order` to let the LLM
        break the high-level request into subtasks automatically.
        """
        order = ProductionOrder(description=description)

        if subtasks:
            order.subtasks = list(subtasks)
        else:
            order.subtasks = self.decompose_order(description)

        order.revenue = len(order.subtasks) * BASE_REVENUE_PER_SUBTASK
        self.orders[order.id] = order

        console.print(
            Panel(
                f"[bold]Order:[/bold] {description}\n"
                f"[bold]Subtasks:[/bold] {len(order.subtasks)}\n"
                f"[bold]Potential revenue:[/bold] {order.revenue:.0f} tokens",
                title="血汗工厂 New Production Order",
                border_style="yellow",
            )
        )
        for i, st in enumerate(order.subtasks, 1):
            console.print(f"  {i}. {st}")
        console.print()

        self._persist_order(order)
        return order

    def decompose_order(self, description: str) -> list[str]:
        """Use the LLM to break a high-level product request into subtasks."""
        console.print(f"  [dim]Decomposing order into subtasks ...[/dim]")

        raw = self.llm.chat_json(
            system=(
                "You are a production planner for a factory. "
                "Break the following product request into a list of concrete, "
                "independent subtasks that can each be assigned to a single "
                "worker agent.\n\n"
                "Respond with a JSON array of strings, each describing one "
                'subtask.  Example: ["Research X", "Draft Y", "Validate Z"]'
            ),
            user=description,
            temperature=0.4,
        )

        if isinstance(raw, list):
            subtasks = [str(s) for s in raw]
        elif isinstance(raw, dict) and "subtasks" in raw:
            subtasks = [str(s) for s in raw["subtasks"]]
        else:
            subtasks = [str(raw)]

        return subtasks

    # ------------------------------------------------------------------
    # Worker assignment
    # ------------------------------------------------------------------

    def assign_workers(
        self, order: ProductionOrder, agents: list[AgentState],
    ) -> dict[str, str]:
        """Assign subtasks to available agents from the execution realm pool.

        Uses round-robin across the supplied *agents* list.
        Returns a mapping of ``{subtask_index -> agent_id}``.
        """
        if not agents:
            console.print("  [red]No workers available for assignment![/red]")
            return {}

        assignments: dict[str, str] = {}
        for idx, _subtask in enumerate(order.subtasks):
            agent = agents[idx % len(agents)]
            task_id = f"{order.id}_sub{idx}"
            assignments[task_id] = agent.id

        order.assignments = assignments
        order.status = ProductionStatus.IN_PROGRESS

        console.print(f"  [cyan]Assigned {len(assignments)} subtasks to "
                       f"{len(agents)} worker(s)[/cyan]")
        self._persist_order(order)
        return assignments

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def process_order(
        self,
        order: ProductionOrder,
        agents: dict[str, AgentState],
        execute_fn: Any = None,
    ) -> ProductionOrder:
        """Run all subtasks through worker agents sequentially.

        Parameters
        ----------
        order:
            The production order to process.
        agents:
            Mapping of ``agent_id -> AgentState`` for all available agents.
        execute_fn:
            A callable ``(agent, task_description) -> result_str`` used to
            actually run each subtask.  When ``None`` the subtask is marked
            with a placeholder result so the rest of the pipeline can still
            be exercised.
        """
        console.print(
            Panel(
                f"[bold]Processing:[/bold] {order.description[:80]}",
                title="血汗工厂 Production Line",
                border_style="cyan",
            )
        )

        order.status = ProductionStatus.IN_PROGRESS
        order.results.clear()

        for idx, subtask_desc in enumerate(order.subtasks):
            task_id = f"{order.id}_sub{idx}"
            agent_id = order.assignments.get(task_id)

            agent = agents.get(agent_id) if agent_id else None

            console.print(
                f"  [bold cyan]>[/bold cyan] Subtask {idx + 1}/{len(order.subtasks)}: "
                f"{subtask_desc[:60]}{'...' if len(subtask_desc) > 60 else ''}"
            )

            if agent and execute_fn:
                try:
                    result = execute_fn(agent, subtask_desc)
                except Exception as e:
                    result = f"Error: {e}"
                    console.print(f"    [red]Worker error: {e}[/red]")
            elif execute_fn:
                # No agent assigned — try with a None agent
                try:
                    result = execute_fn(None, subtask_desc)
                except Exception as e:
                    result = f"Error: {e}"
            else:
                result = f"[placeholder] Result for: {subtask_desc}"

            order.results[task_id] = result
            preview = result[:100].replace("\n", " ")
            console.print(f"    [dim]{preview}[/dim]")

        console.print()
        self._persist_order(order)
        return order

    # ------------------------------------------------------------------
    # Quality check
    # ------------------------------------------------------------------

    def quality_check(self, order: ProductionOrder) -> bool:
        """Run a QA pass on the completed order.

        Uses a simplified single-layer inspection (rather than the full
        three-layer 安检 system) to keep factory throughput high.
        Returns ``True`` if the order passes QA.
        """
        if not order.is_complete:
            console.print("  [red]Cannot QA — order has incomplete subtasks[/red]")
            order.status = ProductionStatus.QA_FAIL
            return False

        # Build a combined output for evaluation
        combined = "\n\n".join(
            f"[Subtask {i + 1}] {order.subtasks[i]}\n{order.results.get(f'{order.id}_sub{i}', '(missing)')}"
            for i in range(len(order.subtasks))
        )

        try:
            evaluation = self.llm.chat_json(
                system=(
                    "You are a factory QA inspector (质检员). "
                    "Evaluate the combined output of a production order.\n"
                    "Score 0.0-1.0 based on:\n"
                    "- Completeness: were all subtasks addressed?\n"
                    "- Quality: is the work acceptable?\n"
                    "- Coherence: do the parts fit together?\n\n"
                    'Respond with JSON: {"score": 0.75, "reasoning": "...", "pass": true}'
                ),
                user=(
                    f"ORDER: {order.description}\n\n"
                    f"COMBINED OUTPUT:\n{combined[:4000]}"
                ),
                temperature=0.3,
            )
            score = float(evaluation.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            reasoning = evaluation.get("reasoning", "")
        except Exception as e:
            console.print(f"  [yellow]QA error:[/yellow] {e}")
            score = 0.5
            reasoning = f"QA error: {e}"

        order.quality_score = round(score, 3)
        passed = score >= QA_THRESHOLD

        score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
        status_label = "[green]QA PASS[/green]" if passed else "[red]QA FAIL[/red]"

        console.print(
            f"  [blue]质检[/blue] Score: [{score_color}]{score:.2f}[/{score_color}] "
            f"{status_label}"
        )
        if reasoning:
            console.print(f"    [dim]{reasoning[:120]}[/dim]")

        if passed:
            order.status = ProductionStatus.QA_PASS
        else:
            order.status = ProductionStatus.QA_FAIL
            order.rework_count += 1
            self.total_reworks += 1
            if order.rework_count <= MAX_REWORK_CYCLES:
                console.print(
                    f"  [yellow]Sending back for rework "
                    f"({order.rework_count}/{MAX_REWORK_CYCLES})[/yellow]"
                )
            else:
                console.print(
                    f"  [red]Max rework cycles exceeded — order abandoned[/red]"
                )

        self._persist_order(order)
        return passed

    # ------------------------------------------------------------------
    # Shipping & revenue
    # ------------------------------------------------------------------

    def ship(self, order: ProductionOrder) -> dict[str, float]:
        """Mark order as shipped and distribute revenue to workers.

        Returns a mapping of ``{agent_id -> tokens_earned}``.
        """
        if order.status != ProductionStatus.QA_PASS:
            console.print("  [red]Cannot ship — order has not passed QA[/red]")
            return {}

        order.status = ProductionStatus.SHIPPED
        self.total_shipped += 1
        self.total_revenue += order.revenue

        # Distribute revenue to workers
        worker_ids = list(set(order.assignments.values()))
        if not worker_ids:
            self._persist_order(order)
            return {}

        worker_pool = order.revenue * WORKER_SHARE
        per_worker = round(worker_pool / len(worker_ids), 2)

        payouts: dict[str, float] = {}
        for wid in worker_ids:
            payouts[wid] = per_worker
            self.worker_earnings[wid] = self.worker_earnings.get(wid, 0.0) + per_worker

        console.print(
            Panel(
                f"[bold green]Order shipped![/bold green]\n"
                f"Revenue: {order.revenue:.0f} tokens\n"
                f"Worker share ({WORKER_SHARE:.0%}): {worker_pool:.0f} tokens "
                f"across {len(worker_ids)} worker(s)\n"
                f"Factory cut ({FACTORY_CUT:.0%}): {order.revenue * FACTORY_CUT:.0f} tokens",
                title="血汗工厂 Shipped",
                border_style="green",
            )
        )

        self._persist_order(order)
        return payouts

    # ------------------------------------------------------------------
    # Full pipeline convenience
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        description: str,
        agents: list[AgentState],
        agents_map: dict[str, AgentState] | None = None,
        execute_fn: Any = None,
        subtasks: list[str] | None = None,
    ) -> ProductionOrder:
        """End-to-end pipeline: create -> assign -> process -> QA -> ship.

        Handles rework loops automatically.
        """
        order = self.create_order(description, subtasks=subtasks)
        self.assign_workers(order, agents)

        if agents_map is None:
            agents_map = {a.id: a for a in agents}

        attempts = 0
        while attempts <= MAX_REWORK_CYCLES:
            self.process_order(order, agents_map, execute_fn=execute_fn)
            passed = self.quality_check(order)

            if passed:
                self.ship(order)
                break

            if order.rework_count > MAX_REWORK_CYCLES:
                console.print(
                    f"  [red]Order {order.id} abandoned after "
                    f"{MAX_REWORK_CYCLES} rework cycles.[/red]"
                )
                break

            attempts += 1

        return order

    # ------------------------------------------------------------------
    # Stats / reporting
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return factory statistics."""
        total = len(self.orders)
        shipped = sum(1 for o in self.orders.values()
                      if o.status == ProductionStatus.SHIPPED)
        qa_pass = sum(1 for o in self.orders.values()
                      if o.status == ProductionStatus.QA_PASS)
        qa_fail = sum(1 for o in self.orders.values()
                      if o.status == ProductionStatus.QA_FAIL)
        in_progress = sum(1 for o in self.orders.values()
                          if o.status == ProductionStatus.IN_PROGRESS)
        queued = sum(1 for o in self.orders.values()
                     if o.status == ProductionStatus.QUEUED)

        avg_quality = 0.0
        scored = [o for o in self.orders.values() if o.quality_score > 0]
        if scored:
            avg_quality = round(
                sum(o.quality_score for o in scored) / len(scored), 3,
            )

        return {
            "total_orders": total,
            "shipped": shipped,
            "qa_pass": qa_pass,
            "qa_fail": qa_fail,
            "in_progress": in_progress,
            "queued": queued,
            "total_revenue": round(self.total_revenue, 2),
            "total_reworks": self.total_reworks,
            "avg_quality": avg_quality,
            "unique_workers": len(self.worker_earnings),
            "worker_earnings": dict(self.worker_earnings),
        }

    def print_report(self) -> None:
        """Print factory statistics."""
        stats = self.get_stats()

        table = Table(
            title="血汗工厂 Factory Report", show_header=False,
            box=None, padding=(0, 2),
        )
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Orders", str(stats["total_orders"]))
        table.add_row("Shipped", f"[green]{stats['shipped']}[/green]")
        table.add_row("QA Pass (pending ship)", f"[cyan]{stats['qa_pass']}[/cyan]")
        table.add_row("QA Fail", f"[red]{stats['qa_fail']}[/red]")
        table.add_row("In Progress", f"[yellow]{stats['in_progress']}[/yellow]")
        table.add_row("Queued", str(stats["queued"]))
        table.add_row("", "")
        table.add_row("Total Revenue", f"[green]{stats['total_revenue']:.0f}[/green] tokens")
        table.add_row("Total Reworks", f"[yellow]{stats['total_reworks']}[/yellow]")

        avg_q = stats["avg_quality"]
        q_color = "green" if avg_q >= 0.7 else "yellow" if avg_q >= 0.4 else "red"
        table.add_row("Avg Quality", f"[{q_color}]{avg_q:.3f}[/{q_color}]")
        table.add_row("Unique Workers", str(stats["unique_workers"]))

        console.print(Panel(table))

    def print_orders(self, limit: int = 20) -> None:
        """Print a table of recent production orders."""
        orders = list(self.orders.values())[-limit:]
        if not orders:
            console.print("  [dim]No production orders yet.[/dim]")
            return

        table = Table(title=f"血汗工厂 Orders ({len(orders)})")
        table.add_column("ID", style="dim", max_width=12)
        table.add_column("Description", max_width=35)
        table.add_column("Subtasks", justify="center")
        table.add_column("Quality", justify="center")
        table.add_column("Revenue", justify="right")
        table.add_column("Status", justify="center")

        STATUS_STYLES: dict[ProductionStatus, str] = {
            ProductionStatus.QUEUED: "dim",
            ProductionStatus.IN_PROGRESS: "yellow",
            ProductionStatus.QA_PASS: "cyan",
            ProductionStatus.QA_FAIL: "red",
            ProductionStatus.SHIPPED: "green",
        }

        for order in orders:
            style = STATUS_STYLES.get(order.status, "white")
            q = order.quality_score
            q_color = "green" if q >= 0.7 else "yellow" if q >= 0.4 else "red"
            q_str = f"[{q_color}]{q:.2f}[/{q_color}]" if q > 0 else "[dim]--[/dim]"

            rework_tag = f" (r{order.rework_count})" if order.rework_count else ""

            table.add_row(
                order.id,
                order.description[:35],
                str(len(order.subtasks)),
                q_str,
                f"{order.revenue:.0f}",
                f"[{style}]{order.status.value}{rework_tag}[/{style}]",
            )

        console.print(table)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_order(self, order: ProductionOrder) -> None:
        """Save order state to memory."""
        self.memory.save_economy_state(
            f"order_{order.id}", order.to_dict(),
        )
