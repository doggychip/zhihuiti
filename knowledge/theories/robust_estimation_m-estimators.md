# Robust Estimation / M-Estimators

**Domain:** Statistics

**Equation:** `θ̂ = argmin Σ ρ(xᵢ−θ);  influence: IF(x;T,F) = lim [T((1−ε)F+εδ_x)−T(F)]/ε;  breakdown: ε* = max ε s.t. bounded;  Huber: ρ(x) = x²/2 if |x|≤k, k|x|−k²/2 else`

**Update Form:** iteratively_reweighted_least_squares

**Optimization:** minimize_robust_loss

**Fixed Points:** robust_location_estimate

## Patterns

- dual_variables
- energy_minimization
- fixed_point_iteration
- gradient_descent
- variational_principle

## Operators

- breakdown_point
- gradient
- huber_loss
- influence_function
- weight_function
