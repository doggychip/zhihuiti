# Variational Quantum Eigensolver (VQE)

**Domain:** Physics

**Equation:** `E(θ) = ⟨ψ(θ)|H|ψ(θ)⟩;  |ψ(θ)⟩ = U(θ)|0⟩;  θ* = argmin E(θ);  ∂E/∂θᵢ = ½[E(θᵢ+π/2) − E(θᵢ−π/2)];  E(θ) ≥ E₀`

**Update Form:** parameter_shift_gradient

**Optimization:** minimize_energy_expectation

**Fixed Points:** approximate_ground_state

## Patterns

- compositional_structure
- energy_minimization
- exploration_exploitation
- gradient_descent
- variational_principle

## Operators

- gradient
- hamiltonian
- measurement
- parameter_shift
- parameterized_circuit
