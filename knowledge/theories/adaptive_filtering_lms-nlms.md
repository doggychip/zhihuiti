# Adaptive Filtering / LMS-NLMS

**Domain:** Signal Processing

**Equation:** `wₙ₊₁ = wₙ + μeₙxₙ/(xₙᵀxₙ+ε);  eₙ = dₙ − wₙᵀxₙ`

**Update Form:** stochastic_gradient_adaptation

**Optimization:** minimize_mse_online

**Fixed Points:** wiener_solution

## Patterns

- convergence_to_equilibrium
- energy_minimization
- exploration_exploitation
- gradient_flow
- signal_noise_separation
- stochastic_dynamics

## Operators

- gradient
- gradient_descent
- inner_product
- normalize
