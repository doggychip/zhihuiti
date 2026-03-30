# Stochastic Optimal Control

**Domain:** Control Theory

**Equation:** `dx = f(x,u)dt + σ(x)dW;  J = E[∫L(x,u)dt + Φ(x_T)];  −∂V/∂t = min_u{L + f·∇V + ½σσᵀ:∇²V}`

**Update Form:** stochastic_hjb

**Optimization:** minimize_expected_cost

**Fixed Points:** optimal_stochastic_policy

## Patterns

- dual_variables
- energy_entropy_tradeoff
- energy_minimization
- exploration_exploitation
- gradient_descent
- variational_principle

## Operators

- bellman_operator
- fokker_planck_adjoint
- hamiltonian
- ito_calculus
- stochastic_gradient
