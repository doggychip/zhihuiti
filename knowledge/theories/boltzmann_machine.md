# Boltzmann Machine

**Domain:** Machine Learning

**Equation:** `P(v) = Σ_h exp(−E(v,h))/Z;  E(v,h) = −v^TWh − b^Tv − c^Th;  ΔW = ⟨vh^T⟩_data − ⟨vh^T⟩_model`

**Update Form:** contrastive_divergence

**Optimization:** maximize_log_likelihood

**Fixed Points:** thermal_equilibrium_distribution

## Patterns

- bayesian_inference
- correlation_learning
- energy_based
- energy_entropy_tradeoff
- energy_minimization
- mean_field
- pairwise_coupling
- phase_transition

## Operators

- expectation
- gradient
- pairwise_interaction
- partition_function
- sampling
