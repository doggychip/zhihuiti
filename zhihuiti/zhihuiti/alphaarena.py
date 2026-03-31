"""AlphaArena Bridge — connect zhihuiti agents to the trading competition.

Provides a Python interface to AlphaArena's REST API for:
- Checking prices, portfolio, leaderboard
- Registering new trading agents
- Generating status reports for zhihuiti goals

Environment variables:
  ALPHAARENA_URL      — API base URL (default: https://alphaarena.zeabur.app)
  ALPHAARENA_API_KEY  — API key for authenticated endpoints (trades)
  ALPHAARENA_AGENT_ID — Agent ID for portfolio/trade operations
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DEFAULT_URL = "https://alphaarena.zeabur.app"


class AlphaArenaBridge:
    """Interface between zhihuiti and AlphaArena."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        agent_id: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get("ALPHAARENA_URL", DEFAULT_URL)).rstrip("/")
        self.api_key = api_key or os.environ.get("ALPHAARENA_API_KEY", "")
        self.agent_id = agent_id or os.environ.get("ALPHAARENA_AGENT_ID", "")
        self.client = httpx.Client(timeout=15)

    def _get(self, path: str) -> Any:
        resp = self.client.get(f"{self.base_url}{path}")
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> Any:
        resp = self.client.post(
            f"{self.base_url}{path}",
            json=data,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Read API ────────────────────────────────────────────────

    def get_prices(self) -> list[dict]:
        data = self._get("/api/prices")
        return data.get("prices", data) if isinstance(data, dict) else data

    def get_portfolio(self, agent_id: str | None = None) -> dict:
        aid = agent_id or self.agent_id
        if not aid:
            return {"error": "no agent_id set"}
        return self._get(f"/api/portfolio/{aid}")

    def get_leaderboard(self) -> list[dict]:
        data = self._get("/api/leaderboard")
        return data if isinstance(data, list) else data.get("leaderboard", [])

    def get_agent(self, agent_id: str | None = None) -> dict:
        aid = agent_id or self.agent_id
        return self._get(f"/api/agents/{aid}")

    def get_trades(self, agent_id: str | None = None, limit: int = 20) -> list[dict]:
        aid = agent_id or self.agent_id
        data = self._get(f"/api/trades?agentId={aid}&limit={limit}")
        return data if isinstance(data, list) else data.get("trades", [])

    # ── Write API ───────────────────────────────────────────────

    def trade(self, pair: str, side: str, quantity: float,
              agent_id: str | None = None) -> dict:
        aid = agent_id or self.agent_id
        return self._post("/api/trades", {
            "agentId": aid,
            "pair": pair,
            "side": side,
            "quantity": quantity,
        })

    def register_agent(self, username: str, email: str, password: str,
                       agent_name: str) -> dict:
        """Register a new agent. Returns dict with apiKey and agent info."""
        return self._post("/api/auth/register", {
            "username": username,
            "email": email,
            "password": password,
            "agentName": agent_name,
            "agentType": "algo_bot",
        })

    # ── Reports ─────────────────────────────────────────────────

    def generate_status_report(self) -> str:
        """Generate a text report for zhihuiti goals to consume."""
        lines = ["# AlphaArena Status Report\n"]

        # Prices
        try:
            prices = self.get_prices()
            lines.append("## Current Prices")
            for p in prices[:10]:
                pair = p.get("pair", p.get("symbol", "?"))
                price = p.get("price", p.get("current_price", 0))
                change = p.get("change24h", p.get("price_change_24h", 0))
                arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
                lines.append(f"  {pair}: ${price:,.2f} {arrow} {change:+.1f}%")
        except Exception as e:
            lines.append(f"## Prices: unavailable ({e})")

        # Portfolio
        if self.agent_id:
            try:
                portfolio = self.get_portfolio()
                cash = portfolio.get("cashBalance", 0)
                equity = portfolio.get("totalEquity", 0)
                positions = portfolio.get("positions", [])
                lines.append(f"\n## Portfolio (agent: {self.agent_id})")
                lines.append(f"  Cash: ${cash:,.2f}")
                lines.append(f"  Total Equity: ${equity:,.2f}")
                lines.append(f"  Positions: {len(positions)}")
                for pos in positions[:5]:
                    lines.append(
                        f"    {pos.get('pair','?')}: {pos.get('side','?')} "
                        f"{pos.get('quantity',0)} @ ${pos.get('avgEntryPrice',0):,.2f} "
                        f"(PnL: ${pos.get('unrealizedPnl',0):+,.2f})"
                    )
            except Exception as e:
                lines.append(f"\n## Portfolio: unavailable ({e})")

        # Leaderboard
        try:
            lb = self.get_leaderboard()
            lines.append(f"\n## Leaderboard (top 5)")
            for i, entry in enumerate(lb[:5], 1):
                name = entry.get("agentName", entry.get("name", "?"))
                score = entry.get("score", entry.get("totalScore", 0))
                ret = entry.get("totalReturn", entry.get("return", 0))
                lines.append(f"  {i}. {name}: score={score:.2f}, return={ret:+.1f}%")
        except Exception as e:
            lines.append(f"\n## Leaderboard: unavailable ({e})")

        return "\n".join(lines)

    def print_status(self) -> None:
        """Pretty-print AlphaArena status."""
        # Prices
        try:
            prices = self.get_prices()
            table = Table(title="AlphaArena Prices")
            table.add_column("Pair")
            table.add_column("Price", justify="right")
            table.add_column("24h", justify="right")
            for p in prices[:10]:
                pair = p.get("pair", p.get("symbol", "?"))
                price = p.get("price", p.get("current_price", 0))
                change = p.get("change24h", p.get("price_change_24h", 0))
                style = "green" if change > 0 else "red" if change < 0 else ""
                table.add_row(pair, f"${price:,.2f}", f"[{style}]{change:+.1f}%[/{style}]")
            console.print(table)
        except Exception as e:
            console.print(f"  [red]Prices unavailable:[/red] {e}")

        # Portfolio
        if self.agent_id:
            try:
                p = self.get_portfolio()
                console.print(Panel(
                    f"Cash: ${p.get('cashBalance', 0):,.2f}\n"
                    f"Equity: ${p.get('totalEquity', 0):,.2f}\n"
                    f"Positions: {len(p.get('positions', []))}",
                    title=f"Portfolio ({self.agent_id[:8]}...)",
                ))
            except Exception as e:
                console.print(f"  [red]Portfolio unavailable:[/red] {e}")

        # Leaderboard
        try:
            lb = self.get_leaderboard()
            table = Table(title="Leaderboard (Top 5)")
            table.add_column("#", justify="right")
            table.add_column("Agent")
            table.add_column("Score", justify="right")
            for i, entry in enumerate(lb[:5], 1):
                name = entry.get("agentName", entry.get("name", "?"))
                score = entry.get("score", entry.get("totalScore", 0))
                table.add_row(str(i), name, f"{score:.2f}")
            console.print(table)
        except Exception as e:
            console.print(f"  [red]Leaderboard unavailable:[/red] {e}")
