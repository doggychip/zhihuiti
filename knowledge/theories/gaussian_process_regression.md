# Gaussian Process Regression

**Domain:** Machine Learning

**Equation:** `f ~ GP(μ,k);  p(f*|X*,X,y) = N(K*ᵀ(K+σ²I)⁻¹y, K**−K*ᵀ(K+σ²I)⁻¹K*);  log p(y|X) = −½yᵀK⁻¹y − ½log|K| − n/2 log 2π`

**Update Form:** posterior_conditioning

**Optimization:** maximize_marginal_likelihood

**Fixed Points:** posterior_predictive

## Patterns

- bayesian_inference
- energy_minimization
- information_gain
- optimal_inference
- pairwise_coupling
- variational_principle

## Operators

- cholesky
- kernel_evaluation
- marginal_likelihood
- matrix_inversion
- posterior_update
