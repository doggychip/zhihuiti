# Value-at-Risk / Conditional VaR

**Domain:** Economics

**Equation:** `VaR_α = inf{x : P(L > x) ≤ 1−α};  CVaR_α = E[L | L ≥ VaR_α]`

**Update Form:** tail_risk_quantile

**Optimization:** minimize_tail_risk

**Fixed Points:** risk_budget_equilibrium

## Patterns

- coherent_risk_measure
- convex_optimization
- dual_variables
- energy_minimization
- extreme_value_theory
- fat_tails
- subadditivity
- tail_risk

## Operators

- conditional_expectation
- expectation
- quantile
- tail_integral
