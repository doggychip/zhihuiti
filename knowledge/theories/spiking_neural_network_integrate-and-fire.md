# Spiking Neural Network / Integrate-and-Fire

**Domain:** Neuroscience

**Equation:** `τ dV/dt = −(V−V_rest) + R·I(t);  V≥V_th ⟹ spike, V←V_reset;  STDP: Δw = A+ exp(−Δt/τ+) if pre<post, else −A− exp(Δt/τ−)`

**Update Form:** spike_timing_plasticity

**Optimization:** minimize_prediction_error

**Fixed Points:** stable_firing_pattern

## Patterns

- conservation_law
- energy_based
- energy_minimization
- fixed_point_iteration
- pairwise_coupling
- population_dynamics

## Operators

- integration
- refractory_dynamics
- spike_response
- synaptic_update
- threshold
