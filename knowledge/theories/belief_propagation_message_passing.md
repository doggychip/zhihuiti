# Belief Propagation / Message Passing

**Domain:** Machine Learning

**Equation:** `m_{i→j}(x_j) = Σ_{x_i} ψ(x_i,x_j) φ(x_i) Π_{k∈N(i)\j} m_{k→i}(x_i);  b(x_i) ∝ φ(x_i) Π_{j∈N(i)} m_{j→i}(x_i)`

**Update Form:** message_passing_fixed_point

**Optimization:** bethe_free_energy

**Fixed Points:** marginal_beliefs

## Patterns

- bayesian_inference
- compositional_structure
- energy_based
- fixed_point_iteration
- mean_field
- pairwise_coupling

## Operators

- bethe_approximation
- factor_graph
- marginalization
- message_update
- partition_function
