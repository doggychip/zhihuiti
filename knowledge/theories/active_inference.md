# Active Inference

**Domain:** Neuroscience

**Equation:** `F = E_q[log q(s) − log p(o,s)];  π* = argmin E_q(π)[G(π)];  G = E[H[P(o|s)] + D_KL[q(s|π)||p(s)]];  action = −∂F/∂a`

**Update Form:** free_energy_minimization

**Optimization:** minimize_expected_free_energy

**Fixed Points:** preferred_observations

## Patterns

- bayesian_inference
- energy_entropy_tradeoff
- energy_minimization
- exploration_exploitation
- information_gain
- variational_principle

## Operators

- belief_update
- gradient
- policy_selection
- precision_weighting
- variational_inference
