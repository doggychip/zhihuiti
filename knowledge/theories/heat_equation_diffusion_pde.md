# Heat Equation / Diffusion PDE

**Domain:** Physics

**Equation:** `∂u/∂t = α∇²u;  u(x,t) = ∫G(x−y,t)u₀(y)dy;  G(x,t) = (4παt)⁻ⁿ/² exp(−|x|²/4αt);  max principle: max on boundary`

**Update Form:** diffusion_kernel_convolution

**Optimization:** dissipate_to_equilibrium

**Fixed Points:** uniform_temperature

## Patterns

- conservation_law
- energy_entropy_tradeoff
- energy_minimization
- renormalization

## Operators

- green_function
- heat_kernel
- laplacian
- maximum_principle
- spectral_decomposition
