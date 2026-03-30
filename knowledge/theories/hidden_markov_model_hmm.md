# Hidden Markov Model (HMM)

**Domain:** Machine Learning

**Equation:** `P(O,S) = π_{s1} Π P(sₜ|sₜ₋₁) Π P(oₜ|sₜ);  forward: α_t(j) = Σᵢ α_{t-1}(i)aᵢⱼbⱼ(oₜ);  Baum-Welch = EM on HMM`

**Update Form:** forward_backward_em

**Optimization:** maximize_observation_likelihood

**Fixed Points:** learned_transition_emission

## Patterns

- bayesian_inference
- compositional_structure
- energy_minimization
- fixed_point_iteration
- information_gain

## Operators

- backward_algorithm
- baum_welch
- forward_algorithm
- transition_matrix
- viterbi_decoding
