"""
Theory Collision Engine
=======================
A computational Structure Mapping Engine that identifies mathematical
isomorphisms between theories across domains.

Based on Gentner's Structure Mapping Theory: analogies work by matching
relational structure (higher-order relations), not surface features.

Usage:
    from silicon_realms.theory import collide
    report = collide("replicator_dynamics", "kalman_filter")
    print(report)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Theory Registry
# Each theory is described by its abstract mathematical properties:
#   - update_form:    how state evolves (the "verb" of the theory)
#   - optimization:   what objective is minimized/maximized
#   - fixed_points:   conditions for equilibrium
#   - operators:      key mathematical operations
#   - patterns:       abstract structural patterns
#   - variables:      semantic roles of key variables
#   - conservation:   what is conserved
#   - domain:         originating field
# ---------------------------------------------------------------------------

THEORY_REGISTRY: dict[str, dict] = {

    # ── Evolutionary Game Theory ──────────────────────────────────────────
    "replicator_dynamics": {
        "display_name": "Replicator Dynamics (EGT)",
        "domain": "Evolutionary Game Theory",
        "equation": "dxᵢ/dt = xᵢ(fᵢ(x) − φ(x))",
        "update_form": "multiplicative_error_correction",
        "optimization": "maximize_mean_fitness",
        "fixed_points": "nash_equilibrium",
        "operators": {"multiply", "subtract_mean", "normalize", "differential"},
        "patterns": {
            "selection",
            "frequency_dependent",
            "mean_field",
            "fixed_point_stability",
            "multiplicative_update",
            "above_average_grows",
            "conservation_of_probability",
        },
        "variables": {
            "state": "strategy_frequency",
            "score": "fitness",
            "reference": "mean_fitness",
            "noise": None,
        },
        "conservation": {"total_probability"},
        "structure": "ode_on_simplex",
    },

    "ess": {
        "display_name": "Evolutionarily Stable Strategy",
        "domain": "Evolutionary Game Theory",
        "equation": "E(σ*,σ*) > E(σ,σ*)  OR  [= AND E(σ*,σ) > E(σ,σ)]",
        "update_form": "invasion_stability_check",
        "optimization": "maximize_payoff",
        "fixed_points": "ess_is_lyapunov_stable",
        "operators": {"comparison", "payoff_matrix", "fixed_point"},
        "patterns": {
            "stability_under_perturbation",
            "nash_equilibrium",
            "fixed_point_stability",
            "game_theoretic_equilibrium",
            "robustness",
        },
        "variables": {"state": "strategy", "score": "payoff", "reference": "resident_strategy"},
        "conservation": set(),
        "structure": "equilibrium_concept",
    },

    # ── Statistical Mechanics ─────────────────────────────────────────────
    "boltzmann_distribution": {
        "display_name": "Boltzmann Distribution",
        "domain": "Statistical Mechanics",
        "equation": "P(Eᵢ) = exp(−Eᵢ/kT) / Z",
        "update_form": "exponential_weighting",
        "optimization": "minimize_free_energy",
        "fixed_points": "thermal_equilibrium",
        "operators": {"exponential", "normalize", "partition_function", "temperature_scale"},
        "patterns": {
            "exponential_family",
            "energy_based",
            "temperature_controls_sharpness",
            "normalization",
            "conservation_of_probability",
            "maximum_entropy_subject_to_mean_energy",
        },
        "variables": {
            "state": "microstate",
            "score": "energy",
            "reference": "temperature",
            "normalizer": "partition_function",
        },
        "conservation": {"total_probability"},
        "structure": "probability_distribution",
    },

    "ising_model": {
        "display_name": "Ising Model",
        "domain": "Statistical Mechanics",
        "equation": "H = −J Σ sᵢsⱼ − h Σ sᵢ",
        "update_form": "energy_minimization_with_noise",
        "optimization": "minimize_hamiltonian",
        "fixed_points": "magnetized_or_disordered_phase",
        "operators": {"pairwise_interaction", "external_field", "sum", "sign"},
        "patterns": {
            "energy_based",
            "pairwise_coupling",
            "phase_transition",
            "spontaneous_symmetry_breaking",
            "order_parameter",
            "mean_field",
            "critical_phenomena",
        },
        "variables": {
            "state": "spin_configuration",
            "score": "hamiltonian_energy",
            "coupling": "interaction_strength",
            "field": "external_bias",
        },
        "conservation": set(),
        "structure": "energy_landscape_on_discrete_config_space",
    },

    "free_energy_thermo": {
        "display_name": "Helmholtz Free Energy",
        "domain": "Statistical Mechanics",
        "equation": "F = U − TS = −kT ln Z",
        "update_form": "legendre_transform_of_energy",
        "optimization": "minimize_free_energy",
        "fixed_points": "thermodynamic_equilibrium",
        "operators": {"entropy", "temperature_scale", "legendre_transform", "logarithm"},
        "patterns": {
            "energy_entropy_tradeoff",
            "temperature_controls_tradeoff",
            "variational_principle",
            "generating_function",
        },
        "variables": {
            "energy": "internal_energy",
            "entropy": "boltzmann_entropy",
            "temperature": "kT",
        },
        "conservation": set(),
        "structure": "thermodynamic_potential",
    },

    # ── Control Theory ────────────────────────────────────────────────────
    "kalman_filter": {
        "display_name": "Kalman Filter",
        "domain": "Control Theory",
        "equation": "x̂ = x̂⁻ + K(y − Cx̂⁻);  K = P⁻Cᵀ(CP⁻Cᵀ+R)⁻¹",
        "update_form": "predict_then_correct",
        "optimization": "minimize_mean_squared_error",
        "fixed_points": "steady_state_riccati",
        "operators": {"predict", "update", "weight_by_precision", "covariance", "bayes_rule"},
        "patterns": {
            "prediction_error_correction",
            "precision_weighted_update",
            "bayesian_inference",
            "hierarchical_estimation",
            "optimal_under_gaussian_noise",
            "recursive",
        },
        "variables": {
            "state": "hidden_state_estimate",
            "error": "innovation",
            "gain": "kalman_gain",
            "uncertainty": "covariance",
        },
        "conservation": set(),
        "structure": "recursive_bayesian_estimator",
    },

    "bellman_equation": {
        "display_name": "Bellman Equation (Dynamic Programming)",
        "domain": "Control Theory",
        "equation": "V*(s) = max_a [r(s,a) + γ V*(s')]",
        "update_form": "recursive_value_propagation",
        "optimization": "maximize_cumulative_reward",
        "fixed_points": "optimal_value_function",
        "operators": {"maximize", "expectation", "discount", "recursive_decomposition"},
        "patterns": {
            "recursive_decomposition",
            "fixed_point_iteration",
            "dynamic_programming",
            "temporal_credit_assignment",
            "value_function",
            "optimality_principle",
        },
        "variables": {
            "state": "system_state",
            "score": "value",
            "discount": "gamma",
            "reward": "immediate_reward",
        },
        "conservation": set(),
        "structure": "recursive_functional_equation",
    },

    "pontryagin": {
        "display_name": "Pontryagin Maximum Principle",
        "domain": "Control Theory",
        "equation": "H(x,u,λ) = L + λᵀf;  λ̇ = −∂H/∂x;  u* = argmin H",
        "update_form": "hamiltonian_optimization",
        "optimization": "minimize_integral_cost",
        "fixed_points": "optimal_trajectory",
        "operators": {"hamiltonian", "costate", "boundary_conditions", "minimize"},
        "patterns": {
            "dual_variables",
            "variational_principle",
            "hamiltonian_mechanics",
            "adjoint_equations",
            "optimality_conditions",
        },
        "variables": {
            "state": "system_trajectory",
            "costate": "adjoint_variable",
            "control": "input",
        },
        "conservation": {"hamiltonian_along_optimal_trajectory"},
        "structure": "calculus_of_variations",
    },

    # ── Information Theory ────────────────────────────────────────────────
    "shannon_entropy": {
        "display_name": "Shannon Information Theory",
        "domain": "Information Theory",
        "equation": "H(X) = −Σ p(x) log p(x)",
        "update_form": "probability_weighted_log_sum",
        "optimization": "maximize_entropy_subject_to_constraints",
        "fixed_points": "uniform_distribution_maximizes_entropy",
        "operators": {"logarithm", "expectation", "sum", "normalize"},
        "patterns": {
            "uncertainty_measure",
            "conservation_of_probability",
            "maximum_entropy",
            "additive_over_independent_sources",
            "chain_rule",
        },
        "variables": {"distribution": "probability", "uncertainty": "entropy_bits"},
        "conservation": {"total_probability"},
        "structure": "functional_of_probability_distribution",
    },

    "maxent": {
        "display_name": "Maximum Entropy Principle (Jaynes)",
        "domain": "Information Theory",
        "equation": "P*(x) = exp(−Σλₖfₖ(x)) / Z",
        "update_form": "constrained_entropy_maximization",
        "optimization": "maximize_entropy_subject_to_moment_constraints",
        "fixed_points": "exponential_family_distribution",
        "operators": {"lagrange_multipliers", "exponential", "partition_function", "constraints"},
        "patterns": {
            "exponential_family",
            "least_informative_prior",
            "variational_principle",
            "temperature_controls_sharpness",
            "normalization",
            "dual_variables",
        },
        "variables": {
            "distribution": "probability",
            "multipliers": "lagrange_multipliers",
            "normalizer": "partition_function",
        },
        "conservation": {"total_probability"},
        "structure": "constrained_optimization_over_distributions",
    },

    "kl_divergence": {
        "display_name": "KL Divergence / Relative Entropy",
        "domain": "Information Theory",
        "equation": "D_KL(P‖Q) = Σ p(x) log[p(x)/q(x)] ≥ 0",
        "update_form": "measure_of_distribution_difference",
        "optimization": "minimize_kl_to_target",
        "fixed_points": "P = Q",
        "operators": {"logarithm", "ratio", "expectation", "non_negative"},
        "patterns": {
            "asymmetric_distance",
            "information_gain",
            "variational_inference",
            "prediction_error",
            "surprise",
        },
        "variables": {"model": "Q", "target": "P", "divergence": "information_gain"},
        "conservation": set(),
        "structure": "f_divergence",
    },

    # ── Neuroscience ──────────────────────────────────────────────────────
    "hebbian_learning": {
        "display_name": "Hebbian Learning",
        "domain": "Neuroscience",
        "equation": "Δwᵢⱼ = η · xᵢ · xⱼ",
        "update_form": "correlation_based_weight_update",
        "optimization": "maximize_correlation",
        "fixed_points": "principal_components",
        "operators": {"multiply", "correlate", "outer_product", "normalize"},
        "patterns": {
            "correlation_learning",
            "unsupervised",
            "multiplicative_update",
            "above_average_grows",
            "local_learning_rule",
        },
        "variables": {
            "weight": "synaptic_strength",
            "input": "presynaptic_activity",
            "output": "postsynaptic_activity",
        },
        "conservation": set(),
        "structure": "online_learning_rule",
    },

    "hopfield_network": {
        "display_name": "Hopfield Network",
        "domain": "Neuroscience",
        "equation": "E = −½ Σ wᵢⱼ sᵢ sⱼ;  sᵢ ← sgn(Σⱼ wᵢⱼ sⱼ)",
        "update_form": "energy_minimization",
        "optimization": "minimize_energy_function",
        "fixed_points": "stored_memories_as_attractors",
        "operators": {"pairwise_interaction", "sign_activation", "sum", "gradient_descent"},
        "patterns": {
            "energy_based",
            "attractor_dynamics",
            "pairwise_coupling",
            "content_addressable_memory",
            "gradient_descent",
        },
        "variables": {
            "state": "neuron_activation",
            "weight": "synaptic_matrix",
            "energy": "network_energy",
        },
        "conservation": {"energy_non_increasing_under_updates"},
        "structure": "energy_landscape_on_binary_config_space",
    },

    "predictive_coding": {
        "display_name": "Predictive Coding",
        "domain": "Neuroscience / Cognitive Science",
        "equation": "ε_l = x_l − μ_l;  dμ_l/dt = −ε_l + (∂f/∂μ)ε_{l+1}",
        "update_form": "hierarchical_error_propagation",
        "optimization": "minimize_prediction_error",
        "fixed_points": "beliefs_match_sensory_input",
        "operators": {"subtract", "predict", "update", "hierarchical", "precision_weight"},
        "patterns": {
            "prediction_error_correction",
            "hierarchical_inference",
            "top_down_prediction",
            "bottom_up_error",
            "precision_weighted_update",
            "bayesian_inference",
        },
        "variables": {
            "prediction": "top_down_belief",
            "error": "prediction_error",
            "precision": "inverse_noise_variance",
        },
        "conservation": set(),
        "structure": "hierarchical_generative_model",
    },

    # ── Cognitive Science ─────────────────────────────────────────────────
    "free_energy_principle": {
        "display_name": "Free Energy Principle (Friston)",
        "domain": "Cognitive Science",
        "equation": "F = D_KL[q(s)‖p(s|o)] − log p(o) ≥ −log p(o)",
        "update_form": "variational_inference",
        "optimization": "minimize_variational_free_energy",
        "fixed_points": "beliefs_match_posterior",
        "operators": {"kl_divergence", "evidence_lower_bound", "variational", "expectation"},
        "patterns": {
            "variational_principle",
            "energy_entropy_tradeoff",
            "bayesian_inference",
            "prediction_error_correction",
            "active_inference",
            "surprise_minimization",
        },
        "variables": {
            "belief": "recognition_density_q",
            "model": "generative_model_p",
            "free_energy": "variational_bound",
        },
        "conservation": set(),
        "structure": "variational_bound_on_surprise",
    },

    "bayesian_brain": {
        "display_name": "Bayesian Brain Hypothesis",
        "domain": "Cognitive Science",
        "equation": "P(H|D) ∝ P(D|H) · P(H)",
        "update_form": "bayesian_belief_update",
        "optimization": "maximize_posterior_probability",
        "fixed_points": "posterior_as_optimal_belief",
        "operators": {"bayes_rule", "likelihood", "prior", "normalize"},
        "patterns": {
            "bayesian_inference",
            "prior_to_posterior",
            "likelihood_weighting",
            "optimal_inference",
            "uncertainty_representation",
        },
        "variables": {
            "hypothesis": "world_state",
            "data": "sensory_observation",
            "prior": "expectation",
            "posterior": "belief",
        },
        "conservation": {"total_probability"},
        "structure": "probabilistic_inference",
    },

    # ── Dynamic Systems ───────────────────────────────────────────────────
    "attractor_dynamics": {
        "display_name": "Attractor Dynamics",
        "domain": "Dynamic Systems",
        "equation": "ẋ = f(x);  ∃V: V̇ ≤ 0 (Lyapunov function)",
        "update_form": "gradient_flow_to_attractor",
        "optimization": "minimize_lyapunov_function",
        "fixed_points": "attractor_states",
        "operators": {"vector_field", "gradient", "lyapunov", "stability_analysis"},
        "patterns": {
            "energy_minimization",
            "gradient_descent",
            "fixed_point_stability",
            "basin_of_attraction",
            "attractor_dynamics",
        },
        "variables": {
            "state": "phase_space_point",
            "energy": "lyapunov_function",
            "flow": "vector_field",
        },
        "conservation": {"energy_non_increasing"},
        "structure": "dissipative_dynamical_system",
    },

    "chaos_theory": {
        "display_name": "Chaos Theory (Lorenz)",
        "domain": "Dynamic Systems",
        "equation": "λ = lim_{t→∞} (1/t) ln|δx(t)/δx(0)|  (Lyapunov exponent)",
        "update_form": "sensitive_dependence_on_ics",
        "optimization": None,
        "fixed_points": "unstable_fixed_points_and_strange_attractor",
        "operators": {"exponential_divergence", "lyapunov_exponent", "fractal_dimension"},
        "patterns": {
            "sensitive_dependence",
            "strange_attractor",
            "fractal_structure",
            "unpredictability",
            "deterministic_yet_random",
        },
        "variables": {
            "state": "phase_space_trajectory",
            "divergence": "lyapunov_exponent",
        },
        "conservation": {"phase_space_volume_contracts_on_attractor"},
        "structure": "nonlinear_ode_with_positive_lyapunov",
    },

    "self_organized_criticality": {
        "display_name": "Self-Organized Criticality (Bak)",
        "domain": "Dynamic Systems",
        "equation": "P(s) ~ s^{−τ}  (avalanche size power law)",
        "update_form": "threshold_cascade",
        "optimization": None,
        "fixed_points": "critical_point_as_attractor_of_dynamics",
        "operators": {"threshold", "cascade", "power_law", "scale_free"},
        "patterns": {
            "scale_free",
            "power_law",
            "critical_phenomena",
            "no_characteristic_scale",
            "self_tuning_criticality",
            "avalanche_statistics",
        },
        "variables": {
            "state": "slope_or_stress",
            "event": "avalanche_size",
            "exponent": "tau",
        },
        "conservation": set(),
        "structure": "driven_dissipative_system_at_criticality",
    },

    # ── Quantum Physics ───────────────────────────────────────────────────
    "path_integral": {
        "display_name": "Feynman Path Integral",
        "domain": "Quantum Physics",
        "equation": "Z = ∫ Dx exp(iS[x]/ℏ)",
        "update_form": "sum_over_histories",
        "optimization": "stationary_action_principle",
        "fixed_points": "classical_path",
        "operators": {"functional_integral", "action", "exponential", "sum_over_paths"},
        "patterns": {
            "sum_over_histories",
            "variational_principle",
            "partition_function",
            "saddle_point_approximation",
            "exponential_weighting",
        },
        "variables": {
            "path": "history",
            "weight": "exp(iS/hbar)",
            "action": "integral_of_lagrangian",
        },
        "conservation": {"unitarity"},
        "structure": "functional_integral",
    },

    # ── Meta-Frameworks ───────────────────────────────────────────────────
    "renormalization_group": {
        "display_name": "Renormalization Group",
        "domain": "Meta-Frameworks",
        "equation": "dg/dl = β(g);  β(g*) = 0  (fixed point)",
        "update_form": "coarse_graining_iteration",
        "optimization": "flow_to_fixed_point",
        "fixed_points": "universality_class_fixed_point",
        "operators": {"coarse_grain", "rescale", "integrate_out", "flow"},
        "patterns": {
            "scale_invariance",
            "universality",
            "fixed_points",
            "relevant_irrelevant_marginal",
            "hierarchical_decomposition",
            "critical_phenomena",
        },
        "variables": {
            "couplings": "coupling_constants",
            "scale": "length_scale",
            "flow": "beta_function",
        },
        "conservation": {"long_wavelength_physics"},
        "structure": "semigroup_of_coarse_graining_transformations",
    },

    "structure_mapping": {
        "display_name": "Structure Mapping Theory (Gentner)",
        "domain": "Meta-Frameworks",
        "equation": "Analogy: Source → Target via M: {(sᵢ,tᵢ)} preserving relations",
        "update_form": "relational_alignment",
        "optimization": "maximize_systematicity",
        "fixed_points": "best_mapping",
        "operators": {"align", "map", "transfer", "infer"},
        "patterns": {
            "structural_isomorphism",
            "relational_transfer",
            "one_to_one_mapping",
            "systematicity_principle",
        },
        "variables": {
            "source": "base_domain",
            "target": "target_domain",
            "mapping": "correspondence",
        },
        "conservation": {"relational_structure"},
        "structure": "graph_homomorphism",
    },

    # ── Topology ──────────────────────────────────────────────────────────
    "persistent_homology": {
        "display_name": "Persistent Homology (TDA)",
        "domain": "Topology",
        "equation": "βₖ(ε) = rank Hₖ(VR(X,ε));  persistence = death − birth",
        "update_form": "filtration_tracking",
        "optimization": None,
        "fixed_points": "topological_features_at_multiple_scales",
        "operators": {"filtration", "homology", "persistence", "betti_numbers"},
        "patterns": {
            "multi_scale_analysis",
            "topological_invariants",
            "birth_death_of_features",
            "scale_free_description",
        },
        "variables": {
            "scale": "epsilon",
            "topology": "betti_numbers",
            "lifetime": "persistence",
        },
        "conservation": {"topological_invariants"},
        "structure": "filtered_simplicial_complex",
    },

    "morse_theory": {
        "display_name": "Morse Theory",
        "domain": "Topology",
        "equation": "χ(M) = Σ (−1)^k cₖ;  ∇f(p)=0 ⇒ index(p) = # negative eigenvalues of Hf",
        "update_form": "gradient_flow_to_critical_points",
        "optimization": "minimize_morse_function",
        "fixed_points": "critical_points_by_index",
        "operators": {"gradient", "hessian", "index", "handle_attachment", "flow"},
        "patterns": {
            "energy_minimization",
            "gradient_descent",
            "fixed_point_stability",
            "birth_death_of_features",
            "multi_scale_analysis",
            "topological_invariants",
            "energy_based",
        },
        "variables": {
            "state": "point_on_manifold",
            "energy": "morse_function",
            "flow": "negative_gradient_flow",
            "curvature": "hessian_eigenvalues",
        },
        "conservation": {"euler_characteristic"},
        "structure": "gradient_dynamical_system_on_manifold",
    },

    # ── Category Theory ──────────────────────────────────────────────────
    "category_theory": {
        "display_name": "Category Theory",
        "domain": "Meta-Frameworks",
        "equation": "F: C → D (functor);  η: F ⇒ G (natural transformation);  F ⊣ G (adjunction)",
        "update_form": "functorial_mapping",
        "optimization": "universal_properties",
        "fixed_points": "terminal_initial_objects",
        "operators": {"functor", "natural_transformation", "adjoint", "limit", "colimit", "composition"},
        "patterns": {
            "structural_isomorphism",
            "relational_transfer",
            "hierarchical_decomposition",
            "universality",
            "one_to_one_mapping",
            "compositional_structure",
        },
        "variables": {
            "source": "category_C",
            "target": "category_D",
            "mapping": "functor",
            "transformation": "natural_transformation",
        },
        "conservation": {"relational_structure", "compositional_structure"},
        "structure": "abstract_algebraic_framework",
    },

    # ── Evolutionary Game Theory (extended) ──────────────────────────────
    "price_equation": {
        "display_name": "Price Equation (Multilevel Selection)",
        "domain": "Evolutionary Game Theory",
        "equation": "w̄ Δz̄ = Cov(w,z) + E(wΔz)",
        "update_form": "covariance_driven_selection",
        "optimization": "maximize_mean_fitness",
        "fixed_points": "selection_transmission_balance",
        "operators": {"covariance", "expectation", "decomposition", "recursive_decomposition"},
        "patterns": {
            "selection",
            "frequency_dependent",
            "hierarchical_decomposition",
            "bayesian_inference",
            "mean_field",
            "above_average_grows",
            "recursive_decomposition",
            "conservation_of_probability",
        },
        "variables": {
            "state": "trait_frequency",
            "score": "fitness",
            "reference": "mean_fitness",
            "trait": "phenotype_value",
        },
        "conservation": {"total_probability"},
        "structure": "statistical_decomposition_of_evolutionary_change",
    },

    # ── Information Theory (extended) ────────────────────────────────────
    "fisher_information": {
        "display_name": "Fisher Information",
        "domain": "Information Theory",
        "equation": "I(θ)ᵢⱼ = E[(∂log p/∂θᵢ)(∂log p/∂θⱼ)]  ≥  1/Var(θ̂)  (Cramér-Rao)",
        "update_form": "curvature_of_likelihood",
        "optimization": "minimize_estimation_variance",
        "fixed_points": "cramer_rao_bound",
        "operators": {"expectation", "logarithm", "gradient", "covariance", "matrix_inverse"},
        "patterns": {
            "precision_weighted_update",
            "bayesian_inference",
            "prediction_error",
            "information_gain",
            "variational_principle",
            "optimal_inference",
            "uncertainty_measure",
        },
        "variables": {
            "parameter": "true_value",
            "estimator": "maximum_likelihood",
            "precision": "fisher_matrix",
            "uncertainty": "cramer_rao_bound",
        },
        "conservation": set(),
        "structure": "riemannian_metric_on_statistical_manifold",
    },

    # ── Dynamic Systems (extended) ───────────────────────────────────────
    "reaction_diffusion": {
        "display_name": "Turing Reaction-Diffusion",
        "domain": "Dynamic Systems",
        "equation": "∂u/∂t = f(u,v) + Dᵤ∇²u;  ∂v/∂t = g(u,v) + Dᵥ∇²v",
        "update_form": "pattern_forming_instability",
        "optimization": None,
        "fixed_points": "spatially_periodic_patterns",
        "operators": {"laplacian", "reaction_kinetics", "linear_stability", "diffusion", "pairwise_interaction"},
        "patterns": {
            "phase_transition",
            "spontaneous_symmetry_breaking",
            "pairwise_coupling",
            "critical_phenomena",
            "order_parameter",
            "mean_field",
            "scale_invariance",
            "fixed_point_stability",
        },
        "variables": {
            "state": "concentration_field",
            "coupling": "diffusion_ratio",
            "field": "chemical_potential",
            "score": "pattern_wavelength",
        },
        "conservation": {"total_mass_in_closed_system"},
        "structure": "nonlinear_pde_with_turing_instability",
    },
}


# ---------------------------------------------------------------------------
# Similarity Engine
# ---------------------------------------------------------------------------

@dataclass
class CollisionReport:
    theory_a: str
    theory_b: str
    similarity_score: float
    shared_patterns: list[str]
    shared_operators: list[str]
    shared_variables: list[str]
    structural_bridges: list[str]
    interpretation: str
    collision_strength: str  # "deep", "significant", "resonance", "weak"

    def __str__(self) -> str:
        stars = {"deep": "●●●", "significant": "●●", "resonance": "●", "weak": "○"}
        s = stars.get(self.collision_strength, "?")
        lines = [
            f"\n{'='*60}",
            f"THEORY COLLISION: {self.theory_a}  ↔  {self.theory_b}",
            f"Strength: {s} ({self.collision_strength.upper()})  |  Score: {self.similarity_score:.3f}",
            f"{'='*60}",
        ]
        if self.shared_patterns:
            lines.append(f"\nShared Mathematical Patterns ({len(self.shared_patterns)}):")
            for p in self.shared_patterns:
                lines.append(f"  · {p.replace('_', ' ')}")
        if self.shared_operators:
            lines.append(f"\nShared Operators:")
            for o in self.shared_operators:
                lines.append(f"  · {o.replace('_', ' ')}")
        if self.structural_bridges:
            lines.append(f"\nStructural Bridges:")
            for b in self.structural_bridges:
                lines.append(f"  → {b}")
        lines.append(f"\nInterpretation:")
        lines.append(f"  {self.interpretation}")
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_coefficient(a: set, b: set) -> float:
    """Overlap coefficient: |A∩B| / min(|A|,|B|).  Less penalizing than Jaccard
    when one theory has many more patterns than the other."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


