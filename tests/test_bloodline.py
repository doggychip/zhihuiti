"""Tests for bloodline system."""

from zhihuiti.bloodline import Bloodline
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
