# Matrix Factorization / NMF

**Domain:** Machine Learning

**Equation:** `min ||X − WH||²_F;  NMF: W,H ≥ 0;  SVD: X = UΣVᵀ;  update: H ← H ⊙ (WᵀX)/(WᵀWH);  W ← W ⊙ (XHᵀ)/(WHHᵀ)`

**Update Form:** alternating_minimization

**Optimization:** minimize_reconstruction_error

**Fixed Points:** optimal_factorization

## Patterns

- compositional_structure
- dual_variables
- energy_minimization
- fixed_point_iteration
- structural_isomorphism

## Operators

- frobenius_norm
- low_rank_approximation
- multiplicative_update
- projection
- svd
