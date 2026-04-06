# Magnetohydrodynamics (MHD)

**Domain:** Physics

**Equation:** `ρ(∂v/∂t + v·∇v) = J×B − ∇p;  ∂B/∂t = ∇×(v×B) + η∇²B;  ∇·B = 0;  Alfvén: v_A = B/√(μ₀ρ);  magnetic Reynolds: Rm = vL/η`

**Update Form:** coupled_fluid_field

**Optimization:** satisfy_mhd_equilibrium

**Fixed Points:** force_free_field

## Patterns

- compositional_structure
- conservation_law
- energy_minimization
- structural_isomorphism
- symmetry_breaking

## Operators

- alfven_wave
- lorentz_force
- magnetic_induction
- ohmic_dissipation
- reconnection
