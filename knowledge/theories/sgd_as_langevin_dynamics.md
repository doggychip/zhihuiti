# SGD as Langevin Dynamics

**Domain:** Optimization

**Equation:** `θ_{t+1} = θ_t − η∇L̃(θ_t);  ∇L̃ = ∇L + ε, ε ~ N(0, Σ/B);  θ(t) ~ exp(−L(θ)/η) as t→∞`

**Update Form:** noisy_gradient_descent

**Optimization:** minimize_loss

**Fixed Points:** flat_minima_basin

## Patterns

- energy_based
- energy_entropy_tradeoff
- energy_minimization
- exploration_exploitation
- gradient_descent
- phase_transition

## Operators

- diffusion
- drift
- gradient
- learning_rate_schedule
- sampling
