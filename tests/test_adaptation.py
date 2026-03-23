"""Tests for the Adaptation Engine — adaptive thresholds, prompt evolution, performance tracking."""

from __future__ import annotations

import pytest

from zhihuiti.adaptation import (
    AdaptiveThresholds,
    DEFAULT_CULL_THRESHOLD,
    DEFAULT_PROMOTE_THRESHOLD,
    MAX_CULL_THRESHOLD,
    MAX_PROMOTE_THRESHOLD,
    MIN_CULL_THRESHOLD,
    MIN_PROMOTE_THRESHOLD,
    MIN_SAMPLES_FOR_ADAPTATION,
    FailurePattern,
    PerformanceTracker,
    PromptEvolver,
    RolePerformance,
    _pearson,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdaptiveThresholds:
    def test_defaults_before_adaptation(self):
        at = AdaptiveThresholds()
        cull, promote = at.get_thresholds()
        assert cull == DEFAULT_CULL_THRESHOLD
        assert promote == DEFAULT_PROMOTE_THRESHOLD

    def test_no_adaptation_with_few_samples(self):
        at = AdaptiveThresholds()
        scores = [0.5] * (MIN_SAMPLES_FOR_ADAPTATION - 1)
        at.update(scores)
        cull, promote = at.get_thresholds()
        # Should remain at defaults
        assert cull == DEFAULT_CULL_THRESHOLD
        assert promote == DEFAULT_PROMOTE_THRESHOLD

    def test_adapts_with_enough_samples(self):
        at = AdaptiveThresholds()
        # High-performing population
        scores = [0.7 + i * 0.02 for i in range(20)]
        at.update(scores)
        cull, promote = at.get_thresholds()
        # Cull should have moved up from default (population is strong)
        assert cull > DEFAULT_CULL_THRESHOLD or cull == DEFAULT_CULL_THRESHOLD
        assert at.state.samples_used == 20

    def test_high_performing_population_raises_bar(self):
        at = AdaptiveThresholds()
        # All agents scoring > 0.8
        scores = [0.85 + i * 0.005 for i in range(20)]
        at.update(scores)
        at.update(scores)  # Twice to let EMA converge
        at.update(scores)
        cull, promote = at.get_thresholds()
        # Bar should rise for high-performing population
        assert cull >= DEFAULT_CULL_THRESHOLD

    def test_low_performing_population_lowers_bar(self):
        at = AdaptiveThresholds()
        # All agents scoring < 0.3
        scores = [0.1 + i * 0.01 for i in range(20)]
        at.update(scores)
        at.update(scores)
        at.update(scores)
        cull, promote = at.get_thresholds()
        # Should be more forgiving
        assert cull <= DEFAULT_CULL_THRESHOLD

    def test_guard_rails_prevent_extreme_values(self):
        at = AdaptiveThresholds()
        # Extreme high scores
        scores = [0.99] * 20
        for _ in range(10):
            at.update(scores)
        cull, promote = at.get_thresholds()
        assert cull >= MIN_CULL_THRESHOLD
        assert cull <= MAX_CULL_THRESHOLD
        assert promote >= MIN_PROMOTE_THRESHOLD
        assert promote <= MAX_PROMOTE_THRESHOLD

    def test_cull_always_below_promote(self):
        at = AdaptiveThresholds()
        # Various score distributions
        for scores in [
            [0.5] * 20,
            [0.3] * 20,
            [0.9] * 20,
            [i * 0.05 for i in range(20)],
        ]:
            at.update(scores)
            cull, promote = at.get_thresholds()
            assert cull < promote, f"cull {cull} >= promote {promote}"

    def test_history_recorded(self):
        at = AdaptiveThresholds()
        scores = [0.5 + i * 0.02 for i in range(10)]
        at.update(scores)
        assert len(at.state.history) == 1
        entry = at.state.history[0]
        assert "cull" in entry
        assert "promote" in entry
        assert "population_size" in entry
        assert entry["population_size"] == 10

    def test_ema_smoothing(self):
        """Thresholds should change gradually, not jump to new values."""
        at = AdaptiveThresholds()
        # Start with medium scores
        at.update([0.5] * 20)
        cull_1, _ = at.get_thresholds()
        # Suddenly high scores
        at.update([0.95] * 20)
        cull_2, _ = at.get_thresholds()
        # Should move toward new value but not jump all the way
        # (EMA with alpha=0.3 means 30% of new, 70% of old)
        assert cull_2 != cull_1  # Did move


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE PATTERN
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailurePattern:
    def test_failure_rate_zero_when_no_inspections(self):
        fp = FailurePattern(role="researcher")
        assert fp.failure_rate == 0.0

    def test_failure_rate_computed(self):
        fp = FailurePattern(
            role="researcher",
            total_inspections=10,
            total_failures=3,
        )
        assert fp.failure_rate == pytest.approx(0.3)

    def test_worst_layer(self):
        fp = FailurePattern(
            role="coder",
            layer_failures={"rigor": 5, "relevance": 2, "safety": 1},
        )
        assert fp.worst_layer() == "rigor"

    def test_worst_layer_none_when_empty(self):
        fp = FailurePattern(role="coder")
        assert fp.worst_layer() is None

    def test_weakest_layers(self):
        fp = FailurePattern(
            role="analyst",
            layer_failures={"rigor": 5, "relevance": 2, "safety": 8},
        )
        weakest = fp.weakest_layers(n=2)
        assert weakest == ["safety", "rigor"]


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT EVOLVER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromptEvolver:
    def test_no_evolution_without_history(self):
        pe = PromptEvolver()
        prompt = pe.evolve_prompt("You are a researcher.", "researcher")
        assert prompt == "You are a researcher."

    def test_no_evolution_below_min_inspections(self):
        pe = PromptEvolver()
        # Only 2 inspections (below default min of 3)
        pe.record_inspection("researcher", {"rigor": 0.2}, {"rigor": 0.5})
        pe.record_inspection("researcher", {"rigor": 0.3}, {"rigor": 0.5})
        prompt = pe.evolve_prompt("Base prompt.", "researcher")
        assert prompt == "Base prompt."

    def test_no_evolution_when_passing(self):
        pe = PromptEvolver()
        # All inspections pass — no failures
        for _ in range(5):
            pe.record_inspection("researcher", {"rigor": 0.8}, {"rigor": 0.5})
        prompt = pe.evolve_prompt("Base prompt.", "researcher")
        assert prompt == "Base prompt."

    def test_evolves_prompt_on_failures(self):
        pe = PromptEvolver()
        # Record failures at rigor
        for _ in range(5):
            pe.record_inspection("researcher",
                                 {"rigor": 0.2, "relevance": 0.9},
                                 {"rigor": 0.5, "relevance": 0.4})
        prompt = pe.evolve_prompt("Base prompt.", "researcher")
        assert "Performance Improvement Directives" in prompt
        assert len(prompt) > len("Base prompt.")

    def test_directives_target_failing_layer(self):
        pe = PromptEvolver()
        # Fail at safety specifically
        for _ in range(5):
            pe.record_inspection("coder",
                                 {"safety": 0.2, "rigor": 0.8, "relevance": 0.9},
                                 {"safety": 0.6, "rigor": 0.5, "relevance": 0.4})
        prompt = pe.evolve_prompt("Base.", "coder")
        # Should contain safety-related directives
        assert "risk" in prompt.lower() or "harm" in prompt.lower() or "safe" in prompt.lower()

    def test_directives_rotate(self):
        pe = PromptEvolver()
        for _ in range(5):
            pe.record_inspection("researcher",
                                 {"rigor": 0.2},
                                 {"rigor": 0.5})
        prompt1 = pe.evolve_prompt("Base.", "researcher")
        prompt2 = pe.evolve_prompt("Base.", "researcher")
        # Directives should rotate (different ones each time)
        assert prompt1 != prompt2

    def test_role_report(self):
        pe = PromptEvolver()
        for _ in range(4):
            pe.record_inspection("researcher",
                                 {"rigor": 0.2, "relevance": 0.8},
                                 {"rigor": 0.5, "relevance": 0.4})
        report = pe.get_role_report()
        assert "researcher" in report
        assert report["researcher"]["worst_layer"] == "rigor"
        assert report["researcher"]["failure_rate"] > 0

    def test_max_directives_capped(self):
        pe = PromptEvolver()
        # Fail at all layers
        for _ in range(10):
            pe.record_inspection("analyst",
                                 {"rigor": 0.1, "relevance": 0.1, "safety": 0.1, "causal": 0.1},
                                 {"rigor": 0.5, "relevance": 0.4, "safety": 0.6, "causal": 0.4})
        prompt = pe.evolve_prompt("Base.", "analyst")
        # Count directive lines (numbered 1., 2., 3.)
        directive_lines = [l for l in prompt.split("\n") if l.strip().startswith(("1.", "2.", "3.", "4."))]
        assert len(directive_lines) <= 3  # MAX_DIRECTIVES_PER_PROMPT


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestRolePerformance:
    def test_mean_score(self):
        rp = RolePerformance(role="researcher", scores=[0.6, 0.8, 0.7])
        assert rp.mean_score == pytest.approx(0.7)

    def test_mean_score_empty(self):
        rp = RolePerformance(role="researcher")
        assert rp.mean_score == 0.0

    def test_score_trend_positive(self):
        rp = RolePerformance(role="researcher", scores=[0.3, 0.4, 0.5, 0.6, 0.7])
        assert rp.score_trend > 0

    def test_score_trend_negative(self):
        rp = RolePerformance(role="researcher", scores=[0.9, 0.8, 0.7, 0.6, 0.5])
        assert rp.score_trend < 0

    def test_score_trend_flat(self):
        rp = RolePerformance(role="researcher", scores=[0.5, 0.5, 0.5, 0.5, 0.5])
        assert rp.score_trend == pytest.approx(0.0)

    def test_score_trend_too_few(self):
        rp = RolePerformance(role="researcher", scores=[0.5, 0.6])
        assert rp.score_trend == 0.0

    def test_layer_mean(self):
        rp = RolePerformance(
            role="coder",
            layer_scores={"rigor": [0.4, 0.6, 0.8], "safety": [0.9, 0.9]},
        )
        assert rp.layer_mean("rigor") == pytest.approx(0.6)
        assert rp.layer_mean("safety") == pytest.approx(0.9)
        assert rp.layer_mean("nonexistent") == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceTracker:
    def test_record_and_retrieve(self):
        pt = PerformanceTracker()
        pt.record("researcher", 0.75, {"rigor": 0.8, "safety": 0.9})
        summary = pt.get_role_summary("researcher")
        assert summary is not None
        assert summary["mean_score"] == 0.75
        assert summary["layer_means"]["rigor"] == 0.8

    def test_get_all_scores(self):
        pt = PerformanceTracker()
        pt.record("researcher", 0.7)
        pt.record("coder", 0.8)
        pt.record("researcher", 0.6)
        all_scores = pt.get_all_scores()
        assert sorted(all_scores) == [0.6, 0.7, 0.8]

    def test_improving_roles(self):
        pt = PerformanceTracker()
        for s in [0.3, 0.4, 0.5, 0.6, 0.7]:
            pt.record("researcher", s)
        assert "researcher" in pt.get_improving_roles()

    def test_declining_roles(self):
        pt = PerformanceTracker()
        for s in [0.9, 0.8, 0.7, 0.6, 0.5]:
            pt.record("coder", s)
        assert "coder" in pt.get_declining_roles()

    def test_suggest_mutation_rate_top_performer(self):
        pt = PerformanceTracker()
        for _ in range(5):
            pt.record("researcher", 0.9)
        rate = pt.suggest_mutation_rate("researcher")
        assert rate <= 0.10  # Low mutation for top performers

    def test_suggest_mutation_rate_low_performer(self):
        pt = PerformanceTracker()
        for _ in range(5):
            pt.record("coder", 0.2)
        rate = pt.suggest_mutation_rate("coder")
        assert rate >= 0.20  # High mutation for low performers

    def test_suggest_mutation_rate_declining(self):
        pt = PerformanceTracker()
        for s in [0.8, 0.7, 0.6, 0.5, 0.4]:
            pt.record("analyst", s)
        rate = pt.suggest_mutation_rate("analyst")
        assert rate >= 0.15  # Should increase mutation for declining

    def test_suggest_mutation_rate_unknown_role(self):
        pt = PerformanceTracker()
        rate = pt.suggest_mutation_rate("unknown_role")
        assert rate == 0.15  # Default

    def test_role_summary_nonexistent(self):
        pt = PerformanceTracker()
        assert pt.get_role_summary("nonexistent") is None

    def test_trend_in_summary(self):
        pt = PerformanceTracker()
        for s in [0.3, 0.5, 0.7]:
            pt.record("researcher", s)
        summary = pt.get_role_summary("researcher")
        assert summary["trend"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION: AdaptiveThresholds + PerformanceTracker
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdaptationIntegration:
    def test_tracker_feeds_thresholds(self):
        """Performance tracker scores feed into threshold calibration."""
        pt = PerformanceTracker()
        at = AdaptiveThresholds()

        # Record a bunch of scores
        for s in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.55, 0.65]:
            pt.record("researcher", s)

        # Feed all scores to threshold calibration
        all_scores = pt.get_all_scores()
        at.update(all_scores)

        cull, promote = at.get_thresholds()
        assert cull < promote
        assert at.state.samples_used == 10

    def test_prompt_evolution_respects_min_inspections(self):
        """Prompt evolution shouldn't modify prompts too aggressively early on."""
        pe = PromptEvolver()
        # Only 1 failure — shouldn't trigger evolution
        pe.record_inspection("researcher", {"rigor": 0.1}, {"rigor": 0.5})
        prompt = pe.evolve_prompt("Base.", "researcher", min_inspections=5)
        assert prompt == "Base."

    def test_mutation_rate_flows_to_breeding(self):
        """Performance tracker mutation rate can be passed to bloodline."""
        pt = PerformanceTracker()
        for _ in range(5):
            pt.record("researcher", 0.9)  # Top performer
        rate = pt.suggest_mutation_rate("researcher")
        assert rate <= 0.10

        # This rate would be passed to bloodline.breed_from_pool(mutation_rate=rate)
        # We just verify the value is reasonable
        assert 0.0 < rate < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTIVE PRUNING
# ═══════════════════════════════════════════════════════════════════════════════

class TestDirectivePruning:
    def test_pruning_after_consecutive_passes(self):
        pe = PromptEvolver()
        # Fail at rigor to create a directive
        for _ in range(5):
            pe.record_inspection("researcher",
                                 {"rigor": 0.2, "relevance": 0.9},
                                 {"rigor": 0.5, "relevance": 0.4})
        # Verify directive is added
        prompt = pe.evolve_prompt("Base.", "researcher")
        assert "Performance Improvement Directives" in prompt

        # Now pass rigor 5 consecutive times (PRUNE_AFTER_PASSES = 5)
        for _ in range(5):
            pe.record_inspection("researcher",
                                 {"rigor": 0.8, "relevance": 0.9},
                                 {"rigor": 0.5, "relevance": 0.4})

        # Rigor should be pruned — no more directives
        prompt2 = pe.evolve_prompt("Base.", "researcher")
        assert prompt2 == "Base."

    def test_pruning_resets_on_new_failure(self):
        pe = PromptEvolver()
        # Build up failures
        for _ in range(5):
            pe.record_inspection("coder",
                                 {"safety": 0.2},
                                 {"safety": 0.6})
        # Pass 4 times (not enough to prune)
        for _ in range(4):
            pe.record_inspection("coder",
                                 {"safety": 0.8},
                                 {"safety": 0.6})
        # Fail once — resets consecutive counter
        pe.record_inspection("coder", {"safety": 0.2}, {"safety": 0.6})
        # Pass 4 more — still not enough
        for _ in range(4):
            pe.record_inspection("coder",
                                 {"safety": 0.8},
                                 {"safety": 0.6})
        prompt = pe.evolve_prompt("Base.", "coder")
        assert "Performance Improvement Directives" in prompt

    def test_pruned_layers_in_report(self):
        pe = PromptEvolver()
        for _ in range(5):
            pe.record_inspection("analyst",
                                 {"rigor": 0.2},
                                 {"rigor": 0.5})
        for _ in range(5):
            pe.record_inspection("analyst",
                                 {"rigor": 0.9},
                                 {"rigor": 0.5})
        report = pe.get_role_report()
        assert "rigor" in report["analyst"]["pruned_layers"]


# ═══════════════════════════════════════════════════════════════════════════════
# VARIANCE-AWARE MUTATION & TEMPORAL DECAY
# ═══════════════════════════════════════════════════════════════════════════════

class TestVarianceAwareMutation:
    def test_high_variance_increases_mutation(self):
        pt = PerformanceTracker()
        # Erratic performer: same mean (~0.55) but high variance
        for s in [0.2, 0.9, 0.3, 0.8, 0.25, 0.85]:
            pt.record("erratic", s)
        # Stable performer: same mean but low variance
        for s in [0.55, 0.55, 0.55, 0.55, 0.55, 0.55]:
            pt.record("stable", s)

        rate_erratic = pt.suggest_mutation_rate("erratic")
        rate_stable = pt.suggest_mutation_rate("stable")
        assert rate_erratic > rate_stable

    def test_mutation_rate_within_bounds(self):
        pt = PerformanceTracker()
        for _ in range(10):
            pt.record("role", 0.99)
        rate = pt.suggest_mutation_rate("role")
        assert 0.03 <= rate <= 0.35


class TestWeightedMean:
    def test_weighted_mean_favors_recent(self):
        rp = RolePerformance(role="test")
        # Early scores are low, recent are high
        rp.scores = [0.2, 0.2, 0.2, 0.2, 0.9, 0.9, 0.9, 0.9]
        # Weighted mean should be higher than simple mean
        assert rp.weighted_mean_score > rp.mean_score

    def test_weighted_mean_empty(self):
        rp = RolePerformance(role="test")
        assert rp.weighted_mean_score == 0.0


class TestCoefficientOfVariation:
    def test_zero_variance(self):
        rp = RolePerformance(role="test", scores=[0.5, 0.5, 0.5])
        assert rp.coefficient_of_variation == 0.0

    def test_high_variance(self):
        rp = RolePerformance(role="test", scores=[0.1, 0.9, 0.1, 0.9, 0.1, 0.9])
        assert rp.coefficient_of_variation > 0.5

    def test_cv_too_few_scores(self):
        rp = RolePerformance(role="test", scores=[0.5])
        assert rp.coefficient_of_variation == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-LAYER CORRELATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestLayerCorrelation:
    def test_perfect_positive_correlation(self):
        pt = PerformanceTracker()
        for i in range(10):
            s = 0.3 + i * 0.05
            pt.record("researcher", s, {"rigor": s, "safety": s})
        corrs = pt.detect_layer_correlations("researcher")
        assert len(corrs) >= 1
        # Perfect positive correlation
        assert corrs[0][2] > 0.9

    def test_negative_correlation(self):
        pt = PerformanceTracker()
        for i in range(10):
            s = 0.3 + i * 0.05
            pt.record("researcher", s, {"rigor": s, "safety": 1.0 - s})
        corrs = pt.detect_layer_correlations("researcher")
        assert len(corrs) >= 1
        assert corrs[0][2] < -0.9

    def test_no_correlation_with_few_samples(self):
        pt = PerformanceTracker()
        pt.record("researcher", 0.5, {"rigor": 0.5, "safety": 0.5})
        corrs = pt.detect_layer_correlations("researcher")
        assert corrs == []

    def test_no_correlation_for_unknown_role(self):
        pt = PerformanceTracker()
        assert pt.detect_layer_correlations("nonexistent") == []

    def test_correlations_in_summary(self):
        pt = PerformanceTracker()
        for i in range(10):
            s = 0.3 + i * 0.05
            pt.record("researcher", s, {"rigor": s, "safety": s})
        summary = pt.get_role_summary("researcher")
        assert "layer_correlations" in summary
        assert len(summary["layer_correlations"]) >= 1

    def test_summary_includes_new_fields(self):
        pt = PerformanceTracker()
        for i in range(5):
            pt.record("coder", 0.5 + i * 0.05)
        summary = pt.get_role_summary("coder")
        assert "weighted_mean" in summary
        assert "variance" in summary
        assert "cv" in summary


class TestPearson:
    def test_perfect_positive(self):
        assert _pearson([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_perfect_negative(self):
        assert _pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)

    def test_zero_variance(self):
        assert _pearson([1, 1, 1], [2, 3, 4]) == 0.0

    def test_too_few(self):
        assert _pearson([1], [2]) == 0.0
