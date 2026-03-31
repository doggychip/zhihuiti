# Navier-Stokes Equations

**Domain:** Physics

**Equation:** `∂u/∂t + (u·∇)u = −∇p/ρ + ν∇²u + f;  ∇·u = 0;  Re = UL/ν;  energy: d/dt ∫½|u|² = −ν∫|∇u|² + ∫f·u`

**Update Form:** momentum_transport

**Optimization:** satisfy_conservation_laws

**Fixed Points:** steady_state_flow

## Patterns

- conservation_law
- energy_entropy_tradeoff
- energy_minimization
- symmetry_breaking

## Operators

- advection
- diffusion
- laplacian
- nonlinear_transport
- pressure_projection
