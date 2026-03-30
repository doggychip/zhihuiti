# Optimal Stopping / Secretary Problem

**Domain:** Statistics

**Equation:** `V(x,t) = max{g(x,t), E[V(X_{t+1},t+1)|X_t=x]};  τ* = inf{t: V(X_t,t) = g(X_t,t)};  secretary: reject first n/e, pick next best`

**Update Form:** backward_induction

**Optimization:** maximize_expected_payoff

**Fixed Points:** optimal_stopping_boundary

## Patterns

- dual_variables
- energy_minimization
- exploration_exploitation
- fixed_point_iteration

## Operators

- bellman_operator
- conditional_expectation
- snell_envelope
- stopping_boundary
