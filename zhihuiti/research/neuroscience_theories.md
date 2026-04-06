# Neuroscience Theories

## Overview
Eight foundational neuroscience theories spanning synaptic learning, neural selection, global communication, brain networks, plasticity, social cognition, and sleep. Each has mathematical formalisms and cross-domain connections to ML, physics, and computation.

---

## 1. Hebbian Learning

**Core rule ("neurons that fire together wire together"):**
```
Δw_ij = η · x_i · x_j
```
**Variables:** w_ij = synaptic weight, x_i = presynaptic activity, x_j = postsynaptic activity, η = learning rate.

**Problem:** Unbounded weight growth (positive feedback). Solutions:

**Oja's rule (normalized Hebb):**
```
Δw_ij = η(x_i x_j - x_j² w_ij)
```
Converges to first principal component of input covariance.

**BCM rule (Bienenstock, Cooper, Munro 1982):**
```
Δw_j = η x_j (x_post - θ_M) x_pre
θ_M = 〈x_post²〉  [sliding threshold]
```
LTP when x_post > θ_M, LTD when x_post < θ_M.

**Spike-Timing-Dependent Plasticity (STDP):**
```
Δw = A+ exp(-Δt/τ+)  if Δt > 0  (pre before post → LTP)
Δw = -A- exp(Δt/τ-)  if Δt < 0  (post before pre → LTD)
```

**Cross-domain:** Unsupervised learning, PCA (Oja), Hopfield networks (Hebb storage rule), temporal difference learning (STDP ↔ eligibility traces).

---

## 2. Neural Darwinism (Edelman, 1987)

**Three principles:**
1. **Primary repertoire:** Developmental variation generates diverse neuronal groups (genetically + epigenetically determined)
2. **Secondary repertoire:** Experience-dependent selection amplifies effective groups via Hebbian synaptic strengthening
3. **Reentrant signaling:** Bidirectional connections between maps synchronize and integrate signals

**Group selection equation (conceptual):**
```
fitness(group G) ∝ Σ_i correlation(G_i response, behavioral value)
ΔP(G) ∝ P(G) · [fitness(G) - mean_fitness]    [replicator dynamics analog]
```

**Reentry:** Not feedback — simultaneous, recursive signaling across parallel pathways. Creates temporal binding of distributed representations.

**Cross-domain:** Evolutionary algorithms (selection without instruction), immune system (clonal selection), cultural evolution, reinforcement learning (reward modulates Hebbian changes).

---

## 3. Global Workspace Theory (Baars, 1988; Dehaene formalization)

**Architecture:** Specialized processors + central global workspace with long-range broadcasting.

**Consciousness = ignition:** Local processing → threshold reached → sudden broadcast to global workspace → conscious awareness.

**Dehaene's neuronal equations:**
```
dA_i/dt = -A_i + S(Σ_j w_ij A_j + I_i + noise)    [local processing]
Broadcast when: Σ_i A_i > Θ_GW                      [ignition threshold]
```

**Predictions confirmed by EEG:**
- Late (~300ms) large-scale ignition for conscious stimuli
- "All-or-none" threshold phenomenon
- P3b wave = global workspace broadcast

**Cross-domain:**
- **Transformer attention:** Global workspace ↔ attention over all tokens
- **Blackboard architectures** in AI: shared workspace for heterogeneous modules
- **Broadcasting in distributed systems:** single source → all nodes

---

## 4. Connectomics

**Goal:** Complete mapping of all neurons and synapses in a nervous system.

**C. elegans:** 302 neurons, ~7,000 synapses — complete connectome (White et al. 1986).

**Graph-theoretic analysis:**
```
Adjacency matrix A: A_ij = strength of synapse i→j
Degree distribution: P(k) ~ k^{-γ} (scale-free in some regions)
Clustering coefficient: C = (triangles)/(triples)
Path length: L = mean shortest path between nodes
Small-world index: σ = (C/C_rand) / (L/L_rand) >> 1
```

**Hub nodes:** High-degree, high-betweenness neurons. Damage → disproportionate disruption (rich club organization).

**Human Connectome Project:** Diffusion MRI tractography, 80 brain regions, functional connectivity matrices.

