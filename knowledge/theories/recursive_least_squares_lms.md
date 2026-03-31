# Recursive Least Squares / LMS

**Domain:** Signal Processing

**Equation:** `θ̂_n = θ̂_{n-1} + K_n(y_n − φ_nᵀθ̂_{n-1});  K_n = P_{n-1}φ_n/(1+φ_nᵀP_{n-1}φ_n);  P_n = (I−K_nφ_nᵀ)P_{n-1};  LMS: θ̂ += μeφ`

**Update Form:** recursive_parameter_update

**Optimization:** minimize_prediction_error

**Fixed Points:** least_squares_estimate

## Patterns

- bayesian_inference
- energy_minimization
- fixed_point_iteration
- gradient_descent
- information_gain

## Operators

- covariance_update
- forgetting_factor
- kalman_gain
- prediction_error
