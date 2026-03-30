# Natural Gradient Descent

**Domain:** Optimization

**Equation:** `θ_{t+1} = θ_t − η F(θ)⁻¹ ∇L(θ);  F(θ)ᵢⱼ = E[(∂log p/∂θᵢ)(∂log p/∂θⱼ)]`

**Update Form:** precision_weighted_gradient

**Optimization:** minimize_loss_on_manifold

**Fixed Points:** fisher_efficient_optimum

## Patterns

- energy_minimization
- gradient_descent
- information_gain
- multiplicative_update
- optimal_inference
- precision_weighted_update

## Operators

- expectation
- fisher_information_matrix
- gradient
- matrix_inverse
