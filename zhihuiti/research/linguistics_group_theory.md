# Formal Linguistics & Group Theory

## Overview
Two foundational theories that provide the mathematical scaffolding for computation (Chomsky hierarchy) and symmetry (group theory). Both appear across physics, biology, computer science, and AI.

---

## Part 1: Formal Linguistics / Chomsky Hierarchy

### Core: Formal Grammar

**Grammar G = (V, Σ, R, S):**
- **V** = variables (nonterminals)
- **Σ** = terminal alphabet (V ∩ Σ = ∅)
- **R** = production rules (finite set of α → β)
- **S ∈ V** = start symbol

**Language L(G) = {w ∈ Σ* : S ⟹* w}** (all strings derivable from S)

---

### The Chomsky Hierarchy

| Level | Grammar type | Automaton | Rule form | Example |
|-------|-------------|-----------|-----------|---------|
| Type 0 | Unrestricted | Turing machine | α → β (any) | Any decidable language |
| Type 1 | Context-sensitive | Linear-bounded automaton | αAβ → αγβ | aⁿbⁿcⁿ |
| Type 2 | Context-free | Pushdown automaton | A → γ | aⁿbⁿ, arithmetic exprs |
| Type 3 | Regular | Finite automaton | A → aB or A → a | (ab)*, email patterns |

**Strict inclusion:** Type 3 ⊂ Type 2 ⊂ Type 1 ⊂ Type 0

---

### Regular Languages (Type 3)

**Finite automaton M = (Q, Σ, δ, q₀, F):**
- Q = states, δ: Q×Σ → Q (transition function), q₀ = start, F = accepting states

**Kleene's theorem:** Regular language ↔ finite automaton ↔ regular expression

**Pumping lemma:** If L is regular and |w| ≥ p (pumping length), then w = xyz with |xy| ≤ p, |y| ≥ 1, and xyⁿz ∈ L for all n ≥ 0.

---

### Context-Free Languages (Type 2)

**Pushdown automaton:** Finite automaton + unbounded stack.

**CNF (Chomsky Normal Form):** Every rule is A → BC or A → a.

**CYK algorithm:** O(n³) parsing of CNF grammars.

**Pumping lemma for CFLs:** w = uvxyz, |vxy| ≤ p, |vy| ≥ 1, uvⁿxyⁿz ∈ L.

**Not context-free:** aⁿbⁿcⁿ, copy language {ww}, palindromes over {a,b,c}.

**Applications:** Programming language syntax (most PLs are CFG-parseable), XML/JSON parsing, natural language syntax (approximately CFG).

---

### Generative Grammar (Chomsky 1957)

**Transformational-generative grammar:**
- Deep structure: underlying logical form
- Surface structure: actual utterance
- Transformations map deep → surface (passivization, question formation)

**Principles and Parameters (GB/Minimalism):**
- Universal Grammar (UG): innate linguistic knowledge
- Parameters set by exposure: head direction, pro-drop, wh-movement
- "Merge" = basic operation: combine two objects into one

**Syntax-semantics interface:** Logical Form (LF) derived from surface structure → compositional semantics.

---

### Connections

```
Regular        ←→  Finite automata  ←→  Regular expressions ←→  Recurrent neural states
Context-free   ←→  Pushdown automata ←→  Parse trees ←→  Recursive data structures
Context-sensitive ←→ LBA ←→  Mildly context-sensitive: tree-adjoining grammar (TAG)
Unrestricted   ←→  Turing machines ←→  Computable languages ←→  General computation
```

**DNA / Biology:**
- DNA = string over {A, T, G, C}
- Protein synthesis = context-sensitive transformation (ribosome = LBA)
- Gene regulatory networks = finite automata
- RNA secondary structure = context-free language (nested base pairs)

**NLP:**
- Neural LMs (Transformers) empirically recognize beyond CFG (superlinear counting tasks)
- Transformers with hard attention = circuits over TC⁰

---

## Part 2: Group Theory

### Core Definition

**Group G = (G, ·, ⁻¹, e):** Set G with operation satisfying:
```
Closure:      a · b ∈ G
Associativity: (a·b)·c = a·(b·c)
Identity:     a·e = e·a = a
Inverse:      a·a⁻¹ = a⁻¹·a = e
```

**Order |G|:** Number of elements (finite groups) or ∞.

**Subgroup H ≤ G:** H is a group under G's operation.

**Lagrange's theorem:** |H| divides |G| for finite groups.

**Normal subgroup N ◁ G:** gN g⁻¹ = N for all g ∈ G. Quotient group G/N well-defined.

**Simple groups:** No nontrivial normal subgroups. Classification of finite simple groups (CFSG): 18 infinite families + 26 sporadic groups (Monster, etc.).

---

### Symmetry Groups

**Cyclic group Cₙ:** Rotations of regular n-gon. Cₙ = 〈r | rⁿ = e〉.

