# Diffusion Maps

**Domain:** Machine Learning

**Equation:** `P = D⁻¹W;  Pᵗ → diffusion at scale t;  Ψ_t(x) = (λ₁ᵗψ₁(x),...,λₖᵗψₖ(x));  D_t²(x,y) = Σ λᵢ²ᵗ(ψᵢ(x)−ψᵢ(y))²`

**Update Form:** markov_chain_embedding

**Optimization:** preserve_diffusion_distance

**Fixed Points:** spectral_embedding

## Patterns

- energy_minimization
- fixed_point_iteration
- pairwise_coupling
- renormalization
- structural_isomorphism

## Operators

- diffusion_kernel
- eigendecomposition
- markov_normalization
- multiscale_geometry
