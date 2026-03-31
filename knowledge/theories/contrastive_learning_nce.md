# Contrastive Learning / NCE

**Domain:** Machine Learning

**Equation:** `L = −log[exp(sim(z_i,z_j)/τ) / Σ_k exp(sim(z_i,z_k)/τ)];  p(d=1|x,c) = σ(f(x)ᵀf(c));  NCE → MLE as k→∞`

**Update Form:** contrastive_gradient

**Optimization:** maximize_mutual_information_bound

**Fixed Points:** aligned_representation

## Patterns

- energy_based
- energy_entropy_tradeoff
- energy_minimization
- gradient_descent
- information_gain
- pairwise_coupling

## Operators

- gradient
- inner_product
- negative_sampling
- projection
- temperature_scaling