**Dihedral group D_{2n}:** Symmetries of regular n-gon (rotations + reflections). |D_{2n}| = 2n.

**Symmetric group Sₙ:** All permutations of n elements. |Sₙ| = n!

**Alternating group Aₙ:** Even permutations. |Aₙ| = n!/2. First non-abelian simple group: A₅ ≅ icosahedral group.

---

### Lie Groups and Lie Algebras

**Lie group G:** Group that is also a smooth manifold. Group operations smooth.

**Examples:**
```
U(1) = {e^{iθ}: θ ∈ ℝ}    (circle group, electromagnetism)
SU(2) = {A ∈ M₂(ℂ): AA† = I, det A = 1}   (weak force, spin-½)
SU(3) = {A ∈ M₃(ℂ): AA† = I, det A = 1}   (strong force, color)
SO(3) = {A ∈ M₃(ℝ): AA^T = I, det A = 1}   (3D rotations)
GL(n,ℝ) = {invertible n×n real matrices}
```

**Lie algebra g = T_e G** (tangent space at identity):
```
[X, Y] = XY - YX    [Lie bracket / commutator]
```

**Exponential map:** exp: g → G, exp(tX) = curve through e with velocity X.

**Generators of SU(2):** Pauli matrices σₓ, σᵧ, σᵤ satisfy [σᵢ, σⱼ] = 2iεᵢⱼₖ σₖ.

**Generators of SU(3):** Gell-Mann matrices λ₁,...,λ₈. Structure constants fᵢⱼₖ.

---

### Representation Theory

**Representation ρ: G → GL(V):** Homomorphism from G to invertible linear maps on vector space V.

**Irreducible representation (irrep):** No non-trivial invariant subspace.

**Schur's lemma:** Intertwining operator between non-isomorphic irreps must be zero; between same irrep must be scalar multiple of identity.

**Character χ_ρ(g) = Tr(ρ(g)):** Class function (constant on conjugacy classes).

**Orthogonality:**
```
(1/|G|) Σ_g χ_ρ(g) χ_σ(g)* = δ_{ρσ}
```

**Peter-Weyl theorem:** L²(G) = ⊕_ρ V_ρ ⊗ V_ρ* (decomposition into irreps).

---

### Noether's Theorem

**Statement:** Every continuous symmetry of a physical system corresponds to a conserved quantity.

| Symmetry | Conserved quantity |
|----------|-------------------|
| Time translation | Energy |
| Space translation | Linear momentum |
| Rotation (SO(3)) | Angular momentum |
| U(1) phase rotation | Electric charge |
| SU(2) (weak isospin) | Weak isospin |
| SU(3) (color) | Color charge |

**Mathematical form:**
```
δS = 0 under x → x + εX implies ∂_μ J^μ = 0 (continuity equation)
```
where J^μ is the Noether current.

---

### Gauge Symmetry

**Gauge symmetry = local symmetry:** Transformation parameters depend on spacetime point.

**U(1) gauge symmetry (electromagnetism):**
```
ψ → e^{iα(x)} ψ
∂_μ → D_μ = ∂_μ + ieA_μ    [covariant derivative]
A_μ → A_μ - (1/e)∂_μα     [gauge transformation of field]
```
Requiring local U(1) invariance forces existence of photon field A_μ.

**Yang-Mills (non-abelian gauge theory):**
```
F_μν = ∂_μA_ν - ∂_νA_μ + g[A_μ, A_ν]    [field strength tensor]
ℒ = -(1/4) Tr(F_μν F^μν)
```
Standard Model = U(1) × SU(2) × SU(3) gauge theory.

---

### Cross-Domain Connections

**Crystallography:** Space groups classify crystal symmetries (230 distinct). X-ray diffraction patterns = group-theoretic predictions.

**Chemistry:** Molecular symmetry (point groups) predicts IR/Raman spectra, orbital hybridization, optical activity.

**Topology:** Fundamental group π₁(X), homotopy groups πₙ(X) are groups. Galois theory: field extensions ↔ groups.

**Error-correcting codes:** Linear codes over finite fields. Reed-Solomon, Hamming codes use group algebra GF(2ⁿ).

**Machine Learning:**
- **Equivariant neural networks:** If input transforms by ρ(g), output transforms by ρ'(g)
  ```
  f(ρ(g)·x) = ρ'(g)·f(x)    [equivariance]
  ```
- **CNNs:** Translation equivariant (discrete translation group ℤ²)
- **Spherical CNNs:** SO(3)-equivariant
- **Graph neural networks:** Permutation equivariant (Sₙ)
- **E(n)-equivariant GNNs:** For 3D molecular structure

**Quantum mechanics:**
- Spin = representation of SU(2)
- Orbital = representation of SO(3)
- Particle multiplets = representations of SU(3) (quark model)
- Wigner-Eckart theorem: selection rules from group theory
