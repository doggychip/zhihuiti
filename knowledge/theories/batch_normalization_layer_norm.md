# Batch Normalization / Layer Norm

**Domain:** Machine Learning

**Equation:** `x̂ = (x−μ_B)/√(σ²_B+ε);  y = γx̂ + β;  μ_B = 1/m Σ xᵢ;  σ²_B = 1/m Σ(xᵢ−μ_B)²;  smooths loss landscape`

**Update Form:** normalize_then_scale

**Optimization:** stabilize_training

**Fixed Points:** trained_scale_shift

## Patterns

- conservation_law
- energy_minimization
- gradient_descent
- symmetry_breaking

## Operators

- affine_transform
- gradient
- normalization
- running_statistics
