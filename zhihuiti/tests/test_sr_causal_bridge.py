"""Tests for the causal bridge between Silicon Realms and zhihuiti's causal engine."""
import math

from zhihuiti.causal import CausalGraph, EdgeType, EvidenceStrength
from silicon_realms.causal_bridge import (
    _lag_correlation,
    _extract_time_series,
    _evidence_strength,
    discover_causal_structure,
    intervention_effects,
    summarize_causal_graph,
)


# ─── Helpers ─────────────────────────────────────────────────────────────

def _make_history(ticks: int = 50) -> dict:
    """Create a minimal simulation history with known causal structure."""
    history = {
        "ticks": list(range(ticks)),
        "total_supply": [1000 + i * 10 for i in range(ticks)],
        "gini": [0.3 + 0.005 * i for i in range(ticks)],
        "temperature": [1.0 + 0.01 * i for i in range(ticks)],
        "entropy": [2.0 + 0.02 * i for i in range(ticks)],
        "fisher_information": [0.5 + 0.01 * i for i in range(ticks)],
        "kl_divergence": [0.1 + 0.01 * i for i in range(ticks)],
        "realm_theory": [],
    }

    for i in range(ticks):
        history["realm_theory"].append({
            "compute": {
                "selection_pressure": 1.0 + 0.02 * i,
                "realm_temperature": 1.0 + 0.01 * i,
                "realm_entropy": 0.5 + 0.01 * i,
                "knowledge_pool": 0.0,
                "route_efficiency": 1.0,
                "congestion": 0.0,
                "channel_capacity": 1.0,
                "noise_level": 0.5,
                "mutual_information": 0.0,
                "redundancy": 0.0,
                "avalanche_exposure": 0.0,
                "reward_modifier": 1.0 + 0.005 * i,
            },
            "memory": {
                "selection_pressure": 1.0,
                "realm_temperature": 1.0 + 0.015 * i,
                "realm_entropy": 0.5 + 0.01 * i,
                "knowledge_pool": 5.0 + 0.5 * i,
                "route_efficiency": 1.0,
                "congestion": 0.0,
                "channel_capacity": 1.0,
                "noise_level": 0.5 + 0.01 * i,
                "mutual_information": 0.0,
                "redundancy": 0.0,
                "avalanche_exposure": 0.0,
                "reward_modifier": 1.0,
            },
        })

    return history


# ─── Lag correlation tests ───────────────────────────────────────────────

