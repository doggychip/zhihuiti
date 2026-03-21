# Topology Theories

## Overview
Eight foundational topology theories from persistent homology through category theory. Topology studies properties preserved under continuous deformation — it is the mathematics of shape, connectivity, and structure. These theories bridge pure mathematics, physics, data analysis, and computation.

---

## 1. Topological Data Analysis (Persistent Homology)

**Core idea:** Detect topological features (connected components, loops, voids) in data across multiple scales, and track their "persistence."

**Vietoris-Rips complex:**
```
VR(X, ε) = simplicial complex with simplex {x₀,...,xₖ} iff d(xᵢ,xⱼ) ≤ ε ∀i,j
```

**Filtration:** Nested sequence of spaces at increasing ε:
```
∅ = VR(X, 0) ⊆ VR(X, ε₁) ⊆ VR(X, ε₂) ⊆ ... ⊆ VR(X, ∞) = Δ^{n-1}
```

**Betti numbers βₖ:** Rank of k-th homology group Hₖ:
```
β₀ = # connected components
β₁ = # independent loops / holes
β₂ = # enclosed voids
```

**Persistence diagram:** Plot (birth εᵢ, death εⱼ) for each topological feature. Long-lived features = "significant" topology.

**Bottleneck distance between diagrams:**
```
d_B(D₁, D₂) = inf_{bijection γ} sup_{x∈D₁} ‖x - γ(x)‖_∞
```

**Applications:** Protein structure, brain networks, material science, natural language (topological text analysis), sensor networks.

**Cross-domain:** Data manifold shape analysis, homological algebra, algebraic K-theory, sheaf theory.

---

## 2. Topological Quantum Field Theory (Witten)

**Core idea:** QFTs whose correlation functions are topological invariants — independent of metric. Defined by Atiyah's axioms.

**Atiyah's TQFT axioms:**
- Functor Z: Cob → Vect (from cobordism category to vector spaces)
- To each (d-1)-manifold Σ: vector space Z(Σ) (Hilbert space of states)
- To each d-manifold M with ∂M = Σ: vector Z(M) ∈ Z(Σ) (partition function)
- Gluing: Z(M₁ ∪_Σ M₂) = 〈Z(M₁), Z(M₂)〉

**Chern-Simons theory (3D):**
```
S[A] = (k/4π) ∫_M Tr(A∧dA + (2/3)A∧A∧A)
```
Partition function Z(M) computes knot invariants (Jones polynomial).

**Witten's insight:** Jones polynomial of knot K = expectation value of Wilson loop:
```
V_K(q) = 〈Tr P exp(∮_K A)〉_{CS}
```

**Cross-domain:** Condensed matter (topological insulators, anyons), quantum computing (topological quantum computation is fault-tolerant), string theory (mirror symmetry, Gromov-Witten invariants).

---

## 3. Knot Theory

**Core idea:** Classify knots (embedded circles in 3D) up to isotopy (continuous deformation without cutting).

**Knot invariants:**

**Alexander polynomial Δ_K(t):**
```
Δ_{unknot}(t) = 1
Δ_{trefoil}(t) = t⁻¹ - 1 + t
Δ_{figure-eight}(t) = -t⁻¹ + 3 - t
```

**Jones polynomial V_K(q):** (Vaughan Jones 1984)
```
V_{unknot}(q) = 1
Skein relation: q⁻¹V(L₊) - qV(L₋) = (q^{1/2} - q^{-1/2})V(L₀)
```

**HOMFLY polynomial:** Generalization depending on two variables p, q.

**Reidemeister moves:** Three local moves that generate all isotopies:
- Move I: twist/untwist
- Move II: poke loop over/under
- Move III: slide strand over crossing

**Knot groups:** π₁(S³ \ K) = fundamental group of complement.

**Writhe and linking numbers:**
```
lk(K₁, K₂) = (1/2) Σ_{crossings} ε(c)    [linking number of two components]
```

**Cross-domain:** DNA topology (supercoiling, topoisomerases solve knot problems), protein folding (knot-like structures), quantum groups, braid groups in quantum computing.

---

## 4. Homotopy Type Theory (HoTT)

**Core idea:** Types (in type theory / programming) correspond to spaces (in topology). Equality corresponds to paths.

**Curry-Howard-Voevodsky correspondence:**
```
Type theory     ↔  Topology         ↔  Logic
Type A          ↔  Space A          ↔  Proposition A
Element a:A     ↔  Point a ∈ A      ↔  Proof a of A
Identity type a=b ↔  Path from a to b ↔  Equality proof
```

**Univalence axiom (Voevodsky):**
```
(A ≃ B) ≃ (A = B)
```
"Isomorphic types are equal." Formalizes mathematical practice: work up to isomorphism.

**Higher inductive types:** Types defined by points AND paths:
```
Circle S¹: point base : S¹
           path loop : base = base
```

**∞-groupoid:** Every type has a tower of identities (paths, paths between paths, etc.) — matches topology of spaces.

**Applications:** Formal verification of mathematics (Lean, Coq use HoTT-inspired type theories), foundations of mathematics independent of set theory.

**Cross-domain:** Category theory (type = object, function = morphism), dependent type theory (proof assistants), topology (spaces), logic.

---

## 5. Manifold Learning / Manifold Hypothesis

**Manifold hypothesis:** High-dimensional real data (images, text, speech) lies near a low-dimensional manifold embedded in high-dimensional space.

**Intrinsic dimension d << ambient dimension D.**

**Isomap (Tenenbaum et al. 2000):**
1. Build neighborhood graph with k-NN
2. Compute geodesic distances d_G(x_i, x_j) via Dijkstra/Floyd
3. Apply MDS to geodesic distance matrix → low-d embedding

