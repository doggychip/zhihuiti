"""Multi-Agent AlphaArena Manager — run 5 competing strategies.

Manages multiple AlphaArena agents, each with a different trading
personality. zhihuiti evolves the population: worst gets strategy
swapped, best gets bred.

Agent Personalities:
1. ZhihuiTi Evolution (existing) — momentum-based, follows trends
2. ZhihuiTi Contrarian — buys dips, sells rallies (mean reversion)
3. ZhihuiTi HODL — long-only, accumulates on drops
4. ZhihuiTi Scalper — small frequent trades on any >1% move
5. ZhihuiTi Diversifier — spreads across all 18 pairs equally
"""

from __future__ import annotations

import os
import random
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

console = Console()


# Strategy-to-trade function mapping
STRATEGY_FN_MAP = {
    "momentum": "_trade_momentum",
    "mean_reversion": "_trade_contrarian",
    "accumulate": "_trade_hodl",
    "scalp": "_trade_scalper",
    "diversify": "_trade_diversifier",
}

# 21 Agent profiles — named with Chinese trading wisdom
AGENT_PROFILES = {
    # Momentum (趋势追踪 — trend followers)
    "agent-zhihuiti": {"name": "龙首 Lóng Shǒu", "strategy": "momentum"},         # Dragon Head — leads the charge
    "agent-zhihuiti-6": {"name": "追风 Zhuī Fēng", "strategy": "momentum"},        # Wind Chaser — rides momentum
    "agent-zhihuiti-11": {"name": "破浪 Pò Làng", "strategy": "momentum"},         # Wave Breaker — surfs trends
    "agent-zhihuiti-16": {"name": "雷动 Léi Dòng", "strategy": "momentum"},        # Thunder Mover — strikes fast
    "agent-zhihuiti-21": {"name": "飞鹰 Fēi Yīng", "strategy": "momentum"},       # Flying Eagle — spots from above
    # Mean Reversion (均值回归 — contrarian)
    "agent-zhihuiti-2": {"name": "静水 Jìng Shuǐ", "strategy": "mean_reversion"}, # Still Water — buys the dip
    "agent-zhihuiti-7": {"name": "逆风 Nì Fēng", "strategy": "mean_reversion"},   # Against Wind — contrarian
    "agent-zhihuiti-12": {"name": "回春 Huí Chūn", "strategy": "mean_reversion"}, # Spring Return — recovery plays
    "agent-zhihuiti-17": {"name": "磐石 Pán Shí", "strategy": "mean_reversion"},  # Bedrock — steady hands
    # Accumulate (积蓄 — long-only holders)
    "agent-zhihuiti-3": {"name": "铁手 Tiě Shǒu", "strategy": "accumulate"},      # Iron Hand — diamond hands
    "agent-zhihuiti-9": {"name": "聚财 Jù Cái", "strategy": "accumulate"},         # Wealth Gatherer — accumulates
    "agent-zhihuiti-14": {"name": "深根 Shēn Gēn", "strategy": "accumulate"},     # Deep Root — patient builder
    "agent-zhihuiti-19": {"name": "守望 Shǒu Wàng", "strategy": "accumulate"},    # Watchkeeper — waits for drops
    # Scalp (闪电交易 — high frequency)
    "agent-zhihuiti-4": {"name": "闪电 Shǎn Diàn", "strategy": "scalp"},           # Lightning — fast strikes
    "agent-zhihuiti-8": {"name": "蜂刺 Fēng Cì", "strategy": "scalp"},             # Bee Sting — small but frequent
    "agent-zhihuiti-13": {"name": "游隼 Yóu Sǔn", "strategy": "scalp"},           # Peregrine — fastest hunter
    "agent-zhihuiti-18": {"name": "旋风 Xuán Fēng", "strategy": "scalp"},          # Whirlwind — rapid trades
    # Diversify (分散 — balanced allocation)
    "agent-zhihuiti-5": {"name": "天平 Tiān Píng", "strategy": "diversify"},        # Scales — balanced weight
    "agent-zhihuiti-10": {"name": "百川 Bǎi Chuān", "strategy": "diversify"},      # Hundred Rivers — flows everywhere
    "agent-zhihuiti-15": {"name": "织网 Zhī Wǎng", "strategy": "diversify"},       # Web Weaver — spread wide
    "agent-zhihuiti-20": {"name": "星图 Xīng Tú", "strategy": "diversify"},        # Star Map — sees the whole sky
}


