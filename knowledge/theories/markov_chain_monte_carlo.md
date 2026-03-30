# Markov Chain Monte Carlo

**Domain:** Statistics

**Equation:** `π(x') T(x'→x) = π(x) T(x→x');  α = min(1, π(x')q(x|x')/π(x)q(x'|x));  x ~ π as t→∞`

**Update Form:** metropolis_hastings

**Fixed Points:** target_distribution_samples

## Patterns

- conservation_of_probability
- energy_based
- energy_entropy_tradeoff
- exploration_exploitation
- fixed_point_stability
- phase_transition

## Operators

- acceptance
- detailed_balance
- mixing_time
- proposal
- sampling
