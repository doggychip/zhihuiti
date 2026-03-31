# Cross-Domain Theory Synthesis: Mathematical Skeleton Map

## Overview
This document maps structural isomorphisms across all 12 research domains. The core claim: the same abstract mathematical skeleton appears in different domains because nature reuses a small set of deep patterns. Finding these skeletons is how breakthroughs happen.

---

## The 7 Universal Mathematical Skeletons

### Skeleton 1: Exponential Family / Energy-Based Distribution
**Form:** P(x) = exp(-E(x) / T) / Z

| Domain | Theory | E(x) | T | Z |
|--------|--------|------|---|---|
| Statistical Mechanics | Boltzmann distribution | Physical energy | Temperature kT | Partition function |
| Evolutionary Game Theory | Logit equilibrium | -Payoff | Selection noise | Normalization |
| Information Theory (MaxEnt) | MaxEnt | Constraint violation | λ | Partition function |
| Machine Learning | Softmax / energy models | Negative logit | 1 | Normalization |
| Neuroscience | Boltzmann machine | -Σ w_ij s_i s_j | T_noise | Z |
| Control Theory | LQG optimal policy | Quadratic cost | 1/β | Z |
| Quantum Physics | Density matrix | Hamiltonian | kT | Tr(e^{-βH}) |

**Isomorphism:** Every case is "probability ∝ exp(−energy/temperature)". Temperature controls exploration/exploitation, randomness/determinism.

---

### Skeleton 2: Replicator / Update Proportional to Above-Average Performance
**Form:** ẋᵢ = xᵢ (fᵢ - f̄)  or  x ← x · f(x) / Z

| Domain | Theory | x | f | Mechanism |
|--------|--------|---|---|-----------|
| Evolutionary Game Theory | Replicator dynamics | Strategy frequency | Fitness | Differential equation |
| Information Theory | MaxEnt iterations | Distribution | Log-likelihood | Multiplicative update |
| Statistical Mechanics | Ising dynamics | Spin configuration | Energy decrease | Metropolis |
| Control Theory | Policy gradient RL | Policy parameters | Value function | Gradient ascent |
| Cognitive Science | Bayesian update | Belief distribution | Likelihood ratio | Bayes rule |
| Meta-Frameworks | Renormalization Group | Coupling constant | RG flow | Beta function |
| Neuroscience | Hebbian learning | Synaptic weight | Pre×post correlation | Δw = η x_pre x_post |

**Isomorphism:** Above-average things grow, below-average things shrink. This is the universal law of selection — in genes, beliefs, policies, and markets.

---

### Skeleton 3: Gradient Flow / Energy Minimization
**Form:** ẋ = -∇V(x)  or  minimize F(x) subject to constraints

| Domain | Theory | x | V(x) | Gradient flow |
|--------|--------|---|------|---------------|
| Statistical Mechanics | Free energy | Macrostate | F = U - TS | Phase evolution |
| Control Theory | LQR/LQG | State | Quadratic cost | Riccati equation |
| Cognitive Science (FEP) | Free energy principle | Belief state | Variational free energy | Perception/action |
| Information Theory | KL divergence | Distribution | D_KL(q‖p) | VI update |
| Neuroscience | Hopfield network | Neural state | E = -½Σw_ij s_i s_j | Gradient descent |
| Dynamic Systems | Attractor dynamics | Phase space point | Lyapunov function V | ẋ = -∇V |
| Topology | Morse theory | Point on manifold | Morse function f | Gradient flow lines |

**Isomorphism:** Systems flow downhill. The "landscape" varies (energy, cost, free energy, belief surprise), but the mathematics is identical: follow the negative gradient.

---

### Skeleton 4: Feedback / Self-Reference
**Form:** ẋ = f(x, control(x))  or  output feeds back into input

| Domain | Theory | Signal | Feedback | Goal |
|--------|--------|--------|---------|------|
| Control Theory | PID / State feedback | Error e = r - y | u = K(r-y) | Minimize error |
| Cybernetics | Homeostasis | Essential variable | Regulator response | Stay in range |
| Cognitive Science | Predictive coding | Prediction error | Model update | Minimize surprise |
| Neuroscience | Synaptic homeostasis | Firing rate | Synaptic scaling | Target rate |
| Dynamic Systems | Limit cycles | Phase variable | Nonlinear feedback | Periodic orbit |
| Statistical Mechanics | Mean field theory | Mean m | Self-consistent m = tanh(βJzm) | Fixed point |
| Evolutionary Game Theory | Replicator | Population frequency | Payoff depends on x | ESS fixed point |

