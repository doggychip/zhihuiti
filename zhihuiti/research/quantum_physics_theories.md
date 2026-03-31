# Quantum Physics Theories

## Overview
Eight foundational quantum theories from the Copenhagen interpretation through General Relativity. Each provides a distinct mathematical framework with surprising cross-domain connections to information theory, computation, and cognitive science.

---

## 1. Copenhagen Interpretation of Quantum Mechanics

**Core formalism (Schrödinger equation):**
```
iℏ ∂|ψ〉/∂t = Ĥ|ψ〉    [time evolution]
|ψ〉 = Σ_n c_n|n〉       [superposition]
P(outcome n) = |c_n|² = |〈n|ψ〉|²   [Born rule]
```

**Uncertainty principle:**
```
ΔxΔp ≥ ℏ/2
ΔEΔt ≥ ℏ/2
```

**Copenhagen postulates:**
1. Complete description = wave function |ψ〉
2. Evolution via Schrödinger equation (deterministic)
3. Measurement collapses |ψ〉 to eigenstate (probabilistic)
4. No "hidden variables" — superposition is real until measured

**Measurement problem:** What counts as measurement? When does collapse occur? Wave function real or epistemic? (Unresolved debate.)

**Cross-domain:** Bayesian collapse = prior → posterior update. Superposition ↔ probability distributions. Measurement ↔ observation in Bayesian inference.

---

## 2. Quantum Field Theory (QFT)

**Core idea:** Fundamental objects are quantum fields φ(x,t), not particles. Particles = excitations of fields.

**Lagrangian density for scalar field:**
```
ℒ = ½(∂_μφ)² - ½m²φ² - λφ⁴/4!
```

**Path integral (Feynman):**
```
Z = ∫ Dφ exp(iS[φ]/ℏ)
S[φ] = ∫ d⁴x ℒ(φ, ∂_μφ)
```

**Renormalization:** Infinities in loop diagrams are absorbed into physical parameters (mass, coupling). Physical predictions are finite.

**Standard Model gauge groups:** U(1) × SU(2) × SU(3) = electromagnetism × weak × strong force.

**Propagator:**
```
G(x,y) = 〈0|T{φ(x)φ(y)}|0〉 = ∫ d⁴k exp(ik(x-y))/(k²-m²+iε)
```

**Cross-domain:** Path integral ↔ partition function (Wick rotation t→-iτ converts QFT to statistical mechanics). Renormalization group ↔ scale-invariance in complex systems.

---

## 3. Quantum Entanglement & Non-locality (Bell's Theorem)

**Entangled state:**
```
|Φ+〉 = (1/√2)(|↑↑〉 + |↓↓〉)    [Bell state]
```
Cannot be written as |ψ_A〉⊗|ψ_B〉. Measurements on A and B are correlated regardless of separation.

**Bell inequalities (CHSH form):**
```
|E(a,b) - E(a,b') + E(a',b) + E(a',b')| ≤ 2    [classical bound]
QM prediction: ≤ 2√2 ≈ 2.828                    [Tsirelson bound]
```
Experiments (Aspect 1982, Hensen 2015 loophole-free) confirm QM violates Bell inequalities.

**Consequences:**
- Nature is nonlocal (or: no local hidden variable theory is correct)
- No-communication theorem: entanglement cannot transmit information
- Quantum teleportation: transmit quantum state using entanglement + classical channel

**Quantum information measures:**
```
Entanglement entropy: S_A = -Tr(ρ_A log ρ_A)
where ρ_A = Tr_B(|ψ〉〈ψ|)    [partial trace]
```

**Cross-domain:** Quantum cryptography (BB84), quantum key distribution, quantum error correction, condensed matter (entanglement entropy ↔ area law for gapped systems).

---

## 4. Quantum Decoherence

**Core idea:** Quantum superpositions become effectively classical through interaction with environment.

**System-environment interaction:**
```
|ψ〉_S ⊗ |E₀〉 = (α|0〉 + β|1〉)|E₀〉
→ α|0〉|E₀〉 + β|1〉|E₁〉    [entanglement with environment]
```

**Reduced density matrix:**
```
ρ_S = Tr_E(|Ψ〉〈Ψ|) = |α|²|0〉〈0| + |β|²|1〉〈1| + (off-diagonals decay)
```

**Decoherence timescale:**
```
τ_dec = τ_rel · (λ_th/Δx)²
```
For macroscopic objects τ_dec << τ_rel — classical behavior emerges extremely fast.

**Pointer states:** Preferred basis selected by environment interaction structure. Explains why we observe definite classical outcomes.

**Cross-domain:** Quantum-to-classical transition explains emergence. Open quantum systems ↔ Markov processes. Master equation ↔ Lindblad equation ↔ stochastic dynamics.

---

## 5. Feynman Path Integral Formulation

**Core idea:** Quantum amplitude = sum over all possible paths, weighted by exp(iS/ℏ):

