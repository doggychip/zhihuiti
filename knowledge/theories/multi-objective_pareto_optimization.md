# Multi-Objective / Pareto Optimization

**Domain:** Optimization

**Equation:** `min (f₁(x),...,fₖ(x));  Pareto: x* if ∄x: fᵢ(x)≤fᵢ(x*) ∀i, strict for some;  scalarization: min Σλᵢfᵢ(x);  ε-constraint`

**Update Form:** pareto_front_construction

**Optimization:** find_pareto_front

**Fixed Points:** pareto_optimal_set

## Patterns

- competitive_dynamics
- dual_variables
- energy_minimization
- exploration_exploitation
- variational_principle

## Operators

- dominance_check
- gradient
- hypervolume_indicator
- scalarization
- weighted_sum
