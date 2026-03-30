# Minimum Description Length (MDL)

**Domain:** Statistics

**Equation:** `M* = argmin [L(D|M) + L(M)];  two-part: L(x,θ) = −log p(x|θ) + L(θ);  normalized ML: p̄(x) = p(x|θ̂(x))/∫p(y|θ̂(y))dy`

**Update Form:** model_selection

**Optimization:** minimize_total_codelength

**Fixed Points:** optimal_model_complexity

## Patterns

- bayesian_inference
- compositional_structure
- dual_variables
- energy_minimization
- information_gain
- variational_principle

## Operators

- fisher_information
- parametric_complexity
- prefix_coding
- stochastic_complexity
- universal_model
