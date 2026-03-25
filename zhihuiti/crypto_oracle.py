"""Crypto Oracle — structural pattern detection on live market data, mapped to theories.

Pulls OHLCV candle data, detects mathematical patterns (mean reversion, momentum,
volatility clustering, order-flow imbalance, etc.), and maps each detected pattern
to the most relevant theories in the Silicon Realms knowledge graph.

This is the bridge between real crypto markets and theory intelligence.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any


# ── Pattern detection results ──────────────────────────────────────────────

@dataclass
class DetectedPattern:
    """A structural pattern detected in market data."""
    name: str
    strength: float          # 0.0–1.0
    description: str
    metrics: dict[str, float] = field(default_factory=dict)
    theory_ids: list[str] = field(default_factory=list)


@dataclass
class MarketDiagnosis:
    """Full theory-grounded diagnosis of current market state."""
    instrument: str
    price: float
    change_pct: float
    patterns: list[DetectedPattern]
    regime: str              # trending_up, trending_down, mean_reverting, volatile, quiet
    dominant_theory: str     # theory_id most relevant to current regime
    theory_details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "price": self.price,
            "change_pct": round(self.change_pct, 4),
            "regime": self.regime,
            "dominant_theory": self.dominant_theory,
            "patterns": [
                {
                    "name": p.name,
                    "strength": round(p.strength, 3),
                    "description": p.description,
                    "metrics": {k: round(v, 6) for k, v in p.metrics.items()},
                    "theory_ids": p.theory_ids,
                }
                for p in self.patterns
            ],
            "theory_details": self.theory_details,
        }


# ── Core pattern detectors ─────────────────────────────────────────────────

def _returns(closes: list[float]) -> list[float]:
    """Log returns from close prices."""
    return [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]


def _sma(values: list[float], period: int) -> list[float]:
    """Simple moving average."""
    if len(values) < period:
        return []
    return [statistics.mean(values[i - period:i]) for i in range(period, len(values) + 1)]


def detect_momentum(closes: list[float]) -> DetectedPattern | None:
    """Detect trend momentum via short/long MA crossover and directional consistency."""
    if len(closes) < 20:
        return None

    short_ma = _sma(closes, 7)
    long_ma = _sma(closes, 20)

    if not short_ma or not long_ma:
        return None

    # Align lengths
    n = min(len(short_ma), len(long_ma))
    short_ma = short_ma[-n:]
    long_ma = long_ma[-n:]

    # Current spread and direction
    spread = (short_ma[-1] - long_ma[-1]) / long_ma[-1]
    prev_spread = (short_ma[-2] - long_ma[-2]) / long_ma[-2] if n > 1 else 0

    # Directional consistency: what fraction of recent returns are same sign
    rets = _returns(closes[-10:])
    if not rets:
        return None
    pos_frac = sum(1 for r in rets if r > 0) / len(rets)
    direction = "bullish" if spread > 0 else "bearish"
    consistency = max(pos_frac, 1 - pos_frac)

    strength = min(1.0, abs(spread) * 20 + consistency * 0.3)

    if strength < 0.2:
        return None

    return DetectedPattern(
        name="momentum",
        strength=strength,
        description=f"{direction} momentum: SMA7/SMA20 spread {spread:+.4f}, directional consistency {consistency:.0%}",
        metrics={
            "sma_spread": spread,
            "spread_change": spread - prev_spread,
            "directional_consistency": consistency,
        },
        theory_ids=["efficient_market_hypothesis", "capm"],
    )


def detect_mean_reversion(closes: list[float]) -> DetectedPattern | None:
    """Detect Ornstein-Uhlenbeck mean reversion via deviation from rolling mean."""
    if len(closes) < 20:
        return None

    mu = statistics.mean(closes[-20:])
    sigma = statistics.stdev(closes[-20:])
    if sigma == 0:
        return None

    current = closes[-1]
    z_score = (current - mu) / sigma

    # Estimate reversion speed: autocorrelation of returns
    rets = _returns(closes[-20:])
    if len(rets) < 2:
        return None

    # Lag-1 autocorrelation (negative = mean-reverting)
    mean_r = statistics.mean(rets)
    var_r = statistics.variance(rets)
    if var_r == 0:
        return None
    autocorr = sum((rets[i] - mean_r) * (rets[i - 1] - mean_r) for i in range(1, len(rets))) / ((len(rets) - 1) * var_r)

    # Mean reversion is indicated by negative autocorrelation and price near mean
    is_reverting = autocorr < -0.1
    strength = min(1.0, max(0.0, -autocorr) + (1.0 - min(1.0, abs(z_score) / 3)))

    if not is_reverting or strength < 0.15:
        return None

    return DetectedPattern(
        name="mean_reversion",
        strength=strength,
        description=f"O-U mean reversion: z-score {z_score:+.2f}, autocorr {autocorr:.3f}, mean ${mu:,.0f}",
        metrics={
            "z_score": z_score,
            "autocorrelation": autocorr,
            "rolling_mean": mu,
            "rolling_std": sigma,
        },
        theory_ids=["mean_reversion", "arbitrage_pricing_theory"],
    )


def detect_volatility_clustering(closes: list[float]) -> DetectedPattern | None:
    """Detect GARCH-like volatility clustering via autocorrelation of squared returns."""
    if len(closes) < 25:
        return None

    rets = _returns(closes)
    sq_rets = [r * r for r in rets]

    if len(sq_rets) < 10:
        return None

    # Autocorrelation of squared returns (volatility clustering)
    mean_sq = statistics.mean(sq_rets)
    var_sq = statistics.variance(sq_rets)
    if var_sq == 0:
        return None

    autocorr_sq = sum(
        (sq_rets[i] - mean_sq) * (sq_rets[i - 1] - mean_sq) for i in range(1, len(sq_rets))
    ) / ((len(sq_rets) - 1) * var_sq)

    # Recent vs historical volatility ratio
    recent_vol = statistics.stdev(rets[-7:]) if len(rets) >= 7 else statistics.stdev(rets)
    hist_vol = statistics.stdev(rets)
    vol_ratio = recent_vol / hist_vol if hist_vol > 0 else 1.0

    clustering = autocorr_sq > 0.1
    strength = min(1.0, max(0.0, autocorr_sq) + abs(vol_ratio - 1.0) * 0.5)

    if not clustering or strength < 0.15:
        return None

    return DetectedPattern(
        name="volatility_clustering",
        strength=strength,
        description=f"GARCH-like clustering: vol autocorr {autocorr_sq:.3f}, recent/hist vol ratio {vol_ratio:.2f}",
        metrics={
            "sq_return_autocorr": autocorr_sq,
            "recent_volatility": recent_vol,
            "historical_volatility": hist_vol,
            "vol_ratio": vol_ratio,
        },
        theory_ids=["heston_stochastic_volatility", "boltzmann_distribution"],
    )


def detect_orderbook_imbalance(bids: list[list], asks: list[list]) -> DetectedPattern | None:
    """Detect Kyle's Lambda style order-flow imbalance from order book snapshot."""
    if not bids or not asks:
        return None

    bid_depth = sum(float(b[1]) for b in bids[:10])
    ask_depth = sum(float(a[1]) for a in asks[:10])
    total = bid_depth + ask_depth

    if total == 0:
        return None

    imbalance = (bid_depth - ask_depth) / total  # -1 to +1
    strength = abs(imbalance)

    if strength < 0.1:
        return None

    direction = "buy pressure" if imbalance > 0 else "sell pressure"
    spread = float(asks[0][0]) - float(bids[0][0])
    mid = (float(asks[0][0]) + float(bids[0][0])) / 2
    spread_bps = (spread / mid) * 10000

    return DetectedPattern(
        name="orderbook_imbalance",
        strength=strength,
        description=f"Kyle's Lambda {direction}: imbalance {imbalance:+.3f}, spread {spread_bps:.1f}bps",
        metrics={
            "imbalance": imbalance,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "spread_bps": spread_bps,
        },
        theory_ids=["market_microstructure"],
    )


