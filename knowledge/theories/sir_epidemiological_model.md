# SIR / Epidemiological Model

**Domain:** Biology

**Equation:** `dS/dt = −βSI;  dI/dt = βSI − γI;  dR/dt = γI;  R₀ = β/γ;  herd immunity: S < 1/R₀;  final size: 1−R∞ = e^{−R₀R∞}`

**Update Form:** compartmental_ode

**Optimization:** minimize_epidemic_size

**Fixed Points:** disease_free_equilibrium

## Patterns

- conservation_law
- energy_minimization
- fixed_point_iteration
- population_dynamics
- symmetry_breaking

## Operators

- basic_reproduction_number
- compartment_transition
- mass_action
- threshold_condition
