# Neuromorphic Computing / Reservoir Computing

**Domain:** Neuroscience

**Equation:** `x(t+1) = (1−α)x(t) + αf(Wᵢₙu(t) + Wx(t));  y(t) = Wₒᵤₜx(t);  train only Wₒᵤₜ = argmin||Y−Wₒᵤₜ X||²`

**Update Form:** reservoir_state_update

**Optimization:** minimize_readout_error

**Fixed Points:** echo_state

## Patterns

- dimensionality_reduction
- echo_state_property
- edge_of_chaos
- feedback_loop
- information_gain
- temporal_processing

## Operators

- linear_combination
- matrix_multiply
- nonlinear_reaction
- regression
