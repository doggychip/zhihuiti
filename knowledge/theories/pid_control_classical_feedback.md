# PID Control / Classical Feedback

**Domain:** Control Theory

**Equation:** `u(t) = Kₚe(t) + Kᵢ∫e(τ)dτ + K_d de/dt;  transfer: C(s) = Kₚ + Kᵢ/s + K_ds`

**Update Form:** proportional_integral_derivative

**Optimization:** minimize_tracking_error

**Fixed Points:** zero_steady_state_error

## Patterns

- convergence_to_equilibrium
- feedback_loop
- integral_control
- linear_response
- lyapunov_stability

## Operators

- derivative
- feedback_loop
- integration
- linear_combination
