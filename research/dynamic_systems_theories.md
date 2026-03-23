# Dynamic Systems Theories

## Overview
Dynamical systems theory studies how systems evolve over time. These 8 theories span chaos, self-organization, criticality, and emergence — collectively forming a framework for understanding complex behavior far from equilibrium.

---

## 1. Chaos Theory (Lorenz)

**Lorenz system (1963):**
```
dx/dt = σ(y - x)
dy/dt = x(ρ - z) - y
dz/dt = xy - βz
```
**Classic parameters:** σ=10, ρ=28, β=8/3 → chaotic attractor.

**Key concepts:**
- **Sensitive dependence on initial conditions:** Lyapunov exponent λ > 0
  ```
  |δx(t)| ≈ |δx(0)| · e^{λt}
  ```
- **Strange attractor:** Fractal structure in phase space, Hausdorff dimension ~2.06 for Lorenz
- **Lyapunov exponents:** λ₁ > 0 (chaos), Σλᵢ < 0 (dissipation), λ₂ = 0 (flow direction)
- **Butterfly effect:** Practical unpredictability beyond ~1/λ time units

**Cross-domain:** Weather forecasting limits, turbulence, cardiac arrhythmia, economic prediction limits, cryptography (chaos-based RNGs).

---

## 2. Dissipative Structures (Prigogine)

**Far-from-equilibrium thermodynamics:**
Entropy production rate: σ_s = Σ_k J_k X_k ≥ 0

**Near equilibrium (linear regime):** Onsager relations J_k = Σ_l L_kl X_l
**Far from equilibrium:** Nonlinear → self-organization, pattern formation

**Brusselator model:**
```
dX/dt = A - (B+1)X + X²Y
dY/dt = BX - X²Y
```
Exhibits Hopf bifurcation and limit cycle oscillation.

**Key insight:** Systems driven far from equilibrium can spontaneously decrease local entropy (at cost of increasing global entropy). Order from disorder.

**Examples:** Bénard convection cells, Belousov-Zhabotinsky reaction, biological rhythms, social self-organization.

