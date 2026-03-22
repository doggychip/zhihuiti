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
@click.option("--model", default=None, help="Model name (Ollama: llama3, mistral… / OpenRouter: anthropic/claude-sonnet-4…)")
@click.option("--workers", default=4, type=int, help="Max parallel workers per wave")
@click.option("--premium-model", default=None, help="Premium model for promoted agents")
@click.option("--retries", default=1, type=int, help="Retry failed tasks (0=no retries)")
@click.option("--pool-size", default=5, type=int, help="Agents per role in bidding pool")
@click.option("--depth", default=3, type=int, help="Max sub-agent delegation depth")
@click.option("--tools", is_flag=True, help="Enable tool execution (gh, git read-only)")
def run(goal: str, db: str, model: str | None, workers: int, premium_model: str | None, retries: int, pool_size: int, depth: int, tools: bool):
    """Execute a goal through the agent swarm."""
    import os
    from zhihuiti.orchestrator import Orchestrator
    from zhihuiti import bidding, agents as agents_mod

    if premium_model:
        os.environ["LLM_PREMIUM_MODEL"] = premium_model
    bidding.POOL_SIZE_PER_ROLE = pool_size
    agents_mod.MAX_DEPTH = depth

    console.print(BANNER, style="bold cyan")

    try:
        orch = Orchestrator(db_path=db, model=model, tools_enabled=tools)
        orch.max_workers = workers
        orch.max_retries = retries
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
@click.option("--model", default=None, help="Model name (Ollama: llama3, mistral… / OpenRouter: anthropic/claude-sonnet-4…)")
@click.option("--workers", default=4, type=int, help="Max parallel workers per wave")
@click.option("--premium-model", default=None, help="Premium model for promoted agents")
@click.option("--retries", default=1, type=int, help="Retry failed tasks (0=no retries)")
def repl(db: str, model: str | None, workers: int, premium_model: str | None, retries: int):
    """Interactive REPL mode — enter goals one at a time."""
    import os
    from zhihuiti.orchestrator import Orchestrator

    if premium_model:
        os.environ["LLM_PREMIUM_MODEL"] = premium_model

    console.print(BANNER, style="bold cyan")
    console.print("[dim]Commands: stats, genes, economy, auctions, pool, bloodline, ancestry <id>, purge <id>,\n  realms, realm <name>, inspection, fuse, laws, behavior, relations, loans,\n  market, futures, arbitration, factory, quit[/dim]\n")

    try:
        orch = Orchestrator(db_path=db, model=model)
        orch.max_workers = workers
        orch.max_retries = retries
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
@click.option("--model", default=None, help="Model name (Ollama: llama3, mistral… / OpenRouter: anthropic/claude-sonnet-4…)")
@click.option("--port", default=8377, help="Dashboard port")
def dashboard(db: str, model: str | None, port: int):
    """Launch the web dashboard."""
    from zhihuiti.dashboard import start_dashboard
    from zhihuiti.orchestrator import Orchestrator

    import traceback
    console.print(BANNER, style="bold cyan")
    try:
        # Enable tools if AlphaArena or CriticAI env vars are set
        import os as _os
        tools = bool(_os.environ.get("ALPHAARENA_API_KEY") or _os.environ.get("CRITICAI_URL"))
        orch = Orchestrator(db_path=db, model=model, tools_enabled=tools)
        backend = getattr(orch.llm, '_backend', 'unknown')
        model_name = getattr(orch.llm, 'model', 'unknown')
        console.print(f"  [green]LLM backend ready:[/green] {backend} ({model_name})")
        if tools:
            console.print(f"  [green]Tools enabled:[/green] agents can execute curl commands")
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Orchestrator init failed: {e}")
        traceback.print_exc()
        console.print("[dim]Dashboard will serve data but cannot run goals.[/dim]")
        from zhihuiti.memory import Memory
        orch = type("MinimalOrch", (), {"memory": Memory(db_path=db), "close": lambda self: self.memory.close()})()
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


@main.group()
def monitor():
    """Manage scheduled goal monitors."""


@monitor.command("add")
@click.argument("goal")
@click.option("--interval", required=True, help="Interval (e.g. 2h, 30m, 1d)")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def monitor_add(goal: str, interval: str, db: str):
    """Add a recurring monitor for a goal."""
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler, parse_interval

    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)
    seconds = parse_interval(interval)
    scheduler.add(goal, seconds)
    mem.close()


