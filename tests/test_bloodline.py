"""Tests for bloodline system."""

import pytest

from zhihuiti.bloodline import (
    Bloodline,
    FITNESS_SELECTION_POWER,
    MAX_MUTATION_RATE,
    MIN_MUTATION_RATE,
    _weighted_sample_two,
)
from zhihuiti.memory import Memory
from zhihuiti.models import AgentConfig, AgentRole


def _make_config(gene_id: str, gen: int = 0, **kwargs) -> AgentConfig:
    return AgentConfig(
        role=AgentRole.RESEARCHER,
        system_prompt="test",
        gene_id=gene_id,
        generation=gen,
        **kwargs,
    )


def test_register():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    gene_id = bl.register(_make_config("g1"), agent_id="a1")
    assert gene_id == "g1"
    stats = mem.get_lineage_stats()
    assert stats["total_genes"] == 1
    mem.close()


def test_breed():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    pa = _make_config("pa")
    pb = _make_config("pb")
    bl.register(pa)
    bl.register(pb)

    result = bl.breed(pa, pb, score_a=0.8, score_b=0.6)
    child = result.child_config
    assert child.generation == 1
    assert child.parent_a_gene == "pa"
    assert child.parent_b_gene == "pb"
    assert child.gene_id != "pa" and child.gene_id != "pb"
    mem.close()


def test_breed_from_pool():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    for i in range(3):
        config = _make_config(f"g{i}")
        bl.register(config, avg_score=0.7 + i * 0.05)

    child = bl.breed_from_pool(AgentRole.RESEARCHER)
    assert child is not None
    assert child.generation >= 1
    mem.close()


def test_breed_from_pool_insufficient_parents():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    bl.register(_make_config("g1"), avg_score=0.8)
    child = bl.breed_from_pool(AgentRole.RESEARCHER)
    assert child is None  # Need at least 2 parents
    mem.close()


def test_trace_ancestors():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    bl.register(_make_config("g1"))
    bl.register(_make_config("g2"))

    result = bl.breed(_make_config("g1"), _make_config("g2"), 0.8, 0.7)
    child = result.child_config
    bl.register(child)

    ancestors = bl.trace_ancestors(child.gene_id)
    gene_ids = {a["gene_id"] for a in ancestors}
    assert child.gene_id in gene_ids
    assert "g1" in gene_ids
    assert "g2" in gene_ids
    mem.close()


def test_zhu_qi_zu():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    bl.register(_make_config("root"))
    bl.register(_make_config("child1", gen=1, parent_a_gene="root"))
    bl.register(_make_config("child2", gen=1, parent_a_gene="root"))
    bl.register(_make_config("grandchild", gen=2, parent_a_gene="child1"))

    purged = bl.zhu_qi_zu("root")
    assert len(purged) == 3
    gene_ids = {p["gene_id"] for p in purged}
    assert "child1" in gene_ids
    assert "child2" in gene_ids
    assert "grandchild" in gene_ids
    mem.close()


def test_mark_dead():
    mem = Memory(":memory:")
    bl = Bloodline(mem)
    bl.register(_make_config("g1"), avg_score=0.8)
    bl.mark_dead("g1", 0.2)

    stats = mem.get_lineage_stats()
    assert stats["alive_genes"] == 0
    mem.close()


