# Statistical Mechanics / Thermodynamics

## Overview
Statistical mechanics bridges microscopic physics (atoms, molecules) and macroscopic thermodynamics (temperature, pressure, entropy) through probabilistic methods. Developed by Boltzmann, Gibbs, and Maxwell; extended by Ising, Landau, Wilson, and Jaynes. It is one of the most powerful cross-domain frameworks in all of science.

---

## 1. Boltzmann Distribution

The fundamental probability distribution over microstates at thermal equilibrium:

```
P(E_i) = exp(-E_i / kT) / Z = exp(-βE_i) / Z
```

**Variables:**
- `E_i` — energy of microstate i
- `k` — Boltzmann constant (1.38 × 10⁻²³ J/K)
- `T` — temperature
- `β = 1/kT` — inverse temperature
- `Z` — partition function (normalization)

**Intuition:** Higher energy states are exponentially less probable. Temperature controls the "softness" of this suppression.

---

## 2. Partition Function Z

The central object of statistical mechanics — a generating function for all thermodynamic quantities:

```
Z = Σ_i exp(-βE_i)    [discrete]
Z = ∫ exp(-βE(x)) dx   [continuous]
```

**Derived quantities:**
```
Helmholtz free energy:   F = -kT ln Z
Mean energy:             〈E〉 = -∂(ln Z)/∂β
Heat capacity:           C_v = ∂〈E〉/∂T = kβ² · Var(E)
Entropy:                 S = -∂F/∂T = k(ln Z + β〈E〉)
```

**Z as Laplace transform:** Z(β) = ∫ g(E) exp(-βE) dE where g(E) is the density of states. All thermodynamics encoded in Z.

---

## 3. Free Energies

**Helmholtz free energy** (constant T, V):
```
F = U - TS
```
Minimized at equilibrium for systems at fixed temperature.

**Gibbs free energy** (constant T, P):
```
G = H - TS = F + PV
```
Minimized for systems at fixed temperature and pressure. Controls chemical reactions, phase transitions.

**Legendre transform structure:**
```
F(T,V) ←→ U(S,V)    (Legendre transform in S↔T)
G(T,P) ←→ H(S,P)    (Legendre transform)
```
This structure recurs in: convex duality, Lagrangian ↔ Hamiltonian mechanics, moment ↔ cumulant generating functions.

---

## 4. Ising Model

The canonical model of phase transitions and collective behavior:

```
H = -J Σ_{〈ij〉} s_i s_j - h Σ_i s_i
```

**Variables:**
- `s_i ∈ {-1, +1}` — spin at site i
- `J` — coupling constant (J > 0: ferromagnetic)
- `h` — external field
- `〈ij〉` — sum over nearest neighbors

**Mean field theory** (Weiss, Bragg-Williams):
```
m = tanh(β(Jzm + h))
```
where z = coordination number, m = 〈s_i〉 = magnetization.

**Phase transition:**
```
T_c = Jz/k    (mean field critical temperature)
```
For T < T_c: spontaneous magnetization (Z₂ symmetry breaking).
For T > T_c: disordered phase, m = 0.

**2D Ising exact solution (Onsager 1944):**
```
T_c = 2J / [k · ln(1 + √2)] ≈ 2.269 J/k
```

---

## 5. Boltzmann Entropy

**Microcanonical entropy:**
```
S = k ln W
```
where W = number of microstates compatible with macrostate.

**Connection to Shannon entropy:**
For uniform distribution over W microstates: S = k ln W
For general distribution: S = -k Σ_i P_i ln P_i

**Shannon entropy** H(X) = -Σ p(x) log p(x) is S/k with k=1, log base 2 in bits.

This isomorphism (Boltzmann 1877 ↔ Shannon 1948) is a fundamental cross-domain bridge.

---

## 6. Maximum Entropy Principle (Jaynes 1957)

Given constraints 〈f_k(x)〉 = F_k, the least-biased distribution is:

```
P*(x) = argmax_{P} H[P] = (1/Z) exp(-Σ_k λ_k f_k(x))
```

