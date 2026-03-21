# Cognitive Science Theories

## Overview
Nine foundational cognitive science theories spanning probabilistic inference, prediction, free energy, embodiment, and distributed cognition. These theories define the modern computational and philosophical framework for understanding mind.

---

## 1. Bayesian Brain Hypothesis

**Core claim:** The brain implements approximate Bayesian inference to estimate hidden states of the world.

**Bayes' theorem:**
```
P(H|D) = P(D|H) · P(H) / P(D)
posterior ∝ likelihood × prior
```

**Perception as inference:**
```
P(world | sensory data) ∝ P(sensory data | world) · P(world)
```

**Bayesian perceptual model:**
- **Prior:** P(s) — expectations about world states
- **Likelihood:** P(d|s) — generative model of sensory data
- **Posterior:** P(s|d) — updated belief after observation
- **Prediction:** ŝ = E[s|d] or MAP = argmax P(s|d)

**Evidence:** Cue combination (Ernst & Banks 2002): visual + haptic size perception combines optimally (inverse-variance weighting):
```
ŝ = (σ_v⁻² s_v + σ_h⁻² s_h) / (σ_v⁻² + σ_h⁻²)
σ_combined⁻² = σ_v⁻² + σ_h⁻²
```

**Cross-domain:** Kalman filter (linear-Gaussian Bayesian), particle filter (nonlinear), variational inference (approximate Bayesian), ML (all supervised learning is implicit Bayesian inference).

---

## 2. Predictive Coding (Rao & Ballard 1999; Friston)

**Hierarchical generative model:**
```
Level l predictions: μ_l = f(μ_{l+1})
Prediction errors:   ε_l = x_l - μ_l
Weight by precision: π_l = Σ_l⁻¹  [inverse covariance]
```

**Update rules:**
```
dμ_l/dt = -ε_l + ∂f(μ_{l+1})/∂μ_l · ε_{l+1}     [update predictions]
dε_l/dt = x_l - μ_l - ε_l                          [update errors]
```

