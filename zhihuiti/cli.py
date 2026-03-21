"""CLI and REPL for zhihuiti (智慧体)."""
from __future__ import annotations

import sys
from typing import Optional

import click

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree
    from rich import print as rprint
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

from .bloodline import BloodlineManager
from .economy import Economy
from .memory import Memory
from .models import AgentRole
from .orchestrator import Orchestrator


console = Console() if _RICH_AVAILABLE else None


def _console_print(msg: str) -> None:
    if console:
        console.print(msg)
    else:
        click.echo(msg)


def _get_orchestrator() -> Orchestrator:
    memory = Memory()
    economy = Economy(memory)
    return Orchestrator(memory=memory, economy=economy)


@click.group()
def main() -> None:
    """zhihuiti (智慧体) — Autonomous multi-agent orchestration system."""


@main.command("run")
@click.argument("goal")
def run_goal(goal: str) -> None:
    """Execute a goal using the multi-agent system."""
    orch = _get_orchestrator()
    _console_print(f"\n[bold cyan]Executing goal:[/bold cyan] {goal}\n")
    result = orch.execute_goal(goal)

    if console:
        # Task table
        table = Table(title="Task Results", show_header=True)
        table.add_column("Task ID", style="dim")
        table.add_column("Description")
        table.add_column("Role", style="yellow")
        table.add_column("Agent", style="blue")
        table.add_column("Score", style="magenta")
        table.add_column("Bid")

        for t in result.get("tasks", []):
            score = t.get("score")
            score_str = f"{score:.2f}" if score is not None else "-"
            bid = t.get("bid_amount")
            bid_str = f"{bid:.1f}" if bid is not None else "spawned"
            table.add_row(
                t["task_id"],
                t["description"][:50] + ("…" if len(t["description"]) > 50 else ""),
                t["role"],
                t["agent_id"],
                score_str,
                bid_str,
            )
        console.print(table)

        # Economy panel
        econ = result.get("economy", {})
        econ_text = (
            f"Supply: [green]{econ.get('total_supply', 0):.1f}[/green]  "
            f"Treasury: [blue]{econ.get('treasury_balance', 0):.1f}[/blue]  "
            f"Tax: [yellow]{econ.get('tax_rate', 0)*100:.1f}%[/yellow]"
        )
        console.print(Panel(econ_text, title="Economy"))

        # Auction stats
        stats = result.get("auction_stats", {})
        console.print(
            f"Auctions: [cyan]{stats.get('won', 0)}[/cyan]/{stats.get('total', 0)} won"
        )

        # Merge info
        merge = result.get("merge")
        if merge:
            console.print(
                Panel(
                    f"Merged [blue]{merge['parent1_id']}[/blue] + "
                    f"[blue]{merge['parent2_id']}[/blue] → "
                    f"[green]{merge['child_id']}[/green] "
                    f"({merge['child_role']}, gen {merge['child_generation']})",
                    title="[bold green]Bloodline Merge[/bold green]",
                )
            )
    else:
        click.echo(str(result))


