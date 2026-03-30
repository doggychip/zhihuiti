# Monte Carlo Tree Search (MCTS)

**Domain:** Reinforcement Learning

**Equation:** `UCB1: a* = argmax[Q(s,a) + c√(ln N(s)/N(s,a))];  V(s) = 1/N Σ R_i;  backup: N(s)+=1, Q(s,a) += (R−Q)/N`

**Update Form:** tree_backup

**Optimization:** maximize_expected_return

**Fixed Points:** optimal_action_values

## Patterns

- bayesian_inference
- compositional_structure
- energy_minimization
- exploration_exploitation
- gradient_descent

## Operators

- backpropagation
- expansion
- selection
- simulation
- ucb_bound
