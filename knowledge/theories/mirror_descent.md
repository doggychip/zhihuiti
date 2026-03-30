# Mirror Descent

**Domain:** Optimization

**Equation:** `∇φ(x_{t+1}) = ∇φ(x_t) − η∇f(x_t);  x_{t+1} = argmin{η⟨∇f,x⟩ + D_φ(x,x_t)};  D_φ = Bregman divergence`

**Update Form:** bregman_proximal

**Optimization:** minimize_loss_in_dual

**Fixed Points:** constrained_optimum

## Patterns

- dual_variables
- energy_minimization
- gradient_descent
- information_gain
- structural_isomorphism
- variational_principle

## Operators

- bregman_divergence
- convex_conjugate
- dual_map
- gradient
- projection
