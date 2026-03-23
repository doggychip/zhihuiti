# Meta-Framework Theories

## Overview
Four theories that operate across multiple domains — studying the structure of structure itself, the mathematics of analogical transfer, the physics of emergence at different scales, the unity of all algebraic systems, and the original cross-domain science of control and communication.

---

## 1. Structure Mapping Theory (Gentner 1983)

**Core claim:** Analogical reasoning works by mapping relational structure from a source domain to a target domain, not by matching surface features.

**Structure Mapping Engine (SME):**
```
Analogy: Source → Target
Mapping M = {(s_i, t_i)} where s_i ∈ Source, t_i ∈ Target
```

**Systematicity principle:** Good analogies preserve higher-order relations (relations between relations), not just object attributes.

**Structure Mapping Axioms:**
1. **One-to-one mapping:** Each element in source maps to at most one target element
2. **Parallel connectivity:** If (R x y) maps to (R' x' y'), then x→x' and y→y'
3. **Systematicity:** Prefer mappings that preserve connected relational systems

**Formal representation:**
```
Source: solar_system(sun, planets)
        more_massive(sun, planet)
        attracts(sun, planet)
        revolves_around(planet, sun)

Target: atom(nucleus, electrons)
        more_massive(nucleus, electron)
        attracts(nucleus, electron)
        revolves_around(electron, nucleus)

Mapping: sun ↔ nucleus, planet ↔ electron
Inferences: electron has an orbit; nucleus has planets' other properties
```

**Analogical inference:** Once mapping is established, transfer relations from source to target:
- "The electron revolves around the nucleus in an elliptical orbit?" (candidate inference)
- Evaluate by testing against target domain knowledge

**Computational SME:**
1. Match local predicates → generate match hypotheses
2. Coalesce consistent hypotheses → global mappings (gMAPS)
3. Score by systematicity → select best mapping
4. Extract candidate inferences

**Cross-domain:** This is the meta-theory of all cross-domain science. Every historical collision (Shannon/Boltzmann, Hopfield/Ising, Black-Scholes/heat equation) is explained by SME: systematic relational structure transfers across domain boundaries.

**Applications:** Analogical learning in AI (analogy-making engines), scientific discovery, education (teaching by analogy), legal reasoning (case-based), design innovation.

---

## 2. Renormalization Group Theory (Wilson 1971)

**Core idea:** Understand how physical laws change with the scale of observation. Fixed points of renormalization transformations describe universal behavior near phase transitions.

**Block spin transformation (Kadanoff 1966):**
```
σ'_I = sign(Σ_{i∈block I} σ_i)    [coarse-graining]
H'(σ') = R[H(σ)]                   [renormalization transformation]
```

**RG flow:**
```
dg/dl = β(g)    [beta function]
```
where g = coupling constants, l = length scale (l → ∞ means zooming out), β = RG beta function.

**Fixed points:** β(g*) = 0. Near fixed point g* + δg:
```
d(δg_i)/dl = Σ_j M_ij δg_j
Eigenvalues λ_i:
  λ_i > 0 → relevant (grows, important at large scales)
  λ_i < 0 → irrelevant (shrinks, unimportant at large scales)
  λ_i = 0 → marginal
```

**Universality:** Different microscopic systems flow to the same fixed point → same critical exponents, same large-scale behavior. Explains why Ising model in 3D matches liquid-gas critical point exactly.

**Critical exponents:**
```
Correlation length: ξ ~ |T - T_c|^{-ν}
Order parameter:    m ~ (T_c - T)^β
Susceptibility:     χ ~ |T - T_c|^{-γ}
```
These are universal — depend only on dimensionality d and symmetry group, not microscopic details.

**Scaling relations:**
```
α + 2β + γ = 2    [Rushbrooke]
γ = ν(2-η)        [Fisher]
dν = 2-α          [hyperscaling]
```

**Effective field theory:** At each scale, write down most general action consistent with symmetries. Irrelevant operators don't affect low-energy physics.

**Cross-domain:**
- Deep learning: each neural network layer = RG transformation (Mehta & Schwab 2014). Training = learning fixed point of input distribution.
- Complex networks: scale-free behavior near critical points
- Linguistics: Zipf's law as near-critical RG fixed point
- Economy: financial markets near critical points show universal scaling
- Emergence: RG explains why macro-theories are self-contained (irrelevant operators die out)
- Wilsonian effective theories: why chemistry doesn't need QFT details

---

## 3. Universal Algebra

**Core idea:** Study all algebraic structures simultaneously by identifying common patterns. "Algebra of algebras."

**Signature Σ = (F, ar):** Set of operation symbols F with arities ar: F → ℕ.

**Algebra A = (A, F^A):** Carrier set A with concrete operations F^A implementing each symbol.

**Example:**
```
Groups: Σ = {·, ⁻¹, e}, ar(·)=2, ar(⁻¹)=1, ar(e)=0
Rings:  Σ = {+, ·, -, 0, 1}, ar(+)=ar(·)=2, ar(-)=1, ar(0)=ar(1)=0
Lattices: Σ = {∨, ∧}, ar(∨)=ar(∧)=2
```

**Homomorphism h: A → B:** Preserves all operations:
```
h(f^A(a₁,...,aₙ)) = f^B(h(a₁),...,h(aₙ))
```

**Isomorphism:** Bijective homomorphism with inverse. A ≅ B means "same structure."

**Variety (equational class):** Class of algebras defined by a set of equations (identities).
```
Group variety: x·(y·z) = (x·y)·z,  x·e = x,  x·x⁻¹ = e
```

**Birkhoff's Theorem (1935):** A class of algebras is a variety iff it is closed under:
1. Homomorphic images H(K)
2. Subalgebras S(K)
3. Direct products P(K)
```
Variety = HSP(K)
```

**Free algebras F_Σ(X):** Generated by set X with no relations except universal axioms. Universal object: every algebra A with map X→A extends uniquely through F_Σ(X).

**Term algebra T_Σ(X):** Algebra of all terms (syntax trees) over signature Σ and variables X.

**Subdirectly irreducible algebras:** Cannot be embedded in proper product — atomic building blocks of variety.

**Cross-domain:**
- Logic (algebraic logic, Boolean algebras as models of propositional logic)
- Type theory (algebraic data types, monoids, monads)
- Database theory (relational algebra)
- Concurrency (process algebras: CCS, CSP)
- Quantum mechanics (operator algebras, C*-algebras)
- Programming languages (abstract data types as algebras, compiler semantics)
- Neural networks (equivariant architectures = algebras of symmetry groups)

---

## 4. Cybernetics (Wiener 1948; Ashby 1956)

**Core claim:** Control and communication are fundamentally the same problem in any system — biological, mechanical, or social.

**Feedback loop:**
```
Set point r → [Controller] → u → [Plant] → output y
                    ↑_________________________|
                          error e = r - y
```

**Requisite variety (Ashby's Law of Requisite Variety):**
```
V(D) ≥ V(R) / V(K)
```
where:
- V(D) = variety of disturbances (number of distinct states environment can be in)
- V(R) = variety of outcomes (acceptable goal states)
- V(K) = variety of controller (number of distinct responses controller can make)

**Interpretation:** "Only variety can destroy variety." To control a system with n states, controller must have at least n states. The brain's complexity reflects the complexity of the environments it must regulate.

**Good Regulator Theorem (Conant & Ashby 1970):**
```
Every good regulator of a system must be a model of that system.
```
Optimal control requires internal model of the controlled system. This theorem justifies internal models in brains, robots, and economic planning.

**Homeostasis:** Essential variables maintained within viability bounds despite perturbation:
```
e(t) ∈ [e_min, e_max]  ∀t    [viability constraint]
```

**Ultrastability:** System that reorganizes its feedback structure when homeostasis fails:
```
if e(t) ∉ [e_min, e_max]: change feedback parameters
```

**Second-order cybernetics (von Foerster):** Observer included in system. Cybernetics of cybernetics. Constructivism.

**Turing's influence:** Cybernetics + computation theory → AI. Wiener explicitly discussed automata and brains as isomorphic.

**Cross-domain:**
- Control theory (cybernetics was the precursor)
- Systems biology (metabolic regulation, gene circuits)
- Cognitive science (Friston's free energy = cybernetic homeostasis)
- Organizational theory (management cybernetics, Beer's Viable System Model)
- Social systems (Luhmann's systems theory)
- AI (reinforcement learning = cybernetic control)
- Robotics (behavior-based robotics)

---

## Key Meta-Pattern

These four theories share a crucial property: they are theories *about* theories.

```
Structure Mapping  ← meta-theory of analogy (why cross-domain works)
Renormalization    ← meta-theory of scale (why macro-theories are autonomous)
Universal Algebra  ← meta-theory of algebra (what all structures share)
Cybernetics        ← meta-theory of control (what all regulators share)
```

**The central claim:** Mathematical structure is substrate-independent. The same equations govern different phenomena because they share abstract relational structure. Structure mapping is the cognitive mechanism; renormalization explains why the structure survives across scales; universal algebra provides the mathematics of common structure; cybernetics was the first systematic project to exploit this.