def detect_support_resistance(closes: list[float], highs: list[float], lows: list[float]) -> DetectedPattern | None:
    """Detect support/resistance levels as price attractors (fixed points)."""
    if len(closes) < 15:
        return None

    current = closes[-1]

    # Find price levels that have been touched multiple times
    # Bin prices into buckets
    price_range = max(highs) - min(lows)
    if price_range == 0:
        return None
    bucket_size = price_range / 20

    # Count touches per bucket
    touch_counts: dict[int, list[float]] = {}
    for h, l in zip(highs, lows):
        for price in [h, l]:
            bucket = int((price - min(lows)) / bucket_size)
            touch_counts.setdefault(bucket, []).append(price)

    # Find most-touched levels
    levels = []
    for bucket, prices in sorted(touch_counts.items(), key=lambda x: -len(x[1])):
        if len(prices) >= 3:
            level = statistics.mean(prices)
            levels.append((level, len(prices)))

    if not levels:
        return None

    # Find nearest support and resistance
    support = max((lv for lv, _ in levels if lv < current), default=None)
    resistance = min((lv for lv, _ in levels if lv > current), default=None)

    if support is None and resistance is None:
        return None

    nearest = support if resistance is None else resistance if support is None else (
        support if (current - support) < (resistance - current) else resistance
    )
    distance_pct = abs(current - nearest) / current

    strength = max(0.0, 1.0 - distance_pct * 20)  # Stronger when closer to level

    if strength < 0.1:
        return None

    return DetectedPattern(
        name="support_resistance",
        strength=strength,
        description=f"Price attractor near ${nearest:,.0f} (distance {distance_pct:.2%})"
                    + (f", support ${support:,.0f}" if support else "")
                    + (f", resistance ${resistance:,.0f}" if resistance else ""),
        metrics={
            "nearest_level": nearest,
            "distance_pct": distance_pct,
            **({"support": support} if support else {}),
            **({"resistance": resistance} if resistance else {}),
        },
        theory_ids=["mean_reversion", "black_scholes"],
    )


