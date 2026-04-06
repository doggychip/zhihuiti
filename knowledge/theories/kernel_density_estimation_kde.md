# Kernel Density Estimation (KDE)

**Domain:** Statistics

**Equation:** `f̂(x) = 1/(nh) Σ K((x−xᵢ)/h);  MISE = ∫(f̂−f)² ≈ 1/(nh)∫K² + h⁴/4(∫K''²)(∫f''²);  h* ∝ n^{-1/5};  AMISE optimal`

**Update Form:** bandwidth_selection

**Optimization:** minimize_integrated_squared_error

**Fixed Points:** optimal_bandwidth_density

## Patterns

- energy_minimization
- information_gain
- pairwise_coupling
- variational_principle

## Operators

- bandwidth_selection
- bias_variance_tradeoff
- cross_validation
- kernel_smoothing
