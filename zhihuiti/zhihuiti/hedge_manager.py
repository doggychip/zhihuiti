"""Hedge Fund Meta-Manager — zhihuiti governs AlphaArena agents.

Observes leaderboard → evaluates performance → evolves strategies.
Bottom performers get their strategy swapped or parameters mutated.
Top performers' parameters get bred together.

Theory-guided evolution: the Crypto Oracle diagnoses current market regime
and detected patterns, then the manager steers strategy selection accordingly
instead of choosing randomly.

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

# ── Theory-guided regime → strategy mapping ────────────────────────────────
# Maps oracle-detected regimes to preferred strategies (ordered by fitness).
# The first strategy is strongest for the regime; the rest are fallbacks.
REGIME_STRATEGIES: dict[str, list[str]] = {
    "trending_up": ["momentum_strong", "momentum", "momentum_multi"],
    "trending_down": ["momentum_strong", "momentum", "indicator_macd"],
    "mean_reverting": ["mean_reversion", "indicator_ichimoku", "hybrid_adaptive"],
    "volatile": ["hybrid_adaptive", "mean_reversion", "indicator_ichimoku"],
    "quiet": ["indicator_ichimoku", "indicator_macd", "mean_reversion"],
}

# Maps detected pattern names to parameter tweaks (applied on top of base params).
# Each entry is (strategy_type, param_key, adjustment_fn).
PATTERN_PARAM_HINTS: dict[str, list[tuple[str, str, str]]] = {
    "momentum": [
        ("momentum", "shortPeriod", "decrease"),
        ("momentum_strong", "threshold", "decrease"),
    ],
    "mean_reversion": [
        ("mean_reversion", "threshold", "decrease"),
        ("mean_reversion", "period", "increase"),
    ],
    "volatility_clustering": [
        ("hybrid_adaptive", "targetVol", "increase"),
        ("momentum_strong", "volThreshold", "increase"),
    ],
    "orderbook_imbalance": [
        ("momentum", "quantity", "increase"),
        ("momentum_strong", "quantity", "increase"),
    ],
    "fat_tails": [
        ("hybrid_adaptive", "baseQuantity", "decrease"),
        ("mean_reversion", "quantity", "decrease"),
    ],
}

# ── Collision-derived strategy overrides ───────────────────────────────────
# When collision insights reveal specific pattern combinations, these overrides
# take priority over the default regime → strategy mapping.
# Key: frozenset of two pattern names → (preferred_strategy, quantity_scale)
COLLISION_OVERRIDES: dict[frozenset[str], tuple[str, float]] = {
    frozenset({"momentum", "volatility_clustering"}):
        ("hybrid_adaptive", 0.5),     # vol masks momentum → adaptive with small size
    frozenset({"momentum", "mean_reversion"}):
        ("mean_reversion", 0.7),      # conflicting signals → favor reversion, cautious size
    frozenset({"momentum", "orderbook_imbalance"}):
        ("momentum_strong", 1.3),     # flow confirms trend → strong momentum, bigger size
    frozenset({"mean_reversion", "volatility_clustering"}):
        ("hybrid_adaptive", 0.6),     # unstable vol → adaptive approach
    frozenset({"volatility_clustering", "fat_tails"}):
        ("hybrid_adaptive", 0.3),     # dangerous regime → minimal exposure
    frozenset({"mean_reversion", "support_resistance"}):
        ("mean_reversion", 1.2),      # structural level confirms reversion → high confidence
    frozenset({"momentum", "support_resistance"}):
        ("momentum", 0.7),            # trend approaching level → take partial profit
    frozenset({"volatility_clustering", "support_resistance"}):
        ("momentum_strong", 1.0),     # breakout setup → prepare for trend
    frozenset({"orderbook_imbalance", "support_resistance"}):
        ("momentum_strong", 1.2),     # flow at level → strong confirmation
    frozenset({"fat_tails", "orderbook_imbalance"}):
        ("momentum", 0.4),            # informed flow in tail regime → follow flow, tiny size
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

    # ── Oracle ──────────────────────────────────────────────────

    def diagnose(self, candles: list[dict], book: dict | None = None) -> "MarketDiagnosis | None":
        """Run the crypto oracle on candle data. Returns None if oracle unavailable."""
        try:
            from zhihuiti.crypto_oracle import diagnose_market
            return diagnose_market(candles, book=book)
        except Exception:
            return None

    def pick_strategy_for_regime(self, regime: str, current_type: str) -> str:
        """Pick the best strategy for a regime, avoiding the current (failing) one."""
        candidates = REGIME_STRATEGIES.get(regime, STRATEGY_TYPES)
        # Prefer regime-matched strategies, but skip the one that's already failing
        for candidate in candidates:
            if candidate != current_type:
                return candidate
        # All candidates are the same as current — fall back to random
        return random.choice([t for t in STRATEGY_TYPES if t != current_type])

    def get_collision_override(self, diagnosis: Any) -> tuple[str, float] | None:
        """Check if collision insights suggest a specific strategy + sizing override.

        When two patterns fire simultaneously and their collision produces a known
        trading rule, the override takes priority over regime-based selection.
        Returns (strategy_type, quantity_scale) or None.
        """
        collision_insights = getattr(diagnosis, "collision_insights", [])
        if not collision_insights:
            return None

        # Use the highest-scoring collision insight
        patterns = getattr(diagnosis, "patterns", [])
        pattern_names = {p.name for p in patterns}

        # Check all known collision overrides against detected pattern pairs
        best_override = None
        best_score = 0.0

        for ci in collision_insights:
            pair = frozenset({ci.pattern_a, ci.pattern_b})
            if pair in COLLISION_OVERRIDES:
                if ci.collision_score > best_score:
                    best_override = COLLISION_OVERRIDES[pair]
                    best_score = ci.collision_score

        return best_override

    def apply_pattern_hints(self, strategy_type: str, params: dict, patterns: list) -> dict:
        """Adjust parameters based on detected patterns from the oracle."""
        new_params = dict(params)
        ranges = PARAM_RANGES.get(strategy_type, {})

        for pattern in patterns:
            hints = PATTERN_PARAM_HINTS.get(pattern.name, [])
            for hint_strat, hint_key, direction in hints:
                if hint_strat != strategy_type:
                    continue
                if hint_key not in new_params or hint_key not in ranges:
                    continue
                lo, hi = ranges[hint_key]
                current = float(new_params[hint_key])
                # Nudge by pattern strength * 15% of range
                nudge = (hi - lo) * 0.15 * pattern.strength
                if direction == "increase":
                    new_params[hint_key] = round(min(hi, current + nudge), 4)
                elif direction == "decrease":
                    new_params[hint_key] = round(max(lo, current - nudge), 4)

        return new_params

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

    def evolve_bottom(
        self,
        bottom_agents: list[dict],
        top_agents: list[dict],
        diagnosis: Any = None,
    ) -> list[dict]:
        """Evolve underperforming agents using top performers' DNA.

        If a MarketDiagnosis is provided, strategy selection is guided by the
        detected regime, patterns, and collision insights instead of being random.
        """
        results = []
        regime = getattr(diagnosis, "regime", None)
        patterns = getattr(diagnosis, "patterns", [])

        # Check for collision-derived strategy override
        collision_override = self.get_collision_override(diagnosis) if diagnosis else None

        for agent_data in bottom_agents:
            agent_id = agent_data["agentId"]

            # Theory-guided action selection based on regime
            if collision_override:
                # Collision insights take priority — always swap to collision-recommended strategy
                action = "swap_strategy"
            elif regime:
                # In volatile/mean-reverting regimes, prefer swapping to regime-fit strategy.
                # In trending regimes with top performers, prefer breeding.
                if regime in ("volatile", "mean_reverting"):
                    action = "swap_strategy"
                elif regime in ("trending_up", "trending_down") and top_agents:
                    action = random.choice(["breed", "swap_strategy"])
                else:
                    action = random.choice(["swap_strategy", "mutate_params", "breed"])
            else:
                action = random.choice(["swap_strategy", "mutate_params", "breed"])

            try:
                agent = self.get_agent(agent_id)
                current_config = json.loads(agent.get("config", "{}") or "{}")
                current_strategy = agent.get("strategy", {}) or {}
                current_type = current_strategy.get("type", "momentum")

                if action == "swap_strategy":
                    # Priority: collision override > regime > random
                    if collision_override:
                        new_type, qty_scale = collision_override
                        if new_type == current_type:
                            new_type = self.pick_strategy_for_regime(regime or "quiet", current_type)
                        reason = f"collision({new_type}, scale={qty_scale})"
                    elif regime:
                        new_type = self.pick_strategy_for_regime(regime, current_type)
                        qty_scale = 1.0
                        reason = f"regime={regime}"
                    else:
                        new_type = random.choice([t for t in STRATEGY_TYPES if t != current_type])
                        qty_scale = 1.0
                        reason = "random"

                    new_params = self.mutate_params(new_type, {})
                    new_params["pair"] = current_config.get("pair", random.choice(PAIRS))

                    # Apply collision quantity scaling
                    if collision_override:
                        for qkey in ("quantity", "baseQuantity"):
                            if qkey in new_params:
                                new_params[qkey] = round(new_params[qkey] * qty_scale, 4)

                    # Apply pattern-based parameter hints
                    if patterns:
                        new_params = self.apply_pattern_hints(new_type, new_params, patterns)

                    # Create new strategy and assign
                    try:
                        strat = self._post("/api/strategies", {
                            "name": f"evolved-{agent_id[-6:]}-{new_type}",
                            "description": f"Auto-evolved by zhihuiti ({reason}) from {current_type}",
                            "type": new_type,
                            "parameters": json.dumps(new_params),
                        })
                        self._put(f"/api/agents/{agent_id}", {
                            "strategyId": strat.get("id"),
                            "config": json.dumps(new_params),
                        })
                        results.append({
                            "agent": agent_id,
                            "action": f"swap: {current_type} -> {new_type} ({reason})",
                            "params": new_params,
                            "regime": regime,
                        })
                    except Exception as e:
                        # If can't create strategy, just update config
                        self._put(f"/api/agents/{agent_id}", {
                            "config": json.dumps(new_params),
                        })
                        results.append({
                            "agent": agent_id,
                            "action": f"config update ({reason}, strategy swap failed: {e})",
                            "params": new_params,
                            "regime": regime,
                        })

                elif action == "mutate_params":
                    # Keep same strategy, mutate parameters + apply pattern hints
                    new_params = self.mutate_params(current_type, current_config)
                    if patterns:
                        new_params = self.apply_pattern_hints(current_type, new_params, patterns)
                    self._put(f"/api/agents/{agent_id}", {
                        "config": json.dumps(new_params),
                    })
                    results.append({
                        "agent": agent_id,
                        "action": f"mutate params ({current_type})" + (f" + {len(patterns)} pattern hints" if patterns else ""),
                        "params": new_params,
                        "regime": regime,
                    })

                elif action == "breed" and top_agents:
                    # Breed with a top performer
                    parent = random.choice(top_agents)
                    parent_agent = self.get_agent(parent["agentId"])
                    parent_config = json.loads(parent_agent.get("config", "{}") or "{}")

                    child_params = self.crossover_params(current_config, parent_config)
                    child_params = self.mutate_params(current_type, child_params)
                    if patterns:
                        child_params = self.apply_pattern_hints(current_type, child_params, patterns)

                    self._put(f"/api/agents/{agent_id}", {
                        "config": json.dumps(child_params),
                    })
                    results.append({
                        "agent": agent_id,
                        "action": f"breed with {parent['agentId'][:10]}" + (f" + {len(patterns)} pattern hints" if patterns else ""),
                        "params": child_params,
                        "regime": regime,
                    })

            except Exception as e:
                results.append({
                    "agent": agent_id,
                    "action": f"failed: {e}",
                    "params": {},
                    "regime": regime,
                })

        return results

    # ── Full Evolution Cycle ────────────────────────────────────

    def run_evolution_cycle(self, candles: list[dict] | None = None, book: dict | None = None) -> dict:
        """Run one full theory-guided evolution cycle:
        1. Run Crypto Oracle on market data (if candles provided)
        2. Observe leaderboard
        3. Evaluate agents into tiers
        4. Evolve bottom performers guided by oracle diagnosis
        5. Report results
        """
        console.print("\n[bold cyan]Hedge Fund Evolution Cycle[/bold cyan]")

        # Oracle diagnosis
        diagnosis = None
        if candles:
            diagnosis = self.diagnose(candles, book=book)
            if diagnosis:
                n_collisions = len(getattr(diagnosis, "collision_insights", []))
                console.print(f"  Oracle: regime=[bold]{diagnosis.regime}[/bold], "
                              f"patterns={len(diagnosis.patterns)}, "
                              f"collisions={n_collisions}, "
                              f"dominant={diagnosis.dominant_theory}")
                if n_collisions:
                    ci = diagnosis.collision_insights[0]
                    console.print(f"  Top collision: {ci.pattern_a} x {ci.pattern_b} "
                                  f"(score={ci.collision_score:.2f})")
                    console.print(f"  Rule: {ci.trading_rule[:100]}")
            else:
                console.print("  Oracle: unavailable, falling back to random evolution")
        else:
            console.print("  Oracle: no candle data, using random evolution")

        # Evaluate
        tiers = self.evaluate_agents()
        console.print(f"  Top: {len(tiers['top'])} | Mid: {len(tiers['mid'])} | Bottom: {len(tiers['bottom'])}")

        if not tiers["bottom"]:
            console.print("  [green]All agents performing well — no evolution needed[/green]")
            return {"evolved": 0, "results": [], "tiers": tiers, "diagnosis": diagnosis.to_dict() if diagnosis else None}

        # Evolve — theory-guided if diagnosis available
        results = self.evolve_bottom(tiers["bottom"], tiers["top"], diagnosis=diagnosis)

        # Report
        table = Table(title="Evolution Results" + (f" (regime: {diagnosis.regime})" if diagnosis else ""))
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
            "diagnosis": diagnosis.to_dict() if diagnosis else None,
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
