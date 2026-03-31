# Variational Inference (ELBO)

**Domain:** Machine Learning

**Equation:** `ELBO = E_q[log p(x,z)] − E_q[log q(z)] ≤ log p(x);  KL(q‖p) = log p(x) − ELBO`

**Update Form:** variational_optimization

**Optimization:** maximize_evidence_lower_bound

**Fixed Points:** approximate_posterior

## Patterns

- bayesian_inference
- energy_entropy_tradeoff
- information_gain
- precision_weighted_update
- prediction_error
- surprise_minimization
- variational_inference
- variational_principle

## Operators

- expectation
- gradient
- kl_divergence
- logarithm
- sampling
