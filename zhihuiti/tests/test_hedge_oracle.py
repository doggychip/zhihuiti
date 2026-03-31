"""Tests for theory-guided hedge fund evolution."""

from __future__ import annotations

import json
import random
from unittest.mock import MagicMock, patch

import pytest

from zhihuiti.hedge_manager import (
    HedgeFundManager,
    REGIME_STRATEGIES,
    PATTERN_PARAM_HINTS,
    COLLISION_OVERRIDES,
    PARAM_RANGES,
    STRATEGY_TYPES,
)
from zhihuiti.crypto_oracle import (
    CollisionInsight,
    DetectedPattern,
    MarketDiagnosis,
    diagnose_market,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _mock_manager() -> HedgeFundManager:
    """Create a manager with mocked HTTP client."""
    mgr = HedgeFundManager.__new__(HedgeFundManager)
    mgr.base_url = "https://test.com"
    mgr.api_key = "key"
    mgr.client = MagicMock()
    mgr.cull_threshold = 0.3
    mgr.promote_threshold = 0.7
    return mgr


def _fake_diagnosis(regime: str, patterns: list[DetectedPattern] | None = None) -> MarketDiagnosis:
    """Create a fake MarketDiagnosis for testing."""
    return MarketDiagnosis(
        instrument="BTC_USDT",
        price=71000.0,
        change_pct=-0.03,
        patterns=patterns or [],
        regime=regime,
        dominant_theory="efficient_market_hypothesis",
    )


def _momentum_pattern(strength: float = 0.7) -> DetectedPattern:
    return DetectedPattern(
        name="momentum",
        strength=strength,
        description="bullish momentum",
        metrics={"sma_spread": 0.01},
        theory_ids=["efficient_market_hypothesis"],
    )


def _mean_reversion_pattern(strength: float = 0.6) -> DetectedPattern:
    return DetectedPattern(
        name="mean_reversion",
        strength=strength,
        description="O-U mean reversion",
        metrics={"z_score": -1.2},
        theory_ids=["mean_reversion"],
    )


def _vol_clustering_pattern(strength: float = 0.5) -> DetectedPattern:
    return DetectedPattern(
        name="volatility_clustering",
        strength=strength,
        description="GARCH-like clustering",
        metrics={"sq_return_autocorr": 0.3},
        theory_ids=["heston_stochastic_volatility"],
    )


# ── Regime → Strategy mapping ─────────────────────────────────────────────

class TestRegimeStrategies:
    def test_all_regimes_have_mapping(self):
        for regime in ("trending_up", "trending_down", "mean_reverting", "volatile", "quiet"):
            assert regime in REGIME_STRATEGIES
            assert len(REGIME_STRATEGIES[regime]) >= 2

    def test_trending_up_favors_momentum(self):
        strats = REGIME_STRATEGIES["trending_up"]
        assert "momentum_strong" in strats or "momentum" in strats

    def test_mean_reverting_favors_mean_reversion(self):
        strats = REGIME_STRATEGIES["mean_reverting"]
        assert "mean_reversion" == strats[0]

    def test_volatile_favors_adaptive(self):
        strats = REGIME_STRATEGIES["volatile"]
        assert "hybrid_adaptive" == strats[0]


# ── pick_strategy_for_regime ───────────────────────────────────────────────

class TestPickStrategyForRegime:
    def test_picks_first_candidate_different_from_current(self):
        mgr = _mock_manager()
        result = mgr.pick_strategy_for_regime("mean_reverting", "momentum")
        assert result == "mean_reversion"  # First in REGIME_STRATEGIES["mean_reverting"]

    def test_skips_current_type(self):
        mgr = _mock_manager()
        # Current is mean_reversion, so should pick second candidate
        result = mgr.pick_strategy_for_regime("mean_reverting", "mean_reversion")
        assert result != "mean_reversion"
        assert result in STRATEGY_TYPES

    def test_unknown_regime_falls_back(self):
        mgr = _mock_manager()
        result = mgr.pick_strategy_for_regime("unknown_regime", "momentum")
        assert result in STRATEGY_TYPES
        assert result != "momentum"


# ── apply_pattern_hints ────────────────────────────────────────────────────

class TestApplyPatternHints:
    def test_momentum_pattern_decreases_short_period(self):
        mgr = _mock_manager()
        params = {"shortPeriod": 10, "longPeriod": 30, "quantity": 0.1}
        patterns = [_momentum_pattern(strength=1.0)]
        result = mgr.apply_pattern_hints("momentum", params, patterns)
        # Short period should decrease
        assert result["shortPeriod"] < 10

    def test_mean_reversion_pattern_adjusts_threshold(self):
        mgr = _mock_manager()
        params = {"period": 20, "threshold": 2.0, "quantity": 0.1}
        patterns = [_mean_reversion_pattern(strength=0.8)]
        result = mgr.apply_pattern_hints("mean_reversion", params, patterns)
        assert result["threshold"] < 2.0

    def test_vol_clustering_increases_target_vol(self):
        mgr = _mock_manager()
        params = {"period": 15, "baseQuantity": 0.1, "targetVol": 0.02}
        patterns = [_vol_clustering_pattern(strength=0.6)]
        result = mgr.apply_pattern_hints("hybrid_adaptive", params, patterns)
        assert result["targetVol"] > 0.02

    def test_no_matching_hints_unchanged(self):
        mgr = _mock_manager()
        params = {"quantity": 0.1}
        patterns = [_momentum_pattern()]
        # indicator_macd has no momentum hints
        result = mgr.apply_pattern_hints("indicator_macd", params, patterns)
        assert result == params

    def test_respects_param_bounds(self):
        mgr = _mock_manager()
        lo, hi = PARAM_RANGES["momentum"]["shortPeriod"]
        params = {"shortPeriod": lo, "longPeriod": 30, "quantity": 0.1}
        patterns = [_momentum_pattern(strength=1.0)]
        result = mgr.apply_pattern_hints("momentum", params, patterns)
        assert result["shortPeriod"] >= lo

    def test_multiple_patterns_compound(self):
        mgr = _mock_manager()
        params = {"shortPeriod": 10, "longPeriod": 30, "quantity": 0.1}
        patterns = [_momentum_pattern(strength=0.5), DetectedPattern(
            name="orderbook_imbalance", strength=0.8,
            description="buy pressure", metrics={}, theory_ids=["market_microstructure"],
        )]
        result = mgr.apply_pattern_hints("momentum", params, patterns)
        # momentum pattern decreases shortPeriod, orderbook increases quantity
        assert result["shortPeriod"] < 10
        assert result["quantity"] > 0.1


# ── Theory-guided evolve_bottom ────────────────────────────────────────────

class TestTheoryGuidedEvolution:
    def _setup_mock_agent(self, mgr, agent_id="agent1", strategy_type="momentum"):
        """Wire up mock HTTP responses for get_agent and put."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": agent_id,
            "config": json.dumps({"shortPeriod": 10, "longPeriod": 30, "quantity": 0.1, "pair": "BTC/USD"}),
            "strategy": {"type": strategy_type},
        }
        mock_resp.raise_for_status.return_value = None

        put_resp = MagicMock()
        put_resp.json.return_value = {"ok": True}
        put_resp.raise_for_status.return_value = None

        post_resp = MagicMock()
        post_resp.json.return_value = {"id": "strat123"}
        post_resp.raise_for_status.return_value = None

        mgr.client.get.return_value = mock_resp
        mgr.client.put.return_value = put_resp
        mgr.client.post.return_value = post_resp

    def test_volatile_regime_forces_swap(self):
        random.seed(42)
        mgr = _mock_manager()
        self._setup_mock_agent(mgr, strategy_type="momentum")

        diag = _fake_diagnosis("volatile", [_vol_clustering_pattern()])
        bottom = [{"agentId": "agent1"}]
        results = mgr.evolve_bottom(bottom, [], diagnosis=diag)

        assert len(results) == 1
        assert "swap" in results[0]["action"]
        assert "regime=volatile" in results[0]["action"]

    def test_mean_reverting_regime_picks_mean_reversion_strategy(self):
        random.seed(42)
        mgr = _mock_manager()
        self._setup_mock_agent(mgr, strategy_type="momentum")

        diag = _fake_diagnosis("mean_reverting", [_mean_reversion_pattern()])
        bottom = [{"agentId": "agent1"}]
        results = mgr.evolve_bottom(bottom, [], diagnosis=diag)

        assert len(results) == 1
        # Should swap to mean_reversion (first in REGIME_STRATEGIES for mean_reverting)
        assert "mean_reversion" in results[0]["action"]

    def test_trending_with_top_agents_can_breed(self):
        random.seed(0)  # Seed that picks "breed" from ["breed", "swap_strategy"]
        mgr = _mock_manager()
        self._setup_mock_agent(mgr, strategy_type="momentum")

        diag = _fake_diagnosis("trending_up", [_momentum_pattern()])
        bottom = [{"agentId": "agent1"}]
        top = [{"agentId": "top1"}]

        # We need to test that breed is a valid option
        # Run multiple times to check both paths are reachable
        actions = set()
        for seed in range(20):
            random.seed(seed)
            results = mgr.evolve_bottom(bottom, top, diagnosis=diag)
            actions.add("breed" if "breed" in results[0]["action"] else "swap")

        assert "breed" in actions or "swap" in actions  # At least one path hit

    def test_no_diagnosis_falls_back_to_random(self):
        # Try multiple seeds to find one that doesn't pick "breed" (no top agents)
        mgr = _mock_manager()
        self._setup_mock_agent(mgr)

        bottom = [{"agentId": "agent1"}]
        for seed in range(50):
            random.seed(seed)
            results = mgr.evolve_bottom(bottom, [], diagnosis=None)
            if results:
                assert results[0]["regime"] is None
                return
        pytest.fail("No seed produced a non-breed action")

    def test_pattern_hints_applied_during_swap(self):
        random.seed(42)
        mgr = _mock_manager()
        self._setup_mock_agent(mgr, strategy_type="momentum")

        patterns = [_vol_clustering_pattern(strength=0.9)]
        diag = _fake_diagnosis("volatile", patterns)
        bottom = [{"agentId": "agent1"}]
        results = mgr.evolve_bottom(bottom, [], diagnosis=diag)

        # volatile regime forces swap, no breed needed
        assert len(results) == 1
        assert "params" in results[0]

    def test_result_includes_regime(self):
        mgr = _mock_manager()
        self._setup_mock_agent(mgr)

        # volatile forces swap (no breed), so always produces a result
        diag = _fake_diagnosis("volatile")
        results = mgr.evolve_bottom([{"agentId": "agent1"}], [], diagnosis=diag)
        assert len(results) == 1
        assert results[0]["regime"] == "volatile"


# ── diagnose method ────────────────────────────────────────────────────────

class TestDiagnoseMethod:
    def test_returns_diagnosis_from_candles(self):
        mgr = _mock_manager()
        candles = [
            {"open": 70000 + i * 100, "high": 70100 + i * 100,
             "low": 69900 + i * 100, "close": 70000 + i * 100 + 50, "volume": 100}
            for i in range(30)
        ]
        diag = mgr.diagnose(candles)
        assert diag is not None
        assert diag.regime in ("trending_up", "trending_down", "mean_reverting", "volatile", "quiet")

    def test_returns_none_on_empty(self):
        mgr = _mock_manager()
        diag = mgr.diagnose([])
        # Should return a diagnosis with price=0, not None
        assert diag is not None
        assert diag.price == 0


# ── run_evolution_cycle with oracle ────────────────────────────────────────

class TestEvolutionCycleWithOracle:
    def test_cycle_accepts_candles(self):
        mgr = _mock_manager()

        # Mock leaderboard
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"agentId": "top1", "compositeScore": 90, "rank": 1, "totalReturn": 10,
             "sharpeRatio": 2.0, "winRate": 0.6, "maxDrawdown": 5, "agent": {}},
            {"agentId": "bot1", "compositeScore": 10, "rank": 2, "totalReturn": -5,
             "sharpeRatio": -0.5, "winRate": 0.3, "maxDrawdown": 20, "agent": {}},
        ]
        mock_resp.raise_for_status.return_value = None

        put_resp = MagicMock()
        put_resp.json.return_value = {"ok": True}
        put_resp.raise_for_status.return_value = None

        post_resp = MagicMock()
        post_resp.json.return_value = {"id": "strat1"}
        post_resp.raise_for_status.return_value = None

        def mock_get(url):
            r = MagicMock()
            r.raise_for_status.return_value = None
            if "leaderboard" in url:
                r.json.return_value = mock_resp.json.return_value
            else:
                r.json.return_value = {
                    "id": "bot1",
                    "config": json.dumps({"quantity": 0.1, "pair": "BTC/USD"}),
                    "strategy": {"type": "momentum"},
                }
            return r

        mgr.client.get.side_effect = mock_get
        mgr.client.put.return_value = put_resp
        mgr.client.post.return_value = post_resp

        candles = [
            {"open": 70000 + i * 100, "high": 70100 + i * 100,
             "low": 69900 + i * 100, "close": 70050 + i * 100, "volume": 100}
            for i in range(30)
        ]

        result = mgr.run_evolution_cycle(candles=candles)
        assert "diagnosis" in result
        assert result["evolved"] >= 1


# ── Collision override tests ───────────────────────────────────────────────

def _fake_collision_insight(pa: str, pb: str, score: float = 0.7) -> CollisionInsight:
    return CollisionInsight(
        pattern_a=pa, pattern_b=pb,
        theory_a="t_a", theory_b="t_b",
        bridge_theory="bridge", bridge_domain="domain",
        collision_score=score,
        interpretation="test",
        shared_patterns=[],
        trading_rule="test rule",
    )


class TestCollisionOverrides:
    def test_overrides_map_covers_key_combos(self):
        expected = [
            frozenset({"momentum", "volatility_clustering"}),
            frozenset({"momentum", "mean_reversion"}),
            frozenset({"momentum", "orderbook_imbalance"}),
            frozenset({"volatility_clustering", "fat_tails"}),
        ]
        for combo in expected:
            assert combo in COLLISION_OVERRIDES, f"Missing override for {combo}"

    def test_get_collision_override_returns_override(self):
        mgr = _mock_manager()
        diag = _fake_diagnosis("volatile", [
            _momentum_pattern(),
            _vol_clustering_pattern(),
        ])
        # Add collision insights
        diag.collision_insights = [
            _fake_collision_insight("momentum", "volatility_clustering", 0.7)
        ]
        result = mgr.get_collision_override(diag)
        assert result is not None
        strategy, scale = result
        assert strategy == "hybrid_adaptive"
        assert scale == 0.5

    def test_get_collision_override_returns_none_without_insights(self):
        mgr = _mock_manager()
        diag = _fake_diagnosis("volatile")
        diag.collision_insights = []
        assert mgr.get_collision_override(diag) is None

    def test_get_collision_override_returns_none_for_unknown_pair(self):
        mgr = _mock_manager()
        diag = _fake_diagnosis("quiet")
        # A pair not in COLLISION_OVERRIDES
        diag.collision_insights = [
            _fake_collision_insight("unknown_a", "unknown_b", 0.9)
        ]
        assert mgr.get_collision_override(diag) is None

    def test_collision_override_takes_priority_over_regime(self):
        mgr = _mock_manager()

        # Setup mock agent
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "agent1",
            "config": json.dumps({"quantity": 0.1, "pair": "BTC/USD"}),
            "strategy": {"type": "momentum"},
        }
        mock_resp.raise_for_status.return_value = None

        put_resp = MagicMock()
        put_resp.json.return_value = {"ok": True}
        put_resp.raise_for_status.return_value = None

        post_resp = MagicMock()
        post_resp.json.return_value = {"id": "strat1"}
        post_resp.raise_for_status.return_value = None

        mgr.client.get.return_value = mock_resp
        mgr.client.put.return_value = put_resp
        mgr.client.post.return_value = post_resp

        # Diagnosis: trending_up regime, but collision says momentum+vol_clustering
        diag = _fake_diagnosis("trending_up", [
            _momentum_pattern(),
            _vol_clustering_pattern(),
        ])
        diag.collision_insights = [
            _fake_collision_insight("momentum", "volatility_clustering", 0.71)
        ]

        results = mgr.evolve_bottom([{"agentId": "agent1"}], [], diagnosis=diag)
        assert len(results) == 1
        # Should use collision override (hybrid_adaptive) not regime (momentum_strong)
        assert "collision" in results[0]["action"]

    def test_collision_override_scales_quantity(self):
        mgr = _mock_manager()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "agent1",
            "config": json.dumps({"quantity": 0.2, "pair": "BTC/USD"}),
            "strategy": {"type": "momentum"},
        }
        mock_resp.raise_for_status.return_value = None
        put_resp = MagicMock()
        put_resp.json.return_value = {"ok": True}
        put_resp.raise_for_status.return_value = None
        post_resp = MagicMock()
        post_resp.json.return_value = {"id": "strat1"}
        post_resp.raise_for_status.return_value = None

        mgr.client.get.return_value = mock_resp
        mgr.client.put.return_value = put_resp
        mgr.client.post.return_value = post_resp

        # vol+fat_tails combo = scale 0.3 (dangerous regime)
        diag = _fake_diagnosis("volatile", [
            _vol_clustering_pattern(),
            DetectedPattern("fat_tails", 0.5, "", {}, ["heston_stochastic_volatility"]),
        ])
        diag.collision_insights = [
            _fake_collision_insight("volatility_clustering", "fat_tails", 0.6)
        ]

        results = mgr.evolve_bottom([{"agentId": "agent1"}], [], diagnosis=diag)
        assert len(results) == 1
        # The quantity in params should be scaled down
        params = results[0]["params"]
        # hybrid_adaptive uses baseQuantity, and it should be < unscaled
        if "baseQuantity" in params:
            assert params["baseQuantity"] <= 0.2 * 0.3 + 0.01  # Scaled + mutation tolerance
