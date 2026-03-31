# Wasserstein Gradient Flow

**Domain:** Optimization

**Equation:** `∂ρ/∂t = ∇·(ρ∇(δF/δρ));  JKO: ρ_{k+1} = argmin[F(ρ) + W₂²(ρ,ρₖ)/2τ];  F(ρ) = ∫ρlogρ + ∫ρV + ∫∫ρWρ`

**Update Form:** jko_proximal_step

**Optimization:** minimize_free_energy_functional

**Fixed Points:** stationary_measure

## Patterns

- dual_variables
- energy_entropy_tradeoff
- energy_minimization
- gradient_descent
- variational_principle

## Operators

- continuity_equation
- functional_derivative
- gradient
- proximal_operator
- wasserstein_distance
