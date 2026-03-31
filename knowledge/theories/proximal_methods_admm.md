# Proximal Methods / ADMM

**Domain:** Optimization

**Equation:** `prox_f(x) = argmin[f(y) + ½||y−x||²];  ADMM: x←argmin[f(x)+ρ/2||Ax+Bz−c+u||²], z←argmin[g(z)+ρ/2||Ax+Bz−c+u||²], u←u+Ax+Bz−c`

**Update Form:** proximal_splitting

**Optimization:** minimize_composite_objective

**Fixed Points:** consensus_solution

## Patterns

- compositional_structure
- dual_variables
- energy_minimization
- fixed_point_iteration
- gradient_descent

## Operators

- augmented_lagrangian
- contraction
- operator_splitting
- projection
- proximal_operator
