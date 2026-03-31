# Constraint Satisfaction / SAT

**Domain:** Optimization

**Equation:** `Find x: ∧ᵢ Cᵢ(x) = true;  E(x) = Σᵢ (1−Cᵢ(x));  α_c: phase transition at clause/variable ratio`

**Update Form:** constraint_propagation

**Optimization:** minimize_violated_constraints

**Fixed Points:** satisfying_assignment

## Patterns

- energy_based
- energy_minimization
- exploration_exploitation
- fixed_point_iteration
- mean_field
- phase_transition

## Operators

- backtracking
- random_restart
- survey_propagation
- unit_propagation
