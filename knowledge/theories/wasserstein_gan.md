# Wasserstein GAN

**Domain:** Machine Learning

**Equation:** `min_G max_D E[D(x)] − E[D(G(z))];  W(p,q) = sup_{||D||_L≤1} E_p[D] − E_q[D];  Kantorovich-Rubinstein duality`

**Update Form:** alternating_gradient

**Optimization:** minimax_wasserstein

**Fixed Points:** generator_matches_data

## Patterns

- competitive_dynamics
- dual_variables
- energy_minimization
- exploration_exploitation
- gradient_descent
- variational_principle

## Operators

- dual_potential
- gradient
- lipschitz_constraint
- pushforward_map
- wasserstein_distance
