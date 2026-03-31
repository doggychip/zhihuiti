# Relevance Vector Machine / Sparse Bayes

**Domain:** Machine Learning

**Equation:** `p(w|α) = Π N(wᵢ|0,αᵢ⁻¹);  marginal: p(t|α) = N(0, σ²I + ΦA⁻¹Φᵀ);  update αᵢ = γᵢ/μᵢ²;  prune if αᵢ→∞;  ARD prior`

**Update Form:** evidence_maximization

**Optimization:** maximize_marginal_likelihood

**Fixed Points:** sparse_posterior

## Patterns

- bayesian_inference
- energy_minimization
- fixed_point_iteration
- gradient_descent
- information_gain

## Operators

- automatic_relevance_determination
- evidence_procedure
- marginal_likelihood
- posterior_mean
- pruning