**LLE (Roweis & Saul 2000):**
1. Find k neighbors of each point
2. Reconstruct each point from neighbors: min Σᵢ ‖xᵢ - Σⱼ Wᵢⱼxⱼ‖²
3. Find low-d coordinates that preserve W: min Σᵢ ‖yᵢ - Σⱼ Wᵢⱼyⱼ‖²

**UMAP (McInnes et al. 2018):**
Fuzzy topological representation:
```
μ(x_i, x_j) = exp(-max(0, d(x_i,x_j) - ρᵢ)/σᵢ)
```
Optimize cross-entropy between fuzzy sets of high-d and low-d representations.

**Diffusion maps:** Normalized graph Laplacian eigendecomposition reveals intrinsic geometry:
```
L = D⁻¹W,  L φₖ = λₖ φₖ
Diffusion distance: d_t²(x,y) = Σₖ λₖ^{2t} (φₖ(x) - φₖ(y))²
```

**Cross-domain:** Dimensionality reduction (PCA is linear manifold learning), variational autoencoders (learn manifold latent space), generative models (learn data manifold distribution), neuroscience (representational geometry of neural responses).

---

## 6. Morse Theory

**Core idea:** Understand topology of a manifold M from critical points of a smooth function f: M → ℝ.

**Critical point:** df(p) = 0 (gradient vanishes). Index k = number of negative eigenvalues of Hessian.

**Morse lemma:** Near non-degenerate critical point of index k:
```
f = f(p) - x₁² - ... - xₖ² + xₖ₊₁² + ... + xₙ²    [local normal form]
```

**Handle decomposition:** M is built by attaching k-handles at each index-k critical point:
- Index 0: attach disk (local min)
- Index 1: attach 1-handle (saddle, creates tunnel)
- Index n: attach top-disk (local max)

**Morse inequalities:**
```
βₖ ≤ Cₖ     [k-th Betti number ≤ number of index-k critical points]
Σₖ (-1)ᵏ Cₖ = χ(M)   [Euler characteristic]
```

**Gradient flow lines:** Connect critical points. Witten's Morse theory: gradient flow lines = instantons in supersymmetric QM.

**Persistent Morse theory:** Link Morse theory to TDA — sublevel set filtration Mₜ = f⁻¹(-∞, t].

**Cross-domain:** Loss landscape analysis in ML (critical points, saddle avoidance), protein energy landscapes, TDA (Morse-Smale complexes), quantum field theory (Morse theory = SUSY QM).

---

## 7. Network Topology & Graph Theory

**Fundamental quantities:**
```
Degree: k_i = Σ_j A_ij
Strength: s_i = Σ_j w_ij  (weighted)
Clustering coefficient: C_i = (triangles through i) / (possible triangles)
Betweenness centrality: b_i = Σ_{s≠t} σ_st(i)/σ_st
```

**Euler characteristic:**
```
χ = V - E + F    [for planar graphs: χ = 2]
χ = Σₖ (-1)ᵏ βₖ  [topological definition]
```

**Spectral graph theory:**
Laplacian L = D - A (D = degree matrix, A = adjacency matrix).
```
Lx = λx
λ₀ = 0 (always), λ₁ = algebraic connectivity (Fiedler value)
# connected components = multiplicity of λ₀
```

**Random graph models:**
- Erdős-Rényi G(n,p): P(edge) = p, Poisson degree distribution
- Watts-Strogatz: small-world (high clustering, low path length)
- Barabási-Albert: preferential attachment, P(k) ~ k^{-γ} scale-free

**Percolation threshold:** Giant component emerges at 〈k〉 = 1 for ER graphs.

**Cross-domain:** Social networks, internet topology, brain connectomics, protein interaction networks, epidemics (R₀ depends on network structure), ecological food webs.

---

## 8. Category Theory

**Core objects:**
- **Objects** (abstract, no internal structure assumed)
- **Morphisms** f: A → B (arrows between objects)
- **Composition** g∘f: A → C for f: A→B, g: B→C
- **Identity** id_A: A → A

**Axioms:**
```
Associativity: h∘(g∘f) = (h∘g)∘f
Unit laws: f∘id_A = f = id_B∘f
```

**Functor F: C → D:** Maps objects to objects, morphisms to morphisms, preserving composition:
```
F(g∘f) = F(g)∘F(f),  F(id_A) = id_{F(A)}
```

**Natural transformation η: F ⇒ G:** Family of morphisms η_A: F(A) → G(A) such that:
```
η_B ∘ F(f) = G(f) ∘ η_A    [naturality square commutes]
```

**Adjunction F ⊣ G:**
```
Hom_D(F(A), B) ≅ Hom_C(A, G(B))    [natural bijection]
```
"F is left adjoint to G." Free-forgetful adjunctions are ubiquitous.

**Yoneda lemma:**
```
Nat(Hom(A,-), F) ≅ F(A)
```
An object is completely determined by the morphisms into/out of it. One of the most important theorems in mathematics.

**Limits and colimits:** Universal constructions — products, coproducts, equalizers, pullbacks, pushouts.

**Monad (T, η, μ):** Functor T with natural transformations η: Id⇒T (unit) and μ: T²⇒T (multiplication) satisfying monoid laws.

**Cross-domain:**
- Programming (functors/monads in Haskell, typed effects)
- Logic (internal language of a topos)
- Physics (TQFT as functor Cob → Vect)
- ML (compositionality, equivariant networks, functorial data migration)
- Databases (schema mappings as functors)
- Proof theory (propositions as objects, proofs as morphisms)
- Neural networks (Lenses/optics for backpropagation, functorial mechanics)
