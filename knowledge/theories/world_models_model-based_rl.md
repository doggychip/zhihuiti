# World Models / Model-Based RL

**Domain:** Reinforcement Learning

**Equation:** `p̂(s'|s,a;θ);  r̂(s,a;φ);  plan: π* = argmax E_{p̂}[Σγᵗr̂];  Dyna: real experience + simulated rollouts;  model error: ||p̂−p||`

**Update Form:** model_learning_plus_planning

**Optimization:** minimize_model_error_and_policy_loss

**Fixed Points:** accurate_model_optimal_policy

## Patterns

- bayesian_inference
- compositional_structure
- energy_minimization
- exploration_exploitation
- gradient_descent

## Operators

- gradient
- planning
- reward_model
- rollout_simulation
- transition_model
