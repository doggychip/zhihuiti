# Kalman Filter

**Domain:** Control Theory

**Equation:** `x̂ = x̂⁻ + K(y − Cx̂⁻);  K = P⁻Cᵀ(CP⁻Cᵀ+R)⁻¹`

**Update Form:** predict_then_correct

**Optimization:** minimize_mean_squared_error

**Fixed Points:** steady_state_riccati

## Patterns

- bayesian_inference
- hierarchical_estimation
- optimal_under_gaussian_noise
- precision_weighted_update
- prediction_error_correction
- recursive

## Operators

- bayes_rule
- covariance
- predict
- update
- weight_by_precision
