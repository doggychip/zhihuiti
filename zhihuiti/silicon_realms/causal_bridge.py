"""
Causal Bridge — Connects Silicon Realms simulation to zhihuiti's causal engine.

Two directions of flow:

  1. Discovery (simulation → causal graph):
     Observe simulation history, detect statistical dependencies between
     realm variables, and encode them as causal edges in a CausalGraph.
     Uses Granger-style lag-correlation to infer causality from time series.

  2. Intervention (causal graph → simulation):
     Use do-calculus to simulate counterfactual realm configurations.
     "What if we boosted compute's reward_modifier?"
     "What if Fisher information were clamped low?"

This bridges the theoretical simulation (silicon_realms) with the
production agent system (zhihuiti), enabling causal reasoning about
emergent economic dynamics.
"""
from __future__ import annotations

import math
from typing import Any

from zhihuiti.causal import CausalGraph, EdgeType, EvidenceStrength


# ─────────────────────────────────────────────────────────────────────────────
# 1. CAUSAL DISCOVERY — extract causal structure from simulation history
# ─────────────────────────────────────────────────────────────────────────────

# Variables we track for causal discovery
REALM_VARIABLES = [
    "selection_pressure",
    "realm_temperature",
    "realm_entropy",
    "knowledge_pool",
    "route_efficiency",
    "congestion",
    "channel_capacity",
    "noise_level",
    "mutual_information",
    "redundancy",
    "avalanche_exposure",
    "reward_modifier",
]

GLOBAL_VARIABLES = [
    "temperature",
    "entropy",
    "fisher_information",
    "kl_divergence",
    "total_supply",
    "gini",
]


def _lag_correlation(x: list[float], y: list[float], lag: int = 1) -> float:
    """
    Compute Pearson correlation between x[:-lag] and y[lag:].

    Positive lag-correlation from X→Y suggests X Granger-causes Y:
    past values of X predict current values of Y.
    """
    n = min(len(x), len(y)) - lag
    if n < 3:
        return 0.0

    x_lagged = x[:n]
    y_current = y[lag:lag + n]

    mx = sum(x_lagged) / n
    my = sum(y_current) / n

    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x_lagged, y_current))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x_lagged) + 1e-12)
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y_current) + 1e-12)

    return cov / (sx * sy)


def _extract_time_series(history: dict, variable: str,
                         realm: str | None = None) -> list[float]:
    """Extract a time series for a variable from simulation history."""
    if variable in GLOBAL_VARIABLES:
        return history.get(variable, [])

    # Realm-level variable: extract from realm_theory snapshots
    series = []
    for snapshot in history.get("realm_theory", []):
        if realm and realm in snapshot:
            series.append(snapshot[realm].get(variable, 0.0))
        else:
            series.append(0.0)
    return series


def _evidence_strength(corr: float) -> EvidenceStrength:
    """Map correlation magnitude to evidence strength."""
    abs_corr = abs(corr)
    if abs_corr >= 0.7:
        return EvidenceStrength.STRONG
    elif abs_corr >= 0.4:
        return EvidenceStrength.MODERATE
    elif abs_corr >= 0.2:
        return EvidenceStrength.WEAK
    return EvidenceStrength.HYPOTHETICAL


def discover_causal_structure(
    history: dict,
    lag: int = 1,
    min_correlation: float = 0.2,
) -> CausalGraph:
    """
    Discover causal structure from simulation history using lag-correlation.

    For each pair of variables (X, Y), computes corr(X[t-lag], Y[t]).
    If |corr| >= min_correlation, we add a causal edge X → Y.

    Returns a CausalGraph populated with discovered relationships.

    Args:
        history: The history dict from engine.run()
        lag: Time lag for Granger-style causality (default 1 tick)
        min_correlation: Minimum |correlation| to register an edge
    """
    graph = CausalGraph()
    realm_names = list(history.get("realm_theory", [{}])[0].keys()) if history.get("realm_theory") else []

    # Build all variable names (global + per-realm)
    all_vars: list[tuple[str, str | None]] = []  # (variable, realm_or_None)

    for var in GLOBAL_VARIABLES:
        all_vars.append((var, None))

    for realm in realm_names:
        for var in REALM_VARIABLES:
            all_vars.append((var, realm))

    # Extract all time series
    series_cache: dict[str, list[float]] = {}
    for var, realm in all_vars:
        key = f"{realm}:{var}" if realm else var
        series_cache[key] = _extract_time_series(history, var, realm)
        # Register as node
        domain = f"realm:{realm}" if realm else "global"
        graph.add_node(key, description=f"{var} in {realm or 'global'}", domain=domain)

    # Test all pairs for lag-correlation
    keys = list(series_cache.keys())
    for i, source_key in enumerate(keys):
        source_series = series_cache[source_key]
        if len(source_series) < lag + 3:
            continue

        for target_key in keys[i + 1:]:
            target_series = series_cache[target_key]
            if len(target_series) < lag + 3:
                continue

            # Test X → Y
            corr_xy = _lag_correlation(source_series, target_series, lag)
            if abs(corr_xy) >= min_correlation:
                edge_type = EdgeType.CAUSES if corr_xy > 0 else EdgeType.PREVENTS
                graph.add_edge(
                    source_key, target_key,
                    edge_type=edge_type,
                    strength=_evidence_strength(corr_xy),
                    confidence=abs(corr_xy),
                    evidence={"lag_correlation": corr_xy, "lag": lag},
                    domain="silicon_realms",
                )

            # Test Y → X
            corr_yx = _lag_correlation(target_series, source_series, lag)
            if abs(corr_yx) >= min_correlation:
                edge_type = EdgeType.CAUSES if corr_yx > 0 else EdgeType.PREVENTS
                graph.add_edge(
                    target_key, source_key,
                    edge_type=edge_type,
                    strength=_evidence_strength(corr_yx),
                    confidence=abs(corr_yx),
                    evidence={"lag_correlation": corr_yx, "lag": lag},
                    domain="silicon_realms",
                )

    return graph


