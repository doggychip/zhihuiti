# Information Bottleneck

**Domain:** Information Theory

**Equation:** `min I(X;T) − β I(T;Y);  p(t|x) = p(t)/Z exp(−β Σ_y p(y|x) log p(y|x)/p(y|t))`

**Update Form:** iterative_blahut_arimoto

**Optimization:** minimize_compression_distortion

**Fixed Points:** optimal_compression_representation

## Patterns

- dual_variables
- energy_entropy_tradeoff
- information_gain
- optimal_inference
- phase_transition
- variational_principle

## Operators

- expectation
- kl_divergence
- lagrange_multiplier
- mutual_information
- rate_distortion
