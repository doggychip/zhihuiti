# Community Detection / Modularity

**Domain:** Network Science

**Equation:** `Q = 1/(2m) Σ [Aᵢⱼ − kᵢkⱼ/(2m)] δ(cᵢ,cⱼ);  SBM: P(Aᵢⱼ=1) = p if cᵢ=cⱼ, q otherwise;  detection threshold: (p−q)²/[2(p+q)] = log n`

**Update Form:** modularity_optimization

**Optimization:** maximize_modularity

**Fixed Points:** optimal_partition

## Patterns

- energy_minimization
- mean_field
- pairwise_coupling
- structural_isomorphism
- symmetry_breaking

## Operators

- likelihood_ratio
- louvain_merge
- modularity_matrix
- spectral_bisection
