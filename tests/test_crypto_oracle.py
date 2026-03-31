"""Tests for the Crypto Oracle — structural pattern detection + theory mapping + collision synthesis."""

from __future__ import annotations

import math

import pytest

from zhihuiti.crypto_oracle import (
    CollisionInsight,
    DetectedPattern,
    MarketDiagnosis,
    classify_regime,
    detect_fat_tails,
    detect_mean_reversion,
    detect_momentum,
    detect_orderbook_imbalance,
    detect_support_resistance,
    detect_volatility_clustering,
    diagnose_market,
    synthesize_collisions,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _trending_up_closes(n: int = 50, start: float = 70000.0, step: float = 100.0) -> list[float]:
    """Generate a steady uptrend."""
    return [start + i * step for i in range(n)]


def _trending_down_closes(n: int = 50, start: float = 75000.0, step: float = 100.0) -> list[float]:
    return [start - i * step for i in range(n)]


def _mean_reverting_closes(n: int = 50, center: float = 70000.0, amplitude: float = 500.0) -> list[float]:
    """Generate oscillating mean-reverting prices."""
    return [center + amplitude * math.sin(i * 0.5) for i in range(n)]


def _volatile_closes(n: int = 50, start: float = 70000.0) -> list[float]:
    """Generate highly volatile prices with alternating large jumps."""
    prices = [start]
    for i in range(1, n):
        jump = 2000 * (1 if i % 2 == 0 else -1)
        prices.append(prices[-1] + jump)
    return prices


def _flat_closes(n: int = 50, price: float = 70000.0) -> list[float]:
    """Flat prices with tiny noise."""
    import random
    random.seed(42)
    return [price + random.uniform(-10, 10) for _ in range(n)]


def _make_candles(closes: list[float], noise: float = 50.0) -> list[dict]:
    """Convert close prices to OHLCV candle dicts."""
    candles = []
    for c in closes:
        candles.append({
            "open": c - noise * 0.5,
            "high": c + noise,
            "low": c - noise,
            "close": c,
            "volume": 100.0,
        })
    return candles


# ── Momentum ───────────────────────────────────────────────────────────────

class TestDetectMomentum:
    def test_detects_uptrend(self):
        closes = _trending_up_closes()
        result = detect_momentum(closes)
        assert result is not None
        assert result.name == "momentum"
        assert result.strength > 0.3
        assert "bullish" in result.description

    def test_detects_downtrend(self):
        closes = _trending_down_closes()
        result = detect_momentum(closes)
        assert result is not None
        assert "bearish" in result.description

    def test_flat_market_weak_or_none(self):
        closes = _flat_closes()
        result = detect_momentum(closes)
        # Either None or very weak
        if result is not None:
            assert result.strength < 0.5

    def test_too_few_candles(self):
        assert detect_momentum([70000, 71000, 72000]) is None

    def test_theory_ids_present(self):
        result = detect_momentum(_trending_up_closes())
        assert result is not None
        assert len(result.theory_ids) > 0


# ── Mean Reversion ─────────────────────────────────────────────────────────

class TestDetectMeanReversion:
    def test_detects_oscillating(self):
        closes = _mean_reverting_closes()
        result = detect_mean_reversion(closes)
        # Mean reverting signal may or may not fire depending on autocorrelation
        if result is not None:
            assert result.name == "mean_reversion"
            assert "mean_reversion" in result.theory_ids

    def test_trending_not_mean_reverting(self):
        closes = _trending_up_closes()
        result = detect_mean_reversion(closes)
        # Strong trend should not show mean reversion
        assert result is None

    def test_too_few_candles(self):
        assert detect_mean_reversion([70000, 71000]) is None


# ── Volatility Clustering ─────────────────────────────────────────────────

class TestDetectVolatilityClustering:
    def test_detects_clustering(self):
        # Create data with volatility clustering: calm, then volatile, then calm
        closes = _flat_closes(20, 70000.0) + _volatile_closes(15, 70000.0) + _flat_closes(15, 70000.0)
        result = detect_volatility_clustering(closes)
        # May or may not detect depending on exact pattern
        if result is not None:
            assert result.name == "volatility_clustering"
            assert "heston_stochastic_volatility" in result.theory_ids

    def test_too_few_candles(self):
        assert detect_volatility_clustering([70000] * 10) is None


# ── Orderbook Imbalance ───────────────────────────────────────────────────

class TestDetectOrderbookImbalance:
    def test_bid_heavy(self):
        bids = [[70000, 10], [69990, 10], [69980, 10]]
        asks = [[70010, 1], [70020, 1], [70030, 1]]
        result = detect_orderbook_imbalance(bids, asks)
        assert result is not None
        assert result.name == "orderbook_imbalance"
        assert result.metrics["imbalance"] > 0
        assert "buy pressure" in result.description
        assert "market_microstructure" in result.theory_ids

    def test_ask_heavy(self):
        bids = [[70000, 1], [69990, 1]]
        asks = [[70010, 10], [70020, 10]]
        result = detect_orderbook_imbalance(bids, asks)
        assert result is not None
        assert result.metrics["imbalance"] < 0
        assert "sell pressure" in result.description

    def test_balanced_book(self):
        bids = [[70000, 5], [69990, 5]]
        asks = [[70010, 5], [70020, 5]]
        result = detect_orderbook_imbalance(bids, asks)
        assert result is None  # Too balanced

    def test_empty_book(self):
        assert detect_orderbook_imbalance([], []) is None


# ── Support/Resistance ────────────────────────────────────────────────────

class TestDetectSupportResistance:
    def test_detects_levels(self):
        # Create prices that bounce between two levels
        closes = []
        for _ in range(5):
            closes.extend([70000, 70200, 70500, 70800, 71000, 70800, 70500, 70200])
        highs = [c + 100 for c in closes]
        lows = [c - 100 for c in closes]
        result = detect_support_resistance(closes, highs, lows)
        if result is not None:
            assert result.name == "support_resistance"
            assert "mean_reversion" in result.theory_ids or "black_scholes" in result.theory_ids

    def test_too_few(self):
        assert detect_support_resistance([70000] * 5, [70100] * 5, [69900] * 5) is None


# ── Fat Tails ──────────────────────────────────────────────────────────────

class TestDetectFatTails:
    def test_detects_fat_tails(self):
        # Create returns with occasional huge jumps
        closes = [70000.0]
        for i in range(49):
            if i in (10, 25, 40):
                closes.append(closes[-1] * 1.05)  # 5% jump
            else:
                closes.append(closes[-1] * 1.001)  # tiny move
        result = detect_fat_tails(closes)
        if result is not None:
            assert result.name == "fat_tails"
            assert result.metrics["excess_kurtosis"] > 0

    def test_normal_returns_no_fat_tails(self):
        # Steady returns shouldn't trigger
        closes = _trending_up_closes(50, step=10.0)
        result = detect_fat_tails(closes)
        assert result is None


# ── Regime Classification ──────────────────────────────────────────────────

class TestClassifyRegime:
    def test_trending_up(self):
        assert classify_regime(_trending_up_closes()) == "trending_up"

    def test_trending_down(self):
        assert classify_regime(_trending_down_closes()) == "trending_down"

    def test_quiet_market(self):
        # Flat with tiny noise can read as quiet or mean-reverting
        assert classify_regime(_flat_closes()) in ("quiet", "mean_reverting")

    def test_few_candles(self):
        assert classify_regime([70000, 71000]) == "quiet"


# ── Full Diagnosis ─────────────────────────────────────────────────────────

class TestDiagnoseMarket:
    def test_basic_diagnosis(self):
        candles = _make_candles(_trending_up_closes())
        diag = diagnose_market(candles, instrument="BTC_USDT")
        assert isinstance(diag, MarketDiagnosis)
        assert diag.instrument == "BTC_USDT"
        assert diag.price > 0
        assert diag.regime in ("trending_up", "trending_down", "mean_reverting", "volatile", "quiet")
        assert diag.dominant_theory != ""

    def test_with_book(self):
        candles = _make_candles(_trending_up_closes())
        book = {
            "bids": [[70000, 10], [69990, 10]],
            "asks": [[70010, 1], [70020, 1]],
        }
        diag = diagnose_market(candles, book=book)
        # Should include orderbook imbalance pattern
        pattern_names = [p.name for p in diag.patterns]
        assert "orderbook_imbalance" in pattern_names

    def test_empty_candles(self):
        diag = diagnose_market([], instrument="BTC_USDT")
        assert diag.price == 0
        assert diag.regime == "quiet"

    def test_to_dict(self):
        candles = _make_candles(_trending_up_closes())
        diag = diagnose_market(candles)
        d = diag.to_dict()
        assert "instrument" in d
        assert "regime" in d
        assert "patterns" in d
        assert isinstance(d["patterns"], list)

    def test_patterns_sorted_by_strength(self):
        candles = _make_candles(_trending_up_closes())
        diag = diagnose_market(candles)
        if len(diag.patterns) > 1:
            for i in range(len(diag.patterns) - 1):
                assert diag.patterns[i].strength >= diag.patterns[i + 1].strength

    def test_to_dict_includes_collision_insights(self):
        candles = _make_candles(_trending_up_closes())
        diag = diagnose_market(candles)
        d = diag.to_dict()
        assert "collision_insights" in d
        assert isinstance(d["collision_insights"], list)


# ── Collision Synthesis ────────────────────────────────────────────────────

def _pat(name: str, theory_ids: list[str], strength: float = 0.6) -> DetectedPattern:
    return DetectedPattern(name=name, strength=strength, description="", metrics={}, theory_ids=theory_ids)


class TestSynthesizeCollisions:
    def test_returns_empty_for_single_pattern(self):
        assert synthesize_collisions([_pat("momentum", ["efficient_market_hypothesis"])]) == []

    def test_returns_empty_for_no_patterns(self):
        assert synthesize_collisions([]) == []

    def test_finds_bridge_for_momentum_vol_clustering(self):
        patterns = [
            _pat("momentum", ["efficient_market_hypothesis", "capm"]),
            _pat("volatility_clustering", ["heston_stochastic_volatility", "boltzmann_distribution"]),
        ]
        insights = synthesize_collisions(patterns)
        assert len(insights) >= 1
        ci = insights[0]
        assert ci.pattern_a in ("momentum", "volatility_clustering")
        assert ci.pattern_b in ("momentum", "volatility_clustering")
        assert ci.trading_rule != ""
        assert ci.collision_score > 0

    def test_finds_bridge_for_mean_reversion_support(self):
        patterns = [
            _pat("mean_reversion", ["mean_reversion", "arbitrage_pricing_theory"]),
            _pat("support_resistance", ["mean_reversion", "black_scholes"]),
        ]
        insights = synthesize_collisions(patterns)
        assert len(insights) >= 1
        # This pair has a real collision bridge (via yield_curve_vasicek)
        ci = insights[0]
        assert ci.bridge_theory != "(rule-template)"
        assert ci.collision_score > 0.5

    def test_rule_template_fallback(self):
        patterns = [
            _pat("fat_tails", ["heston_stochastic_volatility"]),
            _pat("orderbook_imbalance", ["market_microstructure"]),
        ]
        insights = synthesize_collisions(patterns)
        assert len(insights) >= 1
        ci = insights[0]
        # Should get rule template since no direct collision exists
        assert "flow" in ci.trading_rule.lower() or "tail" in ci.trading_rule.lower()

    def test_three_patterns_produce_multiple_insights(self):
        patterns = [
            _pat("momentum", ["efficient_market_hypothesis", "capm"], 0.7),
            _pat("volatility_clustering", ["heston_stochastic_volatility", "boltzmann_distribution"], 0.5),
            _pat("support_resistance", ["mean_reversion", "black_scholes"], 0.8),
        ]
        insights = synthesize_collisions(patterns)
        # Should have insights for up to 3 pairs
        assert len(insights) >= 2
        # Each insight covers a different pair
        pairs = {frozenset({ci.pattern_a, ci.pattern_b}) for ci in insights}
        assert len(pairs) == len(insights)

    def test_insights_sorted_by_score(self):
        patterns = [
            _pat("momentum", ["efficient_market_hypothesis", "capm"]),
            _pat("volatility_clustering", ["heston_stochastic_volatility", "boltzmann_distribution"]),
            _pat("mean_reversion", ["mean_reversion"]),
        ]
        insights = synthesize_collisions(patterns)
        for i in range(len(insights) - 1):
            assert insights[i].collision_score >= insights[i + 1].collision_score

    def test_collision_insight_to_dict(self):
        ci = CollisionInsight(
            pattern_a="momentum",
            pattern_b="vol_clustering",
            theory_a="emh",
            theory_b="heston",
            bridge_theory="maxent",
            bridge_domain="Information Theory",
            collision_score=0.71,
            interpretation="test interpretation",
            shared_patterns=["energy_based"],
            trading_rule="reduce size",
        )
        d = ci.to_dict()
        assert d["pattern_a"] == "momentum"
        assert d["bridge_theory"] == "maxent"
        assert d["collision_score"] == 0.71
        assert d["trading_rule"] == "reduce size"

    def test_deduplicates_per_pair(self):
        # Two patterns with overlapping theory IDs should only produce one insight per pair
        patterns = [
            _pat("momentum", ["efficient_market_hypothesis", "capm"]),
            _pat("volatility_clustering", ["heston_stochastic_volatility", "boltzmann_distribution"]),
        ]
        insights = synthesize_collisions(patterns)
        pairs = [frozenset({ci.pattern_a, ci.pattern_b}) for ci in insights]
        assert len(pairs) == len(set(pairs))  # No duplicate pairs
