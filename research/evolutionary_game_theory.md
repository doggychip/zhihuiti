# Evolutionary Game Theory

## Overview
Evolutionary game theory (EGT) applies game-theoretic models to evolving populations. Unlike classical game theory (rational agents choosing strategies), EGT treats strategies as heritable traits that spread or decline based on reproductive fitness. Developed by John Maynard Smith and George Price in the 1970s.

---

## 1. Replicator Dynamics

The core dynamical equation describing how strategy frequencies evolve:

```
dx_i/dt = x_i [ f_i(x) - φ(x) ]
```

**Variables:**
- `x_i` — frequency of strategy i in population
- `f_i(x)` — fitness of strategy i given population state x
- `φ(x) = Σ_j x_j f_j(x)` — mean population fitness

**Payoff-based fitness:**
```
f_i(x) = Σ_j a_ij x_j
```
where `a_ij` is the payoff matrix entry (payoff to i when meeting j).

**Key property:** Mean fitness φ is non-decreasing along trajectories (Fisher's fundamental theorem analog). Fixed points are Nash equilibria, but not all Nash equilibria are stable fixed points.

**Matrix form:** ẋ = x ⊙ (Ax - x^T Ax · 1) where A is the payoff matrix.

---

## 2. Evolutionarily Stable Strategy (ESS)

**Definition (Maynard Smith & Price 1973):**
Strategy σ* is an ESS if for all σ ≠ σ*:
```
E(σ*, σ*) > E(σ, σ*)
```
OR
```
E(σ*, σ*) = E(σ, σ*)  AND  E(σ*, σ) > E(σ, σ)
```

**Interpretation:** An ESS is a strategy that, when adopted by the entire population, cannot be invaded by any rare mutant strategy.

**Stability:** Every ESS is a Nash equilibrium, but not every Nash equilibrium is an ESS. ESS → asymptotically stable fixed point of replicator dynamics (but converse not always true).

---

## 3. Nash Equilibrium and ESS Relationship

**Nash Equilibrium:** No player can unilaterally improve payoff.
```
E(σ*, σ*) ≥ E(σ, σ*)  ∀σ
```

**Hierarchy:**
- ESS ⊂ Nash equilibria (every ESS is Nash, not vice versa)
- ESS → Lyapunov stable fixed point of replicator dynamics
- Strict Nash equilibrium → ESS

**Mixed strategy ESS:** In the Hawk-Dove game, the mixed ESS p* = V/C is the unique Nash equilibrium where both strategies have equal expected payoff.

---

## 4. Fitness Landscapes

### Wright's Adaptive Landscape (1932)
```
W̄ = Σ_ij p_i p_j W_ij
```
Population moves "uphill" in mean fitness. Problems: mean fitness W̄ is not always a Lyapunov function for diploid genetics.

### Kauffman NK Model
- **N** = number of genes/loci
- **K** = epistatic interactions per gene (0 ≤ K ≤ N-1)

```
F(σ) = (1/N) Σ_i f_i(σ_i, σ_{i1}, ..., σ_{iK})
```

**Ruggedness:** K=0 → smooth single-peaked landscape; K=N-1 → fully random (maximally rugged). Phase transition at intermediate K.

**Applications:** Protein folding, genetic algorithm design, organization theory, drug target landscapes.

---

## 5. Price Equation

Derived by George Price (1970), connects multi-level selection to evolutionary change:

```
w̄ Δz̄ = Cov(w, z) + E(w Δz)
```

**Variables:**
- `w̄` — mean fitness
- `Δz̄` — change in mean trait value z
- `Cov(w, z)` — selection term (covariance between fitness and trait)
- `E(w Δz)` — transmission bias term (within-individual change)

**Nested form (multilevel selection):**
```
w̄ Δz̄ = Cov(W_k, Z_k) + E_k[Cov_j(w_j|k, z_j|k)] + E_k E_j[w_j|k Δz_j|k]
```

**Connection to Holland's Schema Theorem:**
Holland's Schema Theorem for genetic algorithms:
```
m(H, t+1) ≥ m(H,t) · [f(H)/f̄] · [1 - p_c · δ(H)/(l-1)] · [1 - p_m]^{o(H)}
```
Both Price equation and schema theorem describe how "above-average" patterns (strategies/schemata) increase in frequency — the Price equation is the more general mathematical framework.

---

## 6. Classic Games

### Hawk-Dove Game

Payoff matrix (V = resource value, C = cost of fight, V < C):

|   | Hawk | Dove |
|---|------|------|
| **Hawk** | (V-C)/2 | V |
| **Dove** | 0 | V/2 |

**ESS:** Mixed strategy p* = V/C (proportion Hawks). Pure Hawk is not ESS when C > V.

**Replicator dynamics:** ẋ = x(1-x)[x·(V-C)/2 + (1-x)·V - mean] → stable at x* = V/C.

### Prisoner's Dilemma (Evolutionary)

|   | C | D |
|---|---|---|
| **C** | R | S |
| **D** | T | P |

With T > R > P > S. Defection dominates → tragedy of the commons.

**Escape mechanisms:**
- Kin selection (Hamilton's rule): r·b > c
- Reciprocal altruism (Axelrod): Tit-for-Tat in iterated PD
- Network reciprocity: cooperators cluster
- Group selection: Price equation second term

---

## 7. Multi-Level Selection

**Hamilton's inclusive fitness:**
```
Δp ∝ rb - c
```
where r = genetic relatedness, b = benefit to recipient, c = cost to actor.

**Price equation decomposition:**
- Level 1 (within group): E_k[Cov_j(w,z)] — individual selection
- Level 2 (between group): Cov_k(W_k, Z_k) — group selection

**Debate:** Lewontin, Gould vs. Hamilton, Dawkins. Price equation shows both levels always operate; question is their relative magnitudes.

---

## 8. Cross-Domain Applications

### Neuroscience
- Synaptic competition as evolutionary process (Neural Darwinism / Edelman)
- Reinforcement learning: fitness ↔ reward signal
- Homeostatic plasticity: ESS as set-point

### Economics
- Evolutionary economics (Nelson & Winter): firms as strategies
- Market dynamics as replicator dynamics
- Behavioral economics: bounded rationality vs. ESS

### Ecology
- Species coexistence: rock-paper-scissors dynamics
- Predator-prey as evolutionary arms race
- Lotka-Volterra as special case of replicator dynamics

### AI / Machine Learning
- Genetic algorithms: Holland's schema theorem ↔ Price equation
- Multi-agent RL: Nash equilibria as convergence targets
- GANs: generator/discriminator as Hawk-Dove
- Population-based training (PBT): explicit evolutionary dynamics

### Key Mathematical Bridges
```
Replicator dynamics ←→ Lotka-Volterra (change of variables)
ESS ←→ Nash equilibrium (subset)
Price equation ←→ Schema theorem (isomorphism)
Fitness landscape ←→ Energy landscape (Hopfield/Boltzmann)
Kin selection ←→ Green's theorem (social evolution)
```