**Two streams:**
- **Feedforward:** Prediction errors (what's surprising) — bottom-up
- **Feedback:** Predictions (what's expected) — top-down

**Empirical support:** Top-down connections in cortex (V1 ← V2 ← V4 ← IT) carry predictions; bottom-up carry prediction errors. Mismatch negativity (MMN) = prediction error signal in EEG.

**Equivalence:** Predictive coding = variational Bayes with Laplace approximation = hierarchical Kalman filter for linear-Gaussian case.

**Cross-domain:** Transformer architecture (attention = precision weighting), residual networks (learn prediction errors), denoising autoencoders, world models in RL.

---

## 3. Free Energy Principle (Friston, 2010)

**Core claim:** All biological systems minimize their variational free energy (surprise) over time.

**Variational free energy F:**
```
F = E_q[log q(s) - log p(o,s)]
  = D_KL[q(s) || p(s|o)] - log p(o)
  ≥ -log p(o)    [F is an upper bound on surprise]
```

**Variables:**
- `s` — hidden states of world
- `o` — observations
- `q(s)` — recognition density (approximate posterior)
- `p(o,s)` — generative model

**Two ways to minimize F:**
1. **Perception (update q):** Minimize D_KL — bring beliefs in line with evidence
2. **Action:** Change observations to match predictions (minimize surprise actively)

**Active inference:** Agent acts to fulfill predictions, not to maximize reward:
```
a* = argmin_a F(o(a), q)
```

**Mathematical form:**
```
F = -〈log p(o|s)〉_q + D_KL[q(s) || p(s)]
  = Complexity - Accuracy
  = Energy - Entropy (free energy formulation)
```

**Cross-domain:** Thermodynamic free energy (Helmholtz: F = U - TS), ELBO in VAEs, RL (reward = negative surprise), consciousness (awareness = low free energy states).

---

## 4. Embodied Cognition (Varela, Thompson, Rosch; Lakoff & Johnson)

**Core claim:** Cognition is not computation in an abstract symbol system — it is grounded in bodily experience and sensorimotor interaction.

**Enactivism:** Cognition = autonomous action-perception loops.
```
Perception-action cycle:
action → environmental change → perception → action ...
```

**Conceptual metaphor theory (Lakoff & Johnson):**
Abstract concepts are structured by bodily metaphors:
- "ARGUMENT IS WAR" (we attack, defend, shoot down positions)
- "TIME IS MONEY" (spend, waste, save time)
- "MORE IS UP" (prices rise, spirits soar)

**Grounded cognition:** Simulations of sensorimotor states underlie concept use. Brain areas for action activate during language about action.

**Mathematical challenges to classical cognition:**
- Frame problem: symbol systems cannot efficiently update all relevant knowledge
- Binding problem: where are symbols bound in the brain?
- Symbol grounding problem (Harnad): how do symbols get meaning?

**Cross-domain:** Robotics (behavior-based robotics, Brooks), RL (embodied agents), developmental AI, cognitive linguistics.

---

## 5. Extended Mind Thesis (Clark & Chalmers 1998)

**Core claim:** Mental states and processes can extend beyond the skin/skull into tools and environment.

**Parity principle:** If a component of the world functions in a way that, were it done in the head, we would count it as cognitive — then it is cognitive.

**Otto and Inga thought experiment:**
- Inga has internal memory of museum location
- Otto has Alzheimer's; uses notebook as external memory
- **Claim:** Otto's notebook is part of his cognitive system

**Conditions for cognitive extension:**
1. Constant availability
2. Automatically endorsed without scrutiny
3. Accessible as needed

**Active externalism:** Mind leaks into world through tools (notebooks, smartphones, language).

**Coupling-constitution fallacy response:** Just because brain is coupled to tool doesn't mean tool is constitutively cognitive.

**Cross-domain:** Human-computer interaction design, augmented cognition, distributed computing (where is "the program"?), social cognition (collective intelligence).

---

## 6. Cognitive Load Theory (Sweller 1988)

**Working memory model (Baddeley):**
- **Phonological loop:** ~2 seconds of verbal material
- **Visuospatial sketchpad:** ~4 items
- **Central executive:** Attention control
- **Episodic buffer:** Integration

**Capacity limits:**
```
Miller's law: 7 ± 2 chunks in working memory
Cowan's estimate: 4 ± 1 chunks
```

**Three types of cognitive load:**
1. **Intrinsic load:** Complexity inherent to material (element interactivity)
2. **Extraneous load:** Load from poor instructional design
3. **Germane load:** Load devoted to schema formation

**Instructional design principle:**
```
Total load = Intrinsic + Extraneous + Germane ≤ WM capacity
```
Minimize extraneous, manage intrinsic, allocate germane.

**Mathematical formalization:**
```
Interactivity I = number of elements that must be considered simultaneously
Load ∝ I × difficulty per element
```

**Cross-domain:** UI/UX design, AI explanation interfaces, curriculum design in ML training, attention mechanisms (limited capacity), memory-augmented neural networks.

---

## 7. Dual Process Theory (Kahneman, Stanovich & West)

**Two systems:**

| Property | System 1 | System 2 |
|----------|----------|----------|
| Speed | Fast | Slow |
| Effort | Automatic | Deliberate |
| Logic | Associative | Rule-based |
| Consciousness | Unconscious | Conscious |
| Parallel | Yes | Serial |
| Error-prone | Heuristics/biases | Rational |

**System 1 heuristics:**
- **Availability:** Judge frequency by ease of recall
- **Representativeness:** Judge probability by similarity
- **Anchoring:** Over-weight initial value

**Prospect Theory (Kahneman & Tversky 1979):**
```
V(x) = { x^α              if x ≥ 0
        { -λ(-x)^β        if x < 0
```
with α=β≈0.88, λ≈2.25 (loss aversion), and nonlinear probability weighting w(p).

**Cross-domain:** ML (fast ≈ cached/approximate inference, slow ≈ MCTS/exact inference), AlphaGo (System 1 ≈ policy network, System 2 ≈ MCTS), economics (behavioral economics), AI safety (biased System 1 ↔ adversarial examples).

---

## 8. Situated Cognition (Suchman 1987; Clancey)

**Core claim:** Intelligent behavior is not the execution of stored plans — it is improvised, context-sensitive action.

**Suchman's "plans and situated actions":**
Plans are resources for action, not deterministic programs. Actual behavior emerges from moment-to-moment interaction with situation.

**Affordances (Gibson):**
```
Affordance = relationship between organism capabilities and environment properties
```
Perception is direct detection of affordances, not inference from sensory data.

**Mathematical challenges to planning:**
- Classical planning (STRIPS) assumes closed-world
- Real environments: open, unpredictable, ambiguous
- Reactive architectures (Brooks subsumption) outperform deliberative planning in dynamic domains

**Implications:**
- Intelligence is not "in the head" alone
- Behavior is constituted by organism-environment coupling
- Learning must be situated (context-dependent)

**Cross-domain:** Robotics (reactive control vs. deliberative planning), multi-agent systems, HCI, RL (environment as co-constructor of behavior).

---

## 9. Distributed Cognition (Hutchins 1995)

**Core claim:** Cognitive systems extend across individuals, artifacts, and the environment. The unit of analysis is the system, not the individual.

**Cockpit as cognitive system:**
- Instruments encode and transform information
- Crew propagates representations through the system
- Landing: cognitive work distributed across humans + instruments

**State propagation:**
```
System state = (internal representations, artifact states, inter-agent communication)
Cognitive process = transformation and propagation of representational state
```

**Coordination mechanisms:**
- **Shared mental models:** Overlapping task knowledge
- **Transactive memory systems:** Who knows what
- **Artifacts as scaffolding:** External representations reduce cognitive load

**Stigmergy:** Indirect coordination through environment modification (ants, human organizations).

**Cross-domain:** Multi-agent systems design, CSCW (computer-supported cooperative work), collective intelligence, Wikipedia as distributed cognitive system, blockchain as distributed ledger.

---

## Key Cross-Domain Bridges

```
Bayesian brain ←→ Kalman filter ←→ predictive coding (all same math)
Free energy principle ←→ ELBO (VAE) ←→ thermodynamic free energy
System 1/2 ←→ fast/slow RL (policy network vs. MCTS)
Embodied cognition ←→ reactive robotics ←→ embodied RL
Extended mind ←→ tool use in AI ←→ memory-augmented neural nets
Distributed cognition ←→ multi-agent systems ←→ collective intelligence
Cognitive load ←→ attention bottleneck ←→ transformer design
```
