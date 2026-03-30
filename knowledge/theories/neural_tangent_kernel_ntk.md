# Neural Tangent Kernel (NTK)

**Domain:** Machine Learning

**Equation:** `Θ(x,x') = ⟨∇_θf(x),∇_θf(x')⟩;  df/dt = −Θ(X,X)(f(X)−Y);  Θ → Θ∞ as width→∞`

**Update Form:** kernel_gradient_flow

**Optimization:** minimize_squared_loss

**Fixed Points:** kernel_regression_solution

## Patterns

- dual_variables
- energy_minimization
- gradient_descent
- mean_field
- structural_isomorphism
- universality

## Operators

- eigenvalue_decomposition
- gradient
- infinite_width_limit
- inner_product
- kernel_evaluation
