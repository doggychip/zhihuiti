"""Tests for Causal Knowledge Persistence — accumulation across runs."""

from __future__ import annotations

import pytest

from zhihuiti.causal import (
    CausalGraph,
    CausalEdge,
    EdgeType,
    EvidenceStrength,
)
from zhihuiti.memory import Memory


@pytest.fixture
def mem():
    return Memory(":memory:")


class TestSaveToDb:
    def test_save_edges(self, mem):
        graph = CausalGraph()
        graph.add_edge("A", "B", EdgeType.CAUSES, EvidenceStrength.MODERATE, 0.8)
        graph.add_edge("B", "C", EdgeType.ENABLES, EvidenceStrength.WEAK, 0.5)
        count = graph.save_to_db(mem)
        assert count == 2

        # Verify in DB
        rows = mem.get_causal_knowledge()
        assert len(rows) == 2

    def test_save_updates_existing(self, mem):
        graph1 = CausalGraph()
        graph1.add_edge("A", "B", EdgeType.CAUSES, EvidenceStrength.WEAK, 0.5)
        graph1.save_to_db(mem)

        # Second run with same edge
        graph2 = CausalGraph()
        graph2.add_edge("A", "B", EdgeType.CAUSES, EvidenceStrength.MODERATE, 0.7)
        graph2.save_to_db(mem)

        rows = mem.get_causal_knowledge()
        assert len(rows) == 1
        # Confidence should have increased via Bayesian update
        assert rows[0]["confidence"] > 0.5
        assert rows[0]["observation_count"] == 2

    def test_repeated_saves_strengthen(self, mem):
        for i in range(5):
            graph = CausalGraph()
            graph.add_edge("A", "B", EdgeType.CAUSES, EvidenceStrength.WEAK, 0.5)
            graph.save_to_db(mem)

        rows = mem.get_causal_knowledge()
        assert rows[0]["observation_count"] == 5
        # Strength should upgrade with observations
        assert rows[0]["strength"] in ("strong", "moderate")


class TestLoadFromDb:
    def test_load_edges(self, mem):
        # Manually insert
        mem.save_causal_knowledge(
            "e1", "X", "Y", "causes", "moderate", 0.75,
            {"method": "test"}, "test_domain", 3,
        )
        mem.save_causal_knowledge(
            "e2", "Y", "Z", "enables", "weak", 0.4,
            {}, "test_domain", 1,
        )

        graph = CausalGraph()
        count = graph.load_from_db(mem)
        assert count == 2
        assert len(graph.edges) == 2
        assert "X" in graph.nodes
        assert "Y" in graph.nodes
        assert "Z" in graph.nodes

    def test_load_with_min_confidence(self, mem):
        mem.save_causal_knowledge("e1", "A", "B", "causes", "strong", 0.9)
        mem.save_causal_knowledge("e2", "C", "D", "causes", "weak", 0.2)

        graph = CausalGraph()
        count = graph.load_from_db(mem, min_confidence=0.5)
        assert count == 1
        assert graph.edges[0].source == "A"

    def test_roundtrip(self, mem):
        """Save a graph, load into a new graph, verify equivalence."""
        original = CausalGraph()
        original.add_edge("A", "B", EdgeType.CAUSES, EvidenceStrength.STRONG, 0.9,
                          {"granger": 0.01}, "market")
        original.add_edge("B", "C", EdgeType.PREVENTS, EvidenceStrength.MODERATE, 0.6,
                          {"test": True}, "market")
        original.save_to_db(mem)

        loaded = CausalGraph()
        loaded.load_from_db(mem)

        assert len(loaded.edges) == 2
        sources = {e.source for e in loaded.edges}
        targets = {e.target for e in loaded.edges}
        assert "A" in sources
        assert "C" in targets


class TestCrossRunAccumulation:
    def test_knowledge_accumulates_across_runs(self, mem):
        """Simulate 3 separate runs that each discover some causal edges."""
        # Run 1: discover A→B
        g1 = CausalGraph()
        g1.add_edge("liquidity", "spread", EdgeType.CAUSES, EvidenceStrength.WEAK, 0.4)
        g1.save_to_db(mem)

        # Run 2: discover A→B again + B→C
        g2 = CausalGraph()
        g2.load_from_db(mem)  # Inherit prior knowledge
        g2.add_edge("liquidity", "spread", EdgeType.CAUSES, EvidenceStrength.MODERATE, 0.6)
        g2.add_edge("spread", "profit", EdgeType.CAUSES, EvidenceStrength.WEAK, 0.3)
        g2.save_to_db(mem)

        # Run 3: load everything
        g3 = CausalGraph()
        g3.load_from_db(mem)
        assert len(g3.edges) == 2

        # The liquidity→spread edge should be stronger now
        liq_edge = [e for e in g3.edges if e.source == "liquidity"][0]
        assert liq_edge.confidence > 0.4  # Bayesian update
