"""DAG utilities — topological sort into parallel waves, cycle detection."""

from __future__ import annotations

from collections import defaultdict, deque


def detect_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """Return a cycle path if one exists, otherwise None.

    graph: node_id -> [dependency_ids]
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = defaultdict(int)
    parent: dict[str, str | None] = {}

    def dfs(node: str) -> list[str] | None:
        colour[node] = GREY
        for dep in graph.get(node, []):
            if colour[dep] == GREY:
                # Back edge — reconstruct cycle
                path = [dep, node]
                cur = node
                while cur != dep:
                    cur = parent.get(cur, dep)
                    path.append(cur)
                return path
            if colour[dep] == WHITE:
                parent[dep] = node
                cycle = dfs(dep)
                if cycle:
                    return cycle
        colour[node] = BLACK
        return None

    for node in graph:
        if colour[node] == WHITE:
            cycle = dfs(node)
            if cycle:
                return cycle
    return None


def topological_waves(nodes: list[str], deps: dict[str, list[str]]) -> list[list[str]]:
    """Sort nodes into execution waves using Kahn's algorithm.

    Wave 0 contains nodes with no dependencies.
    Wave 1 contains nodes whose deps all appeared in wave 0.
    And so on.

    Returns list of waves, each wave being a list of node ids that can
    run in parallel.

    Raises ValueError if the graph has a cycle.
    """
    # Build adjacency + in-degree
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    successors: dict[str, list[str]] = defaultdict(list)

    for node in nodes:
        for dep in deps.get(node, []):
            if dep in in_degree:  # ignore unknown deps
                successors[dep].append(node)
                in_degree[node] += 1

    # Kahn's BFS, grouped into waves
    waves: list[list[str]] = []
    queue = deque(n for n, d in in_degree.items() if d == 0)

    visited = 0
    while queue:
        wave = list(queue)
        waves.append(wave)
        queue.clear()
        for node in wave:
            visited += 1
            for succ in successors[node]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

    if visited < len(nodes):
        raise ValueError("Dependency graph contains a cycle")

    return waves
