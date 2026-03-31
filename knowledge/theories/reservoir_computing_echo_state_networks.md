# Reservoir Computing / Echo State Networks

**Domain:** Dynamic Systems

**Equation:** `h(t+1) = tanh(W_in x(t) + W h(t));  y(t) = W_out h(t);  W_out = argmin ‖Y − W_out H‖²`

**Update Form:** driven_recurrent_dynamics

**Optimization:** minimize_readout_error

**Fixed Points:** echo_state_property

## Patterns

- correlation_learning
- energy_minimization
- fixed_point_stability
- information_gain
- phase_transition

## Operators

- nonlinear_activation
- projection
- recurrence
- ridge_regression
- spectral_radius
