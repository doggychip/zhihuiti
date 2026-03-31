# Temporal Difference Learning

**Domain:** Reinforcement Learning

**Equation:** `δ_t = r_t + γV(s_{t+1}) − V(s_t);  V(s_t) ← V(s_t) + αδ_t;  TD(λ): e_t = γλe_{t-1} + ∇V(s_t)`

**Update Form:** bootstrapped_value_update

**Optimization:** minimize_td_error

**Fixed Points:** value_function_fixed_point

## Patterns

- energy_minimization
- exploration_exploitation
- fixed_point_iteration
- gradient_descent
- prediction_error

## Operators

- bellman_operator
- bootstrapping
- eligibility_trace
- gradient
- temporal_difference
