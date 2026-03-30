"""Regime Prediction Engine — forecast next likely regime based on historical patterns.

Uses transition probability matrices (Markov chain) built from regime history
to predict what regime is most likely next. Combines with pattern momentum
and theory-informed priors for more accurate forecasts.

Also provides: portfolio risk analysis, theory confidence scoring,
time series comparison, and watchlist management.
"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any


REGIMES = ["trending_up", "trending_down", "mean_reverting", "volatile", "quiet"]


# ── Regime Prediction ─────────────────────────────────────────────────────

@dataclass
class RegimePrediction:
    """Predicted next regime with probabilities."""
    instrument: str
    current_regime: str
    predicted_regime: str
    confidence: float  # 0.0-1.0
    probabilities: dict[str, float]  # regime -> probability
    reasoning: str
    theory_support: list[str]  # theories supporting the prediction

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "current_regime": self.current_regime,
            "predicted_regime": self.predicted_regime,
            "confidence": round(self.confidence, 3),
            "probabilities": {k: round(v, 3) for k, v in self.probabilities.items()},
            "reasoning": self.reasoning,
            "theory_support": self.theory_support,
        }


def build_transition_matrix(history: list[dict]) -> dict[str, dict[str, float]]:
    """Build a Markov transition matrix from regime history snapshots.

    Returns: {from_regime: {to_regime: probability}}
    """
    counts: dict[str, dict[str, int]] = {r: {r2: 0 for r2 in REGIMES} for r in REGIMES}

    for i in range(1, len(history)):
        prev = history[i - 1].get("regime", "quiet")
        curr = history[i].get("regime", "quiet")
        if prev in counts and curr in counts[prev]:
            counts[prev][curr] += 1

    # Normalize to probabilities
    matrix: dict[str, dict[str, float]] = {}
    for from_r, to_counts in counts.items():
        total = sum(to_counts.values())
        if total > 0:
            matrix[from_r] = {to_r: c / total for to_r, c in to_counts.items()}
        else:
            # Uniform prior if no data
            matrix[from_r] = {to_r: 1.0 / len(REGIMES) for to_r in REGIMES}

    return matrix


def predict_regime(
    instrument: str,
    history: list[dict],
    current_regime: str,
    patterns: list[dict] | None = None,
) -> RegimePrediction:
    """Predict the next most likely regime for an instrument.

    Uses:
    1. Transition matrix from history (Markov chain)
    2. Pattern-informed adjustments (momentum → trending, vol clustering → volatile)
    3. Theory-based reasoning
    """
    matrix = build_transition_matrix(history)

    # Base probabilities from Markov chain
    probs = dict(matrix.get(current_regime, {r: 1.0 / len(REGIMES) for r in REGIMES}))

    # Pattern-informed adjustments
    theory_support = []
    if patterns:
        for p in patterns:
            name = p.get("name", "")
            strength = p.get("strength", 0)

            if name == "momentum" and strength > 0.6:
                # Strong momentum → likely to continue trending
                if current_regime == "trending_up":
                    probs["trending_up"] = probs.get("trending_up", 0) * 1.3
                    theory_support.append("EMH: momentum persistence")
                elif current_regime == "trending_down":
                    probs["trending_down"] = probs.get("trending_down", 0) * 1.3
                    theory_support.append("EMH: momentum persistence")
                else:
                    probs["trending_up"] = probs.get("trending_up", 0) * 1.15
                    probs["trending_down"] = probs.get("trending_down", 0) * 1.15

            elif name == "mean_reversion" and strength > 0.6:
                probs["mean_reverting"] = probs.get("mean_reverting", 0) * 1.3
                probs["quiet"] = probs.get("quiet", 0) * 1.1
                theory_support.append("O-U process: reversion to mean")

            elif name == "volatility_clustering" and strength > 0.6:
                probs["volatile"] = probs.get("volatile", 0) * 1.4
                theory_support.append("GARCH: volatility persistence")

            elif name == "fat_tails" and strength > 0.7:
                probs["volatile"] = probs.get("volatile", 0) * 1.2
                theory_support.append("Heavy tails: extreme moves likely")

    # Normalize
    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}

    # Pick winner
    predicted = max(probs, key=lambda k: probs[k])
    confidence = probs[predicted]

    # Build reasoning
    if len(history) < 5:
        reasoning = f"Limited history ({len(history)} snapshots). Prediction based on pattern analysis."
    elif predicted == current_regime:
        reasoning = f"Current {current_regime} regime likely to persist (p={confidence:.0%}). "
        if theory_support:
            reasoning += f"Supported by: {', '.join(theory_support[:2])}."
    else:
        reasoning = f"Regime shift from {current_regime} to {predicted} predicted (p={confidence:.0%}). "
        if theory_support:
            reasoning += f"Key drivers: {', '.join(theory_support[:2])}."

    return RegimePrediction(
        instrument=instrument,
        current_regime=current_regime,
        predicted_regime=predicted,
        confidence=confidence,
        probabilities=probs,
        reasoning=reasoning,
        theory_support=theory_support,
    )


# ── Portfolio Risk Analysis ───────────────────────────────────────────────

@dataclass
class PortfolioRisk:
    """Risk analysis for a portfolio of instruments."""
    instruments: list[str]
    regime_distribution: dict[str, int]
    dominant_regime: str
    risk_score: float  # 0.0-1.0 (higher = more risky)
    diversification_score: float  # 0.0-1.0 (higher = more diversified regimes)
    concentrated_risk: list[str]  # instruments sharing same regime
    hedging_opportunities: list[str]
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "instruments": self.instruments,
            "regime_distribution": self.regime_distribution,
            "dominant_regime": self.dominant_regime,
            "risk_score": round(self.risk_score, 3),
            "diversification_score": round(self.diversification_score, 3),
            "concentrated_risk": self.concentrated_risk,
            "hedging_opportunities": self.hedging_opportunities,
            "interpretation": self.interpretation,
        }


def analyze_portfolio_risk(scan_results: list[dict]) -> PortfolioRisk:
    """Analyze risk across a portfolio of scanned instruments.

    Looks at regime concentration, correlation patterns, and suggests hedges.
    """
    if not scan_results:
        return PortfolioRisk(
            instruments=[], regime_distribution={}, dominant_regime="unknown",
            risk_score=0, diversification_score=0, concentrated_risk=[],
            hedging_opportunities=[], interpretation="No instruments to analyze.",
        )

    instruments = [r.get("instrument", "") for r in scan_results]
    regimes = [r.get("regime", "quiet") for r in scan_results]

    # Regime distribution
    dist: dict[str, int] = {}
    for reg in regimes:
        dist[reg] = dist.get(reg, 0) + 1

    dominant = max(dist, key=lambda k: dist[k])
    dominant_pct = dist[dominant] / len(regimes)

    # Risk score: high if concentrated in risky regimes
    risk_weights = {"volatile": 1.0, "trending_down": 0.7, "trending_up": 0.3, "mean_reverting": 0.2, "quiet": 0.1}
    risk_score = sum(risk_weights.get(r, 0.5) for r in regimes) / len(regimes)

    # Diversification: entropy of regime distribution
    n = len(regimes)
    entropy = 0
    for count in dist.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)
    max_entropy = math.log2(len(REGIMES)) if len(REGIMES) > 1 else 1
    diversification = entropy / max_entropy if max_entropy > 0 else 0

    # Concentrated risk: instruments in dominant regime
    concentrated = [r.get("instrument", "") for r in scan_results if r.get("regime") == dominant]

    # Hedging opportunities
    hedges = []
    if dominant in ("trending_down", "volatile"):
        quiet_instruments = [r.get("instrument", "") for r in scan_results if r.get("regime") in ("quiet", "mean_reverting")]
        if quiet_instruments:
            hedges.append(f"Increase allocation to stable instruments: {', '.join(quiet_instruments[:3])}")
        hedges.append("Consider reducing exposure to trending-down positions")
    if dominant_pct > 0.7:
        hedges.append(f"Portfolio highly concentrated in {dominant} regime ({dominant_pct:.0%}) — diversify across regimes")

    # Interpretation
    if risk_score > 0.7:
        interp = f"HIGH RISK: {dominant_pct:.0%} of portfolio in {dominant} regime. Consider de-risking."
    elif risk_score > 0.4:
        interp = f"MODERATE RISK: Mixed regimes with {dominant} dominant. Monitor for regime shifts."
    else:
        interp = f"LOW RISK: Portfolio is in stable regimes. Good time to build positions gradually."

    return PortfolioRisk(
        instruments=instruments,
        regime_distribution=dist,
        dominant_regime=dominant,
        risk_score=risk_score,
        diversification_score=diversification,
        concentrated_risk=concentrated,
        hedging_opportunities=hedges,
        interpretation=interp,
    )


# ── Theory Confidence Scoring ─────────────────────────────────────────────

@dataclass
class TheoryConfidence:
    """How well a theory explains the current market."""
    theory_id: str
    theory_name: str
    domain: str
    confidence: float  # 0.0-1.0
    supporting_patterns: list[str]
    supporting_instruments: list[str]
    explanation: str

    def to_dict(self) -> dict:
        return {
            "theory_id": self.theory_id,
            "theory_name": self.theory_name,
            "domain": self.domain,
            "confidence": round(self.confidence, 3),
            "supporting_patterns": self.supporting_patterns,
            "supporting_instruments": self.supporting_instruments,
            "explanation": self.explanation,
        }


def score_theory_confidence(scan_results: list[dict]) -> list[TheoryConfidence]:
    """Rank which theories best explain the current market state.

    Looks at which theories are referenced most across all detected patterns
    and instruments, weighted by pattern strength.
    """
    # Aggregate theory mentions with weights
    theory_scores: dict[str, float] = {}
    theory_patterns: dict[str, set] = {}
    theory_instruments: dict[str, set] = {}

    for r in scan_results:
        inst = r.get("instrument", "")
        # The scan result has top_pattern but we need to check theory mappings
        regime = r.get("regime", "quiet")
        dominant_theory = r.get("dominant_theory", "")
        signal = r.get("signal_score", 0.5)

        if dominant_theory:
            theory_scores[dominant_theory] = theory_scores.get(dominant_theory, 0) + signal
            theory_patterns.setdefault(dominant_theory, set()).add(r.get("top_pattern", ""))
            theory_instruments.setdefault(dominant_theory, set()).add(inst)

    # Build results
    results = []
    max_score = max(theory_scores.values()) if theory_scores else 1

    for theory_id, score in sorted(theory_scores.items(), key=lambda x: -x[1]):
        confidence = min(1.0, score / max_score)
        patterns = list(theory_patterns.get(theory_id, set()))
        instruments = list(theory_instruments.get(theory_id, set()))

        # Generate explanation
        if confidence > 0.8:
            explanation = f"{theory_id.replace('_', ' ').title()} strongly explains current market ({len(instruments)} instruments, {len(patterns)} patterns)"
        elif confidence > 0.5:
            explanation = f"{theory_id.replace('_', ' ').title()} moderately relevant to current conditions"
        else:
            explanation = f"{theory_id.replace('_', ' ').title()} has limited explanatory power right now"

        results.append(TheoryConfidence(
            theory_id=theory_id,
            theory_name=theory_id.replace("_", " ").title(),
            domain="economics",
            confidence=confidence,
            supporting_patterns=patterns,
            supporting_instruments=instruments[:5],
            explanation=explanation,
        ))

    return results[:10]  # Top 10


# ── Time Series Comparison ────────────────────────────────────────────────

@dataclass
class RegimeComparison:
    """Comparison of regime histories across instruments."""
    instruments: list[str]
    alignment_score: float  # how synchronized the instruments are
    divergences: list[dict]  # periods where instruments had different regimes
    current_agreement: bool  # are they all in same regime now?
    common_transitions: list[dict]  # transitions that happened in multiple instruments
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "instruments": self.instruments,
            "alignment_score": round(self.alignment_score, 3),
            "divergences": self.divergences,
            "current_agreement": self.current_agreement,
            "common_transitions": self.common_transitions,
            "interpretation": self.interpretation,
        }


def compare_regime_histories(
    histories: dict[str, list[dict]],
) -> RegimeComparison:
    """Compare regime histories across multiple instruments.

    Finds periods of alignment and divergence.
    """
    instruments = list(histories.keys())
    if len(instruments) < 2:
        return RegimeComparison(
            instruments=instruments, alignment_score=1.0, divergences=[],
            current_agreement=True, common_transitions=[],
            interpretation="Need at least 2 instruments to compare.",
        )

    # Get current regimes
    current_regimes = {}
    for inst, hist in histories.items():
        if hist:
            current_regimes[inst] = hist[-1].get("regime", "quiet")

    current_values = list(current_regimes.values())
    all_same = len(set(current_values)) <= 1

    # Compute alignment: what fraction of time are instruments in same regime
    # Use the most recent snapshots, aligned by index
    min_len = min(len(h) for h in histories.values())
    if min_len < 2:
        return RegimeComparison(
            instruments=instruments, alignment_score=0.5, divergences=[],
            current_agreement=all_same, common_transitions=[],
            interpretation="Not enough shared history to compare.",
        )

    agreements = 0
    divergences = []
    n_comparisons = min(min_len, 50)

    for i in range(-n_comparisons, 0):
        regimes_at_i = {}
        for inst, hist in histories.items():
            if len(hist) >= abs(i):
                regimes_at_i[inst] = hist[i].get("regime", "quiet")

        unique_regimes = set(regimes_at_i.values())
        if len(unique_regimes) <= 1:
            agreements += 1
        else:
            divergences.append({
                "offset": i,
                "regimes": regimes_at_i,
            })

    alignment = agreements / n_comparisons if n_comparisons > 0 else 0.5

    # Find common transitions
    all_transitions: dict[str, list] = {}
    for inst, hist in histories.items():
        for i in range(1, len(hist)):
            if hist[i].get("regime") != hist[i-1].get("regime"):
                key = f"{hist[i-1].get('regime')}->{hist[i].get('regime')}"
                all_transitions.setdefault(key, []).append(inst)

    common = [{"transition": k, "instruments": v, "count": len(v)}
              for k, v in all_transitions.items() if len(v) > 1]
    common.sort(key=lambda x: -x["count"])

    # Interpretation
    if alignment > 0.8:
        interp = f"Highly correlated: {', '.join(instruments)} move together {alignment:.0%} of the time."
    elif alignment > 0.5:
        interp = f"Moderately correlated: {alignment:.0%} alignment. Divergences offer hedging opportunities."
    else:
        interp = f"Low correlation: {alignment:.0%} alignment. These instruments move independently — good for diversification."

    return RegimeComparison(
        instruments=instruments,
        alignment_score=alignment,
        divergences=divergences[-5:],  # Last 5
        current_agreement=all_same,
        common_transitions=common[:5],
        interpretation=interp,
    )


# ── Watchlist ─────────────────────────────────────────────────────────────

@dataclass
class WatchlistItem:
    """An instrument on the watchlist with alert thresholds."""
    instrument: str
    domain: str
    alert_on_regime_change: bool = True
    alert_on_signal_above: float = 0.8
    alert_on_pattern: str = ""  # specific pattern to watch for
    added_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "domain": self.domain,
            "alert_on_regime_change": self.alert_on_regime_change,
            "alert_on_signal_above": self.alert_on_signal_above,
            "alert_on_pattern": self.alert_on_pattern,
            "added_at": self.added_at,
        }


class Watchlist:
    """In-memory watchlist with alert thresholds."""

    def __init__(self):
        self._items: dict[str, WatchlistItem] = {}

    def add(self, instrument: str, domain: str = "crypto", **kwargs) -> WatchlistItem:
        item = WatchlistItem(instrument=instrument, domain=domain, **kwargs)
        self._items[instrument] = item
        return item

    def remove(self, instrument: str) -> bool:
        return self._items.pop(instrument, None) is not None

    def list_all(self) -> list[dict]:
        return [item.to_dict() for item in self._items.values()]

    def check_alerts(self, scan_results: list[dict], prev_regimes: dict[str, str]) -> list[dict]:
        """Check watchlist items against scan results, return triggered alerts."""
        alerts = []
        for r in scan_results:
            inst = r.get("instrument", "")
            item = self._items.get(inst)
            if not item:
                continue

            # Regime change alert
            if item.alert_on_regime_change:
                prev = prev_regimes.get(inst, "")
                curr = r.get("regime", "")
                if prev and prev != curr:
                    alerts.append({
                        "instrument": inst,
                        "type": "regime_change",
                        "message": f"{inst}: regime changed from {prev} to {curr}",
                        "data": {"from": prev, "to": curr},
                    })

            # Signal threshold alert
            if r.get("signal_score", 0) >= item.alert_on_signal_above:
                alerts.append({
                    "instrument": inst,
                    "type": "signal_threshold",
                    "message": f"{inst}: signal score {r['signal_score']:.0%} exceeds threshold {item.alert_on_signal_above:.0%}",
                    "data": {"signal_score": r["signal_score"], "threshold": item.alert_on_signal_above},
                })

            # Pattern alert
            if item.alert_on_pattern and r.get("top_pattern") == item.alert_on_pattern:
                alerts.append({
                    "instrument": inst,
                    "type": "pattern_detected",
                    "message": f"{inst}: {item.alert_on_pattern} detected (strength {r.get('top_pattern_strength', 0):.0%})",
                    "data": {"pattern": item.alert_on_pattern, "strength": r.get("top_pattern_strength", 0)},
                })

        return alerts