# Semantic clusters: patterns that are conceptually equivalent or closely related.
# If theory A has pattern X and theory B has pattern Y from the same cluster,
# that should boost similarity even though they don't share the exact string.
_PATTERN_CLUSTERS = [
    {"bayesian_inference", "prior_to_posterior", "likelihood_weighting", "optimal_inference",
     "precision_weighted_update", "information_gain"},
    {"energy_based", "energy_minimization", "energy_entropy_tradeoff", "gradient_descent"},
    {"prediction_error_correction", "prediction_error", "surprise", "surprise_minimization"},
    {"variational_principle", "variational_inference", "active_inference"},
    {"conservation_of_probability", "normalization", "total_probability"},
    {"phase_transition", "critical_phenomena", "spontaneous_symmetry_breaking", "order_parameter"},
    {"scale_invariance", "universality", "scale_free", "no_characteristic_scale", "power_law"},
    {"fixed_point_stability", "fixed_points", "fixed_point_iteration", "attractor_dynamics",
     "basin_of_attraction"},
    {"hierarchical_decomposition", "hierarchical_inference", "hierarchical_estimation",
     "multi_scale_analysis"},
    {"selection", "above_average_grows", "frequency_dependent"},
    {"multiplicative_update", "exponential_family", "exponential_weighting"},
    {"pairwise_coupling", "pairwise_interaction", "correlation_learning"},
    {"recursive_decomposition", "dynamic_programming", "recursive"},
    {"structural_isomorphism", "relational_transfer", "one_to_one_mapping"},
    {"dual_variables", "hamiltonian_mechanics", "adjoint_equations"},
    {"topological_invariants", "birth_death_of_features", "multi_scale_analysis"},
    {"uncertainty_measure", "uncertainty_representation", "maximum_entropy"},
]


