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

    # ── Physics (extended) ───────────────────────────────────────────────
    "noether_theorem": {
        "display_name": "Noether's Theorem",
        "domain": "Physics",
        "equation": "continuous symmetry G ⟹ conserved current Jμ:  ∂μJμ = 0",
        "update_form": "symmetry_implies_conservation",
        "optimization": "stationary_action",
        "fixed_points": "conserved_quantities",
        "operators": {"symmetry_group", "variational_derivative", "lie_derivative",
                      "action_integral", "divergence"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "topological_invariants",
            "universality",
            "compositional_structure",
            "structural_isomorphism",
        },
        "variables": {
            "state": "field_configuration",
            "energy": "lagrangian",
            "symmetry": "lie_group_parameter",
            "conserved": "noether_charge",
        },
        "conservation": {"energy", "momentum", "angular_momentum", "charge"},
        "structure": "variational_principle_with_symmetry",
    },

    # ── Statistical Physics (extended) ───────────────────────────────────
    "percolation_theory": {
        "display_name": "Percolation Theory",
        "domain": "Statistical Physics",
        "equation": "P∞(p) ~ (p − pₖ)^β  for p > pₖ;  ξ(p) ~ |p − pₖ|^{−ν}",
        "update_form": "bond_site_occupation",
        "optimization": None,
        "fixed_points": "percolation_threshold",
        "operators": {"cluster_counting", "renormalization", "scaling", "pairwise_interaction"},
        "patterns": {
            "phase_transition",
            "critical_phenomena",
            "scale_invariance",
            "universality",
            "order_parameter",
            "no_characteristic_scale",
            "power_law",
            "spontaneous_symmetry_breaking",
        },
        "variables": {
            "state": "occupation_probability",
            "coupling": "bond_probability",
            "order": "percolation_strength",
            "scale": "correlation_length",
        },
        "conservation": set(),
        "structure": "random_graph_phase_transition",
    },

    # ── Machine Learning / Bayesian ──────────────────────────────────────
    "variational_inference": {
        "display_name": "Variational Inference (ELBO)",
        "domain": "Machine Learning",
        "equation": "ELBO = E_q[log p(x,z)] − E_q[log q(z)] ≤ log p(x);  KL(q‖p) = log p(x) − ELBO",
        "update_form": "variational_optimization",
        "optimization": "maximize_evidence_lower_bound",
        "fixed_points": "approximate_posterior",
        "operators": {"expectation", "logarithm", "gradient", "kl_divergence", "sampling"},
        "patterns": {
            "variational_inference",
            "bayesian_inference",
            "precision_weighted_update",
            "surprise_minimization",
            "information_gain",
            "prediction_error",
            "variational_principle",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "variational_parameters",
            "energy": "negative_elbo",
            "belief": "approximate_posterior",
            "reference": "prior",
        },
        "conservation": set(),
        "structure": "optimization_on_distribution_manifold",
    },

    # ── Dynamic Systems (extended) ───────────────────────────────────────
    "lotka_volterra": {
        "display_name": "Lotka-Volterra Equations",
        "domain": "Dynamic Systems",
        "equation": "dx/dt = αx − βxy;  dy/dt = δxy − γy",
        "update_form": "coupled_nonlinear_ode",
        "optimization": None,
        "fixed_points": "coexistence_equilibrium",
        "operators": {"pairwise_interaction", "growth_rate", "coupling", "jacobian"},
        "patterns": {
            "pairwise_coupling",
            "frequency_dependent",
            "fixed_point_stability",
            "attractor_dynamics",
            "above_average_grows",
            "mean_field",
        },
        "variables": {
            "state": "population_densities",
            "score": "growth_rate",
            "coupling": "interaction_coefficients",
            "reference": "carrying_capacity",
        },
        "conservation": {"total_conserved_quantity_in_2d"},
        "structure": "coupled_nonlinear_dynamical_system",
    },

    # ── Optimization / Information Geometry ──────────────────────────────
    "natural_gradient": {
        "display_name": "Natural Gradient Descent",
        "domain": "Optimization",
        "equation": "θ_{t+1} = θ_t − η F(θ)⁻¹ ∇L(θ);  F(θ)ᵢⱼ = E[(∂log p/∂θᵢ)(∂log p/∂θⱼ)]",
        "update_form": "precision_weighted_gradient",
        "optimization": "minimize_loss_on_manifold",
        "fixed_points": "fisher_efficient_optimum",
        "operators": {"gradient", "matrix_inverse", "expectation", "fisher_information_matrix"},
        "patterns": {
            "precision_weighted_update",
            "gradient_descent",
            "energy_minimization",
            "information_gain",
            "optimal_inference",
            "multiplicative_update",
        },
        "variables": {
            "state": "parameters",
            "energy": "loss_function",
            "precision": "fisher_matrix",
            "flow": "natural_gradient_direction",
        },
        "conservation": set(),
        "structure": "riemannian_metric_on_statistical_manifold",
    },

    # ── Optimal Transport ────────────────────────────────────────────────
    "optimal_transport": {
        "display_name": "Optimal Transport (Wasserstein)",
        "domain": "Optimization",
        "equation": "W_p(μ,ν) = (inf_{γ∈Γ(μ,ν)} ∫ c(x,y)^p dγ)^{1/p};  Monge: T*=argmin ∫c(x,T(x))dμ",
        "update_form": "transport_plan_optimization",
        "optimization": "minimize_transport_cost",
        "fixed_points": "optimal_coupling",
        "operators": {"infimum", "coupling", "gradient", "pushforward", "dual_potential"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "optimal_inference",
            "energy_minimization",
            "one_to_one_mapping",
            "structural_isomorphism",
            "conservation_of_probability",
        },
        "variables": {
            "state": "transport_plan",
            "energy": "transport_cost",
            "source": "source_distribution",
            "target": "target_distribution",
        },
        "conservation": {"total_mass"},
        "structure": "optimization_on_distribution_manifold",
    },

    # ── Statistical Physics (extended) ───────────────────────────────────
    "spin_glass": {
        "display_name": "Spin Glass (Edwards-Anderson)",
        "domain": "Statistical Physics",
        "equation": "H = −Σᵢⱼ Jᵢⱼ sᵢsⱼ − Σᵢ hᵢsᵢ;  Jᵢⱼ ~ N(0,J²/N);  q = (1/N)Σᵢ ⟨sᵢ⟩²",
        "update_form": "disordered_energy_minimization",
        "optimization": "minimize_frustrated_energy",
        "fixed_points": "metastable_glassy_states",
        "operators": {"pairwise_interaction", "quenched_average", "replica", "overlap",
                      "partition_function"},
        "patterns": {
            "energy_based",
            "pairwise_coupling",
            "phase_transition",
            "energy_entropy_tradeoff",
            "energy_minimization",
            "mean_field",
            "order_parameter",
            "fixed_point_stability",
            "correlation_learning",
        },
        "variables": {
            "state": "spin_configuration",
            "energy": "hamiltonian",
            "coupling": "random_bonds",
            "order": "overlap_parameter",
            "temperature": "inverse_beta",
        },
        "conservation": set(),
        "structure": "disordered_pairwise_energy_model",
    },

    # ── Reinforcement Learning ───────────────────────────────────────────
    "policy_gradient": {
        "display_name": "Policy Gradient (REINFORCE)",
        "domain": "Machine Learning",
        "equation": "∇J(θ) = E_π[∇log π(a|s;θ) · (R − b)];  θ ← θ + α∇J(θ)",
        "update_form": "score_function_gradient",
        "optimization": "maximize_expected_return",
        "fixed_points": "locally_optimal_policy",
        "operators": {"expectation", "logarithm", "gradient", "sampling", "baseline_subtraction"},
        "patterns": {
            "above_average_grows",
            "selection",
            "frequency_dependent",
            "multiplicative_update",
            "gradient_descent",
            "prediction_error",
            "information_gain",
        },
        "variables": {
            "state": "policy_parameters",
            "score": "expected_return",
            "reference": "baseline",
            "action": "sampled_action",
        },
        "conservation": {"total_probability"},
        "structure": "stochastic_gradient_on_policy_manifold",
    },

    # ── Statistical Physics (mean field) ─────────────────────────────────
    "mean_field_theory": {
        "display_name": "Mean Field Theory",
        "domain": "Statistical Physics",
        "equation": "m = tanh(β(Jzm + h));  F_MF = −(Jz/2)m² − hm + (1/β)[(1+m)/2 ln(1+m)/2 + (1−m)/2 ln(1−m)/2]",
        "update_form": "self_consistent_field",
        "optimization": "minimize_free_energy",
        "fixed_points": "self_consistent_magnetization",
        "operators": {"expectation", "self_consistency", "partition_function",
                      "variational_derivative", "pairwise_interaction"},
        "patterns": {
            "mean_field",
            "phase_transition",
            "order_parameter",
            "energy_entropy_tradeoff",
            "energy_based",
            "fixed_point_iteration",
            "variational_principle",
            "pairwise_coupling",
        },
        "variables": {
            "state": "order_parameter",
            "energy": "free_energy_functional",
            "coupling": "interaction_strength",
            "temperature": "inverse_beta",
        },
        "conservation": set(),
        "structure": "self_consistent_approximation",
    },

    # ── Thermodynamics (extended) ────────────────────────────────────────
    "dissipative_structures": {
        "display_name": "Dissipative Structures (Prigogine)",
        "domain": "Thermodynamics",
        "equation": "dᵢS/dt ≥ 0;  dS/dt = dᵢS/dt + dₑS/dt;  far from equilibrium: dₑS/dt < 0 possible",
        "update_form": "entropy_production_driven",
        "optimization": None,
        "fixed_points": "far_from_equilibrium_steady_state",
        "operators": {"entropy_production", "flux", "thermodynamic_force", "bifurcation",
                      "linear_stability"},
        "patterns": {
            "spontaneous_symmetry_breaking",
            "phase_transition",
            "energy_entropy_tradeoff",
            "critical_phenomena",
            "self_organization",
            "scale_invariance",
            "fixed_point_stability",
        },
        "variables": {
            "state": "macroscopic_variables",
            "energy": "entropy_production_rate",
            "flow": "thermodynamic_fluxes",
            "field": "thermodynamic_forces",
        },
        "conservation": {"total_energy"},
        "structure": "open_system_far_from_equilibrium",
    },

    # ── Stochastic Dynamics ──────────────────────────────────────────────
    "fokker_planck": {
        "display_name": "Fokker-Planck / Langevin Dynamics",
        "domain": "Statistical Physics",
        "equation": "∂p/∂t = −∂/∂x[μ(x)p] + (1/2)∂²/∂x²[σ²(x)p];  dx = μdt + σdW",
        "update_form": "drift_diffusion",
        "optimization": None,
        "fixed_points": "stationary_distribution",
        "operators": {"drift", "diffusion", "gradient", "laplacian", "partition_function"},
        "patterns": {
            "energy_based",
            "energy_minimization",
            "conservation_of_probability",
            "mean_field",
            "fixed_point_stability",
            "energy_entropy_tradeoff",
            "gradient_descent",
        },
        "variables": {
            "state": "probability_density",
            "energy": "potential_function",
            "flow": "probability_current",
            "temperature": "noise_intensity",
        },
        "conservation": {"total_probability"},
        "structure": "stochastic_differential_equation",
    },

    # ── Game Theory ──────────────────────────────────────────────────────
    "nash_equilibrium": {
        "display_name": "Nash Equilibrium",
        "domain": "Evolutionary Game Theory",
        "equation": "σ* ∈ NE ⟺ ∀i, uᵢ(σ*) ≥ uᵢ(σ'ᵢ, σ*₋ᵢ);  BR(σ₋ᵢ) = argmax uᵢ(σᵢ, σ₋ᵢ)",
        "update_form": "best_response_dynamics",
        "optimization": "maximize_individual_utility",
        "fixed_points": "mutual_best_response_equilibrium",
        "operators": {"best_response", "expectation", "pairwise_interaction", "mixed_strategy"},
        "patterns": {
            "fixed_point_stability",
            "fixed_point_iteration",
            "pairwise_coupling",
            "frequency_dependent",
            "above_average_grows",
            "mean_field",
        },
        "variables": {
            "state": "strategy_profile",
            "score": "utility",
            "coupling": "payoff_matrix",
            "reference": "opponent_strategy",
        },
        "conservation": {"total_probability"},
        "structure": "fixed_point_of_best_response_map",
    },

    # ── Machine Learning (generative) ────────────────────────────────────
    "boltzmann_machine": {
        "display_name": "Boltzmann Machine",
        "domain": "Machine Learning",
        "equation": "P(v) = Σ_h exp(−E(v,h))/Z;  E(v,h) = −v^TWh − b^Tv − c^Th;  ΔW = ⟨vh^T⟩_data − ⟨vh^T⟩_model",
        "update_form": "contrastive_divergence",
        "optimization": "maximize_log_likelihood",
        "fixed_points": "thermal_equilibrium_distribution",
        "operators": {"partition_function", "expectation", "pairwise_interaction", "sampling",
                      "gradient"},
        "patterns": {
            "energy_based",
            "pairwise_coupling",
            "correlation_learning",
            "energy_entropy_tradeoff",
            "energy_minimization",
            "mean_field",
            "phase_transition",
            "bayesian_inference",
        },
        "variables": {
            "state": "visible_hidden_configuration",
            "energy": "energy_function",
            "coupling": "weight_matrix",
            "temperature": "inverse_beta",
        },
        "conservation": {"total_probability"},
        "structure": "disordered_pairwise_energy_model",
    },

    # ── Information Theory (extended) ────────────────────────────────────
    "compressed_sensing": {
        "display_name": "Compressed Sensing",
        "domain": "Information Theory",
        "equation": "y = Φx, x sparse;  x* = argmin ‖x‖₁ s.t. Φx = y;  RIP: (1−δ)‖x‖₂² ≤ ‖Φx‖₂² ≤ (1+δ)‖x‖₂²",
        "update_form": "sparse_recovery",
        "optimization": "minimize_l1_norm",
        "fixed_points": "sparsest_consistent_solution",
        "operators": {"projection", "thresholding", "gradient", "linear_measurement",
                      "basis_pursuit"},
        "patterns": {
            "information_gain",
            "optimal_inference",
            "variational_principle",
            "structural_isomorphism",
            "one_to_one_mapping",
            "uncertainty_measure",
        },
        "variables": {
            "state": "sparse_signal",
            "energy": "l1_norm",
            "measurement": "compressed_observations",
            "precision": "restricted_isometry_constant",
        },
        "conservation": {"measurement_consistency"},
        "structure": "underdetermined_linear_inverse_problem",
    },

    # ── Physics (extended) ───────────────────────────────────────────────
    "gauge_theory": {
        "display_name": "Gauge Theory",
        "domain": "Physics",
        "equation": "Dμ = ∂μ + igAμ;  Fμν = ∂μAν − ∂νAμ + ig[Aμ,Aν];  L = −(1/4)FμνF^μν + ψ̄(iD̸−m)ψ",
        "update_form": "local_symmetry_covariant",
        "optimization": "stationary_action",
        "fixed_points": "gauge_invariant_observables",
        "operators": {"covariant_derivative", "field_strength", "symmetry_group",
                      "action_integral", "renormalization"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "topological_invariants",
            "universality",
            "compositional_structure",
            "structural_isomorphism",
            "scale_invariance",
        },
        "variables": {
            "state": "field_configuration",
            "energy": "lagrangian_density",
            "symmetry": "gauge_group",
            "coupling": "coupling_constant",
        },
        "conservation": {"gauge_charge", "energy"},
        "structure": "variational_principle_with_symmetry",
    },

    # ── Quantum Information ──────────────────────────────────────────────
    "quantum_information": {
        "display_name": "Quantum Information (Density Matrix)",
        "domain": "Physics",
        "equation": "ρ = Σᵢ pᵢ|ψᵢ⟩⟨ψᵢ|;  S(ρ) = −Tr(ρ ln ρ);  ∂ρ/∂t = −i[H,ρ] + Σ LρL† − ½{L†L,ρ}",
        "update_form": "lindblad_master_equation",
        "optimization": None,
        "fixed_points": "steady_state_density_matrix",
        "operators": {"trace", "partial_trace", "commutator", "tensor_product",
                      "unitary", "measurement", "channel"},
        "patterns": {
            "energy_based",
            "energy_entropy_tradeoff",
            "conservation_of_probability",
            "information_gain",
            "uncertainty_measure",
            "compositional_structure",
            "structural_isomorphism",
        },
        "variables": {
            "state": "density_matrix",
            "energy": "hamiltonian",
            "information": "von_neumann_entropy",
            "coupling": "interaction_hamiltonian",
        },
        "conservation": {"total_probability", "unitarity"},
        "structure": "operator_algebra_on_hilbert_space",
    },

    # ── Optimization ─────────────────────────────────────────────────────
    "simulated_annealing": {
        "display_name": "Simulated Annealing",
        "domain": "Optimization",
        "equation": "P(accept) = min(1, exp(−ΔE / T));  T(t) → 0;  π(x) ∝ exp(−E(x)/T)",
        "update_form": "metropolis_hastings",
        "optimization": "global_minimum_energy",
        "fixed_points": "ground_state_configuration",
        "operators": {"sampling", "perturbation", "acceptance", "cooling_schedule",
                      "partition_function"},
        "patterns": {
            "energy_based",
            "energy_minimization",
            "energy_entropy_tradeoff",
            "phase_transition",
            "exploration_exploitation",
            "gradient_descent",
        },
        "variables": {
            "state": "configuration",
            "energy": "cost_function",
            "temperature": "annealing_schedule",
            "dynamics": "random_perturbation",
        },
        "conservation": {"detailed_balance"},
        "structure": "markov_chain_convergence_to_ground_state",
    },

    # ── Neuroscience (extended) ──────────────────────────────────────────
    "sparse_coding": {
        "display_name": "Sparse Coding / Efficient Neural Coding",
        "domain": "Neuroscience",
        "equation": "x = Φa + ε;  a* = argmin ‖x − Φa‖₂² + λ‖a‖₁;  ΔΦ = η(x − Φa)a^T",
        "update_form": "iterative_shrinkage_thresholding",
        "optimization": "minimize_reconstruction_plus_sparsity",
        "fixed_points": "sparse_representation",
        "operators": {"projection", "thresholding", "gradient", "dictionary_learning",
                      "lateral_inhibition"},
        "patterns": {
            "energy_minimization",
            "information_gain",
            "correlation_learning",
            "optimal_inference",
            "energy_entropy_tradeoff",
            "variational_principle",
        },
        "variables": {
            "state": "sparse_activations",
            "energy": "reconstruction_error_plus_penalty",
            "basis": "dictionary_atoms",
            "coupling": "lateral_inhibition_weights",
        },
        "conservation": {"information_content"},
        "structure": "overcomplete_basis_with_sparsity_constraint",
    },

    # ── Topology (extended) ──────────────────────────────────────────────
    "simplicial_homology": {
        "display_name": "Simplicial Homology",
        "domain": "Topology",
        "equation": "Hₙ(K) = ker ∂ₙ / im ∂ₙ₊₁;  ∂ₙ∂ₙ₊₁ = 0;  χ(K) = Σ (−1)ⁿ βₙ",
        "update_form": "boundary_operator_chain",
        "optimization": None,
        "fixed_points": "homology_classes",
        "operators": {"boundary", "chain_complex", "quotient", "exact_sequence",
                      "betti_number"},
        "patterns": {
            "topological_invariants",
            "compositional_structure",
            "structural_isomorphism",
            "universality",
            "dual_variables",
        },
        "variables": {
            "state": "chain_group",
            "invariant": "homology_group",
            "connectivity": "betti_numbers",
            "shape": "euler_characteristic",
        },
        "conservation": {"topological_invariance"},
        "structure": "algebraic_chain_complex",
    },

    # ── Economics ─────────────────────────────────────────────────────────
    "general_equilibrium": {
        "display_name": "General Equilibrium (Arrow-Debreu)",
        "domain": "Economics",
        "equation": "Σᵢ xᵢ(p) = Σᵢ ωᵢ;  xᵢ(p) = argmax uᵢ(x) s.t. p·x ≤ p·ωᵢ;  ∃p*: z(p*) = 0",
        "update_form": "tatonnement_price_adjustment",
        "optimization": "maximize_utility_under_budget",
        "fixed_points": "walrasian_equilibrium_prices",
        "operators": {"excess_demand", "price_adjustment", "fixed_point",
                      "lagrange_multiplier", "convex_optimization"},
        "patterns": {
            "fixed_point_stability",
            "fixed_point_iteration",
            "variational_principle",
            "dual_variables",
            "pairwise_coupling",
            "mean_field",
        },
        "variables": {
            "state": "price_allocation_pair",
            "energy": "aggregate_excess_demand",
            "score": "utility",
            "coupling": "market_clearing_condition",
        },
        "conservation": {"walras_law", "total_endowment"},
        "structure": "fixed_point_of_excess_demand",
    },

    # ── Evolutionary Computation ─────────────────────────────────────────
    "genetic_algorithm": {
        "display_name": "Genetic Algorithm",
        "domain": "Evolutionary Game Theory",
        "equation": "f(t+1) = select(crossover(mutate(f(t))));  P(select xᵢ) ∝ fitness(xᵢ)/⟨fitness⟩",
        "update_form": "selection_variation_inheritance",
        "optimization": "maximize_fitness",
        "fixed_points": "fitness_landscape_peak",
        "operators": {"selection", "crossover", "mutation", "fitness_evaluation",
                      "population_dynamics"},
        "patterns": {
            "above_average_grows",
            "frequency_dependent",
            "exploration_exploitation",
            "covariance_selection",
            "energy_minimization",
            "phase_transition",
            "population_dynamics",
        },
        "variables": {
            "state": "population_of_genotypes",
            "score": "fitness",
            "dynamics": "selection_pressure",
            "coupling": "crossover_rate",
        },
        "conservation": {"population_size"},
        "structure": "iterative_population_based_search",
    },

    # ── Machine Learning (generative, extended) ──────────────────────────
    "variational_autoencoder": {
        "display_name": "Variational Autoencoder (VAE)",
        "domain": "Machine Learning",
        "equation": "ELBO = E_q[log p(x|z)] − KL(q(z|x) ‖ p(z));  q(z|x) = N(μ(x), σ²(x));  z = μ + σε",
        "update_form": "amortized_variational_inference",
        "optimization": "maximize_ELBO",
        "fixed_points": "learned_generative_model",
        "operators": {"encoder", "decoder", "sampling", "gradient",
                      "kl_divergence", "expectation"},
        "patterns": {
            "bayesian_inference",
            "variational_principle",
            "energy_entropy_tradeoff",
            "information_gain",
            "optimal_inference",
            "energy_based",
            "gradient_descent",
        },
        "variables": {
            "state": "latent_code",
            "energy": "negative_ELBO",
            "flow": "encoder_decoder_pair",
            "information": "kl_divergence_from_prior",
        },
        "conservation": {"total_probability"},
        "structure": "variational_generative_model",
    },

    # ── Machine Learning (attention) ─────────────────────────────────────
    "attention_mechanism": {
        "display_name": "Attention Mechanism (Transformers)",
        "domain": "Machine Learning",
        "equation": "Attn(Q,K,V) = softmax(QK^T/√d)V;  softmax(zᵢ) = exp(zᵢ)/Σⱼ exp(zⱼ);  MultiHead = Concat(head₁,...,headₕ)W",
        "update_form": "weighted_value_aggregation",
        "optimization": "minimize_cross_entropy_loss",
        "fixed_points": "learned_attention_patterns",
        "operators": {"softmax", "dot_product", "projection", "expectation",
                      "gradient", "composition"},
        "patterns": {
            "energy_based",
            "energy_entropy_tradeoff",
            "mean_field",
            "information_gain",
            "compositional_structure",
            "gradient_descent",
            "pairwise_coupling",
        },
        "variables": {
            "state": "query_key_value_triples",
            "energy": "negative_dot_product_similarity",
            "coupling": "attention_weights",
            "information": "context_vector",
        },
        "conservation": {"attention_weights_sum_to_one"},
        "structure": "soft_dictionary_lookup",
    },

    # ── Control Theory (extended) ────────────────────────────────────────
    "hamilton_jacobi_bellman": {
        "display_name": "Hamilton-Jacobi-Bellman Equation",
        "domain": "Control Theory",
        "equation": "−∂V/∂t = min_u [L(x,u) + (∂V/∂x)f(x,u)];  V(x,T) = Φ(x);  u* = argmin H(x,u,∇V)",
        "update_form": "dynamic_programming_continuous",
        "optimization": "minimize_cumulative_cost",
        "fixed_points": "optimal_value_function",
        "operators": {"gradient", "hamiltonian", "infimum", "viscosity_solution",
                      "backward_induction"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "gradient_descent",
            "fixed_point_iteration",
            "dual_variables",
            "optimal_inference",
        },
        "variables": {
            "state": "system_state",
            "energy": "value_function",
            "control": "optimal_policy",
            "flow": "state_dynamics",
        },
        "conservation": {"optimality_principle"},
        "structure": "variational_principle_over_trajectories",
    },

    # ── Optimization (extended) ──────────────────────────────────────────
    "sgd_as_langevin": {
        "display_name": "SGD as Langevin Dynamics",
        "domain": "Optimization",
        "equation": "θ_{t+1} = θ_t − η∇L̃(θ_t);  ∇L̃ = ∇L + ε, ε ~ N(0, Σ/B);  θ(t) ~ exp(−L(θ)/η) as t→∞",
        "update_form": "noisy_gradient_descent",
        "optimization": "minimize_loss",
        "fixed_points": "flat_minima_basin",
        "operators": {"gradient", "sampling", "diffusion", "drift",
                      "learning_rate_schedule"},
        "patterns": {
            "gradient_descent",
            "energy_minimization",
            "energy_entropy_tradeoff",
            "exploration_exploitation",
            "phase_transition",
            "energy_based",
        },
        "variables": {
            "state": "parameter_vector",
            "energy": "loss_function",
            "temperature": "learning_rate_times_noise",
            "dynamics": "gradient_plus_noise",
        },
        "conservation": set(),
        "structure": "stochastic_differential_equation",
    },

    # ── Machine Learning (generative, extended) ──────────────────────────
    "diffusion_model": {
        "display_name": "Diffusion Model (Score Matching)",
        "domain": "Machine Learning",
        "equation": "q(xₜ|x₀) = N(√ᾱₜx₀, (1−ᾱₜ)I);  p_θ(x_{t-1}|xₜ) = N(μ_θ(xₜ,t), σ²I);  L = E‖ε − ε_θ(xₜ,t)‖²",
        "update_form": "iterative_denoising",
        "optimization": "minimize_denoising_score_matching",
        "fixed_points": "learned_data_distribution",
        "operators": {"diffusion", "drift", "gradient", "sampling",
                      "score_function", "noise_schedule"},
        "patterns": {
            "energy_based",
            "energy_entropy_tradeoff",
            "gradient_descent",
            "conservation_of_probability",
            "variational_principle",
            "energy_minimization",
            "phase_transition",
        },
        "variables": {
            "state": "noised_sample",
            "energy": "denoising_loss",
            "flow": "reverse_diffusion_drift",
            "temperature": "noise_level",
        },
        "conservation": {"total_probability"},
        "structure": "stochastic_differential_equation",
    },

    # ── Statistical Physics (extended) ───────────────────────────────────
    "random_matrix_theory": {
        "display_name": "Random Matrix Theory",
        "domain": "Statistical Physics",
        "equation": "ρ(λ) = (1/2πσ²)√(4σ²−λ²);  P(M) ∝ exp(−N Tr V(M));  R₂(λ₁,λ₂) = ρ(λ₁)ρ(λ₂) − sin²(π(λ₁−λ₂)ρ)/(π(λ₁−λ₂))²",
        "update_form": "eigenvalue_statistics",
        "optimization": None,
        "fixed_points": "universal_spectral_distributions",
        "operators": {"trace", "eigenvalue_decomposition", "partition_function",
                      "determinant", "resolvent"},
        "patterns": {
            "universality",
            "phase_transition",
            "mean_field",
            "energy_based",
            "energy_entropy_tradeoff",
            "scale_invariance",
        },
        "variables": {
            "state": "random_matrix_ensemble",
            "energy": "matrix_potential",
            "spectrum": "eigenvalue_density",
            "coupling": "level_repulsion",
        },
        "conservation": {"total_eigenvalue_density"},
        "structure": "ensemble_average_over_matrices",
    },

    # ── Dynamic Systems (extended) ───────────────────────────────────────
    "reservoir_computing": {
        "display_name": "Reservoir Computing / Echo State Networks",
        "domain": "Dynamic Systems",
        "equation": "h(t+1) = tanh(W_in x(t) + W h(t));  y(t) = W_out h(t);  W_out = argmin ‖Y − W_out H‖²",
        "update_form": "driven_recurrent_dynamics",
        "optimization": "minimize_readout_error",
        "fixed_points": "echo_state_property",
        "operators": {"recurrence", "projection", "nonlinear_activation",
                      "ridge_regression", "spectral_radius"},
        "patterns": {
            "fixed_point_stability",
            "phase_transition",
            "information_gain",
            "energy_minimization",
            "correlation_learning",
        },
        "variables": {
            "state": "reservoir_activations",
            "energy": "readout_error",
            "coupling": "recurrent_weight_matrix",
            "dynamics": "driven_nonlinear_map",
        },
        "conservation": {"fading_memory"},
        "structure": "high_dimensional_nonlinear_dynamical_system",
    },

    # ── Statistics ───────────────────────────────────────────────────────
    "maximum_likelihood": {
        "display_name": "Maximum Likelihood Estimation",
        "domain": "Statistics",
        "equation": "θ_ML = argmax Σᵢ log p(xᵢ|θ);  ∂/∂θ Σ log p(xᵢ|θ) = 0;  Var(θ_ML) → I(θ)⁻¹ as n→∞",
        "update_form": "score_equation_root",
        "optimization": "maximize_log_likelihood",
        "fixed_points": "consistent_efficient_estimator",
        "operators": {"gradient", "expectation", "fisher_information",
                      "score_function", "hessian"},
        "patterns": {
            "gradient_descent",
            "optimal_inference",
            "information_gain",
            "variational_principle",
            "fixed_point_iteration",
        },
        "variables": {
            "state": "parameter_estimate",
            "energy": "negative_log_likelihood",
            "information": "fisher_information",
            "data": "observed_sample",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Functional Analysis ──────────────────────────────────────────────
    "kernel_methods": {
        "display_name": "Kernel Methods / RKHS",
        "domain": "Machine Learning",
        "equation": "k(x,x') = ⟨φ(x),φ(x')⟩_H;  f*(x) = Σᵢ αᵢk(xᵢ,x);  α = (K + λI)⁻¹y;  K = Mercer kernel matrix",
        "update_form": "kernel_ridge_regression",
        "optimization": "minimize_regularized_loss_in_RKHS",
        "fixed_points": "representer_theorem_solution",
        "operators": {"inner_product", "projection", "eigenvalue_decomposition",
                      "regularization", "kernel_evaluation"},
        "patterns": {
            "dual_variables",
            "structural_isomorphism",
            "one_to_one_mapping",
            "variational_principle",
            "energy_minimization",
            "compositional_structure",
        },
        "variables": {
            "state": "function_in_RKHS",
            "energy": "regularized_loss",
            "coupling": "kernel_matrix",
            "basis": "kernel_eigenfunctions",
        },
        "conservation": {"representer_theorem"},
        "structure": "optimization_in_reproducing_kernel_hilbert_space",
    },

    # ── Combinatorial Optimization ───────────────────────────────────────
    "constraint_satisfaction": {
        "display_name": "Constraint Satisfaction / SAT",
        "domain": "Optimization",
        "equation": "Find x: ∧ᵢ Cᵢ(x) = true;  E(x) = Σᵢ (1−Cᵢ(x));  α_c: phase transition at clause/variable ratio",
        "update_form": "constraint_propagation",
        "optimization": "minimize_violated_constraints",
        "fixed_points": "satisfying_assignment",
        "operators": {"unit_propagation", "backtracking", "random_restart",
                      "survey_propagation"},
        "patterns": {
            "phase_transition",
            "energy_minimization",
            "energy_based",
            "fixed_point_iteration",
            "mean_field",
            "exploration_exploitation",
        },
        "variables": {
            "state": "variable_assignment",
            "energy": "number_of_violated_constraints",
            "coupling": "clause_structure",
            "dynamics": "search_trajectory",
        },
        "conservation": set(),
        "structure": "disordered_constraint_network",
    },

    # ── Self-Organization ────────────────────────────────────────────────
    "autopoiesis": {
        "display_name": "Autopoiesis",
        "domain": "Dynamic Systems",
        "equation": "dXᵢ/dt = P(X,E) − D(Xᵢ);  boundary: B(X) self-maintains;  organization: O(X) = O(X(t)) ∀t",
        "update_form": "self_producing_network",
        "optimization": None,
        "fixed_points": "self_maintaining_organization",
        "operators": {"production", "degradation", "boundary_maintenance",
                      "network_closure"},
        "patterns": {
            "fixed_point_stability",
            "conservation_of_probability",
            "population_dynamics",
            "compositional_structure",
            "topological_invariants",
        },
        "variables": {
            "state": "component_concentrations",
            "energy": "production_minus_degradation",
            "boundary": "self_generated_membrane",
            "organization": "network_topology",
        },
        "conservation": {"organizational_closure"},
        "structure": "operationally_closed_self_producing_network",
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
    {"self_organization", "spontaneous_symmetry_breaking", "critical_phenomena"},
    {"mean_field", "self_consistent_field", "fixed_point_iteration"},
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
