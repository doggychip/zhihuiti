# Gradient Boosting / AdaBoost

**Domain:** Machine Learning

**Equation:** `F_m(x) = F_{m-1}(x) + ν h_m(x);  h_m = argmin Σ L(yᵢ, F_{m-1}(xᵢ) + h(xᵢ));  wᵢ ∝ exp(−yᵢ F(xᵢ));  AdaBoost = exp loss`

**Update Form:** functional_gradient_descent

**Optimization:** minimize_empirical_loss

**Fixed Points:** converged_ensemble

## Patterns

- compositional_structure
- energy_minimization
- gradient_descent
- information_gain
- variational_principle

## Operators

- functional_gradient
- gradient
- regularizer
- reweighting
- weak_learner