def _semantic_pattern_sim(pa: set, pb: set) -> float:
    """Compute semantic similarity by counting shared cluster memberships
    beyond exact pattern matches."""
    if not pa or not pb:
        return 0.0
    # Direct overlap
    direct = len(pa & pb)
    # Cluster-mediated overlap: for each cluster, if both theories touch it
    cluster_hits = 0
    for cluster in _PATTERN_CLUSTERS:
        a_in = pa & cluster
        b_in = pb & cluster
        if a_in and b_in:
            # Count unique cross-cluster matches (not already direct)
            cross = (a_in - pb) & cluster
            if cross and (b_in - pa):
                cluster_hits += 1
    # Combine: direct Jaccard + cluster bonus
    jaccard = direct / len(pa | pb) if (pa | pb) else 0.0
    overlap = direct / min(len(pa), len(pb)) if min(len(pa), len(pb)) > 0 else 0.0
    cluster_bonus = cluster_hits * 0.04
    return min(1.0, 0.4 * jaccard + 0.4 * overlap + 0.2 * cluster_bonus / max(1, len(_PATTERN_CLUSTERS) * 0.1))


def _structural_bridges(ta: dict, tb: dict) -> list[str]:
    """Generate natural-language descriptions of the mathematical bridges."""
    bridges = []

    # Same update form
    if ta["update_form"] == tb["update_form"]:
        bridges.append(
            f"Both use '{ta['update_form'].replace('_', ' ')}' — same update mechanism"
        )

    # Same optimization target
    if ta["optimization"] and tb["optimization"] and ta["optimization"] == tb["optimization"]:
        bridges.append(
            f"Both optimize '{ta['optimization'].replace('_', ' ')}'"
        )

    # Same fixed point structure
    if ta["fixed_points"] and tb["fixed_points"]:
        fp_a = ta["fixed_points"]
        fp_b = tb["fixed_points"]
        # Check for semantic matches in fixed point descriptions
        for kw in ["equilibrium", "fixed_point", "attractor", "optimal", "minimum", "maximum"]:
            if kw in fp_a and kw in fp_b:
                bridges.append(f"Both converge to a {kw.replace('_', ' ')}")
                break

    # Shared variable roles
    shared_var_roles = set(ta["variables"].keys()) & set(tb["variables"].keys())
    for role in shared_var_roles:
        va = ta["variables"][role]
        vb = tb["variables"][role]
        if va and vb and va != vb:
            bridges.append(
                f"'{role}' role: {va.replace('_', ' ')} ↔ {vb.replace('_', ' ')}"
            )

    # Conservation law overlap
    shared_cons = ta["conservation"] & tb["conservation"]
    for c in shared_cons:
        bridges.append(f"Both conserve '{c.replace('_', ' ')}'")

    # Same mathematical structure
    if ta.get("structure") == tb.get("structure"):
        bridges.append(
            f"Same abstract structure: '{ta['structure'].replace('_', ' ')}'"
        )

    return bridges


