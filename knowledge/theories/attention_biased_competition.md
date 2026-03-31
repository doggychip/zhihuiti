# Attention / Biased Competition

**Domain:** Cognitive Science

**Equation:** `response(i) = Σⱼ w(i,j)·stimulus(j);  w(i,j) ∝ exp(−|i−j|²/2σ²)·top_down(j);  winner-take-all: normalize w`

**Update Form:** biased_competition

**Optimization:** maximize_information_gain

**Fixed Points:** attentional_selection

## Patterns

- competition_selection
- dimensionality_reduction
- feedback_loop
- information_gain
- signal_noise_separation
- winner_take_all

## Operators

- competition
- normalize
- softmax
- threshold