def detect_fat_tails(closes: list[float]) -> DetectedPattern | None:
    """Detect non-Gaussian fat tails via excess kurtosis."""
    if len(closes) < 20:
        return None

    rets = _returns(closes)
    if len(rets) < 10:
        return None

    mean_r = statistics.mean(rets)
    std_r = statistics.stdev(rets)
    if std_r == 0:
        return None

    # Excess kurtosis (Gaussian = 0)
    n = len(rets)
    m4 = sum((r - mean_r) ** 4 for r in rets) / n
    kurtosis = m4 / (std_r ** 4) - 3.0

    if kurtosis < 0.5:
        return None

    strength = min(1.0, kurtosis / 5.0)

    return DetectedPattern(
        name="fat_tails",
        strength=strength,
        description=f"Non-Gaussian fat tails: excess kurtosis {kurtosis:.2f} (Gaussian=0)",
        metrics={
            "excess_kurtosis": kurtosis,
            "return_std": std_r,
        },
        theory_ids=["heston_stochastic_volatility", "boltzmann_distribution"],
    )


# ── Regime classification ──────────────────────────────────────────────────

_REGIME_THEORIES = {
    "trending_up": "efficient_market_hypothesis",
    "trending_down": "efficient_market_hypothesis",
    "mean_reverting": "mean_reversion",
    "volatile": "heston_stochastic_volatility",
    "quiet": "markowitz_portfolio",
}


def classify_regime(closes: list[float]) -> str:
    """Classify the current market regime from price data."""
    if len(closes) < 10:
        return "quiet"

    rets = _returns(closes[-20:])
    if not rets:
        return "quiet"

    cum_return = sum(rets)
    vol = statistics.stdev(rets) if len(rets) > 1 else 0

    # Annualize vol (assuming 4h candles, ~1095 per year)
    ann_vol = vol * math.sqrt(1095)

    if ann_vol > 0.8:
        return "volatile"

    autocorr = 0.0
    if len(rets) > 2:
        mean_r = statistics.mean(rets)
        var_r = statistics.variance(rets)
        if var_r > 0:
            autocorr = sum((rets[i] - mean_r) * (rets[i - 1] - mean_r) for i in range(1, len(rets))) / ((len(rets) - 1) * var_r)

    if autocorr < -0.2:
        return "mean_reverting"

    if cum_return > 0.02:
        return "trending_up"
    elif cum_return < -0.02:
        return "trending_down"

    return "quiet"


# ── Main diagnosis function ────────────────────────────────────────────────

def diagnose_market(
    candles: list[dict],
    instrument: str = "BTC_USDT",
    book: dict | None = None,
) -> MarketDiagnosis:
    """Run all pattern detectors on candle data and map to theories.

    Args:
        candles: List of OHLCV dicts with keys: open, high, low, close, volume.
        instrument: Instrument name.
        book: Optional order book dict with "bids" and "asks" lists.

    Returns:
        MarketDiagnosis with detected patterns and theory mappings.
    """
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    if not closes:
        return MarketDiagnosis(
            instrument=instrument, price=0, change_pct=0,
            patterns=[], regime="quiet", dominant_theory="efficient_market_hypothesis",
        )

    price = closes[-1]
    change_pct = (closes[-1] / closes[0] - 1) if closes[0] else 0

    # Run all detectors
    patterns: list[DetectedPattern] = []
    for detector in [detect_momentum, detect_mean_reversion, detect_volatility_clustering, detect_fat_tails]:
        result = detector(closes)
        if result:
            patterns.append(result)

    sr = detect_support_resistance(closes, highs, lows)
    if sr:
        patterns.append(sr)

    if book:
        ob = detect_orderbook_imbalance(book.get("bids", []), book.get("asks", []))
        if ob:
            patterns.append(ob)

    # Sort by strength
    patterns.sort(key=lambda p: -p.strength)

    # Classify regime
    regime = classify_regime(closes)
    dominant_theory = _REGIME_THEORIES.get(regime, "efficient_market_hypothesis")

    # Enrich with theory details from knowledge graph
    theory_details = _get_theory_details(patterns, dominant_theory)

    return MarketDiagnosis(
        instrument=instrument,
        price=price,
        change_pct=change_pct,
        patterns=patterns,
        regime=regime,
        dominant_theory=dominant_theory,
        theory_details=theory_details,
    )


def _get_theory_details(patterns: list[DetectedPattern], dominant_theory: str) -> list[dict]:
    """Pull theory details from the knowledge graph for detected patterns."""
    try:
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
    except Exception:
        return []

    seen: set[str] = set()
    details: list[dict] = []

    # Always include dominant theory
    all_ids = [dominant_theory]
    for p in patterns:
        all_ids.extend(p.theory_ids)

    for tid in all_ids:
        if tid in seen:
            continue
        seen.add(tid)

        theory = graph.get_theory(tid)
        if not theory:
            continue

        # Find cross-domain analogies for this theory
        analogies = graph.find_analogies(tid, min_score=0.6, limit=3)

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
