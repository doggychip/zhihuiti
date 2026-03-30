# Score Matching / Score Function

**Domain:** Machine Learning

**Equation:** `s_θ(x) ≈ ∇_x log p(x);  J(θ) = ½E_p[||s_θ − ∇log p||²] = E_p[½||s_θ||² + tr(∇s_θ)];  DSM: J = E[||s_θ(x̃) − ∇log p(x̃|x)||²]`

**Update Form:** score_network_training

**Optimization:** minimize_score_matching_loss

**Fixed Points:** learned_score_function

## Patterns

- energy_based
- energy_minimization
- gradient_descent
- information_gain
- variational_principle

## Operators

- denoising
- gradient
- langevin_sampling
- noise_perturbation
- trace_of_jacobian
