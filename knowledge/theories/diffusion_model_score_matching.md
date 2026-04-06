# Diffusion Model (Score Matching)

**Domain:** Machine Learning

**Equation:** `q(xₜ|x₀) = N(√ᾱₜx₀, (1−ᾱₜ)I);  p_θ(x_{t-1}|xₜ) = N(μ_θ(xₜ,t), σ²I);  L = E‖ε − ε_θ(xₜ,t)‖²`

**Update Form:** iterative_denoising

**Optimization:** minimize_denoising_score_matching

**Fixed Points:** learned_data_distribution

## Patterns

- conservation_of_probability
- energy_based
- energy_entropy_tradeoff
- energy_minimization
- gradient_descent
- phase_transition
- variational_principle

## Operators

- diffusion
- drift
- gradient
- noise_schedule
- sampling
- score_function
