# Max Flow / Min Cut

**Domain:** Optimization

**Equation:** `max Σⱼ f(s,j);  s.t. f(u,v) ≤ c(u,v), Σ f(u,v) = Σ f(v,w);  max-flow = min-cut;  Ford-Fulkerson: augment along s-t paths`

**Update Form:** augmenting_path

**Optimization:** maximize_flow

**Fixed Points:** maximum_flow

## Patterns

- compositional_structure
- conservation_law
- dual_variables
- energy_minimization

## Operators

- augmenting_path
- capacity_constraint
- cut_capacity
- flow_conservation
- residual_graph
