# Stein Variational Gradient Descent (SVGD)

**Domain:** Machine Learning

**Equation:** `xᵢ ← xᵢ + ε φ*(xᵢ);  φ* = argmax_{||φ||≤1} −d/dε KL(T_ε q || p);  φ*(x) = E_q[k(x',x)∇log p(x') + ∇_{x'}k(x',x)]`

**Update Form:** kernel_gradient_transport

**Optimization:** minimize_kl_divergence

**Fixed Points:** posterior_particle_approximation

## Patterns

- bayesian_inference
- energy_entropy_tradeoff
- energy_minimization
- gradient_descent
- pairwise_coupling
- variational_principle

## Operators

- functional_gradient
- gradient
- kernel_evaluation
- repulsive_force
- stein_operator
