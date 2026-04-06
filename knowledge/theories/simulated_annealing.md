# Simulated Annealing

**Domain:** Optimization

**Equation:** `P(accept) = min(1, exp(−ΔE / T));  T(t) → 0;  π(x) ∝ exp(−E(x)/T)`

**Update Form:** metropolis_hastings

**Optimization:** global_minimum_energy

**Fixed Points:** ground_state_configuration

## Patterns

- energy_based
- energy_entropy_tradeoff
- energy_minimization
- exploration_exploitation
- gradient_descent
- phase_transition

## Operators

- acceptance
- cooling_schedule
- partition_function
- perturbation
- sampling
