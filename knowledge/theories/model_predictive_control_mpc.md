# Model Predictive Control (MPC)

**Domain:** Control Theory

**Equation:** `u*₀:ₙ = argmin Σₖ [xₖᵀQxₖ + uₖᵀRuₖ] + xₙᵀPxₙ  s.t. xₖ₊₁=Axₖ+Buₖ, constraints`

**Update Form:** receding_horizon_optimization

**Optimization:** minimize_cost_over_horizon

**Fixed Points:** optimal_trajectory

## Patterns

- convex_optimization
- dual_variables
- energy_minimization
- feedback_loop
- receding_horizon
- variational_principle

## Operators

- gradient
- linear_combination
- matrix_multiply
- projection
