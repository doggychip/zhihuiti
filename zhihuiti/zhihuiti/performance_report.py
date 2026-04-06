"""Performance Report — aggregate trading data across all 21 agents.

Pulls portfolio, leaderboard, and trade data from AlphaArena to produce
a comprehensive performance report showing:
- Fleet-wide P&L and equity
- Strategy comparison (which approach is winning?)
- Per-agent breakdown with trade counts
- Best/worst performers
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.multi_agent import AGENT_PROFILES

console = Console()

INITIAL_EQUITY = 100_000  # Starting balance per agent


class PerformanceReport:
    """Aggregate performance report across the zhihuiti agent fleet."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("ALPHAARENA_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("ALPHAARENA_API_KEY", "")
        self.client = httpx.Client(timeout=15)

    def _get(self, path: str) -> Any:
        resp = self.client.get(f"{self.base_url}{path}")
        resp.raise_for_status()
        return resp.json()

    def collect_all(self) -> dict:
        """Fetch portfolios, leaderboard, and trades for all agents."""
        agents = {}
        errors = []

        # Leaderboard (single call)
        try:
            lb_data = self._get("/api/leaderboard")
            leaderboard = lb_data if isinstance(lb_data, list) else lb_data.get("leaderboard", [])
        except Exception as e:
            leaderboard = []
            errors.append(f"leaderboard: {e}")

        # Index leaderboard by agentId
        lb_by_id = {}
        for entry in leaderboard:
            aid = entry.get("agentId", "")
            lb_by_id[aid] = entry

        # Per-agent data
        for agent_id, profile in AGENT_PROFILES.items():
            agent_data = {
                "id": agent_id,
                "name": profile["name"],
                "strategy": profile["strategy"],
                "equity": 0.0,
                "cash": 0.0,
                "positions": 0,
                "return_pct": 0.0,
                "pnl": 0.0,
                "registered": False,
                "leaderboard": lb_by_id.get(agent_id, {}),
                "trades": [],
            }

            # Portfolio
            try:
                portfolio = self._get(f"/api/portfolio/{agent_id}")
                equity = portfolio.get("totalEquity", 0)
                cash = portfolio.get("cashBalance", 0)
                positions = portfolio.get("positions", [])

                if equity > 0 or cash > 0:
                    agent_data["registered"] = True
                    agent_data["equity"] = equity
                    agent_data["cash"] = cash
                    agent_data["positions"] = len(positions)
                    agent_data["pnl"] = equity - INITIAL_EQUITY
                    agent_data["return_pct"] = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
            except Exception:
                pass

            # Recent trades
            try:
                trades_data = self._get(f"/api/trades?agentId={agent_id}&limit=50")
                trades = trades_data if isinstance(trades_data, list) else trades_data.get("trades", [])
                agent_data["trades"] = trades
            except Exception:
                pass

            agents[agent_id] = agent_data

        return {"agents": agents, "leaderboard": leaderboard, "errors": errors}

    def generate(self) -> dict:
        """Generate the full performance report."""
        data = self.collect_all()
        agents = data["agents"]

        registered = {k: v for k, v in agents.items() if v["registered"]}
        if not registered:
            return {"error": "No registered agents found", "agents": agents}

        # Fleet totals
        total_equity = sum(a["equity"] for a in registered.values())
        total_pnl = sum(a["pnl"] for a in registered.values())
        total_initial = len(registered) * INITIAL_EQUITY
        fleet_return = ((total_equity - total_initial) / total_initial) * 100 if total_initial > 0 else 0
        total_trades = sum(len(a["trades"]) for a in registered.values())

        # Strategy aggregation
        by_strategy: dict[str, list[dict]] = defaultdict(list)
        for a in registered.values():
            by_strategy[a["strategy"]].append(a)

        strategy_stats = {}
        for strat, members in by_strategy.items():
            equities = [m["equity"] for m in members]
            returns = [m["return_pct"] for m in members]
            trade_counts = [len(m["trades"]) for m in members]
            strategy_stats[strat] = {
                "count": len(members),
                "total_equity": sum(equities),
                "avg_return": sum(returns) / len(returns) if returns else 0,
                "best_return": max(returns) if returns else 0,
                "worst_return": min(returns) if returns else 0,
                "total_trades": sum(trade_counts),
                "total_pnl": sum(m["pnl"] for m in members),
            }

        # Rankings
        ranked = sorted(registered.values(), key=lambda a: a["return_pct"], reverse=True)

        # Leaderboard metrics (if available)
        lb_agents = [a for a in registered.values() if a["leaderboard"]]
        avg_sharpe = 0.0
        avg_winrate = 0.0
        if lb_agents:
            avg_sharpe = sum(a["leaderboard"].get("sharpeRatio", 0) for a in lb_agents) / len(lb_agents)
            avg_winrate = sum(a["leaderboard"].get("winRate", 0) for a in lb_agents) / len(lb_agents)

        return {
            "timestamp": datetime.now().isoformat(),
            "fleet": {
                "registered": len(registered),
                "total": len(agents),
                "total_equity": total_equity,
                "total_initial": total_initial,
                "total_pnl": total_pnl,
                "fleet_return_pct": fleet_return,
                "total_trades": total_trades,
                "avg_sharpe": avg_sharpe,
                "avg_winrate": avg_winrate,
            },
            "strategy_stats": strategy_stats,
            "ranked_agents": ranked,
            "best": ranked[0] if ranked else None,
            "worst": ranked[-1] if ranked else None,
            "errors": data["errors"],
        }

    def print_report(self) -> None:
        """Pretty-print the full performance report."""
        report = self.generate()

        if "error" in report:
            console.print(f"[red]{report['error']}[/red]")
            return

        fleet = report["fleet"]

        # Fleet summary
        pnl_style = "green" if fleet["total_pnl"] >= 0 else "red"
        console.print(Panel(
            f"Agents: {fleet['registered']}/{fleet['total']} registered\n"
            f"Total Equity: ${fleet['total_equity']:,.2f}\n"
            f"Total P&L: [{pnl_style}]${fleet['total_pnl']:+,.2f} ({fleet['fleet_return_pct']:+.2f}%)[/{pnl_style}]\n"
            f"Total Trades: {fleet['total_trades']}\n"
            f"Avg Sharpe: {fleet['avg_sharpe']:.2f}\n"
            f"Avg Win Rate: {fleet['avg_winrate']*100:.1f}%",
            title="Fleet Performance Summary",
            border_style="cyan",
        ))

        # Strategy comparison
        strat_table = Table(title="Strategy Comparison")
        strat_table.add_column("Strategy")
        strat_table.add_column("Agents", justify="right")
        strat_table.add_column("Avg Return", justify="right")
        strat_table.add_column("Best", justify="right")
        strat_table.add_column("Worst", justify="right")
        strat_table.add_column("Total P&L", justify="right")
        strat_table.add_column("Trades", justify="right")

        sorted_strats = sorted(
            report["strategy_stats"].items(),
            key=lambda x: x[1]["avg_return"],
            reverse=True,
        )
        for strat, stats in sorted_strats:
            avg_style = "green" if stats["avg_return"] >= 0 else "red"
            pnl_s = "green" if stats["total_pnl"] >= 0 else "red"
            strat_table.add_row(
                strat,
                str(stats["count"]),
                f"[{avg_style}]{stats['avg_return']:+.2f}%[/{avg_style}]",
                f"{stats['best_return']:+.2f}%",
                f"{stats['worst_return']:+.2f}%",
                f"[{pnl_s}]${stats['total_pnl']:+,.0f}[/{pnl_s}]",
                str(stats["total_trades"]),
            )
        console.print(strat_table)

        # Per-agent leaderboard
        agent_table = Table(title="Agent Rankings (by return)")
        agent_table.add_column("#", justify="right")
        agent_table.add_column("Agent")
        agent_table.add_column("Strategy")
        agent_table.add_column("Equity", justify="right")
        agent_table.add_column("P&L", justify="right")
        agent_table.add_column("Return", justify="right")
        agent_table.add_column("Trades", justify="right")
        agent_table.add_column("Positions", justify="right")

        for i, agent in enumerate(report["ranked_agents"], 1):
            ret_style = "green" if agent["return_pct"] >= 0 else "red"
            pnl_style = "green" if agent["pnl"] >= 0 else "red"

            # Medal for top 3
            prefix = {1: "1", 2: "2", 3: "3"}.get(i, str(i))

            agent_table.add_row(
                prefix,
                agent["name"],
                agent["strategy"],
                f"${agent['equity']:,.0f}",
                f"[{pnl_style}]${agent['pnl']:+,.0f}[/{pnl_style}]",
                f"[{ret_style}]{agent['return_pct']:+.2f}%[/{ret_style}]",
                str(len(agent["trades"])),
                str(agent["positions"]),
            )
        console.print(agent_table)

        # Best / Worst callout
        best = report["best"]
        worst = report["worst"]
        if best and worst:
            console.print(
                f"\n  Best:  [green]{best['name']}[/green] ({best['strategy']}) "
                f"[green]{best['return_pct']:+.2f}%[/green]"
            )
            console.print(
                f"  Worst: [red]{worst['name']}[/red] ({worst['strategy']}) "
                f"[red]{worst['return_pct']:+.2f}%[/red]"
            )

        if report["errors"]:
            console.print(f"\n  [yellow]Warnings: {', '.join(report['errors'])}[/yellow]")

    def export_json(self) -> str:
        """Export report as JSON string."""
        import json
        report = self.generate()
        return json.dumps(report, indent=2, default=str)
