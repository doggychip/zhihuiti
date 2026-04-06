# Markowitz Portfolio / Mean-Variance

**Domain:** Economics

**Equation:** `min wᵀΣw s.t. wᵀμ=r, wᵀ1=1;  efficient frontier: σ²(r) = a r² − 2br + c;  Sharpe: max (wᵀμ−r_f)/√(wᵀΣw);  CAPM: E[rᵢ]−r_f = βᵢ(E[r_m]−r_f)`

**Update Form:** mean_variance_optimization

**Optimization:** minimize_portfolio_variance

**Fixed Points:** efficient_portfolio

## Patterns

- dual_variables
- energy_minimization
- pairwise_coupling
- variational_principle

## Operators

- covariance_estimation
- lagrange_multiplier
- quadratic_programming
- risk_decomposition