```
〈x_f, t_f | x_i, t_i〉 = ∫ Dx(t) exp(iS[x]/ℏ)
S[x] = ∫_{t_i}^{t_f} L(x, ẋ, t) dt
```

**Stationary phase approximation (ℏ → 0):** Dominated by classical path where δS = 0 (recovers classical mechanics).

**Partition function connection (Wick rotation τ = it):**
```
Z_QM = Tr(e^{-βH}) = ∫ Dx exp(-S_E[x]/ℏ)
S_E = ∫_0^{βℏ} dτ [½mẋ² + V(x)]    [Euclidean action]
```
QM partition function = statistical mechanics partition function with β = 1/kT and τ = βℏ.

**Applications:** Standard Model, string theory, quantum gravity, lattice QCD.

**Cross-domain:**
- Statistical mechanics (same math, Wick rotation)
- Stochastic optimal control (Feynman-Kac formula)
- Diffusion models in ML (reverse SDE = path integral)
- Pontryagin optimal control (stationary action = optimality condition)

---

## 6. Quantum Darwinism (Zurek 2003)

**Core idea:** Classical objective reality emerges when many copies of information about a quantum system are imprinted on the environment.

**Redundancy:**
```
R_δ = number of environment fragments each containing (1-δ) of I(S:E)
Classicality when R_δ >> 1
```

**Partial information plot:**
```
I(S: F_f) vs. f = fraction of environment probed
Plateau at H(S) (classical information) for classically redundant states
```

**Three ingredients:**
1. Decoherence: pointer states selected
2. Redundancy: many copies written into environment
3. Darwinism: selection of pointer states because they multiply best

**Observation = indirect reading of environmental copies.** We never directly observe quantum systems — we read their records in the environment.

**Cross-domain:** Evolution (fitness = redundancy of survival information), epidemiology (viral spread ↔ information redundancy), social epistemology (belief becomes "objective" when many agents hold it independently).

---

## 7. Quantum Bayesianism (QBism)

**Core claim:** The quantum state |ψ〉 is an agent's beliefs, not an objective property of the world.

**QBist interpretation:**
- Wave function = agent's gambling commitments about future experiences
- Collapse = Bayesian updating on new information
- No "quantum reality" independent of observer perspective

**SIC-POVM formulation (Fuchs):**
Symmetric Informationally Complete Positive Operator-Valued Measure:
```
ρ = Σ_j [(d+1)P(H_j) - 1/d] Π_j
```
where P(H_j) = probabilities for d² measurement outcomes.

**Dutch book coherence:** Quantum probabilities are rational gambling odds. Born rule = coherence condition on agent's beliefs.

**Key departure from Copenhagen:** QBism is explicitly subjective (not "the observer" as abstract entity, but "an agent"). No measurement problem — collapse is not physical.

**Cross-domain:** Bayesian probability theory, decision theory (Dutch book), personalist probability, pragmatist philosophy.

---

## 8. General Relativity (Einstein 1915)

**Einstein field equations:**
```
G_μν + Λg_μν = (8πG/c⁴) T_μν
```

**Variables:**
- `G_μν = R_μν - ½g_μν R` — Einstein tensor (geometry)
- `R_μν` — Ricci curvature tensor
- `g_μν` — metric tensor (encodes spacetime geometry)
- `T_μν` — stress-energy tensor (matter/energy)
- `Λ` — cosmological constant
- `G` — Newton's gravitational constant

**Geodesic equation (free-fall):**
```
d²x^μ/dτ² + Γ^μ_νρ (dx^ν/dτ)(dx^ρ/dτ) = 0
```
Christoffel symbols Γ^μ_νρ = "connection" on curved spacetime.

**Weak field limit:** Recovers Newtonian gravity g = -∇Φ, ∇²Φ = 4πGρ.

**Schwarzschild solution (spherical, static mass M):**
```
ds² = -(1-2GM/rc²)c²dt² + (1-2GM/rc²)⁻¹dr² + r²dΩ²
Schwarzschild radius: r_s = 2GM/c²
```

**Cross-domain:**
- Information geometry (Fisher information ↔ Riemannian metric on distributions)
- Holographic principle (Bekenstein-Hawking: black hole entropy = area/4)
- AdS/CFT correspondence: gravity in (d+1)D = QFT on d-dimensional boundary
- Riemannian geometry in ML (natural gradient, geometric deep learning)

---

## Key Cross-Domain Bridges

```
Path integral (QM) ←→ partition function (stat mech) [Wick rotation]
Decoherence ←→ classical emergence ←→ coarse-graining
Bell inequalities ←→ information-theoretic nonlocality
QBism ←→ Bayesian inference ←→ epistemic probability
Renormalization group ←→ scale-free phenomena ←→ deep learning representations
Black hole entropy ←→ information entropy ←→ holographic principle
Einstein equations ←→ information geometry ←→ gradient flows
```
