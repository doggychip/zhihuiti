// Auto-generated collision graph data from Silicon Realms theory engine
// Regenerate with: python3 -m silicon_realms.theory.visualize --json

export interface GraphNode {
  id: string;
  name: string;
  domain: string;
  color: string;
  equation: string;
}

export interface GraphLink {
  source: string;
  target: string;
  score: number;
  strength: "deep" | "significant" | "resonance" | "weak";
  shared_patterns: string[];
  bridges: string[];
}

export interface CollisionGraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  metadata: {
    total_theories: number;
    total_links: number;
    min_score: number;
  };
}

export const COLLISION_GRAPH_DATA: CollisionGraphData = {
  nodes: [
    { id: "attractor_dynamics", name: "Attractor Dynamics", domain: "Dynamic Systems", color: "#1abc9c", equation: "ẋ = f(x);  ∃V: V̇ ≤ 0 (Lyapunov function)" },
    { id: "bayesian_brain", name: "Bayesian Brain Hypothesis", domain: "Cognitive Science", color: "#8e44ad", equation: "P(H|D) ∝ P(D|H) · P(H)" },
    { id: "bellman_equation", name: "Bellman Equation (Dynamic Programming)", domain: "Control Theory", color: "#2ecc71", equation: "V*(s) = max_a [r(s,a) + γ V*(s')]" },
    { id: "boltzmann_distribution", name: "Boltzmann Distribution", domain: "Statistical Mechanics", color: "#e67e22", equation: "P(Eᵢ) = exp(−Eᵢ/kT) / Z" },
    { id: "chaos_theory", name: "Chaos Theory (Lorenz)", domain: "Dynamic Systems", color: "#1abc9c", equation: "λ = lim_{t→∞} (1/t) ln|δx(t)/δx(0)|  (Lyapunov exponent)" },
    { id: "ess", name: "Evolutionarily Stable Strategy", domain: "Evolutionary Game Theory", color: "#e74c3c", equation: "E(σ*,σ*) > E(σ,σ*)  OR  [= AND E(σ*,σ) > E(σ,σ)]" },
    { id: "free_energy_principle", name: "Free Energy Principle (Friston)", domain: "Cognitive Science", color: "#8e44ad", equation: "F = D_KL[q(s)‖p(s|o)] − log p(o) ≥ −log p(o)" },
    { id: "free_energy_thermo", name: "Helmholtz Free Energy", domain: "Statistical Mechanics", color: "#e67e22", equation: "F = U − TS = −kT ln Z" },
    { id: "hebbian_learning", name: "Hebbian Learning", domain: "Neuroscience", color: "#9b59b6", equation: "Δwᵢⱼ = η · xᵢ · xⱼ" },
    { id: "hopfield_network", name: "Hopfield Network", domain: "Neuroscience", color: "#9b59b6", equation: "E = −½ Σ wᵢⱼ sᵢ sⱼ;  sᵢ ← sgn(Σⱼ wᵢⱼ sⱼ)" },
    { id: "ising_model", name: "Ising Model", domain: "Statistical Mechanics", color: "#e67e22", equation: "H = −J Σ sᵢsⱼ − h Σ sᵢ" },
    { id: "kalman_filter", name: "Kalman Filter", domain: "Control Theory", color: "#2ecc71", equation: "x̂ = x̂⁻ + K(y − Cx̂⁻);  K = P⁻Cᵀ(CP⁻Cᵀ+R)⁻¹" },
    { id: "kl_divergence", name: "KL Divergence / Relative Entropy", domain: "Information Theory", color: "#3498db", equation: "D_KL(P‖Q) = Σ p(x) log[p(x)/q(x)] ≥ 0" },
    { id: "maxent", name: "Maximum Entropy Principle (Jaynes)", domain: "Information Theory", color: "#3498db", equation: "P*(x) = exp(−Σλₖfₖ(x)) / Z" },
    { id: "path_integral", name: "Feynman Path Integral", domain: "Quantum Physics", color: "#f39c12", equation: "Z = ∫ Dx exp(iS[x]/ℏ)" },
    { id: "persistent_homology", name: "Persistent Homology (TDA)", domain: "Topology", color: "#e91e63", equation: "βₖ(ε) = rank Hₖ(VR(X,ε));  persistence = death − birth" },
    { id: "pontryagin", name: "Pontryagin Maximum Principle", domain: "Control Theory", color: "#2ecc71", equation: "H(x,u,λ) = L + λᵀf;  λ̇ = −∂H/∂x;  u* = argmin H" },
    { id: "predictive_coding", name: "Predictive Coding", domain: "Neuroscience / Cognitive Science", color: "#9b59b6", equation: "ε_l = x_l − μ_l;  dμ_l/dt = −ε_l + (∂f/∂μ)ε_{l+1}" },
    { id: "renormalization_group", name: "Renormalization Group", domain: "Meta-Frameworks", color: "#34495e", equation: "dg/dl = β(g);  β(g*) = 0  (fixed point)" },
    { id: "replicator_dynamics", name: "Replicator Dynamics (EGT)", domain: "Evolutionary Game Theory", color: "#e74c3c", equation: "dxᵢ/dt = xᵢ(fᵢ(x) − φ(x))" },
    { id: "self_organized_criticality", name: "Self-Organized Criticality (Bak)", domain: "Dynamic Systems", color: "#1abc9c", equation: "P(s) ~ s^{−τ}  (avalanche size power law)" },
    { id: "shannon_entropy", name: "Shannon Information Theory", domain: "Information Theory", color: "#3498db", equation: "H(X) = −Σ p(x) log p(x)" },
    { id: "structure_mapping", name: "Structure Mapping Theory (Gentner)", domain: "Meta-Frameworks", color: "#34495e", equation: "Analogy: Source → Target via M: {(sᵢ,tᵢ)} preserving relations" },
  ],
  links: [
    { source: "attractor_dynamics", target: "ess", score: 0.07, strength: "weak", shared_patterns: ["fixed_point_stability"], bridges: ["'state' role: phase space point ↔ strategy"] },
    { source: "attractor_dynamics", target: "hopfield_network", score: 0.163, strength: "resonance", shared_patterns: ["attractor_dynamics", "gradient_descent"], bridges: ["Both converge to an attractor", "'energy' role: lyapunov function ↔ network energy", "'state' role: phase space point ↔ neuron activation"] },
    { source: "attractor_dynamics", target: "replicator_dynamics", score: 0.058, strength: "weak", shared_patterns: ["fixed_point_stability"], bridges: ["'state' role: phase space point ↔ strategy frequency"] },
    { source: "bayesian_brain", target: "boltzmann_distribution", score: 0.136, strength: "resonance", shared_patterns: [], bridges: ["Both conserve 'total probability'"] },
    { source: "bayesian_brain", target: "kalman_filter", score: 0.076, strength: "weak", shared_patterns: ["bayesian_inference"], bridges: [] },
    { source: "bayesian_brain", target: "maxent", score: 0.1, strength: "weak", shared_patterns: [], bridges: ["Both conserve 'total probability'"] },
    { source: "bayesian_brain", target: "replicator_dynamics", score: 0.136, strength: "resonance", shared_patterns: [], bridges: ["Both conserve 'total probability'"] },
    { source: "bayesian_brain", target: "shannon_entropy", score: 0.136, strength: "resonance", shared_patterns: [], bridges: ["Both conserve 'total probability'"] },
    { source: "boltzmann_distribution", target: "ess", score: 0.075, strength: "weak", shared_patterns: [], bridges: ["'score': energy ↔ payoff", "'state': microstate ↔ strategy"] },
    { source: "boltzmann_distribution", target: "free_energy_thermo", score: 0.136, strength: "resonance", shared_patterns: [], bridges: ["Both optimize 'minimize free energy'", "Both converge to equilibrium"] },
    { source: "boltzmann_distribution", target: "hopfield_network", score: 0.062, strength: "weak", shared_patterns: ["energy_based"], bridges: ["'state': microstate ↔ neuron activation"] },
    { source: "boltzmann_distribution", target: "ising_model", score: 0.071, strength: "weak", shared_patterns: ["energy_based"], bridges: ["'score': energy ↔ hamiltonian energy"] },
    { source: "boltzmann_distribution", target: "maxent", score: 0.35, strength: "significant", shared_patterns: ["exponential_family", "normalization", "temperature_controls_sharpness"], bridges: ["Both conserve 'total probability'"] },
    { source: "boltzmann_distribution", target: "replicator_dynamics", score: 0.233, strength: "resonance", shared_patterns: ["conservation_of_probability"], bridges: ["Both converge to equilibrium", "'score': energy ↔ fitness", "'state': microstate ↔ strategy frequency"] },
    { source: "boltzmann_distribution", target: "shannon_entropy", score: 0.181, strength: "resonance", shared_patterns: ["conservation_of_probability"], bridges: ["Both conserve 'total probability'"] },
    { source: "ess", target: "replicator_dynamics", score: 0.116, strength: "weak", shared_patterns: ["fixed_point_stability"], bridges: ["'score': payoff ↔ fitness", "'state': strategy ↔ strategy frequency"] },
    { source: "free_energy_principle", target: "free_energy_thermo", score: 0.113, strength: "weak", shared_patterns: ["energy_entropy_tradeoff", "variational_principle"], bridges: [] },
    { source: "free_energy_principle", target: "kalman_filter", score: 0.09, strength: "weak", shared_patterns: ["bayesian_inference", "prediction_error_correction"], bridges: [] },
    { source: "free_energy_principle", target: "kl_divergence", score: 0.056, strength: "weak", shared_patterns: [], bridges: ["'model': generative model p ↔ Q"] },
    { source: "free_energy_principle", target: "predictive_coding", score: 0.09, strength: "weak", shared_patterns: ["bayesian_inference", "prediction_error_correction"], bridges: [] },
    { source: "free_energy_thermo", target: "path_integral", score: 0.056, strength: "weak", shared_patterns: ["variational_principle"], bridges: [] },
    { source: "free_energy_thermo", target: "pontryagin", score: 0.056, strength: "weak", shared_patterns: ["variational_principle"], bridges: [] },
    { source: "hebbian_learning", target: "replicator_dynamics", score: 0.173, strength: "resonance", shared_patterns: ["above_average_grows", "multiplicative_update"], bridges: [] },
    { source: "hopfield_network", target: "ising_model", score: 0.19, strength: "resonance", shared_patterns: ["energy_based", "pairwise_coupling"], bridges: ["'state': neuron activation ↔ spin configuration"] },
    { source: "ising_model", target: "replicator_dynamics", score: 0.068, strength: "weak", shared_patterns: ["mean_field"], bridges: ["'score': hamiltonian energy ↔ fitness"] },
    { source: "ising_model", target: "self_organized_criticality", score: 0.054, strength: "weak", shared_patterns: ["critical_phenomena"], bridges: [] },
    { source: "kalman_filter", target: "predictive_coding", score: 0.229, strength: "resonance", shared_patterns: ["bayesian_inference", "precision_weighted_update", "prediction_error_correction"], bridges: ["'error': innovation ↔ prediction error"] },
    { source: "kl_divergence", target: "shannon_entropy", score: 0.083, strength: "weak", shared_patterns: [], bridges: [] },
    { source: "maxent", target: "path_integral", score: 0.081, strength: "weak", shared_patterns: ["variational_principle"], bridges: [] },
    { source: "maxent", target: "pontryagin", score: 0.1, strength: "weak", shared_patterns: ["dual_variables", "variational_principle"], bridges: [] },
    { source: "maxent", target: "replicator_dynamics", score: 0.1, strength: "weak", shared_patterns: [], bridges: ["Both conserve 'total probability'"] },
    { source: "maxent", target: "shannon_entropy", score: 0.125, strength: "resonance", shared_patterns: [], bridges: ["Both conserve 'total probability'"] },
    { source: "replicator_dynamics", target: "shannon_entropy", score: 0.177, strength: "resonance", shared_patterns: ["conservation_of_probability"], bridges: ["Both conserve 'total probability'"] },
  ],
  metadata: { total_theories: 23, total_links: 33, min_score: 0.05 },
};

export const DOMAIN_COLORS: Record<string, string> = {
  "Evolutionary Game Theory": "#e74c3c",
  "Statistical Mechanics": "#e67e22",
  "Control Theory": "#2ecc71",
  "Information Theory": "#3498db",
  "Neuroscience": "#9b59b6",
  "Neuroscience / Cognitive Science": "#9b59b6",
  "Cognitive Science": "#8e44ad",
  "Dynamic Systems": "#1abc9c",
  "Quantum Physics": "#f39c12",
  "Meta-Frameworks": "#34495e",
  "Topology": "#e91e63",
};

export const STRENGTH_COLORS: Record<string, string> = {
  deep: "#e74c3c",
  significant: "#e67e22",
  resonance: "#3498db",
  weak: "#2c3e50",
};
