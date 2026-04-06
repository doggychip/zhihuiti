# Kalman Filter / State Estimation

**Domain:** Signal Processing

**Equation:** `x̂ₖ|ₖ = x̂ₖ|ₖ₋₁ + Kₖ(yₖ − Hx̂ₖ|ₖ₋₁);  Kₖ = Pₖ|ₖ₋₁Hᵀ(HPₖ|ₖ₋₁Hᵀ+R)⁻¹`

**Update Form:** bayesian_state_update

**Optimization:** minimize_estimation_error

**Fixed Points:** steady_state_kalman_gain

## Patterns

- bayesian_updating
- dual_variables
- energy_minimization
- fixed_point_iteration
- information_gain
- lyapunov_stability
- signal_noise_separation

## Operators

- conditional_expectation
- covariance
- linear_combination
- matrix_multiply
- projection
