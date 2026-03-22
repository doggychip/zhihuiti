"""Hedge Fund Meta-Manager — zhihuiti governs AlphaArena agents.

Observes leaderboard → evaluates performance → evolves strategies.
Bottom performers get their strategy swapped or parameters mutated.
Top performers' parameters get bred together.

This is the bridge that makes AlphaArena agents part of zhihuiti's
evolutionary system.
"""

from __future__ import annotations

import json
import os
import random
from typing import Any

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Available strategy types in AlphaArena
STRATEGY_TYPES = [
    "momentum",
    "momentum_multi",
    "momentum_strong",
    "mean_reversion",
    "indicator_macd",
    "indicator_ichimoku",
    "hybrid_adaptive",
]

# Default parameter ranges for each strategy type
PARAM_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "momentum": {
        "shortPeriod": (3, 15),
        "longPeriod": (10, 50),
        "quantity": (0.01, 0.5),
    },
    "momentum_multi": {
        "period": (5, 30),
        "quantity": (0.01, 0.3),
    },
    "momentum_strong": {
        "period": (5, 30),
        "threshold": (0.01, 0.1),
        "volThreshold": (0.005, 0.05),
        "quantity": (0.01, 0.3),
    },
    "mean_reversion": {
        "period": (10, 50),
        "threshold": (0.5, 3.0),
        "quantity": (0.01, 0.3),
    },
    "hybrid_adaptive": {
        "period": (5, 30),
        "baseQuantity": (0.01, 0.2),
        "targetVol": (0.01, 0.05),
    },
    "indicator_macd": {
        "quantity": (0.01, 0.3),
    },
    "indicator_ichimoku": {
        "quantity": (0.01, 0.3),
    },
}

# Tradable pairs
PAIRS = [
    "BTC/USD", "ETH/USD", "BNB/USD", "SOL/USD", "XRP/USD",
    "ADA/USD", "DOGE/USD", "AVAX/USD", "DOT/USD", "LINK/USD",
    "AAPL/USD", "TSLA/USD", "NVDA/USD", "MSFT/USD",
    "GOOGL/USD", "AMZN/USD", "META/USD",
]