**Isomorphism:** The system measures its own state, compares to target, and adjusts. Temperature, noise level, precision weighting — all modulate the feedback gain.

---

### Skeleton 5: Hierarchical Decomposition / Scale Separation
**Form:** Fast variables → slaved to slow variables (order parameters)

| Domain | Theory | Slow (order param) | Fast (slaved) | Bridge |
|--------|--------|-------------------|--------------|--------|
| Statistical Mechanics | Landau theory | Order parameter m | Microscopic spins | Mean field |
| Dynamic Systems | Synergetics | Order parameter ψ | Fast modes | Slaving principle |
| Meta-Frameworks | Renormalization Group | Relevant couplings | Irrelevant operators | RG flow |
| Cognitive Science | Predictive coding | High-level prior | Sensory detail | Hierarchical inference |
| Topology | Manifold learning | Low-d manifold | Ambient noise | Projection |
| Neuroscience | Global Workspace | GW broadcast | Local processors | Ignition |
| Control Theory | Kalman filter | State estimate | Measurement noise | Precision weighting |

**Isomorphism:** Complex systems separate into levels. The top level (slow, coarse) controls the bottom level (fast, fine). This is the basis of effective theories, emergence, and multi-scale organization.

---

### Skeleton 6: Conservation + Symmetry
**Form:** dQ/dt = 0  ↔  symmetry of Lagrangian (Noether)

| Domain | Theory | Symmetry | Conserved quantity |
|--------|--------|----------|-------------------|
| Group Theory / Physics | Noether's theorem | Time translation | Energy |
| Group Theory / Physics | Noether's theorem | Space translation | Momentum |
| Group Theory / Physics | Noether's theorem | U(1) gauge | Charge |
| Statistical Mechanics | Equilibrium | Detailed balance | Probability flux |
| Information Theory | Data processing | Markov processing | I(X;Y) non-increasing |
| Evolutionary Game Theory | Price equation | Selection | Fitness-weighted covariance |
| Quantum Physics | Unitarity | Time evolution | Total probability |

**Isomorphism:** Symmetry generates conservation. Break the symmetry → create a phase transition, a new conserved charge, or a new order parameter.

---

### Skeleton 7: Fixed Points / Critical Phenomena / Phase Transitions
**Form:** System has qualitatively distinct phases separated by critical points

| Domain | Theory | Order parameter | Critical point | Transition |
|--------|--------|----------------|----------------|------------|
| Statistical Mechanics | Ising model | Magnetization m | T_c = Jz/k | Ferromagnetic |
| Dynamic Systems | Bifurcation theory | Fixed point x* | μ = 0 | Saddle-node, Hopf |
| Evolutionary Game Theory | ESS | Strategy freq x* | Invasion threshold | Strategy shift |
| Control Theory | Stability | State x | Re(λ) = 0 | Stable ↔ unstable |
| Cognitive Science | GWT ignition | GW broadcast | Threshold Θ_GW | Conscious access |
| Meta-Frameworks | RG theory | Coupling g* | Fixed point of β | Universality class |
| Dynamic Systems | SOC | Avalanche size | Critical slope | Power law |
| Neuroscience | Neural criticality | Correlation length | Branching ratio = 1 | Neural avalanches |

**Isomorphism:** Near critical points, systems become scale-free, maximally responsive, and display universal behavior independent of microscopic details. Critical exponents are universal across domains.

---

## Full 12×12 Theory Collision Matrix

Strength of mathematical bridge: ●●● = deep isomorphism, ●● = significant overlap, ● = structural resonance

|  | Evo GT | Stat Mech | Ctrl Theory | Dyn Sys | Info Theory | Neuro | Cog Sci | Quantum | Meta | Topology | Linguistics | Hist Cases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Evo GT** | — | ●●● | ●● | ●●● | ●● | ●● | ●● | ● | ●● | ● | ● | ●●● |
| **Stat Mech** | ●●● | — | ●● | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● | ● | ● | ●●● |
| **Ctrl Theory** | ●● | ●● | — | ●●● | ●● | ●●● | ●●● | ●● | ●●● | ● | ● | ●●● |
| **Dyn Sys** | ●●● | ●●● | ●●● | — | ●● | ●●● | ●● | ●● | ●●● | ●●● | ● | ●●● |
| **Info Theory** | ●● | ●●● | ●● | ●● | — | ●●● | ●●● | ●●● | ●●● | ●● | ●● | ●●● |
| **Neuro** | ●● | ●●● | ●●● | ●●● | ●●● | — | ●●● | ● | ●●● | ● | ● | ●●● |
| **Cog Sci** | ●● | ●●● | ●●● | ●● | ●●● | ●●● | — | ●● | ●●● | ● | ●● | ●●● |
| **Quantum** | ● | ●●● | ●● | ●● | ●●● | ● | ●● | — | ●●● | ●●● | ● | ●● |
| **Meta** | ●● | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● | — | ●●● | ●●● | ●●● |
| **Topology** | ● | ● | ● | ●●● | ●● | ● | ● | ●●● | ●●● | — | ●● | ●● |
| **Linguistics** | ● | ● | ● | ● | ●● | ● | ●● | ● | ●●● | ●● | — | ● |
| **Hist Cases** | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● | ●● | ●●● | ●● | ● | — |