def _interpret(ta: dict, tb: dict, score: float, shared: list[str]) -> str:
    a_name = ta["display_name"]
    b_name = tb["display_name"]

    if score > 0.6:
        return (
            f"{a_name} and {b_name} are near-isomorphic. The same abstract skeleton "
            f"({', '.join(shared[:2]) if shared else 'shared structure'}) appears in both. "
            f"Mathematical results in one transfer directly to the other."
        )
    elif score > 0.35:
        return (
            f"{a_name} and {b_name} share significant mathematical structure. "
            f"The collision enables partial transfer of results, especially around "
            f"{', '.join(shared[:2]) if shared else 'common patterns'}."
        )
    elif score > 0.15:
        return (
            f"{a_name} and {b_name} have structural resonance. "
            f"They share {', '.join(shared[:1]) if shared else 'abstract patterns'} "
            f"but live in different mathematical contexts. Analogy works with care."
        )
    else:
        return (
            f"{a_name} and {b_name} have limited direct overlap. "
            f"Cross-domain transfer requires identifying deeper structural abstractions."
        )


def collide(theory_a: str, theory_b: str) -> CollisionReport:
    """
    Compute the collision report between two theories.

    Args:
        theory_a: key from THEORY_REGISTRY
        theory_b: key from THEORY_REGISTRY

    Returns:
        CollisionReport with similarity score, shared patterns, and interpretation
    """
    if theory_a not in THEORY_REGISTRY:
        raise ValueError(f"Unknown theory '{theory_a}'. Available: {list_theories()}")
    if theory_b not in THEORY_REGISTRY:
        raise ValueError(f"Unknown theory '{theory_b}'. Available: {list_theories()}")

    ta = THEORY_REGISTRY[theory_a]
    tb = THEORY_REGISTRY[theory_b]

    shared_patterns = sorted(ta["patterns"] & tb["patterns"])
    shared_operators = sorted(ta["operators"] & tb["operators"])
    shared_var_roles = sorted(
        r for r in set(ta["variables"].keys()) & set(tb["variables"].keys())
        if ta["variables"].get(r) and tb["variables"].get(r)
    )

    # ── Similarity components ──
    # Semantic pattern similarity (cluster-aware, overlap + Jaccard blend)
    pattern_sim = _semantic_pattern_sim(ta["patterns"], tb["patterns"])
    # Operator overlap (use overlap coefficient — less penalizing for asymmetry)
    operator_sim = _overlap_coefficient(ta["operators"], tb["operators"])
    # Variable role overlap
    var_sim = _overlap_coefficient(set(ta["variables"].keys()), set(tb["variables"].keys()))
    # Conservation law overlap
    cons_sim = _jaccard(ta["conservation"], tb["conservation"]) if (ta["conservation"] or tb["conservation"]) else 0.0

    # ── Structural bonuses (deep isomorphism signals) ──
    bonus = 0.0
    if ta["update_form"] == tb["update_form"]:
        bonus += 0.18
    if ta["optimization"] and tb["optimization"] and ta["optimization"] == tb["optimization"]:
        bonus += 0.12
    if ta.get("structure") and tb.get("structure") and ta["structure"] == tb["structure"]:
        bonus += 0.12

    # Cross-domain bonus: isomorphisms across domains are more valuable
    if ta["domain"] != tb["domain"]:
        shared_count = len(ta["patterns"] & tb["patterns"])
        if shared_count >= 3:
            bonus += 0.08
        elif shared_count >= 2:
            bonus += 0.04

    # Fixed-point semantic match bonus
    if ta["fixed_points"] and tb["fixed_points"]:
        fp_keywords = {"equilibrium", "optimal", "attractor", "fixed_point", "minimum",
                       "critical", "stable", "stationary"}
        fp_a_words = set(ta["fixed_points"].split("_"))
        fp_b_words = set(tb["fixed_points"].split("_"))
        if fp_a_words & fp_b_words & fp_keywords:
            bonus += 0.04

    score = min(1.0, 0.40 * pattern_sim + 0.22 * operator_sim + 0.12 * var_sim + 0.08 * cons_sim + bonus)

    if score > 0.50:
        strength = "deep"
    elif score > 0.28:
        strength = "significant"
    elif score > 0.10:
        strength = "resonance"
    else:
        strength = "weak"

    bridges = _structural_bridges(ta, tb)
    interpretation = _interpret(ta, tb, score, shared_patterns)

    return CollisionReport(
        theory_a=ta["display_name"],
        theory_b=tb["display_name"],
        similarity_score=score,
        shared_patterns=shared_patterns,
        shared_operators=shared_operators,
        shared_variables=shared_var_roles,
        structural_bridges=bridges,
        interpretation=interpretation,
        collision_strength=strength,
    )


def collide_all() -> list[CollisionReport]:
    """Compute all pairwise collisions, sorted by similarity score."""
    keys = list(THEORY_REGISTRY.keys())
    reports = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            reports.append(collide(keys[i], keys[j]))
    reports.sort(key=lambda r: r.similarity_score, reverse=True)
    return reports


def top_collisions(n: int = 10) -> list[CollisionReport]:
    """Return the top-n strongest theory collisions."""
    return collide_all()[:n]


def list_theories() -> list[str]:
    """List all available theory keys."""
    return sorted(THEORY_REGISTRY.keys())


def collision_matrix() -> dict[tuple[str, str], float]:
    """Return pairwise similarity scores as a dict."""
    keys = list(THEORY_REGISTRY.keys())
    matrix = {}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            r = collide(keys[i], keys[j])
            matrix[(keys[i], keys[j])] = r.similarity_score
    return matrix
