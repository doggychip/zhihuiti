"""Real P&L Scorer — scores agents based on actual trading performance.

Instead of asking an LLM "rate this output 0-1", this scorer checks
the actual portfolio return on AlphaArena after a trade cycle.

Score = f(return, sharpe, drawdown, win_rate)
"""

from __future__ import annotations

import os
from typing import Any

from rich.console import Console

console = Console()


class PnLScorer:
    """Score agents based on real trading P&L from AlphaArena."""

    def __init__(
        self,
        base_url: str | None = None,
        agent_id: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get("ALPHAARENA_URL", "")).rstrip("/")
        self.agent_id = agent_id or os.environ.get("ALPHAARENA_AGENT_ID", "")
        self._prev_equity: float | None = None

    def get_portfolio(self) -> dict:
        """Fetch current portfolio from AlphaArena."""
        if not self.base_url or not self.agent_id:
            return {}
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/api/portfolio/{self.agent_id}", timeout=10)
            return resp.json()
        except Exception:
            return {}

    def get_leaderboard_entry(self) -> dict | None:
        """Get our agent's leaderboard entry."""
        if not self.base_url or not self.agent_id:
            return None
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/api/leaderboard", timeout=10)
            data = resp.json()
            entries = data if isinstance(data, list) else data.get("leaderboard", data.get("entries", []))
            for entry in entries:
                if entry.get("agentId") == self.agent_id:
                    return entry
        except Exception:
            pass
        return None

    def snapshot_equity(self) -> float:
        """Take a snapshot of current equity (call BEFORE trade cycle)."""
        portfolio = self.get_portfolio()
        equity = portfolio.get("totalEquity", 100000)
        self._prev_equity = equity
        return equity

    def score_cycle(self) -> dict:
        """Score the current trade cycle based on real P&L.

        Call snapshot_equity() before the cycle, then score_cycle() after.

        Returns:
            dict with:
                score: 0.0-1.0 (overall score)
                return_pct: float (period return)
                equity: float (current equity)
                prev_equity: float (equity before cycle)
                leaderboard_rank: int | None
                components: dict (breakdown of score)
        """
        portfolio = self.get_portfolio()
        current_equity = portfolio.get("totalEquity", 100000)
        prev_equity = self._prev_equity or 100000
        positions = portfolio.get("positions", [])
        cash = portfolio.get("cashBalance", 100000)

        # Calculate return
        return_pct = ((current_equity - prev_equity) / prev_equity) * 100 if prev_equity > 0 else 0

        # Get leaderboard metrics
        lb_entry = self.get_leaderboard_entry()
        sharpe = lb_entry.get("sharpeRatio", 0) if lb_entry else 0
        max_drawdown = lb_entry.get("maxDrawdown", 0) if lb_entry else 0
        win_rate = lb_entry.get("winRate", 0) if lb_entry else 0
        rank = lb_entry.get("rank", None) if lb_entry else None
        total_agents = 20  # approximate

        # Score components (each 0.0-1.0)
        # 1. Return score: positive return is good, scale from -5% to +5%
        return_score = max(0, min(1, (return_pct + 5) / 10))

        # 2. Sharpe score: >2 is good, >5 is excellent
        sharpe_score = max(0, min(1, sharpe / 5))

        # 3. Drawdown score: lower is better (inverted)
        drawdown_score = max(0, 1 - max_drawdown)

        # 4. Win rate score: direct mapping
        winrate_score = win_rate

        # 5. Rank score: top 5 out of 20 = good
        rank_score = max(0, 1 - (rank - 1) / total_agents) if rank else 0.5

        # 6. Activity score: having positions = good (agent is actually trading)
        activity_score = min(1.0, len(positions) * 0.3 + 0.1) if positions else 0.0

        # Weighted composite
        score = (
            return_score * 0.25 +
            sharpe_score * 0.20 +
            drawdown_score * 0.15 +
            winrate_score * 0.15 +
            rank_score * 0.15 +
            activity_score * 0.10
        )

        # Clamp to 0-1
        score = max(0.0, min(1.0, round(score, 3)))

        result = {
            "score": score,
            "return_pct": round(return_pct, 4),
            "equity": current_equity,
            "prev_equity": prev_equity,
            "positions": len(positions),
            "cash": cash,
            "leaderboard_rank": rank,
            "components": {
                "return": round(return_score, 3),
                "sharpe": round(sharpe_score, 3),
                "drawdown": round(drawdown_score, 3),
                "win_rate": round(winrate_score, 3),
                "rank": round(rank_score, 3),
                "activity": round(activity_score, 3),
            },
        }

        # Update snapshot for next cycle
        self._prev_equity = current_equity

        return result

    def print_report(self) -> None:
        """Pretty-print current P&L status."""
        result = self.score_cycle()

        from rich.panel import Panel
        from rich.table import Table

        table = Table(title="Real P&L Score")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_column("Score", justify="right")

        table.add_row("Return", f"{result['return_pct']:+.2f}%",
                       f"{result['components']['return']:.3f}")
        table.add_row("Sharpe", "-",
                       f"{result['components']['sharpe']:.3f}")
        table.add_row("Max Drawdown", "-",
                       f"{result['components']['drawdown']:.3f}")
        table.add_row("Win Rate", "-",
                       f"{result['components']['win_rate']:.3f}")
        table.add_row("Rank", str(result.get("leaderboard_rank", "?")),
                       f"{result['components']['rank']:.3f}")
        table.add_row("Activity", f"{result['positions']} positions",
                       f"{result['components']['activity']:.3f}")
        table.add_row("", "", "")
        table.add_row("[bold]COMPOSITE[/bold]", f"${result['equity']:,.2f}",
                       f"[bold]{result['score']:.3f}[/bold]")

        console.print(table)
