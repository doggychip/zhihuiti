# Policy Gradient (REINFORCE)

**Domain:** Machine Learning

**Equation:** `∇J(θ) = E_π[∇log π(a|s;θ) · (R − b)];  θ ← θ + α∇J(θ)`

**Update Form:** score_function_gradient

**Optimization:** maximize_expected_return

**Fixed Points:** locally_optimal_policy

## Patterns

- above_average_grows
- frequency_dependent
- gradient_descent
- information_gain
- multiplicative_update
- prediction_error
- selection

## Operators

- baseline_subtraction
- expectation
- gradient
- logarithm
- sampling
