# Differential Privacy

**Domain:** Computer Science

**Equation:** `P[M(D)∈S] ≤ e^ε P[M(D')∈S] + δ;  Laplace: noise ~ Lap(Δf/ε);  Gaussian: σ ≥ Δf√(2ln(1.25/δ))/ε;  composition: ε_total ~ ε√k;  Rényi DP: D_α(M(D)||M(D')) ≤ ε`

**Update Form:** noise_injection

**Optimization:** maximize_utility_under_privacy

**Fixed Points:** privacy_utility_pareto

## Patterns

- bayesian_inference
- conservation_law
- dual_variables
- energy_entropy_tradeoff
- information_gain

## Operators

- composition_theorem
- gaussian_mechanism
- laplace_mechanism
- sensitivity_analysis
- subsampling
