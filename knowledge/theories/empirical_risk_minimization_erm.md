# Empirical Risk Minimization (ERM)

**Domain:** Machine Learning

**Equation:** `R̂(h) = 1/n Σ ℓ(h(xᵢ),yᵢ);  h* = argmin R̂(h);  R(h) ≤ R̂(h) + O(√(VC(H)/n));  structural risk: min R̂ + Ω(H)`

**Update Form:** loss_minimization

**Optimization:** minimize_empirical_risk

**Fixed Points:** risk_minimizer

## Patterns

- dual_variables
- energy_minimization
- gradient_descent
- information_gain
- variational_principle

## Operators

- generalization_bound
- gradient
- loss_function
- model_selection
- regularizer
