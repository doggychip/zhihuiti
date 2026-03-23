# Information Theory

## Overview
Information theory provides a mathematical framework for quantifying information, communication, and computation. Founded by Shannon (1948), extended to algorithmic complexity (Kolmogorov), Bayesian inference (Jaynes), and consciousness (Tononi). Core equations recur across physics, neuroscience, ML, and biology.

---

## 1. Shannon Information Theory (1948)

**Entropy (uncertainty / information content):**
```
H(X) = -Σ_x p(x) log₂ p(x)    [bits]
H(X) = -Σ_x p(x) ln p(x)      [nats]
```

**Key quantities:**
```
Joint entropy:       H(X,Y) = -Σ_{x,y} p(x,y) log p(x,y)
Conditional entropy: H(X|Y) = H(X,Y) - H(Y)
Mutual information:  I(X;Y) = H(X) + H(Y) - H(X,Y) = KL(p(x,y) || p(x)p(y))
KL divergence:       D_KL(P||Q) = Σ_x p(x) log[p(x)/q(x)] ≥ 0
```

**Fundamental theorems:**
- **Source coding theorem:** Cannot compress below H(X) bits per symbol
- **Channel coding theorem:** For rate R < C = max_{p(x)} I(X;Y), reliable transmission possible
- **Data processing inequality:** I(X;Y) ≥ I(X;Z) if X→Y→Z is a Markov chain

**Cross-domain:** Foundation of all compression, cryptography, statistics, ML.

---

## 2. Algorithmic Information Theory / Kolmogorov Complexity

**Kolmogorov complexity K(x):** Length of shortest program that outputs x:
```
K(x) = min{|p| : U(p) = x}
```
where U is a universal Turing machine, |p| is program length in bits.

**Properties:**
```
K(x) ≤ |x| + c              [trivial upper bound: copy x]
K(x,y) ≤ K(x) + K(y) + c   [subadditivity]
K(x|y) ≤ K(x) + c           [conditioning can only help]
I(x:y) = K(x) + K(y) - K(x,y)  [algorithmic mutual information]
```

**Incomputability:** K(x) is not computable (halting problem reduction). But computable upper bounds exist.

**Relationship to entropy:** For typical strings from source p: K(x) ≈ -log₂ p(x). Ensemble average K̄ ≈ H(X).

**MDL principle (Rissanen):** Best model = shortest description = minimum description length. Connects K to model selection, Occam's razor, Bayesian model comparison.

**Cross-domain:** Occam's razor (simplest model), string theory (vacuum selection), evolutionary biology (genome compression), neural network generalization.

---

## 3. Maximum Entropy Principle (Jaynes 1957)

**Problem:** Choose probability distribution given constraints.

**MaxEnt solution:**
```
P* = argmax H[P] = argmax{-Σ p(x) log p(x)}
subject to: Σ p(x) f_k(x) = F_k,  Σ p(x) = 1
```

**Solution form (exponential family):**
```
P*(x) = (1/Z) exp(-Σ_k λ_k f_k(x))
Z(λ) = Σ_x exp(-Σ_k λ_k f_k(x))    [partition function]
```

**Special cases:**
| Constraints | MaxEnt distribution |
|-------------|-------------------|
| None | Uniform |
| 〈x〉 = μ, 〈x²〉 = σ²+μ² | Gaussian |
| 〈E〉 = U | Boltzmann |
| x ≥ 0, 〈x〉 = μ | Exponential |
| Discrete, nothing | Uniform |

**Cross-domain:** Thermodynamics (Boltzmann distribution), Bayesian priors, regularization in ML (L2 → Gaussian prior, L1 → Laplace prior), natural language (MaxEnt models).

---

## 4. Integrated Information Theory (IIT) — Tononi

**Core claim:** Consciousness = integrated information Φ (phi).

**Effective Information (EI):**
```
EI(M → M') = I(X_t^{do}; X_{t+1})
```
where do(·) denotes intervention on X_t (set to maximum entropy).

**Integrated Information:**
```
Φ = min over bipartitions M = (A,B): φ(A,B)
φ(A,B) = EI(M) - EI(A) - EI(B)
```
Maximum over all possible bipartitions → minimum (weakest link).

**IIT axioms:** Existence, intrinsicality, information, integration, exclusion.

**Phi values:**
- Simple feedforward net: Φ = 0 (no integration)
- Tightly recurrent network: Φ > 0
- Human brain (estimated): Φ ~ 10s of bits

**Cross-domain:** Neuroscience (measure of consciousness), AI (why deep learning ≠ consciousness — Φ ≈ 0 for feedforward nets), philosophy of mind.

---

## 5. Information Bottleneck (Tishby, Pereira, Bialek 1999)

**Problem:** Compress variable X into T while preserving information about relevant variable Y.

**Information bottleneck Lagrangian:**
```
min_{p(t|x)} I(X;T) - β I(T;Y)
```