**Cross-domain:** Evolutionary theory (life as dissipative structure), economics (markets as dissipative systems), consciousness (Friston's free energy).

---

## 3. Self-Organized Criticality (Bak, Tang, Wiesenfeld 1987)

**Sandpile model:**
- Add grains randomly → avalanches when local slope > threshold
- System naturally evolves to critical state without fine-tuning

**Power law statistics:**
```
P(s) ~ s^{-τ},    τ ≈ 1.5 (sandpile)
P(f) ~ 1/f^α     (power spectrum, 1/f noise)
```

**Criticality signatures:**
- No characteristic scale (scale-free avalanches)
- Long-range correlations
- 1/f noise in time series
- Fractal spatial structure

**SOC vs. tuned criticality:** SOC reaches critical point automatically; second-order phase transitions require tuning to T_c.

**Cross-domain:** Earthquakes (Gutenberg-Richter law), forest fires, neural avalanches (Beggs & Plenz 2003), stock market crashes, evolutionary punctuated equilibrium.

---

## 4. Synergetics (Haken)

**Slaving principle:** Near instability, fast modes (stable) are slaved to slow modes (unstable/order parameters).

**Center manifold reduction:**
```
ẋ_s = A_s x_s + h(x_u)    [stable, fast: x_s ≈ -A_s⁻¹ f_s(x_u)]
ẋ_u = A_u x_u + g(x_u)    [unstable, slow: order parameter equation]
```

**Haken's laser model:**
```
dE/dt = (G·n - κ)E           [field amplitude]
dn/dt = γ(n₀ - n) - G·n·E²  [inversion]
```
Below threshold: E=0 (noise). Above threshold: lasing (spontaneous symmetry breaking).

**Order parameters:** Collective variables that describe macroscopic state and determine microscopic behavior.

**Cross-domain:** Cognitive science (order parameters in perception), motor coordination (HKB model of bimanual coupling), social dynamics (opinion formation).

---

## 5. Bifurcation Theory

**Normal forms** for codimension-1 bifurcations:

| Type | Normal Form | Description |
|------|-------------|-------------|
| **Saddle-node** | ẋ = μ + x² | Creation/destruction of fixed points |
| **Transcritical** | ẋ = μx - x² | Exchange of stability |
| **Pitchfork** | ẋ = μx ± x³ | Symmetry breaking |
| **Hopf** | ṙ = (μ - r²)r, θ̇ = ω | Birth of limit cycle |

**Bifurcation parameter μ:** As μ crosses critical value, qualitative behavior changes.

**Catastrophe theory (Thom):** Classification of generic singularities. 7 elementary catastrophes: fold, cusp, swallowtail, butterfly, hyperbolic/elliptic/parabolic umbilic.

**Cross-domain:** Neuroscience (action potential as Hopf bifurcation), ecology (tipping points), climate (ice-albedo feedback), social opinion transitions.

---

## 6. Attractor Dynamics

**Types of attractors:**
- **Fixed point:** ẋ = f(x) = 0, all eigenvalues Re(λ) < 0
- **Limit cycle:** Periodic orbit, isolated in phase space
- **Torus:** Quasiperiodic, two incommensurate frequencies
- **Strange attractor:** Fractal, sensitive dependence (chaotic)

**Basin of attraction:** Set of initial conditions converging to attractor.

**Lyapunov function V(x):** V > 0, V̇ < 0 → proves attractor exists.

**Poincaré section:** Reduce continuous flow to discrete map, study return map.

**Gradient systems:** ẋ = -∇V(x). Every trajectory descends V(x). All attractors are fixed points.

**Cross-domain:**
- Hopfield networks: memories as fixed-point attractors
- Working memory: sustained activity = attractor state
- Landscape metaphor in development (Waddington), evolution (Wright), and cognition

---

## 7. Complex Adaptive Systems (Holland)

**Key components:**
- **Agents:** Heterogeneous, rule-following, adaptive
- **Emergence:** Macro-patterns not designed top-down
- **Fitness landscapes:** Agents explore via adaptation
- **Tags:** Enable selective interaction
- **Internal models:** Anticipatory behavior
- **Building blocks:** Schemas as reusable components

**Echo model equations:**
```
resource[i](t+1) = resource[i](t) + inflow - consumption
agent fitness = f(resource acquisition, defense, reproduction)
```

**Schema theorem (Holland):** Above-average schemata (building blocks) increase in frequency exponentially:
```
m(H, t+1) ≥ m(H,t) · [f(H,t)/f̄(t)] · [1 - p_c·δ(H)/(l-1) - o(H)·p_m]
```

**Cross-domain:** Economics (markets), immunology (immune system as CAS), ecology (food webs), cities (urban dynamics), internet.

---

## 8. Emergence Theory

**Weak emergence:** Macro-properties deducible in principle from micro-rules (but computationally expensive). Example: Game of Life patterns.

**Strong emergence (Chalmers):** Macro-properties not deducible even in principle from micro-description. Proposed for consciousness.

**Causal emergence (Hoel):** Macro-scale has more causal power if its effective information EI(macro) > EI(micro):
```
EI(X→Y) = I(X^do; Y)    [intervention information]
```
Macro causal emergence if max_φ EI(φ(X) → φ(Y)) > EI(X→Y).

**Computational irreducibility (Wolfram):** Some systems (Rule 110 CA) require full simulation — no shortcut. Basis of why emergence exists.

**Levels and scales:**
```
micro → meso → macro
atoms → molecules → cells → organisms → societies
```
Each level has genuine laws not reducible to the level below.

**Cross-domain:**
- Physics → chemistry → biology (reductionism limits)
- Neurons → cognition (hard problem)
- Individuals → institutions (social science)
- Tokens → semantics (language emergence)
