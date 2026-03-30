# Neural ODE

**Domain:** Machine Learning

**Equation:** `dh/dt = f_θ(h,t);  h(T) = h(0) + ∫₀ᵀ f_θ(h,t)dt;  adjoint: da/dt = −aᵀ ∂f/∂h;  ∂L/∂θ = −∫ aᵀ ∂f/∂θ dt`

**Update Form:** adjoint_sensitivity

**Optimization:** minimize_loss_via_adjoint

**Fixed Points:** trained_vector_field

## Patterns

- compositional_structure
- conservation_law
- energy_minimization
- gradient_descent
- variational_principle

## Operators

- adjoint_method
- flow_map
- gradient
- ode_solver
- vector_field