@monitor.command("list")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def monitor_list(db: str):
    """List all monitors."""
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler

    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)
    scheduler.print_monitors()
    mem.close()


@monitor.command("remove")
@click.argument("monitor_id")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def monitor_remove(monitor_id: str, db: str):
    """Remove a monitor."""
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler

    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)
    scheduler.remove(monitor_id)
    mem.close()


@monitor.command("pause")
@click.argument("monitor_id")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def monitor_pause(monitor_id: str, db: str):
    """Pause a monitor."""
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler

    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)
    scheduler.pause(monitor_id)
    mem.close()


@monitor.command("resume")
@click.argument("monitor_id")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def monitor_resume(monitor_id: str, db: str):
    """Resume a paused monitor."""
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler

    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)
    scheduler.resume(monitor_id)
    mem.close()


@main.command()
@click.argument("goal")
@click.option("--theory-a", default="darwinian", help="First theory (darwinian, mutualist, hybrid, elitist)")
@click.option("--theory-b", default="mutualist", help="Second theory")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--model", default=None, help="Model name")
def collide(goal: str, theory_a: str, theory_b: str, db: str, model: str | None):
    """💥 Theory Collision — run a goal under two competing strategies and compare."""
    from zhihuiti.collision import CollisionEngine, THEORIES
    from zhihuiti.orchestrator import Orchestrator

    console.print(BANNER, style="bold cyan")

    available = list(THEORIES.keys())
    if theory_a not in available or theory_b not in available:
        console.print(f"[red]Available theories:[/red] {', '.join(available)}")
        sys.exit(1)

    def make_orchestrator(theory_config):
        from zhihuiti import judge as judge_mod
        # Apply theory settings
        judge_mod.CULL_THRESHOLD = theory_config["cull_threshold"]
        judge_mod.PROMOTE_THRESHOLD = theory_config["promote_threshold"]

        orch = Orchestrator(db_path=":memory:", model=model)
        # Disable/enable messaging based on theory
        if not theory_config["messaging"]:
            orch.messages = type("NullBoard", (), {
                "broadcast": lambda *a, **k: None,
                "collect_context": lambda *a, **k: "",
            })()
        return orch

    engine = CollisionEngine()
    engine.collide(goal, theory_a, theory_b, make_orchestrator)


@main.group()
def alphaarena():
    """📈 AlphaArena — trade crypto with evolving AI agents."""
    pass


@alphaarena.command("status")
@click.option("--url", default=None, help="AlphaArena API URL")
def alphaarena_status(url: str | None):
    """Show prices, portfolio, and leaderboard position."""
    from zhihuiti.alphaarena import AlphaArenaBridge
    bridge = AlphaArenaBridge(base_url=url)
    bridge.print_status()


@alphaarena.command("trade")
@click.argument("goal")
@click.option("--url", default=None, help="AlphaArena API URL")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--model", default=None, help="LLM model")
def alphaarena_trade(goal: str, url: str | None, db: str, model: str | None):
    """Run a trading goal — agents analyze markets and execute trades."""
    import os
    from zhihuiti.alphaarena import AlphaArenaBridge
    from zhihuiti.orchestrator import Orchestrator

    console.print(BANNER, style="bold cyan")

    bridge = AlphaArenaBridge(base_url=url)
    report = bridge.generate_status_report()

    # Inject AlphaArena env vars into the goal context
    aa_url = bridge.base_url
    aa_key = bridge.api_key
    aa_id = bridge.agent_id

    full_goal = (
        f"{goal}\n\n"
        f"## AlphaArena Context\n"
        f"API URL: {aa_url}\n"
        f"Agent ID: {aa_id}\n"
        f"API Key: {aa_key[:8]}... (use in X-API-Key header)\n\n"
        f"Current market state:\n{report}\n\n"
        f"Use curl to interact with AlphaArena API. "
        f"Always check prices before trading. Max 20% portfolio per trade."
    )

    # Set env vars so agent prompts can reference them
    os.environ["ALPHAARENA_URL"] = aa_url
    if aa_key:
        os.environ["ALPHAARENA_API_KEY"] = aa_key

    orch = Orchestrator(db_path=db, model=model, tools_enabled=True)
    orch.max_workers = 4
    orch.max_retries = 1
    orch.execute_goal(full_goal)
    orch.close()