@main.command("agents")
@click.option("--status", default=None, help="Filter by status (active/culled/frozen)")
@click.option("--role", default=None, help="Filter by role")
def list_agents(status: Optional[str], role: Optional[str]) -> None:
    """List all agents."""
    memory = Memory()
    agents = memory.list_agents(status=status, role=role)

    if console:
        table = Table(title=f"Agents ({len(agents)} total)", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Role", style="yellow")
        table.add_column("Gen", justify="right")
        table.add_column("Budget", justify="right", style="green")
        table.add_column("Score", justify="right", style="magenta")
        table.add_column("Status", style="blue")
        table.add_column("Specialization")

        for a in agents:
            role_name = a.role.value if isinstance(a.role, AgentRole) else str(a.role)
            table.add_row(
                a.id,
                role_name,
                str(a.generation),
                f"{a.budget:.1f}",
                f"{a.score:.2f}",
                status or "all",
                a.specialization[:30] if a.specialization else "",
            )
        console.print(table)
    else:
        for a in agents:
            click.echo(f"{a.id} | {a.role} | gen={a.generation} | budget={a.budget:.1f} | score={a.score:.2f}")


@main.command("tasks")
@click.option("--limit", default=20, help="Max tasks to show")
def list_tasks(limit: int) -> None:
    """List recent tasks."""
    memory = Memory()
    tasks = memory.list_tasks(limit=limit)

    if console:
        table = Table(title=f"Recent Tasks (showing {len(tasks)})", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Description")
        table.add_column("Agent", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Score", justify="right", style="magenta")
        table.add_column("Bid", justify="right")

        for t in tasks:
            score_str = f"{t.score:.2f}" if t.score is not None else "-"
            bid_str = f"{t.bid_amount:.1f}" if t.bid_amount is not None else "-"
            table.add_row(
                t.id,
                t.description[:60] + ("…" if len(t.description) > 60 else ""),
                t.assigned_agent_id or "-",
                t.status,
                score_str,
                bid_str,
            )
        console.print(table)
    else:
        for t in tasks:
            click.echo(f"{t.id} | {t.description[:40]} | {t.status} | score={t.score}")


@main.command("economy")
def show_economy() -> None:
    """Show economy report."""
    memory = Memory()
    economy = Economy(memory)
    economy.bootstrap()
    report = economy.report()

    if console:
        text = (
            f"[bold]Total Supply:[/bold]  [green]{report['total_supply']:.2f}[/green]\n"
            f"[bold]Treasury:[/bold]      [blue]{report['treasury_balance']:.2f}[/blue]\n"
            f"[bold]Tax Rate:[/bold]      [yellow]{report['tax_rate']*100:.2f}%[/yellow]\n"
            f"[bold]Tracked Agents:[/bold] {report['num_agents_tracked']}"
        )
        console.print(Panel(text, title="[bold cyan]Economy Report[/bold cyan]"))
    else:
        for k, v in report.items():
            click.echo(f"{k}: {v}")


@main.command("auctions")
@click.option("--limit", default=20, help="Max auctions to show")
def show_auctions(limit: int) -> None:
    """Show auction history."""
    memory = Memory()
    auctions = memory.list_auctions(limit=limit)

    if console:
        table = Table(title=f"Auction History (showing {len(auctions)})", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Task ID")
        table.add_column("Winner", style="green")
        table.add_column("Winning Bid", justify="right", style="yellow")
        table.add_column("Bidders", justify="right")
        table.add_column("Timestamp", style="dim")

        for a in auctions:
            table.add_row(
                str(a["id"]),
                a["task_id"],
                a["winner_agent_id"] or "-",
                f"{a['winning_bid']:.1f}" if a["winning_bid"] is not None else "-",
                str(a["num_bidders"]),
                a["timestamp"][:19],
            )
        console.print(table)
    else:
        for a in auctions:
            click.echo(f"{a['id']} | task={a['task_id']} | winner={a['winner_agent_id']} | bid={a['winning_bid']}")


@main.command("bloodline")
@click.argument("agent_id")
def show_bloodline(agent_id: str) -> None:
    """Show lineage tree for an agent."""
    memory = Memory()
    manager = BloodlineManager()
    report = manager.lineage_report(agent_id, memory)

    if console:
        console.print(Panel(report, title=f"Bloodline: {agent_id}"))
    else:
        click.echo(report)


@main.command("merge")
def do_merge() -> None:
    """Manually trigger a merge of the two best agents."""
    memory = Memory()
    economy = Economy(memory)
    economy.bootstrap()
    orch = Orchestrator(memory=memory, economy=economy)
    manager = BloodlineManager()

    pair = manager.find_best_pair(orch.pool)
    if pair is None:
        # Try from DB
        all_agents = memory.list_agents(status="active")
        from .bidding import AgentPool
        tmp_pool = AgentPool()
        for a in all_agents:
            tmp_pool.add(a)
        pair = manager.find_best_pair(tmp_pool)

    if pair is None:
        _console_print("[yellow]Not enough agents to merge (need at least 2 with budget > 10).[/yellow]")
        return

    parent1, parent2 = pair
    child = manager.merge(parent1, parent2, memory, economy)
    orch.pool.add(child)

    child_role = child.role.value if isinstance(child.role, AgentRole) else str(child.role)
    _console_print(
        f"[green]Merged[/green] [blue]{parent1.id}[/blue] + [blue]{parent2.id}[/blue] → "
        f"[cyan]{child.id}[/cyan] ({child_role}, gen {child.generation}, "
        f"score {child.score:.2f}, budget {child.budget:.1f})"
    )


@main.command("punish")
@click.argument("agent_id")
@click.option("--depth", default=7, help="Generations to punish (default 7)")
def punish_agent(agent_id: str, depth: int) -> None:
    """Trigger 诛七族 — cull agent and ancestors up to depth generations."""
    memory = Memory()
    economy = Economy(memory)
    economy.bootstrap()
    manager = BloodlineManager()

    _console_print(f"[bold red]诛七族 triggered for agent {agent_id} (depth={depth})[/bold red]")
    culled = manager.punish_lineage(agent_id, memory, economy, depth=depth)

    if console:
        table = Table(title="Culled Agents")
        table.add_column("Agent ID", style="red")
        for cid in culled:
            table.add_row(cid)
        console.print(table)
    else:
        for cid in culled:
            click.echo(f"Culled: {cid}")

    _console_print(f"[red]Total culled: {len(culled)}[/red]")


@main.command("stats")
def show_stats() -> None:
    """Show overall system statistics."""
    orch = _get_orchestrator()
    stats = orch.get_stats()

    if console:
        text = (
            f"[bold]Total Agents:[/bold]   {stats['total_agents']}\n"
            f"[bold]Active Agents:[/bold]  {stats['active_agents']}\n"
            f"[bold]Culled Agents:[/bold]  {stats['culled_agents']}\n"
            f"[bold]Pool Size:[/bold]      {stats['pool_size']}\n"
            f"\n"
            f"[bold]Total Tasks:[/bold]    {stats['total_tasks']}\n"
            f"[bold]Done Tasks:[/bold]     {stats['done_tasks']}\n"
            f"[bold]Avg Score:[/bold]      [magenta]{stats['avg_task_score']:.3f}[/magenta]\n"
            f"\n"
            f"[bold]Auctions:[/bold]       {stats['total_auctions']}\n"
            f"[bold]Goals Run:[/bold]      {stats['goals_executed']}\n"
            f"\n"
            f"[bold]Economy:[/bold]\n"
            f"  Supply:    [green]{stats['economy']['total_supply']:.2f}[/green]\n"
            f"  Treasury:  [blue]{stats['economy']['treasury_balance']:.2f}[/blue]\n"
            f"  Tax Rate:  [yellow]{stats['economy']['tax_rate']*100:.2f}%[/yellow]"
        )
        console.print(Panel(text, title="[bold cyan]System Statistics[/bold cyan]"))
    else:
        for k, v in stats.items():
            click.echo(f"{k}: {v}")


@main.command("repl")
def repl() -> None:
    """Interactive REPL — enter goals to execute."""
    _console_print("[bold cyan]zhihuiti REPL[/bold cyan] — type 'exit' or 'quit' to stop.\n")
    orch = _get_orchestrator()

    while True:
        try:
            goal = click.prompt("goal", prompt_suffix="> ").strip()
        except (click.exceptions.Abort, EOFError):
            _console_print("\n[dim]Goodbye.[/dim]")
            break

        if goal.lower() in ("exit", "quit", "q"):
            _console_print("[dim]Goodbye.[/dim]")
            break

        if not goal:
            continue

        result = orch.execute_goal(goal)

        if console:
            console.print(f"\n[bold green]Done.[/bold green] Tasks: {len(result.get('tasks', []))}")
            for t in result.get("tasks", []):
                score = t.get("score")
                score_str = f"{score:.2f}" if score is not None else "-"
                console.print(
                    f"  [cyan]{t['task_id']}[/cyan] [{t['role']}] score={score_str} "
                    f"→ {t['result_preview'][:80]}"
                )
            econ = result.get("economy", {})
            console.print(
                f"  Economy: supply={econ.get('total_supply', 0):.1f} "
                f"treasury={econ.get('treasury_balance', 0):.1f}\n"
            )
        else:
            click.echo(str(result))


if __name__ == "__main__":
    main()