**Lagrange multiplier solution:**
```
P(x) = exp(-Σ_k λ_k f_k(x)) / Z(λ)
```

**Special cases:**
- Constraint: 〈E〉 = U → Boltzmann distribution
- Constraint: 〈x〉 = μ, 〈x²〉 = σ² → Gaussian
- No constraints → Uniform distribution
- Constraint: 〈log p〉 = fixed → Power law (Zipf)

**Bayesian interpretation:** MaxEnt = most honest prior given partial information. Connects thermodynamics to Bayesian inference (Jaynes program).

---

## 7. Fluctuation-Dissipation Theorem

Thermal fluctuations and linear response are related:

```
χ''(ω) = (ω/2kT) S(ω)
```

where χ'' = imaginary part of susceptibility (dissipation), S(ω) = power spectral density of fluctuations.

**Time-domain form:**
```
〈δx(t) δx(0)〉 = kT · G(t)
```
where G(t) is the response function (Green's function).

**Consequences:** You can measure equilibrium fluctuations to predict linear response. Explains: Johnson-Nyquist noise, Brownian motion, Einstein relation D = kT/γ.

---

## 8. Landau Theory of Phase Transitions

Near a continuous phase transition, free energy as power series in order parameter m:

```
F(m) = F₀ + a(T-T_c)m² + bm⁴ + cm⁶ + ... - hm
```

**Variables:**
- `m` — order parameter (magnetization, density difference, etc.)
- `a, b > 0` — material constants
- `T_c` — critical temperature

**Equilibrium condition:** ∂F/∂m = 0 → 2a(T-T_c)m + 4bm³ = 0

**Solutions:**
- T > T_c: m = 0 (disordered)
- T < T_c: m = ±√[a(T_c-T)/2b] (ordered, Z₂ symmetry broken)

**Critical exponents** (mean field values):
```
m ~ (T_c - T)^β,  β = 1/2
χ ~ |T - T_c|^{-γ},  γ = 1
ξ ~ |T - T_c|^{-ν},  ν = 1/2
```

**Universality:** Critical exponents depend only on symmetry and dimensionality, not microscopic details. Classes include: Ising (Z₂), XY (U(1)), Heisenberg (SO(3)).

---

## 9. Cross-Domain Connections

### Machine Learning
- **Boltzmann Machine** (Hinton & Sejnowski 1985): neural network with energy E = -Σ w_ij v_i h_j
  - P(v) = Σ_h exp(-E(v,h)) / Z
  - Learning = gradient descent on KL divergence
- **Simulated Annealing**: temperature schedule T(t) → 0 allows escape from local minima
- **Energy-based models**: f_θ(x) defines energy, density ∝ exp(-f_θ(x))
- **Softmax**: P(class=i) = exp(z_i) / Σ_j exp(z_j) — Boltzmann with β=1

### Neuroscience
- **Hopfield Networks**: E = -½ Σ w_ij s_i s_j — identical to Ising Hamiltonian
  - Memories = attractors = energy minima
  - Temperature = noise level in stochastic Hopfield
- **Neural criticality hypothesis**: brain operates near critical point (maximum information transmission)

### Information Theory
- **Shannon entropy** H = -Σ p log p is Boltzmann entropy with k=1
- **Free energy** F = 〈E〉 - TH: exactly Friston's variational free energy
- **Channel capacity** ~ thermodynamic efficiency

### Economics (Econophysics)
- Agent wealth distributions ~ Boltzmann distribution
- Market crashes ~ phase transitions
- Minority game ~ spin glass

### Mathematical Bridges
```
Partition function Z ←→ moment generating function (probability)
Partition function Z ←→ path integral amplitude (QM)
Helmholtz free energy ←→ KL divergence (information geometry)
Landau theory ←→ Ginzburg-Landau superconductivity ←→ Higgs mechanism
MaxEnt ←→ Bayesian prior ←→ regularization (ML)
Critical phenomena ←→ Renormalization Group ←→ scale-free networks
```
