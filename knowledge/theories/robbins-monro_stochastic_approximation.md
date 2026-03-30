# Robbins-Monro / Stochastic Approximation

**Domain:** Optimization

**Equation:** `x_{n+1} = x_n − a_n(H(x_n) + ξ_n);  Σ aₙ = ∞, Σ aₙ² < ∞;  ODE method: dx/dt = −H(x);  x_n → x* a.s.`

**Update Form:** stochastic_recursion

**Optimization:** find_root_of_expectation

**Fixed Points:** root_of_mean_field

## Patterns

- convergence_guarantee
- energy_minimization
- fixed_point_iteration
- gradient_descent

## Operators

- martingale_difference
- ode_approximation
- step_size_schedule
- stochastic_gradient