@alphaarena.command("evolve")
@click.argument("goal", default="Analyze crypto markets and execute the best trades on AlphaArena")
@click.option("--url", default=None, help="AlphaArena API URL")
@click.option("--theory-a", default="darwinian", help="First theory")
@click.option("--theory-b", default="mutualist", help="Second theory")
@click.option("--model", default=None, help="LLM model")
def alphaarena_evolve(goal: str, url: str | None, theory_a: str, theory_b: str, model: str | None):
    """Evolve trading strategies — collide two theories to find the best approach."""
    import os
    from zhihuiti.alphaarena import AlphaArenaBridge
    from zhihuiti.collision import CollisionEngine, THEORIES
    from zhihuiti.orchestrator import Orchestrator
    from zhihuiti import judge as judge_mod

    console.print(BANNER, style="bold cyan")

    bridge = AlphaArenaBridge(base_url=url)
    report = bridge.generate_status_report()

    full_goal = (
        f"{goal}\n\n"
        f"AlphaArena API: {bridge.base_url}\n"
        f"Agent ID: {bridge.agent_id}\n"
        f"API Key: {bridge.api_key[:8]}...\n\n"
        f"{report}"
    )

    os.environ["ALPHAARENA_URL"] = bridge.base_url
    if bridge.api_key:
        os.environ["ALPHAARENA_API_KEY"] = bridge.api_key

    def make_orch(theory_config):
        judge_mod.CULL_THRESHOLD = theory_config["cull_threshold"]
        judge_mod.PROMOTE_THRESHOLD = theory_config["promote_threshold"]
        orch = Orchestrator(db_path=":memory:", model=model, tools_enabled=True)
        if not theory_config["messaging"]:
            orch.messages = type("Null", (), {
                "broadcast": lambda *a, **k: None,
                "collect_context": lambda *a, **k: "",
            })()
        return orch

    engine = CollisionEngine()
    engine.collide(full_goal, theory_a, theory_b, make_orch)


@alphaarena.command("watch")
@click.option("--url", default=None, help="AlphaArena API URL")
@click.option("--interval", default="1h", help="Trading interval (e.g. 1h, 4h, 1d)")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def alphaarena_watch(url: str | None, interval: str, db: str):
    """Schedule recurring trading — agents trade automatically on interval."""
    from zhihuiti.alphaarena import AlphaArenaBridge
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler, parse_interval

    bridge = AlphaArenaBridge(base_url=url)
    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)

    goal = (
        f"AlphaArena Trading: Check prices at {bridge.base_url}/api/prices. "
        f"Analyze the top 3 movers by 24h change. "
        f"If any pair moved more than 5%, consider a trade. "
        f"Check portfolio at {bridge.base_url}/api/portfolio/{bridge.agent_id}. "
        f"Execute trades via POST {bridge.base_url}/api/trades with "
        f"X-API-Key header. Max 20% of portfolio per trade. "
        f"Agent ID: {bridge.agent_id}."
    )

    seconds = parse_interval(interval)
    monitor_id = scheduler.add(goal, seconds)
    console.print(
        f"  [green]AlphaArena trader active:[/green] "
        f"trading every {interval} (ID: {monitor_id})"
    )
    mem.close()


@alphaarena.command("hedge")
@click.option("--url", default=None, help="AlphaArena API URL")
def alphaarena_hedge(url: str | None):
    """Show hedge fund agent tiers — top, mid, bottom performers."""
    from zhihuiti.hedge_manager import HedgeFundManager
    manager = HedgeFundManager(base_url=url)
    manager.print_status()


@alphaarena.command("evolve-hedge")
@click.option("--url", default=None, help="AlphaArena API URL")
@click.option("--cull", default=0.3, help="Bottom tier threshold (0-1)")
@click.option("--promote", default=0.7, help="Top tier threshold (0-1)")
def alphaarena_evolve_hedge(url: str | None, cull: float, promote: float):
    """Run one evolution cycle — evolve bottom performers using top DNA."""
    from zhihuiti.hedge_manager import HedgeFundManager
    console.print(BANNER, style="bold cyan")
    manager = HedgeFundManager(base_url=url, cull_threshold=cull, promote_threshold=promote)
    result = manager.run_evolution_cycle()
    console.print(f"\n  [green]Evolved {result['evolved']} agents[/green]")


