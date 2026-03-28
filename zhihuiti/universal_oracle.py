"""Universal Oracle — domain-agnostic time series pattern detection mapped to theories.

The same mathematical structures (mean reversion, momentum, volatility clustering,
fat tails, etc.) appear across all domains: server latency, social cascades, revenue
growth, scientific measurements. This module detects them and maps each to the most
relevant theories from the 378-theory knowledge graph.

Domain profiles provide context-aware theory mapping and interpretation:
- crypto/finance: EMH, Black-Scholes, Heston, etc.
- system_perf: queueing theory, control theory, stability
- social: SIR/epidemic models, Ising, network science
- business: population dynamics, game theory, optimization
- scientific: dynamic systems, statistical mechanics, information theory

Usage:
    from zhihuiti.universal_oracle import diagnose, DOMAINS
    diagnosis = diagnose(values, domain="system_perf", label="API latency (ms)")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zhihuiti.crypto_oracle import (
    CollisionInsight,
    DetectedPattern,
    MarketDiagnosis,
    _returns,
    _sma,
    classify_regime,
    detect_fat_tails,
    detect_mean_reversion,
    detect_momentum,
    detect_volatility_clustering,
    synthesize_collisions,
)


# ── Domain profiles ────────────────────────────────────────────────────────

@dataclass
class DomainProfile:
    """Maps a domain to its most relevant theories and interpretations."""
    name: str
    description: str
    # Maps pattern name → list of theory_ids for this domain
    pattern_theories: dict[str, list[str]]
    # Maps regime → theory_id for this domain
    regime_theories: dict[str, str]
    # Maps regime → human-readable interpretation
    regime_interpretations: dict[str, str]
    # Maps pattern name → human-readable interpretation template
    pattern_interpretations: dict[str, str]


DOMAINS: dict[str, DomainProfile] = {
    "crypto": DomainProfile(
        name="Crypto / Finance",
        description="Cryptocurrency and financial market analysis",
        pattern_theories={
            "momentum": ["efficient_market_hypothesis", "capm"],
            "mean_reversion": ["mean_reversion", "arbitrage_pricing_theory"],
            "volatility_clustering": ["heston_stochastic_volatility", "boltzmann_distribution"],
            "fat_tails": ["heston_stochastic_volatility", "boltzmann_distribution"],
            "support_resistance": ["mean_reversion", "black_scholes"],
            "orderbook_imbalance": ["market_microstructure"],
        },
        regime_theories={
            "trending_up": "efficient_market_hypothesis",
            "trending_down": "efficient_market_hypothesis",
            "mean_reverting": "mean_reversion",
            "volatile": "heston_stochastic_volatility",
            "quiet": "markowitz_portfolio",
        },
        regime_interpretations={
            "trending_up": "Bullish trend — prices absorbing positive information",
            "trending_down": "Bearish trend — prices absorbing negative information",
            "mean_reverting": "Range-bound — prices oscillating around equilibrium",
            "volatile": "High volatility regime — stochastic variance dominating",
            "quiet": "Low volatility — efficient portfolio dynamics",
        },
        pattern_interpretations={
            "momentum": "Price trend with directional persistence",
            "mean_reversion": "Ornstein-Uhlenbeck process pulling toward mean",
            "volatility_clustering": "GARCH-like autocorrelation in volatility",
            "fat_tails": "Non-Gaussian return distribution with tail risk",
        },
    ),

    "system_perf": DomainProfile(
        name="System Performance",
        description="Server latency, error rates, throughput, resource utilization",
        pattern_theories={
            "momentum": ["pid_control", "lyapunov_stability_ct"],
            "mean_reversion": ["pid_control", "mean_reversion"],
            "volatility_clustering": ["hopf_bifurcation", "ising_model"],
            "fat_tails": ["self_organized_criticality", "network_robustness"],
        },
        regime_theories={
            "trending_up": "lyapunov_stability_ct",
            "trending_down": "pid_control",
            "mean_reverting": "pid_control",
            "volatile": "hopf_bifurcation",
            "quiet": "lyapunov_stability_ct",
        },
        regime_interpretations={
            "trending_up": "Degrading — metric drifting away from target (check capacity)",
            "trending_down": "Recovering — metric returning toward healthy baseline",
            "mean_reverting": "Stable — metric oscillating within normal bounds (PID-like)",
            "volatile": "Unstable — approaching bifurcation point (investigate root cause)",
            "quiet": "Healthy — system in stable equilibrium",
        },
        pattern_interpretations={
            "momentum": "Sustained drift away from baseline — possible capacity issue or leak",
            "mean_reversion": "Self-correcting behavior — system has effective feedback loops",
            "volatility_clustering": "Bursts of instability — may indicate approaching a phase transition",
            "fat_tails": "Rare extreme events — system has heavy-tailed failure modes",
        },
    ),

    "social": DomainProfile(
        name="Social Dynamics",
        description="Information cascades, network effects, opinion dynamics, virality",
        pattern_theories={
            "momentum": ["influence_maximization", "network_epidemic"],
            "mean_reversion": ["evolutionary_stability", "ising_model"],
            "volatility_clustering": ["self_organized_criticality", "hopf_bifurcation"],
            "fat_tails": ["preferential_attachment", "self_organized_criticality"],
        },
        regime_theories={
            "trending_up": "network_epidemic",
            "trending_down": "epidemic_seir",
            "mean_reverting": "ising_model",
            "volatile": "self_organized_criticality",
            "quiet": "evolutionary_stability",
        },
        regime_interpretations={
            "trending_up": "Viral growth — cascade spreading through network (SIR supercritical)",
            "trending_down": "Decay phase — cascade exhausting susceptible population",
            "mean_reverting": "Polarization equilibrium — opinions oscillating (Ising near critical temp)",
            "volatile": "Critical state — small events trigger large avalanches (SOC)",
            "quiet": "Stable consensus — system at evolutionary stable strategy",
        },
        pattern_interpretations={
            "momentum": "Information cascade propagating — network amplification in effect",
            "mean_reversion": "Opinion correction — social pressure pulling back toward consensus",
            "volatility_clustering": "Burst-silence dynamics — hallmark of self-organized criticality",
            "fat_tails": "Power-law event sizes — preferential attachment producing scale-free dynamics",
        },
    ),

    "business": DomainProfile(
        name="Business Metrics",
        description="Revenue, churn, conversion, growth, engagement",
        pattern_theories={
            "momentum": ["replicator_dynamics", "logistic_growth"],
            "mean_reversion": ["mean_reversion", "nash_equilibrium_econ"],
            "volatility_clustering": ["hopf_bifurcation", "lotka_volterra"],
            "fat_tails": ["preferential_attachment", "wright_fisher"],
        },
        regime_theories={
            "trending_up": "logistic_growth",
            "trending_down": "lotka_volterra",
            "mean_reverting": "nash_equilibrium_econ",
            "volatile": "hopf_bifurcation",
            "quiet": "evolutionary_stability",
        },
        regime_interpretations={
            "trending_up": "Growth phase — logistic curve ascending (check for saturation ceiling)",
            "trending_down": "Contraction — competitive dynamics or market saturation",
            "mean_reverting": "Mature market — metric oscillating around Nash equilibrium",
            "volatile": "Market disruption — unstable dynamics, possible bifurcation",
            "quiet": "Steady state — stable competitive equilibrium",
        },
        pattern_interpretations={
            "momentum": "Sustained growth/decline — replicator dynamics favoring current trajectory",
            "mean_reversion": "Market correction — competitive forces pulling back to equilibrium",
            "volatility_clustering": "Demand shocks — clustered periods of high/low activity",
            "fat_tails": "Black swan risk — extreme events more likely than Gaussian model predicts",
        },
    ),

    "scientific": DomainProfile(
        name="Scientific Data",
        description="Any measured time series: sensor data, experimental results, natural phenomena",
        pattern_theories={
            "momentum": ["lyapunov_stability_ds", "gradient_descent"],
            "mean_reversion": ["mean_reversion", "langevin_dynamics"],
            "volatility_clustering": ["ising_model", "renormalization_group_mf"],
            "fat_tails": ["self_organized_criticality", "boltzmann_distribution"],
        },
        regime_theories={
            "trending_up": "lyapunov_stability_ds",
            "trending_down": "gradient_descent",
            "mean_reverting": "langevin_dynamics",
            "volatile": "ising_model",
            "quiet": "boltzmann_distribution",
        },
        regime_interpretations={
            "trending_up": "Diverging from equilibrium — system gaining energy / moving along gradient",
            "trending_down": "Relaxation — system descending energy landscape toward minimum",
            "mean_reverting": "Langevin dynamics — thermal fluctuations around equilibrium",
            "volatile": "Near phase transition — critical fluctuations (check order parameter)",
            "quiet": "Thermal equilibrium — Boltzmann-distributed fluctuations",
        },
        pattern_interpretations={
            "momentum": "Systematic drift — possible uncontrolled variable or gradient flow",
            "mean_reversion": "Restoring force present — stochastic process around stable fixed point",
            "volatility_clustering": "Intermittency — may indicate proximity to critical point",
            "fat_tails": "Heavy-tailed fluctuations — system may be at or near criticality",
        },
    ),
}


# ── Universal diagnosis ────────────────────────────────────────────────────

@dataclass
class UniversalDiagnosis:
    """Domain-aware diagnosis of a time series."""
    label: str
    domain: str
    domain_name: str
    current_value: float
    change_pct: float
    regime: str
    regime_interpretation: str
    dominant_theory: str
    patterns: list[dict]
    collision_insights: list[dict]
    theory_details: list[dict]

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "domain": self.domain,
            "domain_name": self.domain_name,
            "current_value": self.current_value,
            "change_pct": round(self.change_pct, 4),
            "regime": self.regime,
            "regime_interpretation": self.regime_interpretation,
            "dominant_theory": self.dominant_theory,
            "patterns": self.patterns,
            "collision_insights": self.collision_insights,
            "theory_details": self.theory_details,
        }


def diagnose(
    values: list[float],
    domain: str = "scientific",
    label: str = "time series",
) -> UniversalDiagnosis:
    """Run structural pattern detection on any time series, mapped to domain-specific theories.

    Args:
        values: Ordered numeric values (oldest first).
        domain: One of "crypto", "system_perf", "social", "business", "scientific".
        label: Human-readable label for the metric (e.g., "API latency (ms)").

    Returns:
        UniversalDiagnosis with patterns, regime, collision insights, and theory details.
    """
    profile = DOMAINS.get(domain, DOMAINS["scientific"])

    if not values:
        return UniversalDiagnosis(
            label=label, domain=domain, domain_name=profile.name,
            current_value=0, change_pct=0,
            regime="quiet", regime_interpretation=profile.regime_interpretations.get("quiet", ""),
            dominant_theory="", patterns=[], collision_insights=[], theory_details=[],
        )

    current = values[-1]
    change_pct = (values[-1] / values[0] - 1) if values[0] != 0 else 0

    # Run domain-agnostic pattern detectors
    raw_patterns: list[DetectedPattern] = []
    for detector in [detect_momentum, detect_mean_reversion, detect_volatility_clustering, detect_fat_tails]:
        result = detector(values)
        if result:
            # Remap theory_ids to domain-specific ones
            domain_theories = profile.pattern_theories.get(result.name, result.theory_ids)
            result.theory_ids = domain_theories
            # Add domain-specific interpretation
            domain_interp = profile.pattern_interpretations.get(result.name, "")
            if domain_interp:
                result.description = f"{domain_interp}. {result.description}"
            raw_patterns.append(result)

    raw_patterns.sort(key=lambda p: -p.strength)

    # Classify regime
    regime = classify_regime(values)
    dominant_theory = profile.regime_theories.get(regime, "")
    regime_interpretation = profile.regime_interpretations.get(regime, "")

    # Collision synthesis
    collision_insights = synthesize_collisions(raw_patterns)

    # Get theory details
    theory_details = _get_domain_theory_details(raw_patterns, dominant_theory)

    # Build pattern dicts with domain context
    pattern_dicts = [
        {
            "name": p.name,
            "strength": round(p.strength, 3),
            "description": p.description,
            "metrics": {k: round(v, 6) for k, v in p.metrics.items()},
            "theory_ids": p.theory_ids,
        }
        for p in raw_patterns
    ]

    return UniversalDiagnosis(
        label=label,
        domain=domain,
        domain_name=profile.name,
        current_value=current,
        change_pct=change_pct,
        regime=regime,
        regime_interpretation=regime_interpretation,
        dominant_theory=dominant_theory,
        patterns=pattern_dicts,
        collision_insights=[ci.to_dict() for ci in collision_insights],
        theory_details=theory_details,
    )


def _get_domain_theory_details(patterns: list[DetectedPattern], dominant_theory: str) -> list[dict]:
    """Pull theory details from the knowledge graph."""
    try:
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
    except Exception:
        return []

    seen: set[str] = set()
    details: list[dict] = []

    all_ids = [dominant_theory] if dominant_theory else []
    for p in patterns:
        all_ids.extend(p.theory_ids)

    for tid in all_ids:
        if not tid or tid in seen:
            continue
        seen.add(tid)

        theory = graph.get_theory(tid)
        if not theory:
            continue

        analogies = graph.find_analogies(tid, min_score=0.5, limit=3)

        details.append({
            "id": tid,
            "name": theory.get("name", tid),
            "domain": theory.get("domain", ""),
            "equation": theory.get("equation", ""),
            "key_patterns": theory.get("patterns", [])[:5],
            "structure": theory.get("structure", ""),
            "cross_domain_analogies": [
                {
                    "theory": a["theory_name"],
                    "domain": a["theory_domain"],
                    "score": a["score"],
                    "interpretation": a["interpretation"],
                }
                for a in analogies
            ],
        })

    return details
