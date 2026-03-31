# No-Regret Learning / Multiplicative Weights

**Domain:** Game Theory

**Equation:** `wᵢ(t+1) = wᵢ(t)·exp(−η·ℓᵢ(t));  pᵢ(t) = wᵢ(t)/Σⱼwⱼ(t);  regret ≤ √(T ln N)`

**Update Form:** multiplicative_weight_update

**Optimization:** minimize_regret

**Fixed Points:** coarse_correlated_equilibrium

## Patterns

- convergence_to_equilibrium
- dual_variables
- energy_entropy_tradeoff
- exploration_exploitation
- game_theoretic_equilibrium
- information_gain
- multiplicative_update

## Operators

- exponential
- gradient
- normalize
- softmax
