# Expectation Propagation (EP)

**Domain:** Machine Learning

**Equation:** `q(θ) = 1/Z Π f̃ᵢ(θ);  f̃ᵢ ← proj[q^\i · fᵢ] / q^\i;  proj = moment matching to exponential family;  q^\i = q/f̃ᵢ`

**Update Form:** moment_matching_iteration

**Optimization:** minimize_local_kl_divergence

**Fixed Points:** consistent_site_approximations

## Patterns

- bayesian_inference
- compositional_structure
- energy_minimization
- fixed_point_iteration
- information_gain
- mean_field

## Operators

- cavity_distribution
- exponential_family_projection
- moment_matching
- partition_function
