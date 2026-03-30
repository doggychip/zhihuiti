# Particle Filter / Sequential Monte Carlo

**Domain:** Statistics

**Equation:** `p(xₜ|y₁:ₜ) ≈ Σ wₜⁱ δ(xₜ−xₜⁱ);  wₜⁱ ∝ p(yₜ|xₜⁱ)p(xₜⁱ|xₜ₋₁ⁱ)/q(xₜⁱ);  resample when ESS < N/2;  N_eff = 1/Σ(wⁱ)²`

**Update Form:** importance_sampling_resampling

**Optimization:** approximate_posterior_filtering

**Fixed Points:** posterior_particle_cloud

## Patterns

- bayesian_inference
- energy_minimization
- exploration_exploitation
- information_gain
- population_dynamics

## Operators

- ess_monitoring
- importance_sampling
- proposal_distribution
- resampling
- weight_update