class HedgeFundManager:
    """zhihuiti meta-manager for AlphaArena hedge fund agents."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        cull_threshold: float = 0.3,
        promote_threshold: float = 0.7,
    ):
        self.base_url = (base_url or os.environ.get("ALPHAARENA_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("ALPHAARENA_API_KEY", "")
        self.client = httpx.Client(timeout=15)
        self.cull_threshold = cull_threshold
        self.promote_threshold = promote_threshold

    def _get(self, path: str) -> Any:
        resp = self.client.get(f"{self.base_url}{path}")
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, data: dict) -> Any:
        resp = self.client.put(
            f"{self.base_url}{path}",
            json=data,
            headers={"X-API-Key": self.api_key},
        )
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

    # ── Observe ─────────────────────────────────────────────────

    def get_leaderboard(self) -> list[dict]:
        data = self._get("/api/leaderboard")
        entries = data if isinstance(data, list) else data.get("leaderboard", data.get("entries", []))
        return entries

    def get_agent(self, agent_id: str) -> dict:
        return self._get(f"/api/agents/{agent_id}")

    def get_strategies(self) -> list[dict]:
        try:
            return self._get("/api/strategies")
        except Exception:
            return []

    # ── Evaluate ────────────────────────────────────────────────

    def evaluate_agents(self) -> dict:
        """Score all agents and categorize into tiers."""
        lb = self.get_leaderboard()
        if not lb:
            return {"top": [], "mid": [], "bottom": [], "all": []}

        # Normalize composite scores
        scores = [e.get("compositeScore", 0) for e in lb]
        max_score = max(scores) if scores else 1

        top = []
        mid = []
        bottom = []

        for entry in lb:
            score = entry.get("compositeScore", 0)
            normalized = score / max_score if max_score > 0 else 0

            agent_data = {
                "agentId": entry.get("agentId"),
                "rank": entry.get("rank", 0),
                "score": score,
                "normalized": round(normalized, 3),
                "totalReturn": entry.get("totalReturn", 0),
                "sharpeRatio": entry.get("sharpeRatio", 0),
                "winRate": entry.get("winRate", 0),
                "maxDrawdown": entry.get("maxDrawdown", 0),
                "agent": entry.get("agent", {}),
            }

            if normalized >= self.promote_threshold:
                top.append(agent_data)
            elif normalized <= self.cull_threshold:
                bottom.append(agent_data)
            else:
                mid.append(agent_data)

        return {"top": top, "mid": mid, "bottom": bottom, "all": lb}

    # ── Evolve ──────────────────────────────────────────────────

    def mutate_params(self, strategy_type: str, params: dict) -> dict:
        """Mutate strategy parameters within valid ranges."""
        ranges = PARAM_RANGES.get(strategy_type, {})
        new_params = dict(params)

        for key, (lo, hi) in ranges.items():
            if key in new_params:
                # Mutate by +/- 20%
                current = float(new_params[key])
                delta = current * 0.2 * (random.random() * 2 - 1)
                new_val = max(lo, min(hi, current + delta))
                # Keep integers as integers
                if isinstance(params.get(key), int):
                    new_params[key] = int(round(new_val))
                else:
                    new_params[key] = round(new_val, 4)
            else:
                # Add missing param with random value
                new_params[key] = round(random.uniform(lo, hi), 4)

        # Randomly swap pair
        if random.random() < 0.2:
            new_params["pair"] = random.choice(PAIRS)

        return new_params

    def crossover_params(self, parent_a: dict, parent_b: dict) -> dict:
        """Breed two parameter sets together."""
        child = {}
        all_keys = set(list(parent_a.keys()) + list(parent_b.keys()))

        for key in all_keys:
            if key in parent_a and key in parent_b:
                # Average numeric values, random pick for strings
                va, vb = parent_a[key], parent_b[key]
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    child[key] = round((va + vb) / 2, 4)
                else:
                    child[key] = random.choice([va, vb])
            elif key in parent_a:
                child[key] = parent_a[key]
            else:
                child[key] = parent_b[key]

        return child

    def evolve_bottom(self, bottom_agents: list[dict], top_agents: list[dict]) -> list[dict]:
        """Evolve underperforming agents using top performers' DNA."""
        results = []

        for agent_data in bottom_agents:
            agent_id = agent_data["agentId"]
            action = random.choice(["swap_strategy", "mutate_params", "breed"])

            try:
                agent = self.get_agent(agent_id)
                current_config = json.loads(agent.get("config", "{}") or "{}")
                current_strategy = agent.get("strategy", {}) or {}
                current_type = current_strategy.get("type", "momentum")

                if action == "swap_strategy":
                    # Switch to a different strategy type
                    new_type = random.choice([t for t in STRATEGY_TYPES if t != current_type])
                    new_params = self.mutate_params(new_type, {})
                    new_params["pair"] = current_config.get("pair", random.choice(PAIRS))

                    # Create new strategy and assign
                    try:
                        strat = self._post("/api/strategies", {
                            "name": f"evolved-{agent_id[-6:]}-{new_type}",
                            "description": f"Auto-evolved by zhihuiti from {current_type}",
                            "type": new_type,
                            "parameters": json.dumps(new_params),
                        })
                        self._put(f"/api/agents/{agent_id}", {
                            "strategyId": strat.get("id"),
                            "config": json.dumps(new_params),
                        })
                        results.append({
                            "agent": agent_id,
                            "action": f"swap: {current_type} → {new_type}",
                            "params": new_params,
                        })
                    except Exception as e:
                        # If can't create strategy, just update config
                        self._put(f"/api/agents/{agent_id}", {
                            "config": json.dumps(new_params),
                        })
                        results.append({
                            "agent": agent_id,
                            "action": f"config update (strategy swap failed: {e})",
                            "params": new_params,
                        })

                elif action == "mutate_params":
                    # Keep same strategy, mutate parameters
                    new_params = self.mutate_params(current_type, current_config)
                    self._put(f"/api/agents/{agent_id}", {
                        "config": json.dumps(new_params),
                    })
                    results.append({
                        "agent": agent_id,
                        "action": f"mutate params ({current_type})",
                        "params": new_params,
                    })

                elif action == "breed" and top_agents:
                    # Breed with a top performer
                    parent = random.choice(top_agents)
                    parent_agent = self.get_agent(parent["agentId"])
                    parent_config = json.loads(parent_agent.get("config", "{}") or "{}")

                    child_params = self.crossover_params(current_config, parent_config)
                    child_params = self.mutate_params(current_type, child_params)

                    self._put(f"/api/agents/{agent_id}", {
                        "config": json.dumps(child_params),
                    })
                    results.append({
                        "agent": agent_id,
                        "action": f"breed with {parent['agentId'][:10]}",
                        "params": child_params,
                    })

            except Exception as e:
                results.append({
                    "agent": agent_id,
                    "action": f"failed: {e}",
                    "params": {},
                })

        return results

    # ── Full Evolution Cycle ────────────────────────────────────

    def run_evolution_cycle(self) -> dict:
        """Run one full evolution cycle:
        1. Observe leaderboard
        2. Evaluate agents into tiers
        3. Evolve bottom performers using top performers' DNA
        4. Report results
        """
        console.print("\n[bold cyan]🧬 Hedge Fund Evolution Cycle[/bold cyan]")

        # Evaluate
        tiers = self.evaluate_agents()
        console.print(f"  Top: {len(tiers['top'])} | Mid: {len(tiers['mid'])} | Bottom: {len(tiers['bottom'])}")

        if not tiers["bottom"]:
            console.print("  [green]All agents performing well — no evolution needed[/green]")
            return {"evolved": 0, "results": [], "tiers": tiers}

        # Evolve
        results = self.evolve_bottom(tiers["bottom"], tiers["top"])

        # Report
        table = Table(title="Evolution Results")
        table.add_column("Agent")
        table.add_column("Action")
        for r in results:
            table.add_row(r["agent"][:12], r["action"])
        console.print(table)

        return {
            "evolved": len(results),
            "results": results,
            "tiers": {
                "top": len(tiers["top"]),
                "mid": len(tiers["mid"]),
                "bottom": len(tiers["bottom"]),
            },
        }

    def print_status(self) -> None:
        """Pretty-print hedge fund status."""
        tiers = self.evaluate_agents()

        table = Table(title="AlphaArena Hedge Fund — Agent Tiers")
        table.add_column("#", justify="right")
        table.add_column("Agent")
        table.add_column("Score", justify="right")
        table.add_column("Return", justify="right")
        table.add_column("Sharpe", justify="right")
        table.add_column("Win Rate", justify="right")
        table.add_column("Tier")

        for tier_name, agents, style in [
            ("🏆 TOP", tiers["top"], "green"),
            ("📊 MID", tiers["mid"], ""),
            ("⚠️ BOTTOM", tiers["bottom"], "red"),
        ]:
            for a in agents:
                table.add_row(
                    str(a["rank"]),
                    (a.get("agent", {}).get("name", "") or a["agentId"])[:15],
                    f"[{style}]{a['score']:.3f}[/{style}]" if style else f"{a['score']:.3f}",
                    f"{a['totalReturn']:+.2f}%",
                    f"{a['sharpeRatio']:.1f}",
                    f"{a['winRate']*100:.0f}%",
                    tier_name,
                )

        console.print(table)
