# Frank-Wolfe / Conditional Gradient

**Domain:** Optimization

**Equation:** `s_t = argmin_{s∈C} ⟨∇f(x_t), s⟩;  x_{t+1} = x_t + γ_t(s_t − x_t);  gap_t = ⟨∇f(x_t), x_t−s_t⟩;  f(x_t)−f* ≤ O(1/t)`

**Update Form:** linear_minimization_oracle

**Optimization:** minimize_over_convex_set

**Fixed Points:** constrained_optimum

## Patterns

- dual_variables
- energy_minimization
- fixed_point_iteration
- gradient_descent
- variational_principle

## Operators

- away_step
- convex_combination
- duality_gap
- gradient
- linear_minimization
