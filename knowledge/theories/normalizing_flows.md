# Normalizing Flows

**Domain:** Machine Learning

**Equation:** `x = f(z), z ~ p_z;  log p_x(x) = log p_z(f⁻¹(x)) + log|det ∂f⁻¹/∂x|;  max Σ log p_x(xᵢ)`

**Update Form:** gradient_on_flow_parameters

**Optimization:** maximize_log_likelihood

**Fixed Points:** trained_invertible_map

## Patterns

- compositional_structure
- energy_minimization
- gradient_descent
- information_gain
- structural_isomorphism
- variational_principle

## Operators

- change_of_variables
- determinant
- gradient
- invertible_transform
- jacobian
