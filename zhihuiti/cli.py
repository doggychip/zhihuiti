"""CLI interface for zhihuiti."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel

console = Console()

BANNER = """
╔══════════════════════════════════════╗
║          智 慧 体  zhihuiti          ║
║   Autonomous Multi-Agent System     ║
╚══════════════════════════════════════╝
"""


@click.group()
@click.version_option(package_name="zhihuiti")
def main():
    """智慧体 (zhihuiti) — Autonomous multi-agent orchestration system."""


@main.command()
@click.argument("goal")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--model", default=None, help="OpenRouter model ID")
def run(goal: str, db: str, model: str | None):
    """Execute a goal through the agent swarm."""
    from zhihuiti.orchestrator import Orchestrator

    console.print(BANNER, style="bold cyan")

    try:
        orch = Orchestrator(db_path=db, model=model)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    try:
        orch.execute_goal(goal)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    finally:
        orch.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--model", default=None, help="OpenRouter model ID")
def repl(db: str, model: str | None):
    """Interactive REPL mode — enter goals one at a time."""
    from zhihuiti.orchestrator import Orchestrator

    console.print(BANNER, style="bold cyan")
    console.print("[dim]Commands: stats, genes, economy, auctions, pool, bloodline, ancestry <id>, purge <id>,\n  realms, realm <name>, inspection, fuse, laws, behavior, relations, loans,\n  market, futures, arbitration, factory, quit[/dim]\n")

    try:
        orch = Orchestrator(db_path=db, model=model)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Start dashboard in background
    from zhihuiti.dashboard import start_dashboard
    start_dashboard(orch, background=True)

    try:
        while True:
            try:
                goal = console.input("[bold green]goal>[/bold green] ").strip()
            except EOFError:
                break

            if not goal:
                continue
            if goal.lower() in ("quit", "exit", "q"):
                break
            if goal.lower() == "stats":
                stats = orch.memory.get_stats()
                for k, v in stats.items():
                    console.print(f"  {k}: {v}")
                continue
            if goal.lower() == "genes":
                _show_genes(orch)
                continue
            if goal.lower() == "economy":
                orch.economy.print_report()
                continue
            if goal.lower() == "auctions":
                orch.bidding.print_auction_history()
                continue
            if goal.lower() == "pool":
                _show_pool(orch)
                continue
            if goal.lower() == "bloodline":
                orch.bloodline.print_lineage_stats()
                orch.bloodline.print_living_lineage()
                continue
            if goal.lower().startswith("ancestry "):
                gene_id = goal.split(None, 1)[1].strip()
                orch.bloodline.print_ancestry_tree(gene_id)
                continue
            if goal.lower().startswith("purge "):
                gene_id = goal.split(None, 1)[1].strip()
                orch.bloodline.zhu_qi_zu(gene_id)
                continue
            if goal.lower() == "inspection":
                orch.judge.inspection.print_report()
                orch.judge.inspection.print_history()
                continue
            if goal.lower() == "fuse":
                orch.circuit_breaker.print_report()
                orch.circuit_breaker.print_events()
                continue
            if goal.lower() == "laws":
                orch.circuit_breaker.print_laws()
                continue
            if goal.lower() == "behavior":
                orch.behavior.print_report()
                continue
            if goal.lower() == "relations":
                orch.rel_graph.print_report()
                continue
            if goal.lower() == "loans":
                orch.lending.print_report()
                orch.lending.print_active_loans()
                continue
            if goal.lower() == "market":
                orch.market.print_report()
                orch.market.print_orderbook()
                continue
            if goal.lower() == "futures":
                orch.futures.print_report()
                orch.futures.print_active_stakes()
                continue
            if goal.lower() == "arbitration":
                orch.arbitration.print_report()
                orch.arbitration.print_cases()
                continue
            if goal.lower() == "factory":
                orch.factory.print_report()
                orch.factory.print_orders()
                continue
            if goal.lower() == "realms":
                orch.realm_manager.print_report(orch.agent_manager.agents)
                continue
            if goal.lower().startswith("realm "):
                realm_name = goal.split(None, 1)[1].strip().lower()
                from zhihuiti.models import Realm
                realm_map = {"research": Realm.RESEARCH, "execution": Realm.EXECUTION, "central": Realm.CENTRAL}
                if realm_name in realm_map:
                    orch.realm_manager.print_realm_detail(
                        realm_map[realm_name], orch.agent_manager.agents,
                    )
                else:
                    console.print(f"  [red]Unknown realm:[/red] {realm_name}. Use: research, execution, central")
                continue

            orch.execute_goal(goal)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    finally:
        orch.close()
        console.print("[dim]Goodbye.[/dim]")


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def stats(db: str):
    """Show memory statistics."""
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    s = mem.get_stats()
    console.print(Panel(
        "\n".join(f"  {k}: {v}" for k, v in s.items()),
        title="zhihuiti Stats",
    ))
    mem.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def economy(db: str):
    """Show economy report — central bank, treasury, taxes."""
    from zhihuiti.economy import Economy
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    econ = Economy(mem)
    econ.print_report()

    # Transaction breakdown
    tx_summary = mem.get_transaction_summary()
    if tx_summary:
        from rich.table import Table
        table = Table(title="Transaction Breakdown")
        table.add_column("Type")
        table.add_column("Count", justify="right")
        table.add_column("Total", justify="right")
        for tx_type, data in sorted(tx_summary.items()):
            table.add_row(tx_type, str(data["count"]), f"{data['total']:.1f}")
        console.print(table)

    mem.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def auctions(db: str):
    """Show auction history and savings."""
    from zhihuiti.bidding import BiddingHouse
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    bh = BiddingHouse.__new__(BiddingHouse)
    bh.memory = mem
    bh.pool = None
    bh.auctions = []
    bh.print_auction_history()

    # Show aggregate stats
    astats = mem.get_auction_stats()
    if astats["total_auctions"] > 0:
        console.print(Panel(
            "\n".join(f"  {k}: {v}" for k, v in astats.items()),
            title="Auction Stats",
        ))
    mem.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--model", default=None, help="OpenRouter model ID")
@click.option("--port", default=8377, help="Dashboard port")
def dashboard(db: str, model: str | None, port: int):
    """Launch the web dashboard."""
    from zhihuiti.dashboard import start_dashboard
    from zhihuiti.orchestrator import Orchestrator

    console.print(BANNER, style="bold cyan")
    orch = Orchestrator(db_path=db, model=model)
    start_dashboard(orch, port=port, background=False)
    orch.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def inspection(db: str):
    """Show 3-layer inspection (三层安检) statistics."""
    from zhihuiti.inspection import InspectionGate
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    llm = LLM.__new__(LLM)  # Dummy — stats only, no LLM calls
    gate = InspectionGate(llm, mem)
    gate.print_report()
    mem.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def realms(db: str):
    """Show Three Realms (三界) status report."""
    from zhihuiti.memory import Memory
    from zhihuiti.realms import RealmManager

    mem = Memory(db_path=db)
    rm = RealmManager(mem)
    rm.print_report()
    mem.close()


@main.command()
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--role", default=None, help="Filter by agent role")
def bloodline(db: str, role: str | None):
    """Show bloodline / lineage stats and living genes."""
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    bl = Bloodline(mem)
    bl.print_lineage_stats()
    bl.print_living_lineage(role=role)
    mem.close()


@main.command()
@click.argument("gene_id")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def ancestry(gene_id: str, db: str):
    """Trace ancestry tree for a gene (up to 7 generations)."""
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    bl = Bloodline(mem)
    bl.print_ancestry_tree(gene_id)
    mem.close()


@main.command()
@click.argument("gene_id")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def purge(gene_id: str, db: str):
    """诛七族 — purge a gene and all its descendants."""
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.memory import Memory

    mem = Memory(db_path=db)
    bl = Bloodline(mem)
    purged = bl.zhu_qi_zu(gene_id)
    console.print(f"\n[dim]Purged {len(purged)} descendants total.[/dim]")
    mem.close()


def _show_pool(orch) -> None:
    """Show the agent pool status."""
    from rich.table import Table

    alive = orch.bidding.pool.get_all_alive()
    if not alive:
        console.print("  [dim]Agent pool is empty.[/dim]")
        return

    table = Table(title=f"Agent Pool ({len(alive)} alive)")
    table.add_column("ID", style="dim")
    table.add_column("Role", style="cyan")
    table.add_column("Budget", justify="right")
    table.add_column("Avg Score", justify="center")
    table.add_column("Tasks", justify="center")

    for a in sorted(alive, key=lambda x: x.config.role.value):
        score_str = f"{a.avg_score:.2f}" if a.scores else "—"
        table.add_row(
            a.id,
            a.config.role.value,
            f"{a.budget:.1f}",
            score_str,
            str(len(a.scores)),
        )

    console.print(table)


def _show_genes(orch) -> None:
    """Show gene pool contents."""
    from rich.table import Table

    rows = orch.memory.conn.execute(
        "SELECT role, gene_id, avg_score, temperature, mutation_notes "
        "FROM gene_pool ORDER BY avg_score DESC LIMIT 20"
    ).fetchall()

    if not rows:
        console.print("  [dim]Gene pool is empty.[/dim]")
        return

    table = Table(title="Gene Pool")
    table.add_column("Role")
    table.add_column("Gene ID")
    table.add_column("Avg Score", justify="center")
    table.add_column("Temperature", justify="center")
    table.add_column("Notes")

    for r in rows:
        table.add_row(r[0], r[1], f"{r[2]:.2f}", f"{r[3]:.2f}", r[4] or "")

    console.print(table)


if __name__ == "__main__":
    main()
