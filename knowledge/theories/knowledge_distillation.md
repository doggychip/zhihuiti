# Knowledge Distillation

**Domain:** Machine Learning

**Equation:** `L = (1−α)H(y,σ(z_s)) + α T² KL(σ(z_t/T)||σ(z_s/T));  student: small model;  teacher: large model;  dark knowledge in soft labels`

**Update Form:** soft_label_training

**Optimization:** minimize_distillation_loss

**Fixed Points:** compressed_student

## Patterns

- energy_entropy_tradeoff
- energy_minimization
- gradient_descent
- information_gain
- pairwise_coupling

## Operators

- feature_matching
- gradient
- kl_divergence
- soft_targets
- temperature_scaling
