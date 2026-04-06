"""Oracle Agents — lightweight rule-based agents that watch markets and act.

No LLM required. Agents are saved configurations that:
1. Watch specific instruments across domains (crypto, equities, forex)
2. Run scans on demand or scheduled intervals
3. Evaluate rules based on regime, patterns, and signals
4. Generate alerts and trading suggestions

Each agent has:
- A role (scanner, trader, researcher, sentinel)
- A watchlist of instruments
- A set of rules (regime triggers, pattern triggers, signal thresholds)
- A log of actions taken
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Agent Roles ───────────────────────────────────────────────────────────

AGENT_ROLES = {
    "scanner": {
        "name": "Scanner",
        "description": "Monitors markets and detects regime changes across instruments",
        "default_rules": [
            {"type": "regime_change", "action": "alert"},
            {"type": "signal_above", "threshold": 0.8, "action": "alert"},
        ],
    },
    "trader": {
        "name": "Trader",
        "description": "Generates buy/sell signals based on pattern + regime analysis",
        "default_rules": [
            {"type": "regime_is", "regime": "trending_up", "action": "signal_buy"},
            {"type": "regime_is", "regime": "trending_down", "action": "signal_sell"},
            {"type": "pattern_detected", "pattern": "momentum", "min_strength": 0.7, "action": "signal_buy"},
        ],
    },
    "researcher": {
        "name": "Researcher",
        "description": "Tracks theory confidence and cross-domain correlations",
        "default_rules": [
            {"type": "theory_shift", "action": "alert"},
            {"type": "cross_domain", "min_score": 0.5, "action": "alert"},
        ],
    },
    "sentinel": {
        "name": "Sentinel",
        "description": "Watches for high-risk conditions and regime volatility spikes",
        "default_rules": [
            {"type": "regime_is", "regime": "volatile", "action": "alert_critical"},
            {"type": "signal_above", "threshold": 0.9, "action": "alert"},
            {"type": "pattern_detected", "pattern": "fat_tails", "min_strength": 0.6, "action": "alert_critical"},
        ],
    },
}


# ── Data Models ───────────────────────────────────────────────────────────

@dataclass
class AgentRule:
    """A rule that triggers an action when conditions are met."""
    type: str           # regime_change, regime_is, pattern_detected, signal_above, cross_domain, theory_shift
    action: str         # alert, alert_critical, signal_buy, signal_sell, log
    regime: str = ""
    pattern: str = ""
    min_strength: float = 0.0
    threshold: float = 0.0
    min_score: float = 0.0

    def to_dict(self) -> dict:
        d = {"type": self.type, "action": self.action}
        if self.regime: d["regime"] = self.regime
        if self.pattern: d["pattern"] = self.pattern
        if self.min_strength: d["min_strength"] = self.min_strength
        if self.threshold: d["threshold"] = self.threshold
        if self.min_score: d["min_score"] = self.min_score
        return d

    @staticmethod
    def from_dict(d: dict) -> "AgentRule":
        return AgentRule(
            type=d.get("type", ""),
            action=d.get("action", "alert"),
            regime=d.get("regime", ""),
            pattern=d.get("pattern", ""),
            min_strength=d.get("min_strength", 0.0),
            threshold=d.get("threshold", 0.0),
            min_score=d.get("min_score", 0.0),
        )


@dataclass
class AgentAction:
    """A logged action taken by an agent."""
    timestamp: float
    agent_id: str
    action_type: str    # alert, alert_critical, signal_buy, signal_sell, scan
    instrument: str
    message: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "instrument": self.instrument,
            "message": self.message,
            "data": self.data,
        }


@dataclass
class OracleAgent:
    """A lightweight oracle agent."""
    id: str
    name: str
    role: str                       # scanner, trader, researcher, sentinel
    status: str = "active"          # active, paused, stopped
    instruments: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=lambda: ["crypto"])
    rules: list[AgentRule] = field(default_factory=list)
    actions: list[AgentAction] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_run: float = 0.0
    total_scans: int = 0
    total_alerts: int = 0
    total_signals: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "role_info": AGENT_ROLES.get(self.role, {}),
            "status": self.status,
            "instruments": self.instruments,
            "domains": self.domains,
            "rules": [r.to_dict() for r in self.rules],
            "actions": [a.to_dict() for a in self.actions[-20:]],  # Last 20
            "created_at": self.created_at,
            "last_run": self.last_run,
            "total_scans": self.total_scans,
            "total_alerts": self.total_alerts,
            "total_signals": self.total_signals,
        }

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "instruments": self.instruments,
            "domains": self.domains,
            "last_run": self.last_run,
            "total_scans": self.total_scans,
            "total_alerts": self.total_alerts,
            "total_signals": self.total_signals,
        }


# ── Agent Manager ─────────────────────────────────────────────────────────

class AgentManager:
    """Manages oracle agents — CRUD + execution."""

    def __init__(self, storage_path: str | Path | None = None):
        if storage_path is None:
            self._path = Path.home() / ".zhihuiti" / "agents.json"
        else:
            self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._agents: dict[str, OracleAgent] = {}
        self._load()

    def _load(self):
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            for ad in data:
                agent = OracleAgent(
                    id=ad["id"],
                    name=ad["name"],
                    role=ad["role"],
                    status=ad.get("status", "active"),
                    instruments=ad.get("instruments", []),
                    domains=ad.get("domains", ["crypto"]),
                    rules=[AgentRule.from_dict(r) for r in ad.get("rules", [])],
                    created_at=ad.get("created_at", time.time()),
                    last_run=ad.get("last_run", 0),
                    total_scans=ad.get("total_scans", 0),
                    total_alerts=ad.get("total_alerts", 0),
                    total_signals=ad.get("total_signals", 0),
                )
                self._agents[agent.id] = agent
        except Exception:
            pass

    def _save(self):
        try:
            data = []
            for agent in self._agents.values():
                d = agent.to_dict()
                d.pop("role_info", None)
                d.pop("actions", None)  # Don't persist actions
                data.append(d)
            with open(self._path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def genesis(self):
        """Seed the default agent team if no agents exist."""
        if self._agents:
            return  # Already have agents

        DEFAULT_TEAM = [
            {
                "name": "Alpha Scanner",
                "role": "scanner",
                "instruments": ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "DOGE_USDT"],
                "domains": ["crypto"],
            },
            {
                "name": "Equity Watch",
                "role": "scanner",
                "instruments": ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL"],
                "domains": ["equities"],
            },
            {
                "name": "Momentum Trader",
                "role": "trader",
                "instruments": ["BTC_USDT", "ETH_USDT", "SOL_USDT"],
                "domains": ["crypto"],
            },
            {
                "name": "Risk Sentinel",
                "role": "sentinel",
                "instruments": [],  # Watches everything
                "domains": ["crypto", "equities"],
            },
            {
                "name": "Theory Researcher",
                "role": "researcher",
                "instruments": ["BTC_USDT", "ETH_USDT", "AAPL", "NVDA"],
                "domains": ["crypto", "equities"],
            },
        ]

        for spec in DEFAULT_TEAM:
            self.create(
                name=spec["name"],
                role=spec["role"],
                instruments=spec["instruments"],
                domains=spec["domains"],
            )

        return len(DEFAULT_TEAM)

    def create(self, name: str, role: str, instruments: list[str] | None = None,
               domains: list[str] | None = None, rules: list[dict] | None = None) -> OracleAgent:
        """Create a new oracle agent."""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        role_info = AGENT_ROLES.get(role, AGENT_ROLES["scanner"])

        # Use provided rules or defaults for the role
        if rules:
            agent_rules = [AgentRule.from_dict(r) for r in rules]
        else:
            agent_rules = [AgentRule.from_dict(r) for r in role_info.get("default_rules", [])]

        agent = OracleAgent(
            id=agent_id,
            name=name,
            role=role,
            instruments=instruments or [],
            domains=domains or ["crypto"],
            rules=agent_rules,
        )

        with self._lock:
            self._agents[agent_id] = agent
            self._save()

        return agent

    def get(self, agent_id: str) -> OracleAgent | None:
        return self._agents.get(agent_id)

    def list_all(self) -> list[dict]:
        return [a.to_summary() for a in self._agents.values()]

    def delete(self, agent_id: str) -> bool:
        with self._lock:
            removed = self._agents.pop(agent_id, None)
            if removed:
                self._save()
            return removed is not None

    def update_status(self, agent_id: str, status: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        with self._lock:
            agent.status = status
            self._save()
        return True

    def run_agent(self, agent_id: str, scan_results: list[dict],
                  prev_regimes: dict[str, str] | None = None) -> list[AgentAction]:
        """Execute an agent's rules against scan results.

        Returns list of triggered actions.
        """
        agent = self._agents.get(agent_id)
        if not agent or agent.status != "active":
            return []

        if prev_regimes is None:
            prev_regimes = {}

        actions: list[AgentAction] = []
        now = time.time()

        # Filter scan results to agent's instruments (or all if empty)
        relevant = scan_results
        if agent.instruments:
            inst_set = set(agent.instruments)
            relevant = [r for r in scan_results if r.get("instrument", "") in inst_set]

        for r in relevant:
            inst = r.get("instrument", "")
            regime = r.get("regime", "quiet")
            signal = r.get("signal_score", 0)
            top_pattern = r.get("top_pattern", "")
            pattern_strength = r.get("top_pattern_strength", 0)
            prev_regime = prev_regimes.get(inst, "")

            for rule in agent.rules:
                triggered = False
                message = ""

                if rule.type == "regime_change" and prev_regime and prev_regime != regime:
                    triggered = True
                    message = f"{inst}: regime changed {prev_regime} → {regime}"

                elif rule.type == "regime_is" and regime == rule.regime:
                    triggered = True
                    message = f"{inst}: in {regime} regime"

                elif rule.type == "signal_above" and signal >= rule.threshold:
                    triggered = True
                    message = f"{inst}: signal {signal:.0%} exceeds {rule.threshold:.0%}"

                elif rule.type == "pattern_detected" and top_pattern == rule.pattern and pattern_strength >= rule.min_strength:
                    triggered = True
                    message = f"{inst}: {rule.pattern} at {pattern_strength:.0%}"

                if triggered:
                    action = AgentAction(
                        timestamp=now,
                        agent_id=agent_id,
                        action_type=rule.action,
                        instrument=inst,
                        message=message,
                        data={"regime": regime, "signal": signal, "pattern": top_pattern},
                    )
                    actions.append(action)

        # Update agent stats
        with self._lock:
            agent.last_run = now
            agent.total_scans += 1
            agent.total_alerts += sum(1 for a in actions if "alert" in a.action_type)
            agent.total_signals += sum(1 for a in actions if "signal" in a.action_type)
            agent.actions.extend(actions)
            # Keep last 100 actions
            if len(agent.actions) > 100:
                agent.actions = agent.actions[-100:]
            self._save()

        return actions

    def run_all(self, scan_results: list[dict],
                prev_regimes: dict[str, str] | None = None) -> dict[str, list[dict]]:
        """Run all active agents and return their actions."""
        results = {}
        for agent_id, agent in self._agents.items():
            if agent.status == "active":
                actions = self.run_agent(agent_id, scan_results, prev_regimes)
                if actions:
                    results[agent_id] = [a.to_dict() for a in actions]
        return results