class MultiAgentManager:
    """Manages multiple competing AlphaArena agents."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get("ALPHAARENA_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("ALPHAARENA_API_KEY", "")
        self.client = httpx.Client(timeout=15)

    def _get(self, path: str) -> Any:
        resp = self.client.get(f"{self.base_url}{path}")
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> Any:
        resp = self.client.post(
            f"{self.base_url}{path}",
            json=data,
            headers={"X-API-Key": self.api_key},
        )
        resp.raise_for_status()
        return resp.json()

    def get_prices(self) -> list[dict]:
        data = self._get("/api/prices")
        return data.get("prices", data) if isinstance(data, dict) else data

    def get_portfolio(self, agent_id: str) -> dict:
        try:
            return self._get(f"/api/portfolio/{agent_id}")
        except Exception:
            return {"cashBalance": 0, "totalEquity": 0, "positions": []}

    def trade(self, agent_id: str, pair: str, side: str, quantity: float) -> dict | None:
        try:
            return self._post("/api/trades", {
                "agentId": agent_id,
                "pair": pair,
                "side": side,
                "quantity": quantity,
            })
        except Exception as e:
            console.print(f"  [red]Trade failed ({agent_id}):[/red] {e}")
            return None

    # ── Trading Strategies ──────────────────────────────────────

    def _trade_momentum(self, agent_id: str, prices: list[dict], portfolio: dict) -> list[dict]:
        """Buy the top mover if >2% change."""
        trades = []
        cash = portfolio.get("cashBalance", 0)
        if cash < 500:
            return trades

        # Sort by absolute 24h change
        movers = sorted(prices, key=lambda p: abs(p.get("change24h", 0)), reverse=True)
        top = movers[0] if movers else None

        if top and abs(top.get("change24h", 0)) > 2.0:
            pair = top["pair"]
            price = top["price"]
            side = "buy" if top["change24h"] > 0 else "sell"
            max_spend = cash * 0.15
            quantity = round(max_spend / price, 4) if price > 0 else 0
            if quantity > 0:
                result = self.trade(agent_id, pair, side, quantity)
                if result:
                    trades.append({"pair": pair, "side": side, "quantity": quantity})
        return trades

    def _trade_contrarian(self, agent_id: str, prices: list[dict], portfolio: dict) -> list[dict]:
        """Buy biggest losers, sell biggest winners (mean reversion)."""
        trades = []
        cash = portfolio.get("cashBalance", 0)
        if cash < 500:
            return trades

        movers = sorted(prices, key=lambda p: p.get("change24h", 0))

        # Buy the biggest loser (expecting bounce)
        loser = movers[0] if movers else None
        if loser and loser.get("change24h", 0) < -2.0:
            pair = loser["pair"]
            price = loser["price"]
            max_spend = cash * 0.1
            quantity = round(max_spend / price, 4) if price > 0 else 0
            if quantity > 0:
                result = self.trade(agent_id, pair, "buy", quantity)
                if result:
                    trades.append({"pair": pair, "side": "buy", "quantity": quantity})

        # Sell the biggest winner (expecting pullback)
        winner = movers[-1] if movers else None
        if winner and winner.get("change24h", 0) > 3.0:
            pair = winner["pair"]
            price = winner["price"]
            max_spend = cash * 0.1
            quantity = round(max_spend / price, 4) if price > 0 else 0
            if quantity > 0:
                result = self.trade(agent_id, pair, "sell", quantity)
                if result:
                    trades.append({"pair": pair, "side": "sell", "quantity": quantity})

        return trades

    def _trade_hodl(self, agent_id: str, prices: list[dict], portfolio: dict) -> list[dict]:
        """Long-only: accumulate BTC, ETH, SOL on dips >3%."""
        trades = []
        cash = portfolio.get("cashBalance", 0)
        if cash < 500:
            return trades

        targets = ["BTC/USD", "ETH/USD", "SOL/USD", "NVDA/USD"]
        for p in prices:
            if p["pair"] in targets and p.get("change24h", 0) < -3.0:
                price = p["price"]
                max_spend = cash * 0.08
                quantity = round(max_spend / price, 4) if price > 0 else 0
                if quantity > 0:
                    result = self.trade(agent_id, p["pair"], "buy", quantity)
                    if result:
                        trades.append({"pair": p["pair"], "side": "buy", "quantity": quantity})
                        cash -= max_spend
        return trades

    def _trade_scalper(self, agent_id: str, prices: list[dict], portfolio: dict) -> list[dict]:
        """Small trades on any >1% move."""
        trades = []
        cash = portfolio.get("cashBalance", 0)
        if cash < 500:
            return trades

        for p in prices:
            change = p.get("change24h", 0)
            if abs(change) > 1.0:
                price = p["price"]
                side = "buy" if change > 0 else "sell"
                max_spend = cash * 0.03  # Small positions
                quantity = round(max_spend / price, 4) if price > 0 else 0
                if quantity > 0:
                    result = self.trade(agent_id, p["pair"], side, quantity)
                    if result:
                        trades.append({"pair": p["pair"], "side": side, "quantity": quantity})
                        cash -= max_spend
                        if cash < 500:
                            break
        return trades

    def _trade_diversifier(self, agent_id: str, prices: list[dict], portfolio: dict) -> list[dict]:
        """Equal weight across top 5 pairs by market cap."""
        trades = []
        cash = portfolio.get("cashBalance", 0)
        positions = portfolio.get("positions", [])
        held_pairs = {p.get("pair") for p in positions}

        if cash < 500:
            return trades

        # Top 5 by price (proxy for market cap)
        top5 = sorted(prices, key=lambda p: p.get("price", 0), reverse=True)[:5]
        per_position = cash * 0.1

        for p in top5:
            if p["pair"] not in held_pairs:
                price = p["price"]
                quantity = round(per_position / price, 4) if price > 0 else 0
                if quantity > 0:
                    result = self.trade(agent_id, p["pair"], "buy", quantity)
                    if result:
                        trades.append({"pair": p["pair"], "side": "buy", "quantity": quantity})
        return trades

    # ── Run All Agents ──────────────────────────────────────────

    def run_all(self) -> dict:
        """Execute one trade cycle for all agents."""
        prices = self.get_prices()
        if not prices:
            return {"error": "no prices", "trades": {}}

        results = {}
        for agent_id, profile in AGENT_PROFILES.items():
            portfolio = self.get_portfolio(agent_id)
            if not portfolio.get("cashBalance") and portfolio.get("cashBalance") != 0:
                # Agent doesn't exist yet, skip
                continue

            fn_name = STRATEGY_FN_MAP.get(profile["strategy"], "_trade_momentum")
            trade_fn = getattr(self, fn_name, None)
            if trade_fn:
                try:
                    trades = trade_fn(agent_id, prices, portfolio)
                    results[agent_id] = {
                        "name": profile["name"],
                        "strategy": profile["strategy"],
                        "trades": trades,
                        "equity": portfolio.get("totalEquity", 0),
                    }
                    if trades:
                        console.print(
                            f"  [green]{profile['name']}:[/green] "
                            f"{len(trades)} trade(s) executed"
                        )
                except Exception as e:
                    results[agent_id] = {"name": profile["name"], "error": str(e)}

        return results

    def generate_registration_sql(self) -> str:
        """Generate SQL to register all agents in AlphaArena's PostgreSQL."""
        lines = ["-- Register zhihuiti multi-agent fleet in AlphaArena", ""]

        for agent_id, profile in AGENT_PROFILES.items():
            if agent_id == "agent-zhihuiti":
                continue  # Already exists

            user_id = agent_id.replace("agent-", "usr-")
            port_id = agent_id.replace("agent-", "port-")
            name = profile["name"]
            strategy = profile["strategy"]
            num = agent_id.split("-")[-1]

            lines.append(f"-- {name} ({strategy})")
            lines.append(
                f"INSERT INTO users (id, username, email, password_hash, api_key, created_at, credits) "
                f"VALUES ('{user_id}', 'zhihuiti_{num}', 'zhihuiti{num}@doggychip.com', "
                f"'zhihuiti2026', '{self.api_key}', NOW(), 1000) "
                f"ON CONFLICT (id) DO NOTHING;"
            )
            lines.append(
                f"INSERT INTO agents (id, user_id, name, description, type, status, "
                f"strategy_language, strategy_interval, execution_count, created_at) "
                f"VALUES ('{agent_id}', '{user_id}', '{name}', "
                f"'zhihuiti {strategy} agent', 'algo_bot', 'active', "
                f"'python', '1h', 0, NOW()) "
                f"ON CONFLICT (id) DO NOTHING;"
            )
            lines.append(
                f"INSERT INTO portfolios (id, agent_id, competition_id, cash_balance, total_equity, created_at) "
                f"VALUES ('{port_id}', '{agent_id}', 'comp-1', 100000, 100000, NOW()) "
                f"ON CONFLICT (id) DO NOTHING;"
            )
            lines.append("")

        return "\n".join(lines)

    def print_status(self) -> None:
        """Show all agents' portfolio status."""
        table = Table(title="Multi-Agent Portfolio Status")
        table.add_column("Agent")
        table.add_column("Strategy")
        table.add_column("Equity", justify="right")
        table.add_column("Cash", justify="right")
        table.add_column("Positions", justify="right")

        for agent_id, profile in AGENT_PROFILES.items():
            portfolio = self.get_portfolio(agent_id)
            equity = portfolio.get("totalEquity", 0)
            cash = portfolio.get("cashBalance", 0)
            positions = len(portfolio.get("positions", []))

            if equity == 0 and cash == 0:
                table.add_row(
                    profile["name"], profile["strategy"],
                    "[red]Not registered[/red]", "-", "-"
                )
            else:
                ret_pct = ((equity - 100000) / 100000) * 100
                style = "green" if ret_pct >= 0 else "red"
                table.add_row(
                    profile["name"], profile["strategy"],
                    f"[{style}]${equity:,.0f} ({ret_pct:+.1f}%)[/{style}]",
                    f"${cash:,.0f}",
                    str(positions),
                )

        console.print(table)
