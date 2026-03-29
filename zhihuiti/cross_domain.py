"""Cross-domain correlation engine — finds structural bridges between different domains.

When patterns fire across domains simultaneously (e.g., crypto trending down while
social sentiment mean-reverting), this engine finds the theoretical bridges between
them using the collision knowledge graph.

Also provides regime alerts when transitions are detected.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainSnapshot:
    """A regime snapshot for one domain."""
    domain: str
    label: str  # e.g. "BTC_USDT", "AAPL", "API latency"
    regime: str
    top_pattern: str
    top_pattern_strength: float
    pattern_count: int
    signal_score: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class CrossDomainCorrelation:
    """A detected correlation between two domains."""
    domain_a: str
    label_a: str
    regime_a: str
    pattern_a: str
    domain_b: str
    label_b: str
    regime_b: str
    pattern_b: str
    bridge_theories: list[str]
    correlation_type: str  # "convergent", "divergent", "resonant"
    interpretation: str
    score: float

    def to_dict(self) -> dict:
        return {
            "domain_a": self.domain_a,
            "label_a": self.label_a,
            "regime_a": self.regime_a,
            "pattern_a": self.pattern_a,
            "domain_b": self.domain_b,
            "label_b": self.label_b,
            "regime_b": self.regime_b,
            "pattern_b": self.pattern_b,
            "bridge_theories": self.bridge_theories,
            "correlation_type": self.correlation_type,
            "interpretation": self.interpretation,
            "score": round(self.score, 3),
        }


@dataclass
class Alert:
    """A regime transition alert."""
    id: str
    timestamp: float
    domain: str
    label: str
    alert_type: str  # "regime_change", "high_volatility", "pattern_spike", "cross_domain"
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "label": self.label,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "data": self.data,
        }


# ── Correlation type detection ────────────────────────────────────────────

_CORRELATION_RULES: dict[tuple[str, str], tuple[str, str]] = {
    # (regime_a, regime_b) → (type, interpretation_template)
    ("trending_up", "trending_up"): ("convergent", "Both {a} and {b} are trending up — synchronized bullish momentum"),
    ("trending_down", "trending_down"): ("convergent", "Both {a} and {b} are trending down — synchronized bearish pressure"),
    ("trending_up", "trending_down"): ("divergent", "{a} rising while {b} falling — potential rotation or decoupling"),
    ("trending_down", "trending_up"): ("divergent", "{a} falling while {b} rising — potential rotation or decoupling"),
    ("volatile", "volatile"): ("resonant", "Both {a} and {b} in volatile regime — systemic uncertainty spreading"),
    ("mean_reverting", "trending_up"): ("divergent", "{a} mean-reverting while {b} trends up — potential catch-up opportunity"),
    ("mean_reverting", "trending_down"): ("divergent", "{a} mean-reverting while {b} trends down — divergence may resolve"),
    ("volatile", "quiet"): ("divergent", "{a} volatile while {b} quiet — stress is domain-specific, not systemic"),
    ("quiet", "volatile"): ("divergent", "{a} quiet while {b} volatile — stress is domain-specific, not systemic"),
}


def find_cross_domain_correlations(
    snapshots: list[DomainSnapshot],
) -> list[CrossDomainCorrelation]:
    """Find structural correlations between domain snapshots.

    Compares each pair of snapshots from different domains and looks for
    theoretical bridges between their active patterns.
    """
    from zhihuiti.theory_intelligence import get_graph

    graph = get_graph()
    correlations = []

    for i, a in enumerate(snapshots):
        for b in snapshots[i + 1:]:
            if a.domain == b.domain and a.label == b.label:
                continue

            # Determine correlation type
            key = (a.regime, b.regime)
            if key in _CORRELATION_RULES:
                corr_type, interp_template = _CORRELATION_RULES[key]
            else:
                corr_type = "neutral"
                interp_template = "{a} ({ra}) and {b} ({rb}) show no strong directional link"

            interpretation = interp_template.format(
                a=f"{a.domain}:{a.label}", b=f"{b.domain}:{b.label}",
                ra=a.regime, rb=b.regime,
            )

            # Find bridge theories between the two patterns
            bridges = _find_bridges(a.top_pattern, b.top_pattern, graph)

            score = _compute_correlation_score(a, b, bridges, corr_type)

            if score > 0.2:  # Only report meaningful correlations
                correlations.append(CrossDomainCorrelation(
                    domain_a=a.domain,
                    label_a=a.label,
                    regime_a=a.regime,
                    pattern_a=a.top_pattern,
                    domain_b=b.domain,
                    label_b=b.label,
                    regime_b=b.regime,
                    pattern_b=b.top_pattern,
                    bridge_theories=bridges,
                    correlation_type=corr_type,
                    interpretation=interpretation,
                    score=score,
                ))

    correlations.sort(key=lambda c: -c.score)
    return correlations


def _find_bridges(pattern_a: str, pattern_b: str, graph) -> list[str]:
    """Find theories that bridge two patterns via the collision graph."""
    # Map patterns to likely theory names
    pattern_theory_map = {
        "momentum": ["efficient_market_hypothesis", "capm"],
        "mean_reversion": ["mean_reversion", "ornstein_uhlenbeck"],
        "volatility_clustering": ["heston_stochastic_volatility", "arch_garch"],
        "fat_tails": ["boltzmann_distribution", "power_law"],
        "support_resistance": ["mean_reversion", "black_scholes"],
        "orderbook_imbalance": ["market_microstructure", "kyle_lambda"],
    }

    theories_a = set(pattern_theory_map.get(pattern_a, []))
    theories_b = set(pattern_theory_map.get(pattern_b, []))

    bridges = set()
    for ta in theories_a:
        collisions_a = set(graph.get_collisions(ta))
        for tb in theories_b:
            collisions_b = set(graph.get_collisions(tb))
            # Shared collision partners = bridge theories
            shared = collisions_a & collisions_b
            bridges.update(shared)

    return list(bridges)[:5]  # Top 5 bridges


def _compute_correlation_score(a: DomainSnapshot, b: DomainSnapshot,
                                bridges: list[str], corr_type: str) -> float:
    """Score how meaningful a cross-domain correlation is."""
    # Base: average signal strength
    base = (a.signal_score + b.signal_score) / 2

    # Bridge bonus: more theoretical connections = stronger correlation
    bridge_bonus = min(0.3, len(bridges) * 0.1)

    # Type bonus: convergent/divergent are more actionable than neutral
    type_bonus = {"convergent": 0.15, "divergent": 0.1, "resonant": 0.2, "neutral": 0.0}
    tb = type_bonus.get(corr_type, 0.0)

    return min(1.0, base * 0.6 + bridge_bonus + tb)


# ── Alert generation ──────────────────────────────────────────────────────

_alert_counter = 0


def _next_alert_id() -> str:
    global _alert_counter
    _alert_counter += 1
    return f"alert_{int(time.time())}_{_alert_counter}"


def generate_alerts(
    current_snapshots: list[DomainSnapshot],
    previous_snapshots: list[DomainSnapshot] | None = None,
    correlations: list[CrossDomainCorrelation] | None = None,
) -> list[Alert]:
    """Generate alerts from current state and transitions.

    Alert types:
    - regime_change: regime transitioned from previous scan
    - high_volatility: volatile regime detected
    - pattern_spike: unusually strong pattern (>0.8)
    - cross_domain: significant cross-domain correlation found
    """
    alerts = []
    now = time.time()

    # Build lookup of previous snapshots
    prev_map: dict[str, DomainSnapshot] = {}
    if previous_snapshots:
        for s in previous_snapshots:
            prev_map[f"{s.domain}:{s.label}"] = s

    for snap in current_snapshots:
        key = f"{snap.domain}:{snap.label}"

        # Regime change alerts
        prev = prev_map.get(key)
        if prev and prev.regime != snap.regime:
            severity = "critical" if snap.regime == "volatile" else "warning"
            alerts.append(Alert(
                id=_next_alert_id(),
                timestamp=now,
                domain=snap.domain,
                label=snap.label,
                alert_type="regime_change",
                severity=severity,
                title=f"Regime shift: {prev.regime} → {snap.regime}",
                message=f"{snap.label} ({snap.domain}) transitioned from {prev.regime} to {snap.regime}",
                data={"from": prev.regime, "to": snap.regime, "price": snap.signal_score},
            ))

        # High volatility alerts
        if snap.regime == "volatile" and snap.signal_score > 0.6:
            alerts.append(Alert(
                id=_next_alert_id(),
                timestamp=now,
                domain=snap.domain,
                label=snap.label,
                alert_type="high_volatility",
                severity="warning",
                title=f"High volatility: {snap.label}",
                message=f"{snap.label} ({snap.domain}) is in volatile regime with signal score {snap.signal_score:.0%}",
                data={"regime": snap.regime, "signal_score": snap.signal_score},
            ))

        # Pattern spike alerts
        if snap.top_pattern_strength > 0.8:
            alerts.append(Alert(
                id=_next_alert_id(),
                timestamp=now,
                domain=snap.domain,
                label=snap.label,
                alert_type="pattern_spike",
                severity="info",
                title=f"Strong {snap.top_pattern}: {snap.label}",
                message=f"{snap.top_pattern} detected at {snap.top_pattern_strength:.0%} in {snap.label}",
                data={"pattern": snap.top_pattern, "strength": snap.top_pattern_strength},
            ))

    # Cross-domain alerts
    if correlations:
        for corr in correlations[:5]:  # Top 5
            if corr.score > 0.5:
                alerts.append(Alert(
                    id=_next_alert_id(),
                    timestamp=now,
                    domain="cross_domain",
                    label=f"{corr.label_a} ↔ {corr.label_b}",
                    alert_type="cross_domain",
                    severity="warning" if corr.correlation_type == "resonant" else "info",
                    title=f"Cross-domain: {corr.domain_a} ↔ {corr.domain_b}",
                    message=corr.interpretation,
                    data=corr.to_dict(),
                ))

    alerts.sort(key=lambda a: {"critical": 0, "warning": 1, "info": 2}[a.severity])
    return alerts