@main.group()
def criticai():
    """🎬 CriticAI Bridge — monitor and collaborate with CriticAI agents."""
    pass


@criticai.command("status")
@click.option("--url", default="https://criticai.zeabur.app", help="CriticAI base URL")
def criticai_status(url: str):
    """Check CriticAI system status."""
    from zhihuiti.criticai_bridge import CriticAIBridge
    bridge = CriticAIBridge(base_url=url)
    bridge.print_status()


@criticai.command("report")
@click.option("--url", default="https://criticai.zeabur.app", help="CriticAI base URL")
def criticai_report(url: str):
    """Generate a full CriticAI status report."""
    from zhihuiti.criticai_bridge import CriticAIBridge
    bridge = CriticAIBridge(base_url=url)
    report = bridge.generate_status_report()
    console.print(report)


@criticai.command("trigger")
@click.option("--url", default="https://criticai.zeabur.app", help="CriticAI base URL")
def criticai_trigger(url: str):
    """Trigger a CriticAI agent to generate a new activity."""
    from zhihuiti.criticai_bridge import CriticAIBridge
    bridge = CriticAIBridge(base_url=url)
    result = bridge.trigger_activity()
    if result:
        agent_name = result.get("agent", {}).get("name", "Unknown")
        console.print(f"  [green]✓[/green] {agent_name}: [{result.get('activityType', '?')}] {result.get('content', '')[:80]}")
    else:
        console.print("  [red]Failed to trigger activity[/red]")


@criticai.command("watch")
@click.option("--url", default="https://criticai.zeabur.app", help="CriticAI base URL")
@click.option("--interval", default="30m", help="Check interval (e.g. 10m, 1h)")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
def criticai_watch(url: str, interval: str, db: str):
    """Set up a recurring monitor that watches CriticAI agent health."""
    from zhihuiti.memory import Memory
    from zhihuiti.scheduler import MonitorScheduler, parse_interval

    mem = Memory(db_path=db)
    scheduler = MonitorScheduler(mem)

    goal = (
        f"Monitor CriticAI at {url}: "
        f"1) curl -s {url}/api/agents to check if the system is online and count agents. "
        f"2) curl -s {url}/api/leaderboard to check agent rankings and activity. "
        f"3) curl -s '{url}/api/activity-feed?limit=3' to check recent activity. "
        f"Report: system status (online/offline), agent count, top critic name and score, "
        f"latest activity timestamp. Flag if: system offline, no recent activity in 1h, "
        f"or any agent's avg score dropped below 5.0."
    )

    interval_s = parse_interval(interval)
    monitor_id = scheduler.add(goal, interval_s)
    console.print(f"  [green]CriticAI watcher active:[/green] checking every {interval} (ID: {monitor_id})")
    mem.close()


@criticai.command("analyze")
@click.option("--url", default="https://criticai.zeabur.app", help="CriticAI base URL")
@click.option("--db", default="zhihuiti.db", help="SQLite database path")
@click.option("--model", default=None, help="Model name")
def criticai_analyze(url: str, db: str, model: str | None):
    """Run zhihuiti agents to deeply analyze CriticAI's critic ecosystem."""
    from zhihuiti.orchestrator import Orchestrator
    from zhihuiti.criticai_bridge import CriticAIBridge

    console.print(BANNER, style="bold cyan")
    bridge = CriticAIBridge(base_url=url)
    report = bridge.generate_status_report()

    goal = (
        f"Analyze the CriticAI entertainment review platform. Here is the current status:\n\n"
        f"{report}\n\n"
        f"Tasks:\n"
        f"1) Evaluate the critic agent ecosystem: Are agents diverse enough? Is any agent dominating? "
        f"Are rivalries balanced or one-sided?\n"
        f"2) Analyze content coverage: What content types are well-reviewed vs under-represented?\n"
        f"3) Check agent activity health: Are agents generating fresh content? Is the activity feed active?\n"
        f"4) Provide actionable recommendations: What new agent personas would add value? "
        f"What content categories need attention? How can debates be more engaging?\n"
        f"Use tools to fetch more data from {url} if needed."
    )

    orch = Orchestrator(db_path=db, model=model)
    orch.execute_goal(goal)


if __name__ == "__main__":
    main()
