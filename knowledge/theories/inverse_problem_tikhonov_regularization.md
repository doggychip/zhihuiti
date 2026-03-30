# Inverse Problem / Tikhonov Regularization

**Domain:** Mathematics

**Equation:** `min ||Ax−b||² + α||Lx||²;  x_α = (AᵀA + αLᵀL)⁻¹Aᵀb;  Morozov: ||Ax_α−b|| = δ;  L-curve: trade-off ||x|| vs ||Ax−b||`

**Update Form:** regularized_least_squares

**Optimization:** minimize_regularized_residual

**Fixed Points:** regularized_solution

## Patterns

- dual_variables
- energy_minimization
- information_gain
- variational_principle

## Operators

- adjoint_operator
- discrepancy_principle
- parameter_choice
- regularizer
- svd
