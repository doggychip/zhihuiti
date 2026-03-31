# Disentangled Representations / β-VAE

**Domain:** Machine Learning

**Equation:** `L = E_q[log p(x|z)] − β D_KL(q(z|x)||p(z));  disentanglement: z_i ⊥ z_j;  DCI metric;  β>1 → more disentangled, less reconstruction`

**Update Form:** regularized_variational

**Optimization:** maximize_disentangled_elbo

**Fixed Points:** disentangled_latent_space

## Patterns

- bayesian_inference
- energy_entropy_tradeoff
- energy_minimization
- gradient_descent
- information_gain
- variational_principle

## Operators

- decoder
- encoder
- information_bottleneck
- kl_divergence
- reparameterization
