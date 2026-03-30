# Maximum a Posteriori (MAP) Estimation

**Domain:** Statistics

**Equation:** `θ_MAP = argmax p(θ|x) = argmax [log p(x|θ) + log p(θ)];  ∇log p(x|θ) + ∇log p(θ) = 0;  MAP → MLE as prior → flat`

**Update Form:** penalized_likelihood_gradient

**Optimization:** maximize_posterior

**Fixed Points:** posterior_mode

## Patterns

- bayesian_inference
- dual_variables
- energy_minimization
- gradient_descent
- optimal_inference
- variational_principle

## Operators

- gradient
- laplace_approximation
- posterior
- prior
- regularizer
