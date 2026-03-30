# Variational Autoencoder (VAE)

**Domain:** Machine Learning

**Equation:** `ELBO = E_q[log p(x|z)] − KL(q(z|x) ‖ p(z));  q(z|x) = N(μ(x), σ²(x));  z = μ + σε`

**Update Form:** amortized_variational_inference

**Optimization:** maximize_ELBO

**Fixed Points:** learned_generative_model

## Patterns

- bayesian_inference
- energy_based
- energy_entropy_tradeoff
- gradient_descent
- information_gain
- optimal_inference
- variational_principle

## Operators

- decoder
- encoder
- expectation
- gradient
- kl_divergence
- sampling