---

## Key Deep Isomorphisms (●●● bridges)

### 1. Statistical Mechanics ↔ Evolutionary Game Theory
```
Boltzmann: P(state) = exp(-βE) / Z
Logit EGT: P(strategy) = exp(βf_i) / Z

Ising H = -J Σ s_i s_j   ↔   Hopfield E = -½ Σ w_ij s_i s_j
Temperature T              ↔   Selection noise 1/β
Phase transition            ↔   Strategy shift (ESS → new ESS)
```

### 2. Statistical Mechanics ↔ Information Theory
```
Boltzmann S = -k Σ p_i ln p_i   ↔   Shannon H = -Σ p_i log p_i
Partition function Z              ↔   Moment generating function
Free energy F = -kT ln Z         ↔   ELBO = E[log p] - D_KL[q‖p]
MaxEnt: maximize H s.t. 〈E〉=U   ↔   Boltzmann distribution
```

### 3. Control Theory ↔ Cognitive Science
```
Kalman predict-update  ↔  Predictive coding (Friston)
Bellman V(s)           ↔  Expected free energy (active inference)
LQR minimize Σ x^T Q x ↔  Minimize variational free energy
State estimation        ↔  Perception (posterior inference)
Optimal control         ↔  Action selection (minimize surprise)
```

### 4. Dynamic Systems ↔ Statistical Mechanics
```
Attractor              ↔  Equilibrium state
Basin of attraction    ↔  Phase (in phase diagram)
Bifurcation            ↔  Phase transition
Order parameter        ↔  Order parameter
Lyapunov function V    ↔  Free energy F
Critical point         ↔  Second-order phase transition
```

### 5. Information Theory ↔ Cognitive Science
```
MaxEnt P* = exp(-Σλ_k f_k)/Z  ↔  Free energy principle P* = argmin F
KL divergence                   ↔  Prediction error / surprise
Mutual information I(X;Y)       ↔  Information bottleneck (perception)
Shannon capacity                ↔  Perceptual channel capacity
Fisher information              ↔  Precision weighting in predictive coding
```

### 6. Evolutionary Game Theory ↔ Dynamic Systems
```
Replicator dynamics ẋᵢ = xᵢ(fᵢ-f̄)  ↔  Population dynamics ṅᵢ = rᵢnᵢ - D
ESS fixed point                        ↔  Asymptotically stable equilibrium
Fitness landscape                      ↔  Lyapunov landscape
Strategy invasion                      ↔  Bifurcation (stability lost)
Price equation                         ↔  Change of variables in flow
```

---

## Silicon Realms Mapping

The simulation already instantiates several skeletons:

| Skeleton | Silicon Realms Expression |
|----------|--------------------------|
| Energy minimization | Agents migrate to "least crowded" realm (implicit gradient) |
| Selection | Staker strategy survives longer (implicit fitness selection) |
| Exponential family | Reward decay `base_reward / (1 + growth·t)` (implicit cooling) |
| Conservation | Token burning preserves supply accounting |
| Fixed points | Realm populations stabilize under capacity constraints |

**What's missing (the enhancements):**

| Theory | Enhancement |
|--------|-------------|
| Replicator dynamics | Strategy frequencies evolve by fitness differential |
| Statistical mechanics | Temperature parameter governs economy; entropy tracked |
| Control theory | Bellman value function guides realm migration decisions |
| SOC | Track wealth avalanches; detect power-law regime |

---

## Meta-Pattern: The Cross-Domain Recipe

1. **Identify the mathematical skeleton** (which of the 7 above)
2. **Map variables** (what is "energy"? what is "temperature"? what is "state"?)
3. **Transfer theorems** (all results about the skeleton transfer automatically)
4. **Find the new physics** (what does this domain add that the source domain doesn't have?)

The deepest skeleton is **free energy / variational principle**: every system minimizes some free energy F = Energy - Temperature × Entropy. This unifies thermodynamics, Bayesian inference, evolutionary fitness, optimal control, and neural computation.
