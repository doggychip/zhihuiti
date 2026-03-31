# Kernel Methods / RKHS

**Domain:** Machine Learning

**Equation:** `k(x,x') = ⟨φ(x),φ(x')⟩_H;  f*(x) = Σᵢ αᵢk(xᵢ,x);  α = (K + λI)⁻¹y;  K = Mercer kernel matrix`

**Update Form:** kernel_ridge_regression

**Optimization:** minimize_regularized_loss_in_RKHS

**Fixed Points:** representer_theorem_solution

## Patterns

- compositional_structure
- dual_variables
- energy_minimization
- one_to_one_mapping
- structural_isomorphism
- variational_principle

## Operators

- eigenvalue_decomposition
- inner_product
- kernel_evaluation
- projection
- regularization