**Self-consistent equations:**
```
p(t|x) = p(t)/Z(x,β) · exp(-β D_KL(p(y|x) || p(y|t)))
p(y|t) = Σ_x p(y|x) p(x|t)
p(t) = Σ_x p(t|x) p(x)
```

**Information plane:** Plot I(T;X) vs I(T;Y). Optimal codes lie on the information bottleneck curve.

**Deep learning connection (Tishby & Schwartz-Ziv 2017):** Each layer of DNN is a stochastic encoder. Training: compression phase (reduce I(T;X)) then fitting phase (increase I(T;Y)). Generalization = compression.

**Rate-distortion connection:** IB = rate-distortion with D = -I(T;Y). Optimal compression at each rate.

**Cross-domain:** Neuroscience (efficient coding in retina/V1), genetics (gene regulatory networks), NLP (BERT representations), lossy compression.

---

## 6. Fisher Information

**Fisher information matrix:**
```
I(θ)_{ij} = E[(∂ log p(x;θ)/∂θ_i)(∂ log p(x;θ)/∂θ_j)]
           = -E[∂² log p(x;θ)/∂θ_i ∂θ_j]
```

**Cramér-Rao bound:**
```
Var(θ̂) ≥ 1/I(θ)    [scalar]
Cov(θ̂) ≥ I(θ)⁻¹   [matrix: achievable by MLE asymptotically]
```

**Connection to KL divergence:**
```
D_KL(p(·;θ) || p(·;θ+dθ)) ≈ ½ dθᵀ I(θ) dθ
```
Fisher information is the Riemannian metric on the manifold of probability distributions (information geometry, Amari).

**Natural gradient:**
```
θ ← θ + η I(θ)⁻¹ ∇L(θ)
```
Gradient descent in distribution space rather than parameter space. Invariant to parameterization.

**Cross-domain:** Statistics (optimal estimators), quantum mechanics (quantum Fisher information, Heisenberg uncertainty), neural networks (natural gradient / K-FAC), neuroscience (efficient neural coding).

---

## 7. Causal Emergence (Hoel, Albantakis, Tononi 2013)

**Effective Information at macro scale:**
```
EI(macro) = I(X^{do}_t; X_{t+1}) at macro level φ
```

**Causal emergence condition:**
```
∃ coarse-graining φ: EI(φ(X)) > EI(X)
```
The macro-scale description has more causal power than the micro-scale.

**Why it happens:** Micro-scale noise (irrelevant micro-states) dilutes causal information. Coarse-graining can eliminate noise while preserving causal signal.

**Example:** 4-state Markov chain where macro-states (grouping 2 states each) have higher EI than micro-states.

**Philosophical implication:** Higher-level descriptions (psychology, economics) can be causally more fundamental than lower-level descriptions (neuroscience, physics). Legitimizes special sciences.

**Cross-domain:** Philosophy of science (reductionism vs. emergence), neuroscience (brain regions vs. neurons), social science (institutions vs. individuals).

---

## 8. Information Thermodynamics (Landauer's Principle)

**Landauer's principle (1961):**
```
Erasing 1 bit of information generates ≥ kT ln 2 of heat
```

**Maxwell's demon resolution:** Demon must store measurement → eventual erasure → no violation of second law. Information has physical entropy cost.

**Generalized second law:**
```
ΔS_system + ΔS_environment ≥ -I_acquired
```
where I_acquired = mutual information gained by measurement.

**Szilard engine:** Single-molecule gas + one bit of measurement → kT ln 2 of work extracted. Confirms Landauer.

**Sagawa-Ueda fluctuation theorem (2010):**
```
〈exp(-βW - I)〉 = 1
```
Generalizes Jarzynski inequality to include measurement/feedback.

**Thermodynamic cost of computation:**
- Logically irreversible operations (AND, ERASE) → heat dissipation
- Logically reversible computation (Toffoli gate) → no thermodynamic cost in principle
- Brain energy budget: ~20W for ~10^15 operations/s = ~2×10⁻¹⁴ J/op >> kT ln 2

**Cross-domain:** Quantum computing (no-cloning theorem ↔ erasure cost), black holes (Bekenstein-Hawking entropy = information), neural energy budget, DNA replication fidelity.

---

## Key Cross-Domain Bridges

```
Shannon H ←→ Boltzmann S (same equation)
MaxEnt ←→ Bayesian inference ←→ variational inference
KL divergence ←→ free energy ←→ ELBO (VAE training)
Fisher information ←→ Riemannian metric on probability manifold
Kolmogorov complexity ←→ Occam's razor ←→ MDL ←→ Bayesian model selection
Information bottleneck ←→ rate-distortion ←→ deep learning compression
Landauer principle ←→ Maxwell's demon ←→ second law
Phi (IIT) ←→ integrated information ←→ consciousness
```