**Cross-domain:** Network science (Watts-Strogatz small-world, Barabási-Albert scale-free), graph theory, systems biology (protein interaction networks), internet topology.

---

## 5. Neuroplasticity

**Forms:**
- **Synaptic plasticity:** LTP/LTD (minutes to hours)
- **Structural plasticity:** Spine growth/retraction (hours to days)
- **Adult neurogenesis:** New neurons in hippocampus (DG) and olfactory bulb
- **Cortical remapping:** Use-dependent expansion (London taxi drivers)

**LTP molecular cascade:**
```
NMDA receptor activation (needs pre+post coincidence, Mg²⁺ block removal)
→ Ca²⁺ influx
→ CaMKII activation
→ AMPA receptor insertion + phosphorylation
→ Synaptic strengthening
```

**Homeostatic plasticity (synaptic scaling):**
```
w_ij ← w_ij · (target_rate / actual_rate)
```
Stabilizes firing rates globally — prevents runaway potentiation.

**Cross-domain:** Meta-learning (learning to learn), continual learning (avoiding catastrophic forgetting), transfer learning, curriculum learning, regularization (homeostasis ↔ weight decay).

---

## 6. Mirror Neuron Theory

**Discovery (Rizzolatti, di Pellegrino et al. 1992):**
F5 neurons in macaque fire both when monkey performs action AND observes same action performed by another.

**"Mirror system" properties:**
- Action-coded, not movement-coded
- Multimodal (visual + motor + auditory for some actions)
- Strictly congruent vs. broadly congruent neurons

**Simulation theory of mind:**
```
Observed_action → motor representation activation → understanding via simulation
```
Rather than: observed_action → inference via theory of mind

**Human homolog:** Broca's area (IFG) + inferior parietal lobe. BOLD activation during action observation + execution.

**Controversy:** MNS as explanation for autism (broken mirrors hypothesis — not well supported). Imitation, language evolution, empathy — role debated.

**Cross-domain:** Embodied cognition, social learning in RL (imitation learning), inverse kinematics, motor planning.

---

## 7. Default Mode Network (Raichle et al. 2001)

**Regions:** Medial prefrontal cortex, posterior cingulate cortex, angular gyrus, hippocampus, medial temporal lobe.

**Task-negative activation:** DMN deactivates during externally-focused tasks (attention, working memory); activates at rest.

**Functions:** Self-referential processing, mind-wandering, future simulation, social cognition, episodic memory retrieval.

**Resting-state fMRI measures:**
```
BOLD signal correlation matrix C_ij = corr(BOLD_i(t), BOLD_j(t))
Graph partition: modularity Q = Σ_{community c} [L_c/L - (d_c/2L)²]
```
DMN = one of 7-8 large-scale resting-state networks.

**Anti-correlation:** DMN anti-correlates with dorsal attention network (task-positive). Competition for cognitive resources.

**Predictive coding interpretation:** DMN maintains generative model of self and world. External tasks suppress this model; rest allows model updating.

**Cross-domain:** AI autoencoder (DMN = internal generative model), default/exploratory behavior in RL, world model learning.

---

## 8. Synaptic Homeostasis Hypothesis (SHY — Tononi & Cirelli, 2003)

**Core claim:** Waking = net synaptic potentiation; Sleep (slow-wave) = global synaptic downscaling.

**SHY equations:**
```
During wake:    〈w〉 increases (Hebbian + noisy LTP)
During sleep:   Δw_ij = -α · w_ij    (proportional downscaling)
Net effect:     w_ij → w_ij · (1 - α · T_sleep)
```
Maintains synaptic weights in dynamic range; prevents saturation.

**Slow-wave activity (SWA):** EEG 0.5-4 Hz oscillations during NREM sleep. SWA intensity ∝ prior wake duration and learning intensity.

**Evidence:** Spine density increases during wake, decreases during sleep (mouse cortex, de Vivo et al. 2017). Sleep after learning improves memory consolidation.

**Memory consolidation:** Selected synapses tagged (synaptic tagging & capture) survive downscaling. Strong memories persist; noise is pruned.

**Cross-domain:**
- ML regularization: sleep = weight decay/pruning
- Continual learning: sleep prevents catastrophic interference
- Model compression: prune during "sleep" phase
- Variational inference: KL regularization term in ELBO = synaptic homeostasis