# ═══════════════════════════════════════════════════════════════════════════════
# WEIGHTED SAMPLING (fitness-proportional selection)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeightedSampleTwo:
    def test_returns_two_distinct_items(self):
        items = ["a", "b", "c", "d"]
        weights = [1.0, 1.0, 1.0, 1.0]
        a, b = _weighted_sample_two(items, weights)
        assert a != b
        assert a in items
        assert b in items

    def test_raises_on_fewer_than_two(self):
        with pytest.raises(ValueError):
            _weighted_sample_two(["a"], [1.0])

    def test_zero_weights_falls_back_to_uniform(self):
        items = ["a", "b", "c"]
        weights = [0.0, 0.0, 0.0]
        a, b = _weighted_sample_two(items, weights)
        assert a in items
        assert b in items
        assert a != b

    def test_heavily_weighted_item_selected_often(self):
        """Item with weight 100x others should be selected ~always."""
        items = ["star", "a", "b", "c", "d"]
        weights = [100.0, 0.01, 0.01, 0.01, 0.01]
        star_count = 0
        for _ in range(100):
            a, b = _weighted_sample_two(items, weights)
            if a == "star" or b == "star":
                star_count += 1
        # "star" should be selected in almost every trial
        assert star_count >= 90

    def test_two_items_always_returns_both(self):
        items = ["x", "y"]
        weights = [1.0, 1.0]
        a, b = _weighted_sample_two(items, weights)
        assert {a, b} == {"x", "y"}


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE MUTATION RATE IN BREEDING
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdaptiveMutation:
    def test_breed_accepts_custom_mutation_rate(self):
        mem = Memory(":memory:")
        bl = Bloodline(mem)
        pa = _make_config("pa")
        pb = _make_config("pb")
        # Should not raise
        result = bl.breed(pa, pb, score_a=0.8, score_b=0.6, mutation_rate=0.05)
        assert result.child_config is not None
        mem.close()

    def test_breed_with_zero_mutation_rate(self):
        """Minimum mutation rate is clamped to MIN_MUTATION_RATE."""
        mem = Memory(":memory:")
        bl = Bloodline(mem)
        pa = _make_config("pa")
        pb = _make_config("pb")
        # Even with 0.0 passed, internal rate should be MIN_MUTATION_RATE
        result = bl.breed(pa, pb, score_a=0.8, score_b=0.6, mutation_rate=0.0)
        assert result.child_config is not None
        mem.close()

    def test_breed_with_high_mutation_rate(self):
        """High mutation rate is clamped to MAX_MUTATION_RATE."""
        mem = Memory(":memory:")
        bl = Bloodline(mem)
        pa = _make_config("pa")
        pb = _make_config("pb")
        result = bl.breed(pa, pb, score_a=0.8, score_b=0.6, mutation_rate=1.0)
        assert result.child_config is not None
        mem.close()

    def test_breed_from_pool_accepts_mutation_rate(self):
        mem = Memory(":memory:")
        bl = Bloodline(mem)
        for i in range(3):
            config = _make_config(f"g{i}")
            bl.register(config, avg_score=0.7 + i * 0.05)

        child = bl.breed_from_pool(AgentRole.RESEARCHER, mutation_rate=0.05)
        assert child is not None
        mem.close()

    def test_high_mutation_rate_produces_more_mutations(self):
        """With high mutation rate, more children should have mutations."""
        mem = Memory(":memory:")
        bl = Bloodline(mem)
        pa = _make_config("pa")
        pb = _make_config("pb")

        mutation_counts = {0.05: 0, 0.35: 0}
        trials = 200

        for rate in [0.05, 0.35]:
            for _ in range(trials):
                result = bl.breed(pa, pb, score_a=0.8, score_b=0.6, mutation_rate=rate)
                if result.mutations:
                    mutation_counts[rate] += 1

        # Higher rate should produce more mutations
        assert mutation_counts[0.35] > mutation_counts[0.05]
        mem.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FITNESS-PROPORTIONAL SELECTION IN breed_from_pool
# ═══════════════════════════════════════════════════════════════════════════════

class TestFitnessProportionalSelection:
    def test_top_performers_selected_more_often(self):
        """Higher-scoring genes should be selected as parents more often."""
        mem = Memory(":memory:")
        bl = Bloodline(mem)

        # Create genes with varying scores
        configs = {
            "star": 0.95,    # Should be selected most
            "good": 0.80,
            "mid": 0.50,
            "low": 0.20,
            "bad": 0.05,
        }
        for gene_id, score in configs.items():
            bl.register(_make_config(gene_id), avg_score=score)

        # Breed many times and count who gets selected
        parent_counts: dict[str, int] = {k: 0 for k in configs}
        for _ in range(200):
            child = bl.breed_from_pool(AgentRole.RESEARCHER)
            if child:
                if child.parent_a_gene in parent_counts:
                    parent_counts[child.parent_a_gene] += 1
                if child.parent_b_gene in parent_counts:
                    parent_counts[child.parent_b_gene] += 1

        # "star" should be selected much more than "bad"
        assert parent_counts["star"] > parent_counts["bad"]
        mem.close()
