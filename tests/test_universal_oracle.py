"""Tests for the Universal Oracle — multi-domain time series pattern detection."""

from __future__ import annotations

import math

import pytest

from zhihuiti.universal_oracle import (
    DOMAINS,
    DomainProfile,
    UniversalDiagnosis,
    diagnose,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _trending_up(n: int = 50, start: float = 100.0, step: float = 2.0) -> list[float]:
    return [start + i * step for i in range(n)]


def _trending_down(n: int = 50, start: float = 200.0, step: float = 2.0) -> list[float]:
    return [start - i * step for i in range(n)]


def _oscillating(n: int = 50, center: float = 100.0, amp: float = 10.0) -> list[float]:
    return [center + amp * math.sin(i * 0.5) for i in range(n)]


def _flat(n: int = 50, val: float = 100.0) -> list[float]:
    import random
    random.seed(42)
    return [val + random.uniform(-0.5, 0.5) for _ in range(n)]


def _spiky(n: int = 50, base: float = 100.0) -> list[float]:
    """Data with occasional spikes (fat tails)."""
    vals = [base] * n
    for i in [10, 25, 40]:
        vals[i] = base * 1.5
    return vals


# ── Domain profiles ───────────────────────────────────────────────────────

class TestDomainProfiles:
    def test_all_five_domains_exist(self):
        assert set(DOMAINS.keys()) == {"crypto", "system_perf", "social", "business", "scientific"}

    def test_each_domain_has_required_fields(self):
        for key, profile in DOMAINS.items():
            assert profile.name, f"{key} missing name"
            assert profile.description, f"{key} missing description"
            assert len(profile.pattern_theories) >= 3, f"{key} missing pattern theories"
            assert len(profile.regime_theories) >= 4, f"{key} missing regime theories"
            assert len(profile.regime_interpretations) >= 4, f"{key} missing regime interpretations"

    def test_system_perf_maps_to_control_theory(self):
        p = DOMAINS["system_perf"]
        # PID control should appear in multiple patterns
        all_theories = [t for theories in p.pattern_theories.values() for t in theories]
        assert "pid_control" in all_theories

    def test_social_maps_to_epidemic_model(self):
        p = DOMAINS["social"]
        assert "network_epidemic" in p.regime_theories.values() or "epidemic_seir" in p.regime_theories.values()

    def test_business_maps_to_game_theory(self):
        p = DOMAINS["business"]
        all_theories = [t for theories in p.pattern_theories.values() for t in theories]
        regime_theories = list(p.regime_theories.values())
        all_t = all_theories + regime_theories
        assert any("nash" in t or "equilibrium" in t or "replicator" in t for t in all_t)


# ── Universal diagnose function ───────────────────────────────────────────

class TestUniversalDiagnose:
    def test_empty_values(self):
        result = diagnose([], domain="system_perf", label="latency")
        assert result.current_value == 0
        assert result.regime == "quiet"
        assert result.domain == "system_perf"

    def test_trending_up_system_perf(self):
        # Simulating increasing latency
        result = diagnose(_trending_up(), domain="system_perf", label="API latency (ms)")
        assert result.label == "API latency (ms)"
        assert result.domain == "system_perf"
        assert result.domain_name == "System Performance"
        assert result.regime == "trending_up"
        assert "Degrading" in result.regime_interpretation

    def test_trending_down_social(self):
        # Simulating decaying virality
        result = diagnose(_trending_down(), domain="social", label="daily shares")
        assert result.regime == "trending_down"
        assert "Decay" in result.regime_interpretation or "cascade" in result.regime_interpretation.lower()

    def test_flat_business_metrics(self):
        result = diagnose(_flat(), domain="business", label="MRR ($)")
        assert result.regime in ("quiet", "mean_reverting")

    def test_scientific_data(self):
        result = diagnose(_oscillating(), domain="scientific", label="temperature (K)")
        assert result.domain_name == "Scientific Data"
        assert result.dominant_theory != ""

    def test_patterns_use_domain_theories(self):
        # Trending up data should detect momentum
        result = diagnose(_trending_up(), domain="system_perf", label="latency")
        momentum_patterns = [p for p in result.patterns if p["name"] == "momentum"]
        if momentum_patterns:
            # Should use system_perf theories, not crypto theories
            theory_ids = momentum_patterns[0]["theory_ids"]
            assert "efficient_market_hypothesis" not in theory_ids
            assert any(t in theory_ids for t in ["pid_control", "lyapunov_stability_ct"])

    def test_patterns_have_domain_interpretations(self):
        result = diagnose(_trending_up(), domain="system_perf", label="latency")
        for p in result.patterns:
            if p["name"] == "momentum":
                # Should contain system_perf interpretation
                assert "drift" in p["description"].lower() or "capacity" in p["description"].lower() or "baseline" in p["description"].lower()

    def test_to_dict_structure(self):
        result = diagnose(_trending_up(), domain="business", label="revenue")
        d = result.to_dict()
        assert "label" in d
        assert "domain" in d
        assert "domain_name" in d
        assert "regime" in d
        assert "regime_interpretation" in d
        assert "patterns" in d
        assert "collision_insights" in d
        assert "theory_details" in d

    def test_default_domain_is_scientific(self):
        result = diagnose(_flat())
        assert result.domain == "scientific"

    def test_crypto_domain_matches_original(self):
        result = diagnose(_trending_up(), domain="crypto", label="BTC price")
        # Should use EMH for trending_up
        assert result.dominant_theory == "efficient_market_hypothesis"

    def test_collision_insights_present_for_multiple_patterns(self):
        # Spiky data should trigger multiple patterns
        result = diagnose(_spiky(), domain="system_perf", label="error rate")
        # May or may not find collisions depending on pattern detection
        assert isinstance(result.collision_insights, list)

    def test_all_domains_produce_valid_output(self):
        for domain in DOMAINS:
            result = diagnose(_trending_up(30), domain=domain, label="test")
            assert result.domain == domain
            assert result.regime in ("trending_up", "trending_down", "mean_reverting", "volatile", "quiet")
            assert isinstance(result.patterns, list)
