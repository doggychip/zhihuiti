# Lagrange Duality / KKT Conditions

**Domain:** Optimization

**Equation:** `L(x,λ,ν) = f(x) + Σλᵢgᵢ(x) + Σνⱼhⱼ(x);  d* = max_{λ≥0} min_x L;  strong duality: p*=d*;  KKT: ∇f + Σλᵢ∇gᵢ = 0, λᵢgᵢ = 0`

**Update Form:** primal_dual_iteration

**Optimization:** saddle_point_of_lagrangian

**Fixed Points:** kkt_point

## Patterns

- dual_variables
- energy_minimization
- fixed_point_iteration
- gradient_descent
- variational_principle

## Operators

- barrier_function
- complementary_slackness
- dual_ascent
- gradient
- lagrangian
