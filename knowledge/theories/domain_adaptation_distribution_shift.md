# Domain Adaptation / Distribution Shift

**Domain:** Machine Learning

**Equation:** `R_T(h) ≤ R_S(h) + d_H(S,T) + λ*;  importance weighting: E_T[ℓ] = E_S[w(x)ℓ], w=p_T/p_S;  DANN: min_θ max_d L_task − λL_domain`

**Update Form:** domain_adversarial_training

**Optimization:** minimize_target_risk

**Fixed Points:** domain_invariant_representation

## Patterns

- competitive_dynamics
- dual_variables
- energy_minimization
- gradient_descent
- information_gain

## Operators

- adversarial_alignment
- distribution_distance
- domain_discriminator
- gradient
- importance_weighting