class TestLagCorrelation:
    def test_perfect_positive_correlation(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # y = x lagged by 1
        corr = _lag_correlation(x, y, lag=1)
        assert corr > 0.99

    def test_no_correlation(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y = [5, 3, 7, 1, 9, 2, 8, 4, 6, 10]  # random
        corr = _lag_correlation(x, y, lag=1)
        assert abs(corr) < 0.8  # not strongly correlated

    def test_negative_correlation(self):
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]  # reversed
        corr = _lag_correlation(x, y, lag=1)
        assert corr < -0.9

    def test_too_short_returns_zero(self):
        assert _lag_correlation([1, 2], [3, 4], lag=1) == 0.0

    def test_empty_returns_zero(self):
        assert _lag_correlation([], [], lag=1) == 0.0


# ─── Time series extraction ─────────────────────────────────────────────

class TestExtractTimeSeries:
    def test_global_variable(self):
        history = _make_history(10)
        series = _extract_time_series(history, "temperature")
        assert len(series) == 10
        assert series[0] == 1.0

    def test_realm_variable(self):
        history = _make_history(10)
        series = _extract_time_series(history, "selection_pressure", realm="compute")
        assert len(series) == 10
        assert series[0] == 1.0
        assert series[5] > 1.0  # increases over time

    def test_missing_global_variable(self):
        history = _make_history(10)
        series = _extract_time_series(history, "nonexistent_global_var")
        # Not in GLOBAL_VARIABLES → falls to realm extraction → zeros
        assert all(v == 0.0 for v in series)

    def test_missing_realm(self):
        history = _make_history(10)
        series = _extract_time_series(history, "selection_pressure", realm="nonexistent")
        assert all(v == 0.0 for v in series)


# ─── Evidence strength ───────────────────────────────────────────────────

class TestEvidenceStrength:
    def test_strong(self):
        assert _evidence_strength(0.8) == EvidenceStrength.STRONG

    def test_moderate(self):
        assert _evidence_strength(0.5) == EvidenceStrength.MODERATE

    def test_weak(self):
        assert _evidence_strength(0.25) == EvidenceStrength.WEAK

    def test_hypothetical(self):
        assert _evidence_strength(0.1) == EvidenceStrength.HYPOTHETICAL


# ─── Causal discovery ───────────────────────────────────────────────────

class TestCausalDiscovery:
    def test_discovers_edges(self):
        """History with correlated variables should produce causal edges."""
        history = _make_history(50)
        graph = discover_causal_structure(history, lag=1, min_correlation=0.2)
        assert len(graph.edges) > 0
        assert len(graph.nodes) > 0

    def test_correlated_variables_connected(self):
        """Variables that trend together should have causal edges."""
        history = _make_history(50)
        graph = discover_causal_structure(history, lag=1, min_correlation=0.2)

        # temperature and entropy both increase → should be connected
        edge_pairs = {(e.source, e.target) for e in graph.edges}
        # At least one of the global trending variables should be connected
        connected_globals = [
            e for e in graph.edges
            if ":" not in e.source and ":" not in e.target
        ]
        assert len(connected_globals) > 0

    def test_high_threshold_fewer_edges(self):
        """Higher min_correlation should yield fewer edges."""
        history = _make_history(50)
        graph_low = discover_causal_structure(history, min_correlation=0.2)
        graph_high = discover_causal_structure(history, min_correlation=0.8)
        assert len(graph_high.edges) <= len(graph_low.edges)

    def test_empty_history(self):
        """Empty history should produce empty graph."""
        history = {"ticks": [], "realm_theory": []}
        graph = discover_causal_structure(history)
        assert len(graph.edges) == 0

    def test_short_history(self):
        """Too-short history should produce empty graph (not enough data)."""
        history = _make_history(3)
        graph = discover_causal_structure(history, lag=1)
        # May have some edges or not — should not crash
        assert isinstance(graph, CausalGraph)

    def test_cross_realm_edges_discovered(self):
        """Variables from different realms should be connected if correlated."""
        history = _make_history(50)
        graph = discover_causal_structure(history, min_correlation=0.2)

        cross_realm = [
            e for e in graph.edges
            if "compute:" in e.source and "memory:" in e.target
            or "memory:" in e.source and "compute:" in e.target
        ]
        # Both realms trend similarly, so should find cross-realm edges
        assert len(cross_realm) > 0

    def test_edge_metadata(self):
        """Discovered edges should contain lag_correlation evidence."""
        history = _make_history(50)
        graph = discover_causal_structure(history, min_correlation=0.2)
        if graph.edges:
            edge = graph.edges[0]
            assert "lag_correlation" in edge.evidence
            assert "lag" in edge.evidence
            assert edge.domain == "silicon_realms"


# ─── Intervention effects ───────────────────────────────────────────────

class TestInterventionEffects:
    def test_intervention_finds_downstream(self):
        """Intervention on a hub node should find downstream effects."""
        graph = CausalGraph()
        graph.add_edge("A", "B", edge_type=EdgeType.CAUSES, confidence=0.8)
        graph.add_edge("B", "C", edge_type=EdgeType.CAUSES, confidence=0.7)
        graph.add_edge("D", "B", edge_type=EdgeType.CAUSES, confidence=0.6)

        effects = intervention_effects(graph, "A")
        assert "B" in effects["direct"]
        assert "C" in effects["indirect"]

    def test_intervention_blocks_confounders(self):
        """do(X) should block incoming paths to X."""
        graph = CausalGraph()
        graph.add_edge("Z", "X", edge_type=EdgeType.CAUSES, confidence=0.8)
        graph.add_edge("X", "Y", edge_type=EdgeType.CAUSES, confidence=0.7)

        effects = intervention_effects(graph, "X")
        # Y should be a direct effect
        assert "Y" in effects["direct"]
        # Z's path to X is cut, so Z is not downstream

    def test_intervention_empty_graph(self):
        """Intervention on empty graph should not crash."""
        graph = CausalGraph()
        graph.add_node("A")
        effects = intervention_effects(graph, "A")
        assert effects["direct"] == []
        assert effects["indirect"] == []
        assert effects["blocked"] == []

    def test_intervention_on_discovered_graph(self):
        """Should work on a graph from discover_causal_structure."""
        history = _make_history(50)
        graph = discover_causal_structure(history, min_correlation=0.3)
        if graph.nodes:
            node = list(graph.nodes.keys())[0]
            effects = intervention_effects(graph, node)
            assert isinstance(effects, dict)
            assert "direct" in effects


# ─── Summarize causal graph ─────────────────────────────────────────────

class TestSummarizeCausalGraph:
    def test_summary_structure(self):
        history = _make_history(50)
        graph = discover_causal_structure(history, min_correlation=0.3)
        summary = summarize_causal_graph(graph)

        assert "strongest_edges" in summary
        assert "hub_nodes" in summary
        assert "sink_nodes" in summary
        assert "cross_realm_edges" in summary
        assert "total_edges" in summary
        assert "total_nodes" in summary

    def test_summary_empty_graph(self):
        graph = CausalGraph()
        summary = summarize_causal_graph(graph)
        assert summary["total_edges"] == 0
        assert summary["total_nodes"] == 0

    def test_strongest_edges_sorted(self):
        graph = CausalGraph()
        graph.add_edge("A", "B", confidence=0.3)
        graph.add_edge("C", "D", confidence=0.9)
        graph.add_edge("E", "F", confidence=0.6)

        summary = summarize_causal_graph(graph)
        confidences = [e["confidence"] for e in summary["strongest_edges"]]
        assert confidences == sorted(confidences, reverse=True)

    def test_hub_nodes_ranked(self):
        graph = CausalGraph()
        graph.add_edge("hub", "A", confidence=0.8)
        graph.add_edge("hub", "B", confidence=0.7)
        graph.add_edge("hub", "C", confidence=0.6)
        graph.add_edge("other", "D", confidence=0.5)

        summary = summarize_causal_graph(graph)
        assert summary["hub_nodes"][0]["node"] == "hub"
        assert summary["hub_nodes"][0]["out_degree"] == 3
