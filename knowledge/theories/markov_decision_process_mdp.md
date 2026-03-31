# Markov Decision Process (MDP)

**Domain:** Reinforcement Learning

**Equation:** `V*(s) = max_a [R(s,a) + γ Σ P(s'|s,a)V*(s')];  π*(s) = argmax_a Q*(s,a);  Q*(s,a) = R + γ Σ P V*`

**Update Form:** bellman_optimality

**Optimization:** maximize_discounted_return

**Fixed Points:** optimal_value_and_policy

## Patterns

- compositional_structure
- dual_variables
- energy_minimization
- exploration_exploitation
- fixed_point_iteration

## Operators

- bellman_operator
- contraction
- policy_evaluation
- policy_improvement
- transition_kernel
