# Link Prediction / Network Evolution

**Domain:** Network Science

**Equation:** `score(i,j) = |Γ(i) ∩ Γ(j)| / |Γ(i) ∪ Γ(j)|;  AA: Σₖ∈Γ(i)∩Γ(j) 1/log(kₖ)`

**Update Form:** similarity_scoring

**Optimization:** maximize_auc

**Fixed Points:** predicted_edge_set

## Patterns

- bayesian_updating
- exploration_exploitation
- information_gain
- null_model
- random_walk

## Operators

- comparison
- graph_adjacency
- normalize
- random_walk
