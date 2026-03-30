# Multi-Armed Bandit / UCB

**Domain:** Reinforcement Learning

**Equation:** `UCB: a* = argmax[μ̂ₐ + c√(ln t / Nₐ)];  regret R_T = T μ* − Σ μ_{aₜ};  Thompson: sample θₐ ~ posterior, play argmax θₐ`

**Update Form:** index_policy_update

**Optimization:** minimize_cumulative_regret

**Fixed Points:** optimal_arm

## Patterns

- bayesian_inference
- energy_minimization
- exploration_exploitation
- information_gain
- optimal_inference

## Operators

- confidence_bound
- exploration_bonus
- posterior_update
- regret_decomposition
