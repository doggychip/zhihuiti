# Shortest Path / Dijkstra-Bellman-Ford

**Domain:** Computer Science

**Equation:** `d(v) = min_{u:(u,v)∈E} [d(u) + w(u,v)];  Dijkstra: greedy + priority queue O(E log V);  Bellman-Ford: relax all edges V−1 times;  Floyd: d[i][j] = min(d[i][j], d[i][k]+d[k][j])`

**Update Form:** relaxation_iteration

**Optimization:** minimize_path_cost

**Fixed Points:** shortest_path_tree

## Patterns

- compositional_structure
- conservation_law
- energy_minimization
- fixed_point_iteration

## Operators

- dynamic_programming
- edge_relaxation
- path_reconstruction
- priority_queue