# ─────────────────────────────────────────────────────────────────────────────
# 2. CAUSAL INTERVENTION — use do-calculus on simulation dynamics
# ─────────────────────────────────────────────────────────────────────────────

def intervention_effects(
    graph: CausalGraph,
    variable: str,
    value: Any = None,
) -> dict[str, list[str]]:
    """
    Simulate do(variable=value) and return predicted downstream effects.

    Uses the causal graph to identify:
      - direct_effects: variables immediately caused by the intervention
      - indirect_effects: variables reached through causal chains
      - blocked: variables that were connected but are now d-separated

    Returns:
        {"direct": [...], "indirect": [...], "blocked": [...]}
    """
    # Mutilated graph (incoming edges to variable removed)
    mutilated = graph.do_intervention(variable, value)

    # Find all downstream effects via BFS from intervention variable
    direct = []
    indirect = []
    visited = set()
    queue = [(variable, 0)]  # (node, depth)

    while queue:
        node, depth = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)

        for edge in mutilated._adjacency.get(node, []):
            target = edge.target
            if target not in visited:
                if depth == 0:
                    direct.append(target)
                else:
                    indirect.append(target)
                queue.append((target, depth + 1))

    # Blocked: nodes that had paths in original but not in mutilated
    original_reachable = set()
    queue_orig = [variable]
    visited_orig = set()
    while queue_orig:
        node = queue_orig.pop(0)
        if node in visited_orig:
            continue
        visited_orig.add(node)
        for edge in graph._adjacency.get(node, []):
            if edge.target not in visited_orig:
                original_reachable.add(edge.target)
                queue_orig.append(edge.target)

    blocked = [n for n in original_reachable if n not in visited and n != variable]

    return {"direct": direct, "indirect": indirect, "blocked": blocked}


def summarize_causal_graph(graph: CausalGraph) -> dict:
    """
    Return a summary of the discovered causal structure.

    Useful for understanding which dynamics drive the simulation:
    - strongest_edges: top edges by confidence
    - hub_nodes: nodes with most outgoing causal edges (key drivers)
    - sink_nodes: nodes with most incoming edges (key outcomes)
    - cross_realm_edges: edges connecting different realms
    """
    if not graph.edges:
        return {"strongest_edges": [], "hub_nodes": [], "sink_nodes": [],
                "cross_realm_edges": [], "total_edges": 0, "total_nodes": 0}

    # Top edges
    sorted_edges = sorted(graph.edges, key=lambda e: -e.confidence)
    strongest = [
        {"source": e.source, "target": e.target, "type": e.edge_type.value,
         "confidence": round(e.confidence, 3)}
        for e in sorted_edges[:10]
    ]

    # Hub analysis
    out_degree: dict[str, int] = {}
    in_degree: dict[str, int] = {}
    for edge in graph.edges:
        out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    hubs = sorted(out_degree.items(), key=lambda x: -x[1])[:5]
    sinks = sorted(in_degree.items(), key=lambda x: -x[1])[:5]

    # Cross-realm edges
    cross_realm = []
    for edge in sorted_edges:
        src_domain = graph.nodes.get(edge.source, CausalGraph()).domain if hasattr(graph.nodes.get(edge.source), 'domain') else ""
        tgt_domain = graph.nodes.get(edge.target, CausalGraph()).domain if hasattr(graph.nodes.get(edge.target), 'domain') else ""
        src_node = graph.nodes.get(edge.source)
        tgt_node = graph.nodes.get(edge.target)
        if src_node and tgt_node and src_node.domain != tgt_node.domain:
            cross_realm.append({
                "source": edge.source, "target": edge.target,
                "confidence": round(edge.confidence, 3),
            })

    return {
        "strongest_edges": strongest,
        "hub_nodes": [{"node": n, "out_degree": d} for n, d in hubs],
        "sink_nodes": [{"node": n, "in_degree": d} for n, d in sinks],
        "cross_realm_edges": cross_realm[:10],
        "total_edges": len(graph.edges),
        "total_nodes": len(graph.nodes),
    }
