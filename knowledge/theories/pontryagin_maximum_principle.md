# Pontryagin Maximum Principle

**Domain:** Control Theory

**Equation:** `H(x,u,λ) = L(x,u) + λ^T f(x,u);  u* = argmax H;  ẋ = ∂H/∂λ, λ̇ = −∂H/∂x;  λ(T) = ∂Φ/∂x(T)`

**Update Form:** hamiltonian_two_point_boundary

**Optimization:** maximize_hamiltonian

**Fixed Points:** optimal_costate_trajectory

## Patterns

- dual_variables
- energy_minimization
- fixed_point_iteration
- gradient_descent
- variational_principle

## Operators

- bang_bang_control
- costate
- hamiltonian
- switching_function
- transversality
