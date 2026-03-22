"""Tests for silicon_realms.theory.collision_engine — theory collision detection."""
import pytest

from silicon_realms.theory.collision_engine import (
    THEORY_REGISTRY,
    CollisionReport,
    collide,
    collide_all,
    top_collisions,
    list_theories,
    collision_matrix,
    _jaccard,
)


# ─── Registry Integrity ─────────────────────────────────────────────────

class TestTheoryRegistry:
    def test_registry_not_empty(self):
        assert len(THEORY_REGISTRY) > 0

    def test_all_theories_have_required_fields(self):
        required = {
            "display_name", "domain", "equation", "update_form",
            "operators", "patterns", "variables", "conservation",
        }
        for key, theory in THEORY_REGISTRY.items():
            missing = required - set(theory.keys())
            assert not missing, f"Theory '{key}' missing fields: {missing}"

    def test_patterns_are_sets(self):
        for key, theory in THEORY_REGISTRY.items():
            assert isinstance(theory["patterns"], set), f"{key}: patterns should be a set"

    def test_operators_are_sets(self):
        for key, theory in THEORY_REGISTRY.items():
            assert isinstance(theory["operators"], set), f"{key}: operators should be a set"

    def test_conservation_are_sets(self):
        for key, theory in THEORY_REGISTRY.items():
            assert isinstance(theory["conservation"], set), f"{key}: conservation should be a set"

    def test_variables_are_dicts(self):
        for key, theory in THEORY_REGISTRY.items():
            assert isinstance(theory["variables"], dict), f"{key}: variables should be a dict"

    def test_list_theories_returns_sorted(self):
        theories = list_theories()
        assert theories == sorted(theories)

    def test_list_theories_matches_registry(self):
        assert set(list_theories()) == set(THEORY_REGISTRY.keys())


# ─── Jaccard Helper ──────────────────────────────────────────────────────

class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        assert abs(_jaccard({"a", "b", "c"}, {"b", "c", "d"}) - 0.5) < 1e-9

    def test_empty_sets(self):
        assert _jaccard(set(), set()) == 0.0

    def test_one_empty(self):
        assert _jaccard({"a"}, set()) == 0.0


# ─── Collision Reports ──────────────────────────────────────────────────

class TestCollide:
    def test_collide_returns_report(self):
        report = collide("replicator_dynamics", "boltzmann_distribution")
        assert isinstance(report, CollisionReport)

    def test_collide_score_in_range(self):
        report = collide("replicator_dynamics", "boltzmann_distribution")
        assert 0.0 <= report.similarity_score <= 1.0

    def test_collide_strength_valid(self):
        report = collide("replicator_dynamics", "boltzmann_distribution")
        assert report.collision_strength in {"deep", "significant", "resonance", "weak"}

    def test_collide_uses_display_names(self):
        report = collide("replicator_dynamics", "boltzmann_distribution")
        assert report.theory_a == "Replicator Dynamics (EGT)"
        assert report.theory_b == "Boltzmann Distribution"

    def test_collide_shared_patterns_are_real(self):
        """Shared patterns must actually be in both theories."""
        report = collide("replicator_dynamics", "boltzmann_distribution")
        ta = THEORY_REGISTRY["replicator_dynamics"]
        tb = THEORY_REGISTRY["boltzmann_distribution"]
        for p in report.shared_patterns:
            assert p in ta["patterns"], f"'{p}' not in replicator_dynamics patterns"
            assert p in tb["patterns"], f"'{p}' not in boltzmann_distribution patterns"

    def test_collide_unknown_theory_raises(self):
        with pytest.raises(ValueError, match="Unknown theory"):
            collide("nonexistent", "boltzmann_distribution")

    def test_collide_unknown_second_theory_raises(self):
        with pytest.raises(ValueError, match="Unknown theory"):
            collide("replicator_dynamics", "nonexistent")

    def test_same_theory_is_deep(self):
        """A theory collided with itself should score very high."""
        report = collide("kalman_filter", "kalman_filter")
        assert report.similarity_score > 0.8
        assert report.collision_strength == "deep"

    def test_distant_theories_low_score(self):
        """Very different theories should score low."""
        report = collide("persistent_homology", "ess")
        assert report.similarity_score < 0.2

    def test_related_theories_higher_score(self):
        """Theories from same domain should generally score higher."""
        same_domain = collide("boltzmann_distribution", "ising_model")
        diff_domain = collide("boltzmann_distribution", "persistent_homology")
        assert same_domain.similarity_score > diff_domain.similarity_score

    def test_collide_report_str(self):
        report = collide("replicator_dynamics", "boltzmann_distribution")
        s = str(report)
        assert "THEORY COLLISION" in s
        assert "Replicator Dynamics" in s

    def test_collide_interpretation_present(self):
        report = collide("replicator_dynamics", "boltzmann_distribution")
        assert len(report.interpretation) > 10

    def test_structural_bridges_present_for_related(self):
        """Related theories should have structural bridges."""
        report = collide("kalman_filter", "predictive_coding")
        assert len(report.structural_bridges) > 0


# ─── Batch Operations ────────────────────────────────────────────────────

class TestBatchOperations:
    def test_collide_all_returns_list(self):
        reports = collide_all()
        assert isinstance(reports, list)
        assert len(reports) > 0

    def test_collide_all_sorted_descending(self):
        reports = collide_all()
        scores = [r.similarity_score for r in reports]
        assert scores == sorted(scores, reverse=True)

    def test_collide_all_correct_count(self):
        n = len(THEORY_REGISTRY)
        expected = n * (n - 1) // 2
        assert len(collide_all()) == expected

    def test_top_collisions_respects_n(self):
        reports = top_collisions(5)
        assert len(reports) == 5

    def test_top_collisions_are_strongest(self):
        top5 = top_collisions(5)
        all_reports = collide_all()
        for i in range(5):
            assert top5[i].similarity_score == all_reports[i].similarity_score

    def test_collision_matrix_keys(self):
        matrix = collision_matrix()
        keys = list(THEORY_REGISTRY.keys())
        for (a, b), score in matrix.items():
            assert a in keys
            assert b in keys
            assert 0.0 <= score <= 1.0

    def test_collision_matrix_size(self):
        n = len(THEORY_REGISTRY)
        expected = n * (n - 1) // 2
        assert len(collision_matrix()) == expected


# ─── Scoring Invariants ─────────────────────────────────────────────────

class TestScoringInvariants:
    def test_all_scores_in_range(self):
        for report in collide_all():
            assert 0.0 <= report.similarity_score <= 1.0

    def test_strength_thresholds(self):
        """Verify strength labels match score thresholds."""
        for report in collide_all():
            s = report.similarity_score
            strength = report.collision_strength
            if s > 0.55:
                assert strength == "deep"
            elif s > 0.30:
                assert strength == "significant"
            elif s > 0.12:
                assert strength == "resonance"
            else:
                assert strength == "weak"
