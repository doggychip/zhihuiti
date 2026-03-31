# Network Embedding / Node2Vec

**Domain:** Network Science

**Equation:** `max Σᵢ log P(N(i) | zᵢ);  P(j|i) = exp(zᵢᵀzⱼ) / Σₖ exp(zᵢᵀzₖ)`

**Update Form:** skip_gram_on_graph

**Optimization:** maximize_likelihood

**Fixed Points:** embedding_convergence

## Patterns

- dimensionality_reduction
- energy_minimization
- exploration_exploitation
- information_gain
- random_walk
- stochastic_dynamics

## Operators

- gradient
- random_walk
- softmax
- stochastic_integral
