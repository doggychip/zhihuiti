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

    # ── Classical Mechanics ──────────────────────────────────────────────
    "lagrangian_mechanics": {
        "display_name": "Lagrangian Mechanics",
        "domain": "Physics",
        "equation": "L = T − V;  δS = δ∫L dt = 0;  d/dt(∂L/∂q̇) − ∂L/∂q = 0 (Euler-Lagrange)",
        "update_form": "euler_lagrange_equations",
        "optimization": "stationary_action",
        "fixed_points": "classical_trajectory",
        "operators": {"action_integral", "functional_derivative", "lagrange_multiplier",
                      "symmetry_group", "canonical_transform"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "energy_minimization",
            "structural_isomorphism",
            "compositional_structure",
            "topological_invariants",
        },
        "variables": {
            "state": "generalized_coordinates_and_velocities",
            "energy": "lagrangian",
            "action": "integral_of_lagrangian",
            "symmetry": "continuous_symmetry_group",
        },
        "conservation": {"energy", "momentum", "angular_momentum"},
        "structure": "variational_principle_with_symmetry",
    },

    # ── Statistical Sampling ─────────────────────────────────────────────
    "mcmc": {
        "display_name": "Markov Chain Monte Carlo",
        "domain": "Statistics",
        "equation": "π(x') T(x'→x) = π(x) T(x→x');  α = min(1, π(x')q(x|x')/π(x)q(x'|x));  x ~ π as t→∞",
        "update_form": "metropolis_hastings",
        "optimization": None,
        "fixed_points": "target_distribution_samples",
        "operators": {"sampling", "acceptance", "proposal", "detailed_balance",
                      "mixing_time"},
        "patterns": {
            "energy_based",
            "energy_entropy_tradeoff",
            "conservation_of_probability",
            "fixed_point_stability",
            "phase_transition",
            "exploration_exploitation",
        },
        "variables": {
            "state": "markov_chain_state",
            "energy": "negative_log_target",
            "dynamics": "proposal_kernel",
            "temperature": "inverse_beta",
        },
        "conservation": {"detailed_balance", "total_probability"},
        "structure": "markov_chain_convergence_to_ground_state",
    },

    # ── Machine Learning (latent variable) ───────────────────────────────
    "expectation_maximization": {
        "display_name": "Expectation Maximization (EM)",
        "domain": "Machine Learning",
        "equation": "E: Q(z) = p(z|x,θ_old);  M: θ_new = argmax E_Q[log p(x,z|θ)];  L(θ) ↑ monotonically",
        "update_form": "alternating_optimization",
        "optimization": "maximize_log_likelihood",
        "fixed_points": "local_maximum_likelihood",
        "operators": {"expectation", "gradient", "kl_divergence",
                      "sufficient_statistics", "posterior"},
        "patterns": {
            "bayesian_inference",
            "variational_principle",
            "fixed_point_iteration",
            "energy_minimization",
            "optimal_inference",
            "gradient_descent",
        },
        "variables": {
            "state": "parameters_and_responsibilities",
            "energy": "negative_log_likelihood",
            "latent": "hidden_variables",
            "information": "expected_complete_log_likelihood",
        },
        "conservation": {"likelihood_monotonicity"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Information Theory (extended) ────────────────────────────────────
    "information_bottleneck": {
        "display_name": "Information Bottleneck",
        "domain": "Information Theory",
        "equation": "min I(X;T) − β I(T;Y);  p(t|x) = p(t)/Z exp(−β Σ_y p(y|x) log p(y|x)/p(y|t))",
        "update_form": "iterative_blahut_arimoto",
        "optimization": "minimize_compression_distortion",
        "fixed_points": "optimal_compression_representation",
        "operators": {"mutual_information", "kl_divergence", "expectation",
                      "lagrange_multiplier", "rate_distortion"},
        "patterns": {
            "information_gain",
            "variational_principle",
            "energy_entropy_tradeoff",
            "dual_variables",
            "optimal_inference",
            "phase_transition",
        },
        "variables": {
            "state": "compressed_representation",
            "energy": "rate_distortion_lagrangian",
            "information": "mutual_information",
            "coupling": "relevance_variable",
        },
        "conservation": {"data_processing_inequality"},
        "structure": "variational_rate_distortion",
    },

    # ── Control Theory (extended) ────────────────────────────────────────
    "pontryagin_maximum": {
        "display_name": "Pontryagin Maximum Principle",
        "domain": "Control Theory",
        "equation": "H(x,u,λ) = L(x,u) + λ^T f(x,u);  u* = argmax H;  ẋ = ∂H/∂λ, λ̇ = −∂H/∂x;  λ(T) = ∂Φ/∂x(T)",
        "update_form": "hamiltonian_two_point_boundary",
        "optimization": "maximize_hamiltonian",
        "fixed_points": "optimal_costate_trajectory",
        "operators": {"hamiltonian", "costate", "transversality",
                      "bang_bang_control", "switching_function"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "energy_minimization",
            "gradient_descent",
            "fixed_point_iteration",
        },
        "variables": {
            "state": "state_and_costate",
            "energy": "hamiltonian",
            "control": "optimal_control_input",
            "flow": "canonical_equations",
        },
        "conservation": {"hamiltonian_along_optimal_trajectory"},
        "structure": "variational_principle_over_trajectories",
    },

    # ── Machine Learning (kernel, extended) ──────────────────────────────
    "neural_tangent_kernel": {
        "display_name": "Neural Tangent Kernel (NTK)",
        "domain": "Machine Learning",
        "equation": "Θ(x,x') = ⟨∇_θf(x),∇_θf(x')⟩;  df/dt = −Θ(X,X)(f(X)−Y);  Θ → Θ∞ as width→∞",
        "update_form": "kernel_gradient_flow",
        "optimization": "minimize_squared_loss",
        "fixed_points": "kernel_regression_solution",
        "operators": {"inner_product", "gradient", "eigenvalue_decomposition",
                      "infinite_width_limit", "kernel_evaluation"},
        "patterns": {
            "dual_variables",
            "structural_isomorphism",
            "gradient_descent",
            "energy_minimization",
            "universality",
            "mean_field",
        },
        "variables": {
            "state": "function_output",
            "energy": "squared_loss",
            "coupling": "ntk_kernel_matrix",
            "dynamics": "kernel_gradient_flow",
        },
        "conservation": set(),
        "structure": "optimization_in_reproducing_kernel_hilbert_space",
    },

    # ── Bifurcation Theory ───────────────────────────────────────────────
    "hopf_bifurcation": {
        "display_name": "Hopf Bifurcation",
        "domain": "Dynamic Systems",
        "equation": "ẋ = f(x,μ);  eigenvalues λ(μ_c) = ±iω;  dRe(λ)/dμ|_{μ_c} ≠ 0;  x → limit cycle for μ > μ_c",
        "update_form": "normal_form_reduction",
        "optimization": None,
        "fixed_points": "limit_cycle_via_bifurcation",
        "operators": {"linearization", "eigenvalue_decomposition", "center_manifold",
                      "normal_form", "amplitude_equation"},
        "patterns": {
            "fixed_point_stability",
            "phase_transition",
            "scale_invariance",
            "universality",
            "topological_invariants",
        },
        "variables": {
            "state": "dynamical_state",
            "energy": "stability_eigenvalue",
            "control": "bifurcation_parameter",
            "dynamics": "limit_cycle_amplitude",
        },
        "conservation": set(),
        "structure": "parameter_dependent_dynamical_system",
    },

    # ── Chemical Kinetics ────────────────────────────────────────────────
    "chemical_reaction_network": {
        "display_name": "Chemical Reaction Network Theory (CRNT)",
        "domain": "Dynamic Systems",
        "equation": "dc/dt = S·v(c);  v_j(c) = k_j Π cᵢ^{y_ij};  deficiency δ = n − l − s;  δ=0 → unique equilibrium",
        "update_form": "mass_action_kinetics",
        "optimization": None,
        "fixed_points": "detailed_balance_equilibrium",
        "operators": {"stoichiometric_matrix", "mass_action", "deficiency",
                      "complex_balanced", "lyapunov_function"},
        "patterns": {
            "fixed_point_stability",
            "conservation_of_probability",
            "population_dynamics",
            "energy_minimization",
            "compositional_structure",
            "phase_transition",
        },
        "variables": {
            "state": "species_concentrations",
            "energy": "gibbs_free_energy",
            "flow": "reaction_fluxes",
            "coupling": "stoichiometric_matrix",
        },
        "conservation": {"mass_conservation", "detailed_balance"},
        "structure": "stoichiometric_network",
    },

    # ── Statistical Physics (disordered systems) ─────────────────────────
    "replica_method": {
        "display_name": "Replica Method",
        "domain": "Statistical Physics",
        "equation": "⟨ln Z⟩ = lim_{n→0} (⟨Z^n⟩−1)/n;  F = −(1/β) lim_{n→0} ∂/∂n ⟨Z^n⟩;  RSB: Q_ab → Parisi functional",
        "update_form": "analytic_continuation",
        "optimization": None,
        "fixed_points": "quenched_free_energy",
        "operators": {"partition_function", "disorder_average", "saddle_point",
                      "replica_symmetry_breaking", "overlap_distribution"},
        "patterns": {
            "energy_based",
            "energy_entropy_tradeoff",
            "mean_field",
            "phase_transition",
            "universality",
            "pairwise_coupling",
        },
        "variables": {
            "state": "replica_overlap_matrix",
            "energy": "quenched_free_energy",
            "coupling": "disorder_distribution",
            "order_parameter": "overlap_distribution",
        },
        "conservation": {"replica_limit"},
        "structure": "disordered_pairwise_energy_model",
    },

    # ── Differential Geometry (statistical) ──────────────────────────────
    "information_geometry": {
        "display_name": "Information Geometry",
        "domain": "Statistics",
        "equation": "gᵢⱼ(θ) = E[∂ᵢlog p · ∂ⱼlog p] = I(θ)ᵢⱼ;  Γᵢⱼₖ = E[∂ᵢ∂ⱼlog p · ∂ₖlog p];  ds² = gᵢⱼdθⁱdθʲ",
        "update_form": "riemannian_gradient",
        "optimization": "geodesic_on_statistical_manifold",
        "fixed_points": "sufficient_statistic_submanifold",
        "operators": {"fisher_information", "connection", "geodesic",
                      "divergence", "dual_affine_connection"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "structural_isomorphism",
            "information_gain",
            "optimal_inference",
            "gradient_descent",
        },
        "variables": {
            "state": "point_on_statistical_manifold",
            "energy": "kl_divergence",
            "metric": "fisher_information_matrix",
            "flow": "natural_gradient_direction",
        },
        "conservation": {"riemannian_metric_invariance"},
        "structure": "riemannian_manifold_of_distributions",
    },

    # ── Stability Theory ─────────────────────────────────────────────────
    "lyapunov_stability": {
        "display_name": "Lyapunov Stability Theory",
        "domain": "Dynamic Systems",
        "equation": "V(x) > 0, V(0) = 0;  V̇(x) = ∇V·f(x) ≤ 0;  V̇ < 0 → asymptotic stability;  V̇ ≤ 0 → stability",
        "update_form": "lyapunov_function_descent",
        "optimization": None,
        "fixed_points": "stable_equilibrium",
        "operators": {"lyapunov_function", "linearization", "eigenvalue_decomposition",
                      "invariance_principle", "basin_of_attraction"},
        "patterns": {
            "fixed_point_stability",
            "energy_minimization",
            "topological_invariants",
            "gradient_descent",
            "conservation_of_probability",
        },
        "variables": {
            "state": "dynamical_state",
            "energy": "lyapunov_function",
            "dynamics": "flow_field",
            "basin": "region_of_attraction",
        },
        "conservation": {"lyapunov_decrease"},
        "structure": "parameter_dependent_dynamical_system",
    },

    # ── Optimization (geometry-aware) ────────────────────────────────────
    "mirror_descent": {
        "display_name": "Mirror Descent",
        "domain": "Optimization",
        "equation": "∇φ(x_{t+1}) = ∇φ(x_t) − η∇f(x_t);  x_{t+1} = argmin{η⟨∇f,x⟩ + D_φ(x,x_t)};  D_φ = Bregman divergence",
        "update_form": "bregman_proximal",
        "optimization": "minimize_loss_in_dual",
        "fixed_points": "constrained_optimum",
        "operators": {"gradient", "bregman_divergence", "dual_map",
                      "convex_conjugate", "projection"},
        "patterns": {
            "gradient_descent",
            "dual_variables",
            "variational_principle",
            "energy_minimization",
            "structural_isomorphism",
            "information_gain",
        },
        "variables": {
            "state": "primal_and_dual_iterates",
            "energy": "objective_function",
            "metric": "bregman_divergence",
            "flow": "mirror_map_direction",
        },
        "conservation": {"regret_bound"},
        "structure": "riemannian_manifold_of_distributions",
    },

    # ── Generative Models (adversarial) ──────────────────────────────────
    "gan": {
        "display_name": "Generative Adversarial Network (GAN)",
        "domain": "Machine Learning",
        "equation": "min_G max_D E[log D(x)] + E[log(1−D(G(z)))];  p_G → p_data at Nash equilibrium",
        "update_form": "alternating_gradient",
        "optimization": "minimax_saddle_point",
        "fixed_points": "nash_equilibrium_generative",
        "operators": {"gradient", "sampling", "discriminator",
                      "generator", "wasserstein_distance"},
        "patterns": {
            "dual_variables",
            "gradient_descent",
            "exploration_exploitation",
            "energy_minimization",
            "fixed_point_stability",
            "adversarial",
        },
        "variables": {
            "state": "generator_discriminator_params",
            "energy": "minimax_value",
            "dynamics": "adversarial_gradient_updates",
            "distribution": "generated_distribution",
        },
        "conservation": set(),
        "structure": "minimax_game_over_distributions",
    },

    # ── Reinforcement Learning (value-based) ─────────────────────────────
    "td_learning": {
        "display_name": "Temporal Difference Learning",
        "domain": "Reinforcement Learning",
        "equation": "δ_t = r_t + γV(s_{t+1}) − V(s_t);  V(s_t) ← V(s_t) + αδ_t;  TD(λ): e_t = γλe_{t-1} + ∇V(s_t)",
        "update_form": "bootstrapped_value_update",
        "optimization": "minimize_td_error",
        "fixed_points": "value_function_fixed_point",
        "operators": {"bellman_operator", "eligibility_trace", "gradient",
                      "temporal_difference", "bootstrapping"},
        "patterns": {
            "gradient_descent",
            "fixed_point_iteration",
            "exploration_exploitation",
            "energy_minimization",
            "prediction_error",
        },
        "variables": {
            "state": "value_function_estimate",
            "energy": "mean_squared_td_error",
            "signal": "td_error",
            "dynamics": "value_iteration_dynamics",
        },
        "conservation": {"bellman_consistency"},
        "structure": "bellman_recursion",
    },

    # ── Algebraic Graph Theory ───────────────────────────────────────────
    "spectral_graph_theory": {
        "display_name": "Spectral Graph Theory",
        "domain": "Mathematics",
        "equation": "Lf = λf;  L = D − A;  λ_2 = algebraic connectivity;  h(G) ≤ √(2λ_2) (Cheeger);  f_k = k-th Fiedler vector",
        "update_form": "eigenvalue_decomposition",
        "optimization": None,
        "fixed_points": "graph_laplacian_spectrum",
        "operators": {"eigenvalue_decomposition", "laplacian", "adjacency",
                      "graph_fourier_transform", "cheeger_constant"},
        "patterns": {
            "universality",
            "topological_invariants",
            "pairwise_coupling",
            "structural_isomorphism",
            "scale_invariance",
            "phase_transition",
        },
        "variables": {
            "state": "graph_signal",
            "energy": "dirichlet_energy",
            "coupling": "adjacency_matrix",
            "spectrum": "laplacian_eigenvalues",
        },
        "conservation": {"total_edge_weight"},
        "structure": "graph_operator_spectrum",
    },

    # ── Generative Models (flow-based) ───────────────────────────────────
    "normalizing_flows": {
        "display_name": "Normalizing Flows",
        "domain": "Machine Learning",
        "equation": "x = f(z), z ~ p_z;  log p_x(x) = log p_z(f⁻¹(x)) + log|det ∂f⁻¹/∂x|;  max Σ log p_x(xᵢ)",
        "update_form": "gradient_on_flow_parameters",
        "optimization": "maximize_log_likelihood",
        "fixed_points": "trained_invertible_map",
        "operators": {"gradient", "jacobian", "change_of_variables",
                      "invertible_transform", "determinant"},
        "patterns": {
            "variational_principle",
            "gradient_descent",
            "energy_minimization",
            "structural_isomorphism",
            "information_gain",
            "compositional_structure",
        },
        "variables": {
            "state": "flow_parameters",
            "energy": "negative_log_likelihood",
            "dynamics": "invertible_transformation",
            "distribution": "pushforward_density",
        },
        "conservation": {"probability_mass_conservation"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Stochastic Control ───────────────────────────────────────────────
    "stochastic_optimal_control": {
        "display_name": "Stochastic Optimal Control",
        "domain": "Control Theory",
        "equation": "dx = f(x,u)dt + σ(x)dW;  J = E[∫L(x,u)dt + Φ(x_T)];  −∂V/∂t = min_u{L + f·∇V + ½σσᵀ:∇²V}",
        "update_form": "stochastic_hjb",
        "optimization": "minimize_expected_cost",
        "fixed_points": "optimal_stochastic_policy",
        "operators": {"bellman_operator", "ito_calculus", "hamiltonian",
                      "fokker_planck_adjoint", "stochastic_gradient"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "gradient_descent",
            "dual_variables",
            "exploration_exploitation",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "stochastic_state_process",
            "energy": "expected_cost_to_go",
            "control": "feedback_policy",
            "dynamics": "controlled_diffusion",
        },
        "conservation": {"bellman_optimality"},
        "structure": "bellman_recursion",
    },

    # ── Self-Supervised Learning ─────────────────────────────────────────
    "contrastive_learning": {
        "display_name": "Contrastive Learning / NCE",
        "domain": "Machine Learning",
        "equation": "L = −log[exp(sim(z_i,z_j)/τ) / Σ_k exp(sim(z_i,z_k)/τ)];  p(d=1|x,c) = σ(f(x)ᵀf(c));  NCE → MLE as k→∞",
        "update_form": "contrastive_gradient",
        "optimization": "maximize_mutual_information_bound",
        "fixed_points": "aligned_representation",
        "operators": {"inner_product", "gradient", "temperature_scaling",
                      "negative_sampling", "projection"},
        "patterns": {
            "energy_based",
            "gradient_descent",
            "energy_minimization",
            "information_gain",
            "pairwise_coupling",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "encoder_parameters",
            "energy": "contrastive_loss",
            "coupling": "similarity_matrix",
            "temperature": "softmax_temperature",
        },
        "conservation": set(),
        "structure": "energy_based_pairwise_model",
    },

    # ── Probabilistic Graphical Models ───────────────────────────────────
    "belief_propagation": {
        "display_name": "Belief Propagation / Message Passing",
        "domain": "Machine Learning",
        "equation": "m_{i→j}(x_j) = Σ_{x_i} ψ(x_i,x_j) φ(x_i) Π_{k∈N(i)\\j} m_{k→i}(x_i);  b(x_i) ∝ φ(x_i) Π_{j∈N(i)} m_{j→i}(x_i)",
        "update_form": "message_passing_fixed_point",
        "optimization": "bethe_free_energy",
        "fixed_points": "marginal_beliefs",
        "operators": {"message_update", "marginalization", "factor_graph",
                      "partition_function", "bethe_approximation"},
        "patterns": {
            "fixed_point_iteration",
            "bayesian_inference",
            "pairwise_coupling",
            "energy_based",
            "compositional_structure",
            "mean_field",
        },
        "variables": {
            "state": "messages_and_beliefs",
            "energy": "bethe_free_energy",
            "coupling": "factor_potentials",
            "dynamics": "message_schedule",
        },
        "conservation": {"normalization_of_beliefs"},
        "structure": "energy_based_pairwise_model",
    },

    # ── Bayesian Estimation ──────────────────────────────────────────────
    "map_estimation": {
        "display_name": "Maximum a Posteriori (MAP) Estimation",
        "domain": "Statistics",
        "equation": "θ_MAP = argmax p(θ|x) = argmax [log p(x|θ) + log p(θ)];  ∇log p(x|θ) + ∇log p(θ) = 0;  MAP → MLE as prior → flat",
        "update_form": "penalized_likelihood_gradient",
        "optimization": "maximize_posterior",
        "fixed_points": "posterior_mode",
        "operators": {"gradient", "prior", "posterior", "regularizer",
                      "laplace_approximation"},
        "patterns": {
            "bayesian_inference",
            "gradient_descent",
            "energy_minimization",
            "variational_principle",
            "optimal_inference",
            "dual_variables",
        },
        "variables": {
            "state": "parameter_estimate",
            "energy": "negative_log_posterior",
            "prior": "regularization_term",
            "information": "posterior_curvature",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Generative Adversarial ───────────────────────────────────────────
    "wasserstein_gan": {
        "display_name": "Wasserstein GAN",
        "domain": "Machine Learning",
        "equation": "min_G max_D E[D(x)] − E[D(G(z))];  W(p,q) = sup_{||D||_L≤1} E_p[D] − E_q[D];  Kantorovich-Rubinstein duality",
        "update_form": "alternating_gradient",
        "optimization": "minimax_wasserstein",
        "fixed_points": "generator_matches_data",
        "operators": {"gradient", "lipschitz_constraint", "wasserstein_distance",
                      "pushforward_map", "dual_potential"},
        "patterns": {
            "variational_principle",
            "gradient_descent",
            "dual_variables",
            "competitive_dynamics",
            "energy_minimization",
            "exploration_exploitation",
        },
        "variables": {
            "state": "generator_critic_parameters",
            "energy": "wasserstein_distance",
            "dynamics": "adversarial_training",
            "coupling": "critic_potential",
        },
        "conservation": set(),
        "structure": "minimax_optimization",
    },

    # ── Planning / Search ────────────────────────────────────────────────
    "mcts": {
        "display_name": "Monte Carlo Tree Search (MCTS)",
        "domain": "Reinforcement Learning",
        "equation": "UCB1: a* = argmax[Q(s,a) + c√(ln N(s)/N(s,a))];  V(s) = 1/N Σ R_i;  backup: N(s)+=1, Q(s,a) += (R−Q)/N",
        "update_form": "tree_backup",
        "optimization": "maximize_expected_return",
        "fixed_points": "optimal_action_values",
        "operators": {"selection", "expansion", "simulation", "backpropagation",
                      "ucb_bound"},
        "patterns": {
            "exploration_exploitation",
            "energy_minimization",
            "gradient_descent",
            "bayesian_inference",
            "compositional_structure",
        },
        "variables": {
            "state": "tree_statistics",
            "energy": "negative_expected_return",
            "dynamics": "tree_traversal_policy",
            "information": "visit_counts",
        },
        "conservation": {"total_simulation_count"},
        "structure": "bellman_recursion",
    },

    # ── Sequential Optimization ──────────────────────────────────────────
    "bayesian_optimization": {
        "display_name": "Bayesian Optimization",
        "domain": "Optimization",
        "equation": "x_{n+1} = argmax α(x; D_n);  α_EI(x) = E[max(f(x)−f*,0)];  f ~ GP(μ,k);  p(f|D) ∝ p(D|f)p(f)",
        "update_form": "acquisition_maximization",
        "optimization": "maximize_acquisition_function",
        "fixed_points": "global_optimum",
        "operators": {"gaussian_process", "acquisition_function",
                      "posterior_update", "kernel_evaluation", "gradient"},
        "patterns": {
            "bayesian_inference",
            "exploration_exploitation",
            "information_gain",
            "energy_minimization",
            "variational_principle",
            "optimal_inference",
        },
        "variables": {
            "state": "gp_posterior",
            "energy": "negative_acquisition_value",
            "coupling": "kernel_gram_matrix",
            "information": "posterior_variance",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Approximate Inference ────────────────────────────────────────────
    "expectation_propagation": {
        "display_name": "Expectation Propagation (EP)",
        "domain": "Machine Learning",
        "equation": "q(θ) = 1/Z Π f̃ᵢ(θ);  f̃ᵢ ← proj[q^\\i · fᵢ] / q^\\i;  proj = moment matching to exponential family;  q^\\i = q/f̃ᵢ",
        "update_form": "moment_matching_iteration",
        "optimization": "minimize_local_kl_divergence",
        "fixed_points": "consistent_site_approximations",
        "operators": {"moment_matching", "cavity_distribution",
                      "exponential_family_projection", "partition_function"},
        "patterns": {
            "bayesian_inference",
            "fixed_point_iteration",
            "mean_field",
            "energy_minimization",
            "compositional_structure",
            "information_gain",
        },
        "variables": {
            "state": "site_approximations",
            "energy": "bethe_free_energy",
            "dynamics": "message_schedule",
            "information": "moment_parameters",
        },
        "conservation": {"moment_consistency"},
        "structure": "energy_based_pairwise_model",
    },

    # ── Tensor Methods ───────────────────────────────────────────────────
    "tensor_network": {
        "display_name": "Tensor Network / Tensor Decomposition",
        "domain": "Physics",
        "equation": "Ψ = Σ A^{s1} A^{s2} ... A^{sN};  MPS: Ψ_{s1...sN} = Tr(A^{s1}...A^{sN});  SVD truncation: ||Ψ − Ψ̃|| ≤ ε",
        "update_form": "local_tensor_update",
        "optimization": "minimize_truncation_error",
        "fixed_points": "optimal_low_rank_approximation",
        "operators": {"contraction", "svd_truncation", "bond_dimension",
                      "transfer_matrix", "tensor_product"},
        "patterns": {
            "compositional_structure",
            "structural_isomorphism",
            "energy_minimization",
            "variational_principle",
            "information_gain",
            "renormalization",
        },
        "variables": {
            "state": "tensor_cores",
            "energy": "truncation_error",
            "coupling": "bond_indices",
            "spectrum": "singular_values",
        },
        "conservation": {"unitarity_of_isometries"},
        "structure": "renormalization_hierarchy",
    },
    # ── Sequential Decision Making ─────────────────────────────────────
    "multi_armed_bandit": {
        "display_name": "Multi-Armed Bandit / UCB",
        "domain": "Reinforcement Learning",
        "equation": "UCB: a* = argmax[μ̂ₐ + c√(ln t / Nₐ)];  regret R_T = T μ* − Σ μ_{aₜ};  Thompson: sample θₐ ~ posterior, play argmax θₐ",
        "update_form": "index_policy_update",
        "optimization": "minimize_cumulative_regret",
        "fixed_points": "optimal_arm",
        "operators": {"confidence_bound", "posterior_update",
                      "regret_decomposition", "exploration_bonus"},
        "patterns": {
            "exploration_exploitation",
            "bayesian_inference",
            "information_gain",
            "energy_minimization",
            "optimal_inference",
        },
        "variables": {
            "state": "arm_statistics",
            "energy": "cumulative_regret",
            "information": "posterior_uncertainty",
            "dynamics": "sequential_allocation",
        },
        "conservation": {"total_pulls_equal_time"},
        "structure": "bellman_recursion",
    },

    # ── Measure-Theoretic Optimization ───────────────────────────────────
    "wasserstein_gradient_flow": {
        "display_name": "Wasserstein Gradient Flow",
        "domain": "Optimization",
        "equation": "∂ρ/∂t = ∇·(ρ∇(δF/δρ));  JKO: ρ_{k+1} = argmin[F(ρ) + W₂²(ρ,ρₖ)/2τ];  F(ρ) = ∫ρlogρ + ∫ρV + ∫∫ρWρ",
        "update_form": "jko_proximal_step",
        "optimization": "minimize_free_energy_functional",
        "fixed_points": "stationary_measure",
        "operators": {"wasserstein_distance", "functional_derivative",
                      "continuity_equation", "proximal_operator", "gradient"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "gradient_descent",
            "energy_entropy_tradeoff",
            "dual_variables",
        },
        "variables": {
            "state": "probability_density",
            "energy": "free_energy_functional",
            "dynamics": "continuity_equation",
            "coupling": "interaction_potential",
        },
        "conservation": {"probability_mass_conservation"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Particle Variational Inference ───────────────────────────────────
    "stein_variational": {
        "display_name": "Stein Variational Gradient Descent (SVGD)",
        "domain": "Machine Learning",
        "equation": "xᵢ ← xᵢ + ε φ*(xᵢ);  φ* = argmax_{||φ||≤1} −d/dε KL(T_ε q || p);  φ*(x) = E_q[k(x',x)∇log p(x') + ∇_{x'}k(x',x)]",
        "update_form": "kernel_gradient_transport",
        "optimization": "minimize_kl_divergence",
        "fixed_points": "posterior_particle_approximation",
        "operators": {"stein_operator", "kernel_evaluation", "gradient",
                      "repulsive_force", "functional_gradient"},
        "patterns": {
            "gradient_descent",
            "bayesian_inference",
            "energy_minimization",
            "pairwise_coupling",
            "variational_principle",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "particle_positions",
            "energy": "kl_divergence",
            "coupling": "kernel_gram_matrix",
            "dynamics": "deterministic_particle_flow",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Continuous-Depth Networks ────────────────────────────────────────
    "neural_ode": {
        "display_name": "Neural ODE",
        "domain": "Machine Learning",
        "equation": "dh/dt = f_θ(h,t);  h(T) = h(0) + ∫₀ᵀ f_θ(h,t)dt;  adjoint: da/dt = −aᵀ ∂f/∂h;  ∂L/∂θ = −∫ aᵀ ∂f/∂θ dt",
        "update_form": "adjoint_sensitivity",
        "optimization": "minimize_loss_via_adjoint",
        "fixed_points": "trained_vector_field",
        "operators": {"ode_solver", "adjoint_method", "gradient",
                      "vector_field", "flow_map"},
        "patterns": {
            "gradient_descent",
            "energy_minimization",
            "variational_principle",
            "compositional_structure",
            "conservation_law",
        },
        "variables": {
            "state": "hidden_trajectory",
            "energy": "terminal_loss",
            "dynamics": "learned_vector_field",
            "control": "network_parameters",
        },
        "conservation": {"flow_invertibility"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Causal Reasoning ─────────────────────────────────────────────────
    "causal_inference": {
        "display_name": "Causal Inference / do-calculus",
        "domain": "Statistics",
        "equation": "P(y|do(x)) = Σ_z P(y|x,z)P(z);  backdoor: P(y|do(x)) = Σ_z P(y|x,z)P(z);  frontdoor;  counterfactual: Y_x(u)",
        "update_form": "interventional_query",
        "optimization": "identify_causal_effect",
        "fixed_points": "causal_estimand",
        "operators": {"do_operator", "d_separation", "graph_surgery",
                      "adjustment_formula", "counterfactual_reasoning"},
        "patterns": {
            "bayesian_inference",
            "compositional_structure",
            "structural_isomorphism",
            "information_gain",
            "optimal_inference",
        },
        "variables": {
            "state": "causal_graph",
            "energy": "interventional_distribution",
            "coupling": "structural_equations",
            "information": "identifiability_conditions",
        },
        "conservation": {"markov_compatibility"},
        "structure": "graphical_model_structure",
    },

    # ── Nonparametric Bayes ──────────────────────────────────────────────
    "gaussian_process": {
        "display_name": "Gaussian Process Regression",
        "domain": "Machine Learning",
        "equation": "f ~ GP(μ,k);  p(f*|X*,X,y) = N(K*ᵀ(K+σ²I)⁻¹y, K**−K*ᵀ(K+σ²I)⁻¹K*);  log p(y|X) = −½yᵀK⁻¹y − ½log|K| − n/2 log 2π",
        "update_form": "posterior_conditioning",
        "optimization": "maximize_marginal_likelihood",
        "fixed_points": "posterior_predictive",
        "operators": {"kernel_evaluation", "matrix_inversion", "cholesky",
                      "posterior_update", "marginal_likelihood"},
        "patterns": {
            "bayesian_inference",
            "variational_principle",
            "energy_minimization",
            "pairwise_coupling",
            "information_gain",
            "optimal_inference",
        },
        "variables": {
            "state": "posterior_mean_and_covariance",
            "energy": "negative_log_marginal_likelihood",
            "coupling": "kernel_gram_matrix",
            "information": "posterior_variance",
        },
        "conservation": {"consistency_under_marginalization"},
        "structure": "hilbert_space_optimization",
    },

    # ── Sequential Decision Process ──────────────────────────────────────
    "markov_decision_process": {
        "display_name": "Markov Decision Process (MDP)",
        "domain": "Reinforcement Learning",
        "equation": "V*(s) = max_a [R(s,a) + γ Σ P(s'|s,a)V*(s')];  π*(s) = argmax_a Q*(s,a);  Q*(s,a) = R + γ Σ P V*",
        "update_form": "bellman_optimality",
        "optimization": "maximize_discounted_return",
        "fixed_points": "optimal_value_and_policy",
        "operators": {"bellman_operator", "transition_kernel",
                      "policy_evaluation", "policy_improvement", "contraction"},
        "patterns": {
            "fixed_point_iteration",
            "energy_minimization",
            "exploration_exploitation",
            "compositional_structure",
            "dual_variables",
        },
        "variables": {
            "state": "value_function",
            "energy": "negative_expected_return",
            "dynamics": "transition_probabilities",
            "control": "policy",
        },
        "conservation": {"probability_flow_conservation"},
        "structure": "bellman_recursion",
    },

    # ── Fixed Point Theory ───────────────────────────────────────────────
    "contraction_mapping": {
        "display_name": "Contraction Mapping / Banach Fixed Point",
        "domain": "Mathematics",
        "equation": "T: X→X;  d(Tx,Ty) ≤ γ d(x,y), γ<1;  x* = lim T^n(x₀);  d(x_n,x*) ≤ γⁿ/(1−γ) d(x₁,x₀)",
        "update_form": "iterated_contraction",
        "optimization": "find_fixed_point",
        "fixed_points": "unique_fixed_point",
        "operators": {"contraction", "metric", "iteration",
                      "error_bound", "completeness"},
        "patterns": {
            "fixed_point_iteration",
            "energy_minimization",
            "convergence_guarantee",
        },
        "variables": {
            "state": "iterate",
            "energy": "distance_to_fixed_point",
            "dynamics": "contraction_operator",
            "rate": "contraction_coefficient",
        },
        "conservation": set(),
        "structure": "bellman_recursion",
    },

    # ── Active Inference ─────────────────────────────────────────────────
    "active_inference": {
        "display_name": "Active Inference",
        "domain": "Neuroscience",
        "equation": "F = E_q[log q(s) − log p(o,s)];  π* = argmin E_q(π)[G(π)];  G = E[H[P(o|s)] + D_KL[q(s|π)||p(s)]];  action = −∂F/∂a",
        "update_form": "free_energy_minimization",
        "optimization": "minimize_expected_free_energy",
        "fixed_points": "preferred_observations",
        "operators": {"variational_inference", "belief_update",
                      "policy_selection", "precision_weighting", "gradient"},
        "patterns": {
            "bayesian_inference",
            "variational_principle",
            "energy_minimization",
            "exploration_exploitation",
            "information_gain",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "beliefs_about_hidden_states",
            "energy": "variational_free_energy",
            "dynamics": "belief_updating",
            "control": "action_policy",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Ensemble Learning ────────────────────────────────────────────────
    "boosting": {
        "display_name": "Gradient Boosting / AdaBoost",
        "domain": "Machine Learning",
        "equation": "F_m(x) = F_{m-1}(x) + ν h_m(x);  h_m = argmin Σ L(yᵢ, F_{m-1}(xᵢ) + h(xᵢ));  wᵢ ∝ exp(−yᵢ F(xᵢ));  AdaBoost = exp loss",
        "update_form": "functional_gradient_descent",
        "optimization": "minimize_empirical_loss",
        "fixed_points": "converged_ensemble",
        "operators": {"gradient", "weak_learner", "reweighting",
                      "functional_gradient", "regularizer"},
        "patterns": {
            "gradient_descent",
            "energy_minimization",
            "compositional_structure",
            "information_gain",
            "variational_principle",
        },
        "variables": {
            "state": "ensemble_function",
            "energy": "empirical_loss",
            "dynamics": "residual_fitting",
            "prior": "learning_rate_shrinkage",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Matrix Methods ───────────────────────────────────────────────────
    "matrix_factorization": {
        "display_name": "Matrix Factorization / NMF",
        "domain": "Machine Learning",
        "equation": "min ||X − WH||²_F;  NMF: W,H ≥ 0;  SVD: X = UΣVᵀ;  update: H ← H ⊙ (WᵀX)/(WᵀWH);  W ← W ⊙ (XHᵀ)/(WHHᵀ)",
        "update_form": "alternating_minimization",
        "optimization": "minimize_reconstruction_error",
        "fixed_points": "optimal_factorization",
        "operators": {"svd", "multiplicative_update", "projection",
                      "frobenius_norm", "low_rank_approximation"},
        "patterns": {
            "energy_minimization",
            "fixed_point_iteration",
            "compositional_structure",
            "structural_isomorphism",
            "dual_variables",
        },
        "variables": {
            "state": "factor_matrices",
            "energy": "reconstruction_error",
            "spectrum": "singular_values",
            "coupling": "factor_product",
        },
        "conservation": {"eckart_young_optimality"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Learning Theory ──────────────────────────────────────────────────
    "pac_learning": {
        "display_name": "PAC Learning / VC Theory",
        "domain": "Statistics",
        "equation": "P(sup_{h∈H} |R(h)−R̂(h)| > ε) ≤ 2|H|e^{-2nε²};  VC: n = O(d/ε² log(1/δ));  Rademacher: R̂_n(H) = E_σ[sup_h 1/n Σ σᵢh(xᵢ)]",
        "update_form": "uniform_convergence_bound",
        "optimization": "minimize_generalization_error",
        "fixed_points": "consistent_hypothesis",
        "operators": {"covering_number", "rademacher_complexity",
                      "vc_dimension", "concentration_inequality"},
        "patterns": {
            "information_gain",
            "dual_variables",
            "structural_isomorphism",
            "energy_minimization",
        },
        "variables": {
            "state": "hypothesis_class",
            "energy": "generalization_gap",
            "information": "sample_complexity",
            "coupling": "hypothesis_complexity",
        },
        "conservation": {"no_free_lunch"},
        "structure": "information_theoretic_bound",
    },

    # ── Fluid Dynamics ───────────────────────────────────────────────────
    "navier_stokes": {
        "display_name": "Navier-Stokes Equations",
        "domain": "Physics",
        "equation": "∂u/∂t + (u·∇)u = −∇p/ρ + ν∇²u + f;  ∇·u = 0;  Re = UL/ν;  energy: d/dt ∫½|u|² = −ν∫|∇u|² + ∫f·u",
        "update_form": "momentum_transport",
        "optimization": "satisfy_conservation_laws",
        "fixed_points": "steady_state_flow",
        "operators": {"advection", "diffusion", "pressure_projection",
                      "laplacian", "nonlinear_transport"},
        "patterns": {
            "conservation_law",
            "energy_minimization",
            "symmetry_breaking",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "velocity_field",
            "energy": "kinetic_energy",
            "dynamics": "momentum_equation",
            "dissipation": "viscous_dissipation",
        },
        "conservation": {"mass_conservation", "momentum_conservation"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Information Complexity ───────────────────────────────────────────
    "kolmogorov_complexity": {
        "display_name": "Kolmogorov Complexity / AIT",
        "domain": "Information Theory",
        "equation": "K(x) = min{|p| : U(p) = x};  K(x|y) = min{|p| : U(p,y) = x};  K(x,y) ≈ K(x) + K(y|x);  incompressibility: K(x) ≥ |x| − c",
        "update_form": "shortest_program_search",
        "optimization": "minimize_description_length",
        "fixed_points": "minimal_sufficient_program",
        "operators": {"universal_turing_machine", "prefix_coding",
                      "conditional_complexity", "mutual_information"},
        "patterns": {
            "information_gain",
            "compositional_structure",
            "structural_isomorphism",
            "dual_variables",
        },
        "variables": {
            "state": "description",
            "energy": "program_length",
            "information": "algorithmic_mutual_information",
            "coupling": "conditional_complexity",
        },
        "conservation": {"symmetry_of_information"},
        "structure": "information_theoretic_bound",
    },

    # ── Theory #100: Minimum Description Length ──────────────────────────
    "minimum_description_length": {
        "display_name": "Minimum Description Length (MDL)",
        "domain": "Statistics",
        "equation": "M* = argmin [L(D|M) + L(M)];  two-part: L(x,θ) = −log p(x|θ) + L(θ);  normalized ML: p̄(x) = p(x|θ̂(x))/∫p(y|θ̂(y))dy",
        "update_form": "model_selection",
        "optimization": "minimize_total_codelength",
        "fixed_points": "optimal_model_complexity",
        "operators": {"prefix_coding", "universal_model", "stochastic_complexity",
                      "parametric_complexity", "fisher_information"},
        "patterns": {
            "information_gain",
            "energy_minimization",
            "variational_principle",
            "bayesian_inference",
            "dual_variables",
            "compositional_structure",
        },
        "variables": {
            "state": "model_and_parameters",
            "energy": "total_codelength",
            "information": "stochastic_complexity",
            "prior": "model_complexity_penalty",
        },
        "conservation": {"kraft_inequality"},
        "structure": "information_theoretic_bound",
    },

    # ── Convex Optimization ──────────────────────────────────────────────
    "lagrange_duality": {
        "display_name": "Lagrange Duality / KKT Conditions",
        "domain": "Optimization",
        "equation": "L(x,λ,ν) = f(x) + Σλᵢgᵢ(x) + Σνⱼhⱼ(x);  d* = max_{λ≥0} min_x L;  strong duality: p*=d*;  KKT: ∇f + Σλᵢ∇gᵢ = 0, λᵢgᵢ = 0",
        "update_form": "primal_dual_iteration",
        "optimization": "saddle_point_of_lagrangian",
        "fixed_points": "kkt_point",
        "operators": {"gradient", "lagrangian", "complementary_slackness",
                      "dual_ascent", "barrier_function"},
        "patterns": {
            "variational_principle",
            "dual_variables",
            "energy_minimization",
            "gradient_descent",
            "fixed_point_iteration",
        },
        "variables": {
            "state": "primal_dual_variables",
            "energy": "lagrangian_value",
            "coupling": "constraint_jacobian",
            "dynamics": "primal_dual_dynamics",
        },
        "conservation": {"complementary_slackness"},
        "structure": "minimax_optimization",
    },

    # ── Online Learning ──────────────────────────────────────────────────
    "online_convex_optimization": {
        "display_name": "Online Convex Optimization / Regret",
        "domain": "Machine Learning",
        "equation": "Regret_T = Σ f_t(x_t) − min_x Σ f_t(x);  FTRL: x_t = argmin[Σ f_s(x) + R(x)];  OGD: x_{t+1} = Π(x_t − η∇f_t)",
        "update_form": "follow_the_regularized_leader",
        "optimization": "minimize_regret",
        "fixed_points": "no_regret_strategy",
        "operators": {"gradient", "projection", "regularizer",
                      "regret_bound", "adaptive_learning_rate"},
        "patterns": {
            "gradient_descent",
            "energy_minimization",
            "exploration_exploitation",
            "dual_variables",
            "variational_principle",
        },
        "variables": {
            "state": "online_iterate",
            "energy": "cumulative_regret",
            "dynamics": "adversarial_loss_sequence",
            "prior": "regularization_function",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Sequential Analysis ──────────────────────────────────────────────
    "optimal_stopping": {
        "display_name": "Optimal Stopping / Secretary Problem",
        "domain": "Statistics",
        "equation": "V(x,t) = max{g(x,t), E[V(X_{t+1},t+1)|X_t=x]};  τ* = inf{t: V(X_t,t) = g(X_t,t)};  secretary: reject first n/e, pick next best",
        "update_form": "backward_induction",
        "optimization": "maximize_expected_payoff",
        "fixed_points": "optimal_stopping_boundary",
        "operators": {"bellman_operator", "conditional_expectation",
                      "snell_envelope", "stopping_boundary"},
        "patterns": {
            "energy_minimization",
            "exploration_exploitation",
            "dual_variables",
            "fixed_point_iteration",
        },
        "variables": {
            "state": "continuation_value",
            "energy": "negative_expected_payoff",
            "dynamics": "stochastic_process",
            "control": "stopping_rule",
        },
        "conservation": {"supermartingale_property"},
        "structure": "bellman_recursion",
    },

    # ── Probability Theory ───────────────────────────────────────────────
    "large_deviations": {
        "display_name": "Large Deviations / Cramér's Theorem",
        "domain": "Mathematics",
        "equation": "P(S_n/n ∈ A) ≈ exp(−n inf_{x∈A} I(x));  I(x) = sup_θ[θx − log M(θ)];  Sanov: I(Q) = D_KL(Q||P);  Varadhan: lim 1/n log E[e^{nF}] = sup[F−I]",
        "update_form": "rate_function_computation",
        "optimization": "minimize_rate_function",
        "fixed_points": "most_likely_deviation",
        "operators": {"legendre_transform", "rate_function",
                      "moment_generating_function", "contraction_principle"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "dual_variables",
            "energy_entropy_tradeoff",
            "information_gain",
        },
        "variables": {
            "state": "empirical_measure",
            "energy": "rate_function",
            "information": "kl_divergence",
            "coupling": "tilted_distribution",
        },
        "conservation": set(),
        "structure": "information_theoretic_bound",
    },

    # ── Dynamical Systems (measure-theoretic) ────────────────────────────
    "ergodic_theory": {
        "display_name": "Ergodic Theory",
        "domain": "Mathematics",
        "equation": "lim 1/N Σ f(T^n x) = ∫ f dμ  a.e.;  mixing: μ(A∩T⁻ⁿB) → μ(A)μ(B);  entropy: h(T) = sup_P H(P|T⁻¹P)",
        "update_form": "time_average_convergence",
        "optimization": "characterize_invariant_measure",
        "fixed_points": "ergodic_measure",
        "operators": {"koopman_operator", "transfer_operator",
                      "time_average", "mixing_rate", "entropy_rate"},
        "patterns": {
            "fixed_point_iteration",
            "conservation_law",
            "energy_entropy_tradeoff",
            "structural_isomorphism",
        },
        "variables": {
            "state": "invariant_measure",
            "energy": "metric_entropy",
            "dynamics": "measure_preserving_map",
            "rate": "mixing_rate",
        },
        "conservation": {"measure_preservation"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Economic Design ──────────────────────────────────────────────────
    "mechanism_design": {
        "display_name": "Mechanism Design / Auction Theory",
        "domain": "Economics",
        "equation": "max Σ vᵢ(a(θ)) s.t. IC: Uᵢ(θᵢ) ≥ Uᵢ(θ'ᵢ);  IR: Uᵢ(θᵢ) ≥ 0;  VCG: pᵢ = max_{a} Σ_{j≠i} vⱼ − Σ_{j≠i} vⱼ(a*(θ));  revelation principle",
        "update_form": "incentive_compatible_mechanism",
        "optimization": "maximize_social_welfare",
        "fixed_points": "incentive_compatible_equilibrium",
        "operators": {"revelation_principle", "vcg_payment",
                      "incentive_constraint", "individual_rationality"},
        "patterns": {
            "dual_variables",
            "variational_principle",
            "competitive_dynamics",
            "information_gain",
            "optimal_inference",
        },
        "variables": {
            "state": "allocation_and_payments",
            "energy": "negative_social_welfare",
            "coupling": "type_reports",
            "information": "private_information",
        },
        "conservation": {"budget_balance"},
        "structure": "minimax_optimization",
    },

    # ── Proximal Algorithms ──────────────────────────────────────────────
    "proximal_methods": {
        "display_name": "Proximal Methods / ADMM",
        "domain": "Optimization",
        "equation": "prox_f(x) = argmin[f(y) + ½||y−x||²];  ADMM: x←argmin[f(x)+ρ/2||Ax+Bz−c+u||²], z←argmin[g(z)+ρ/2||Ax+Bz−c+u||²], u←u+Ax+Bz−c",
        "update_form": "proximal_splitting",
        "optimization": "minimize_composite_objective",
        "fixed_points": "consensus_solution",
        "operators": {"proximal_operator", "augmented_lagrangian",
                      "operator_splitting", "projection", "contraction"},
        "patterns": {
            "fixed_point_iteration",
            "dual_variables",
            "energy_minimization",
            "gradient_descent",
            "compositional_structure",
        },
        "variables": {
            "state": "primal_dual_split_variables",
            "energy": "composite_objective",
            "coupling": "consensus_constraint",
            "dynamics": "splitting_iteration",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Mean-Field Games ─────────────────────────────────────────────────
    "mean_field_game": {
        "display_name": "Mean-Field Game",
        "domain": "Game Theory",
        "equation": "−∂V/∂t − ν∆V + H(x,∇V) = F(x,m);  ∂m/∂t − ν∆m − div(m∇_pH) = 0;  coupled HJB + Fokker-Planck;  Nash of N→∞ players",
        "update_form": "coupled_hjb_fokker_planck",
        "optimization": "nash_equilibrium_of_continuum",
        "fixed_points": "mean_field_equilibrium",
        "operators": {"hamilton_jacobi", "fokker_planck_operator",
                      "fixed_point", "mean_field_coupling", "gradient"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "competitive_dynamics",
            "mean_field",
            "fixed_point_iteration",
            "energy_entropy_tradeoff",
        },
        "variables": {
            "state": "value_and_distribution",
            "energy": "social_cost",
            "dynamics": "coupled_pde_system",
            "coupling": "mean_field_interaction",
        },
        "conservation": {"mass_conservation"},
        "structure": "minimax_optimization",
    },

    # ── Spectral Embedding ───────────────────────────────────────────────
    "diffusion_maps": {
        "display_name": "Diffusion Maps",
        "domain": "Machine Learning",
        "equation": "P = D⁻¹W;  Pᵗ → diffusion at scale t;  Ψ_t(x) = (λ₁ᵗψ₁(x),...,λₖᵗψₖ(x));  D_t²(x,y) = Σ λᵢ²ᵗ(ψᵢ(x)−ψᵢ(y))²",
        "update_form": "markov_chain_embedding",
        "optimization": "preserve_diffusion_distance",
        "fixed_points": "spectral_embedding",
        "operators": {"markov_normalization", "eigendecomposition",
                      "diffusion_kernel", "multiscale_geometry"},
        "patterns": {
            "structural_isomorphism",
            "pairwise_coupling",
            "energy_minimization",
            "renormalization",
            "fixed_point_iteration",
        },
        "variables": {
            "state": "diffusion_coordinates",
            "energy": "embedding_distortion",
            "coupling": "transition_kernel",
            "spectrum": "markov_eigenvalues",
        },
        "conservation": {"probability_mass_conservation"},
        "structure": "graph_operator_spectrum",
    },

    # ── Spiking Networks ─────────────────────────────────────────────────
    "spiking_neural_network": {
        "display_name": "Spiking Neural Network / Integrate-and-Fire",
        "domain": "Neuroscience",
        "equation": "τ dV/dt = −(V−V_rest) + R·I(t);  V≥V_th ⟹ spike, V←V_reset;  STDP: Δw = A+ exp(−Δt/τ+) if pre<post, else −A− exp(Δt/τ−)",
        "update_form": "spike_timing_plasticity",
        "optimization": "minimize_prediction_error",
        "fixed_points": "stable_firing_pattern",
        "operators": {"threshold", "integration", "spike_response",
                      "synaptic_update", "refractory_dynamics"},
        "patterns": {
            "energy_based",
            "fixed_point_iteration",
            "pairwise_coupling",
            "energy_minimization",
            "population_dynamics",
            "conservation_law",
        },
        "variables": {
            "state": "membrane_potential",
            "energy": "spike_timing_error",
            "coupling": "synaptic_weights",
            "dynamics": "integrate_and_fire",
        },
        "conservation": {"charge_conservation"},
        "structure": "energy_based_pairwise_model",
    },

    # ── Inverse Problems ─────────────────────────────────────────────────
    "inverse_problem": {
        "display_name": "Inverse Problem / Tikhonov Regularization",
        "domain": "Mathematics",
        "equation": "min ||Ax−b||² + α||Lx||²;  x_α = (AᵀA + αLᵀL)⁻¹Aᵀb;  Morozov: ||Ax_α−b|| = δ;  L-curve: trade-off ||x|| vs ||Ax−b||",
        "update_form": "regularized_least_squares",
        "optimization": "minimize_regularized_residual",
        "fixed_points": "regularized_solution",
        "operators": {"regularizer", "adjoint_operator", "svd",
                      "discrepancy_principle", "parameter_choice"},
        "patterns": {
            "energy_minimization",
            "dual_variables",
            "variational_principle",
            "information_gain",
        },
        "variables": {
            "state": "regularized_estimate",
            "energy": "regularized_residual",
            "prior": "regularization_penalty",
            "information": "noise_level",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Stochastic Approximation ─────────────────────────────────────────
    "robbins_monro": {
        "display_name": "Robbins-Monro / Stochastic Approximation",
        "domain": "Optimization",
        "equation": "x_{n+1} = x_n − a_n(H(x_n) + ξ_n);  Σ aₙ = ∞, Σ aₙ² < ∞;  ODE method: dx/dt = −H(x);  x_n → x* a.s.",
        "update_form": "stochastic_recursion",
        "optimization": "find_root_of_expectation",
        "fixed_points": "root_of_mean_field",
        "operators": {"stochastic_gradient", "step_size_schedule",
                      "martingale_difference", "ode_approximation"},
        "patterns": {
            "gradient_descent",
            "fixed_point_iteration",
            "energy_minimization",
            "convergence_guarantee",
        },
        "variables": {
            "state": "stochastic_iterate",
            "energy": "distance_to_root",
            "dynamics": "mean_ode",
            "rate": "step_size_decay",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Network Science ──────────────────────────────────────────────────
    "preferential_attachment": {
        "display_name": "Preferential Attachment / Scale-Free Networks",
        "domain": "Network Science",
        "equation": "P(new edge to i) ∝ kᵢ;  P(k) ~ k^{−γ}, γ≈3;  mean-field: dkᵢ/dt = m·kᵢ/(2mt);  kᵢ(t) = m√(t/tᵢ)",
        "update_form": "growth_attachment",
        "optimization": "characterize_degree_distribution",
        "fixed_points": "power_law_distribution",
        "operators": {"degree_counting", "attachment_kernel",
                      "mean_field_approximation", "master_equation"},
        "patterns": {
            "population_dynamics",
            "mean_field",
            "symmetry_breaking",
            "renormalization",
            "pairwise_coupling",
        },
        "variables": {
            "state": "degree_sequence",
            "energy": "network_entropy",
            "dynamics": "preferential_growth",
            "coupling": "attachment_kernel",
        },
        "conservation": {"total_edge_count"},
        "structure": "dynamical_system_on_simplex",
    },

    # ── Spectral Theory ─────────────────────────────────────────────────
    "operator_semigroup": {
        "display_name": "Operator Semigroups / Hille-Yosida",
        "domain": "Mathematics",
        "equation": "du/dt = Au;  T(t) = e^{tA};  T(t+s)=T(t)T(s);  resolvent: R(λ,A) = (λI−A)⁻¹;  Hille-Yosida: ||R(λ,A)ⁿ|| ≤ M/(λ−ω)ⁿ",
        "update_form": "semigroup_evolution",
        "optimization": "characterize_generator_spectrum",
        "fixed_points": "equilibrium_of_generator",
        "operators": {"infinitesimal_generator", "resolvent",
                      "spectral_decomposition", "functional_calculus"},
        "patterns": {
            "compositional_structure",
            "structural_isomorphism",
            "fixed_point_iteration",
            "conservation_law",
        },
        "variables": {
            "state": "semigroup_element",
            "energy": "spectral_bound",
            "spectrum": "generator_spectrum",
            "dynamics": "abstract_cauchy_problem",
        },
        "conservation": {"semigroup_property"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Cooperative Game Theory ──────────────────────────────────────────
    "shapley_value": {
        "display_name": "Shapley Value / Cooperative Games",
        "domain": "Game Theory",
        "equation": "φᵢ(v) = Σ_{S⊆N\\i} |S|!(n−|S|−1)!/n! [v(S∪{i})−v(S)];  efficiency: Σφᵢ=v(N);  linearity;  null player;  symmetry",
        "update_form": "marginal_contribution_average",
        "optimization": "fair_surplus_allocation",
        "fixed_points": "unique_fair_allocation",
        "operators": {"marginal_contribution", "coalition_function",
                      "permutation_average", "weighted_sum"},
        "patterns": {
            "variational_principle",
            "compositional_structure",
            "dual_variables",
            "structural_isomorphism",
        },
        "variables": {
            "state": "allocation_vector",
            "energy": "deviation_from_core",
            "coupling": "coalition_function",
            "information": "marginal_contributions",
        },
        "conservation": {"efficiency_axiom"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Algebraic Topology (applied) ─────────────────────────────────────
    "topological_data_analysis": {
        "display_name": "Topological Data Analysis (TDA)",
        "domain": "Mathematics",
        "equation": "VR_ε = {σ⊆X : diam(σ)≤ε};  β_k = rank H_k;  persistence: dgm = {(b_i,d_i)};  stability: d_B(dgm_f,dgm_g) ≤ ||f−g||_∞",
        "update_form": "filtration_computation",
        "optimization": "extract_topological_features",
        "fixed_points": "persistent_features",
        "operators": {"boundary_operator", "persistence_algorithm",
                      "filtration", "bottleneck_distance", "homology"},
        "patterns": {
            "structural_isomorphism",
            "renormalization",
            "compositional_structure",
            "information_gain",
        },
        "variables": {
            "state": "persistence_diagram",
            "energy": "total_persistence",
            "spectrum": "betti_numbers",
            "coupling": "simplicial_complex",
        },
        "conservation": {"stability_of_persistence"},
        "structure": "renormalization_hierarchy",
    },

    # ── Reinforcement Learning (model-based) ────────────────────────────
    "world_model": {
        "display_name": "World Models / Model-Based RL",
        "domain": "Reinforcement Learning",
        "equation": "p̂(s'|s,a;θ);  r̂(s,a;φ);  plan: π* = argmax E_{p̂}[Σγᵗr̂];  Dyna: real experience + simulated rollouts;  model error: ||p̂−p||",
        "update_form": "model_learning_plus_planning",
        "optimization": "minimize_model_error_and_policy_loss",
        "fixed_points": "accurate_model_optimal_policy",
        "operators": {"transition_model", "reward_model", "planning",
                      "gradient", "rollout_simulation"},
        "patterns": {
            "bayesian_inference",
            "energy_minimization",
            "exploration_exploitation",
            "compositional_structure",
            "gradient_descent",
        },
        "variables": {
            "state": "model_parameters_and_policy",
            "energy": "model_prediction_error",
            "dynamics": "learned_transition",
            "control": "planned_policy",
        },
        "conservation": set(),
        "structure": "bellman_recursion",
    },

    # ── Variational Calculus ─────────────────────────────────────────────
    "calculus_of_variations": {
        "display_name": "Calculus of Variations / Euler-Lagrange",
        "domain": "Mathematics",
        "equation": "δJ[y] = 0;  J[y] = ∫ F(x,y,y')dx;  Euler-Lagrange: ∂F/∂y − d/dx(∂F/∂y') = 0;  natural BC: ∂F/∂y'|_{∂Ω} = 0",
        "update_form": "euler_lagrange_equation",
        "optimization": "stationarity_of_functional",
        "fixed_points": "extremal_curve",
        "operators": {"functional_derivative", "euler_lagrange",
                      "first_variation", "second_variation", "jacobi_field"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "conservation_law",
            "structural_isomorphism",
            "dual_variables",
        },
        "variables": {
            "state": "extremal_function",
            "energy": "action_functional",
            "dynamics": "euler_lagrange_flow",
            "coupling": "boundary_conditions",
        },
        "conservation": {"first_integral"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Concentration of Measure ─────────────────────────────────────────
    "concentration_inequalities": {
        "display_name": "Concentration of Measure / Tail Bounds",
        "domain": "Mathematics",
        "equation": "Hoeffding: P(S_n−E[S_n]≥t) ≤ exp(−2t²/Σ(bᵢ−aᵢ)²);  McDiarmid: P(f−Ef≥t) ≤ exp(−2t²/Σcᵢ²);  sub-Gaussian: E[e^{λX}] ≤ e^{λ²σ²/2}",
        "update_form": "chernoff_bound_optimization",
        "optimization": "tightest_tail_bound",
        "fixed_points": "concentration_radius",
        "operators": {"moment_generating_function", "legendre_transform",
                      "entropy_method", "martingale_method"},
        "patterns": {
            "dual_variables",
            "information_gain",
            "energy_entropy_tradeoff",
            "variational_principle",
        },
        "variables": {
            "state": "deviation_probability",
            "energy": "rate_exponent",
            "information": "sub_gaussian_parameter",
            "coupling": "bounded_difference_constants",
        },
        "conservation": set(),
        "structure": "information_theoretic_bound",
    },

    # ── Stochastic Processes ─────────────────────────────────────────────
    "martingale_theory": {
        "display_name": "Martingale Theory / Optional Stopping",
        "domain": "Mathematics",
        "equation": "E[X_{n+1}|F_n] = X_n;  optional stopping: E[X_τ] = E[X_0] if τ bounded;  Doob: X_n = M_n + A_n;  maximal: P(max X_k ≥ λ) ≤ E[X_n]/λ",
        "update_form": "conditional_expectation",
        "optimization": "fair_game_characterization",
        "fixed_points": "martingale_limit",
        "operators": {"conditional_expectation", "doob_decomposition",
                      "stopping_time", "maximal_inequality", "filtration"},
        "patterns": {
            "conservation_law",
            "fixed_point_iteration",
            "dual_variables",
            "information_gain",
        },
        "variables": {
            "state": "adapted_process",
            "energy": "expected_value",
            "dynamics": "conditional_increment",
            "information": "filtration",
        },
        "conservation": {"expected_value_conservation"},
        "structure": "information_theoretic_bound",
    },

    # ── Latent Sequence Models ───────────────────────────────────────────
    "hidden_markov_model": {
        "display_name": "Hidden Markov Model (HMM)",
        "domain": "Machine Learning",
        "equation": "P(O,S) = π_{s1} Π P(sₜ|sₜ₋₁) Π P(oₜ|sₜ);  forward: α_t(j) = Σᵢ α_{t-1}(i)aᵢⱼbⱼ(oₜ);  Baum-Welch = EM on HMM",
        "update_form": "forward_backward_em",
        "optimization": "maximize_observation_likelihood",
        "fixed_points": "learned_transition_emission",
        "operators": {"forward_algorithm", "backward_algorithm",
                      "viterbi_decoding", "baum_welch", "transition_matrix"},
        "patterns": {
            "bayesian_inference",
            "compositional_structure",
            "energy_minimization",
            "fixed_point_iteration",
            "information_gain",
        },
        "variables": {
            "state": "latent_state_sequence",
            "energy": "negative_log_likelihood",
            "dynamics": "transition_probabilities",
            "coupling": "emission_probabilities",
        },
        "conservation": {"probability_mass_conservation"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Sequential Monte Carlo ───────────────────────────────────────────
    "particle_filter": {
        "display_name": "Particle Filter / Sequential Monte Carlo",
        "domain": "Statistics",
        "equation": "p(xₜ|y₁:ₜ) ≈ Σ wₜⁱ δ(xₜ−xₜⁱ);  wₜⁱ ∝ p(yₜ|xₜⁱ)p(xₜⁱ|xₜ₋₁ⁱ)/q(xₜⁱ);  resample when ESS < N/2;  N_eff = 1/Σ(wⁱ)²",
        "update_form": "importance_sampling_resampling",
        "optimization": "approximate_posterior_filtering",
        "fixed_points": "posterior_particle_cloud",
        "operators": {"importance_sampling", "resampling",
                      "proposal_distribution", "weight_update", "ess_monitoring"},
        "patterns": {
            "bayesian_inference",
            "population_dynamics",
            "energy_minimization",
            "exploration_exploitation",
            "information_gain",
        },
        "variables": {
            "state": "weighted_particle_set",
            "energy": "negative_log_likelihood",
            "dynamics": "sequential_importance_sampling",
            "information": "effective_sample_size",
        },
        "conservation": {"weight_normalization"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Linear Optimization ──────────────────────────────────────────────
    "linear_programming": {
        "display_name": "Linear Programming / Simplex Method",
        "domain": "Optimization",
        "equation": "min cᵀx s.t. Ax≤b, x≥0;  dual: max bᵀy s.t. Aᵀy≤c, y≥0;  strong duality: cᵀx* = bᵀy*;  complementary slackness",
        "update_form": "simplex_pivot",
        "optimization": "minimize_linear_objective",
        "fixed_points": "optimal_vertex",
        "operators": {"pivot_operation", "dual_simplex",
                      "reduced_cost", "complementary_slackness", "basis_exchange"},
        "patterns": {
            "dual_variables",
            "energy_minimization",
            "fixed_point_iteration",
            "variational_principle",
        },
        "variables": {
            "state": "basic_feasible_solution",
            "energy": "objective_value",
            "coupling": "constraint_matrix",
            "dynamics": "simplex_path",
        },
        "conservation": {"strong_duality"},
        "structure": "minimax_optimization",
    },

    # ── Combinatorial Optimization (flow) ────────────────────────────────
    "max_flow_min_cut": {
        "display_name": "Max Flow / Min Cut",
        "domain": "Optimization",
        "equation": "max Σⱼ f(s,j);  s.t. f(u,v) ≤ c(u,v), Σ f(u,v) = Σ f(v,w);  max-flow = min-cut;  Ford-Fulkerson: augment along s-t paths",
        "update_form": "augmenting_path",
        "optimization": "maximize_flow",
        "fixed_points": "maximum_flow",
        "operators": {"residual_graph", "augmenting_path",
                      "capacity_constraint", "flow_conservation", "cut_capacity"},
        "patterns": {
            "dual_variables",
            "energy_minimization",
            "conservation_law",
            "compositional_structure",
        },
        "variables": {
            "state": "flow_assignment",
            "energy": "negative_total_flow",
            "coupling": "capacity_graph",
            "dynamics": "augmentation_sequence",
        },
        "conservation": {"flow_conservation"},
        "structure": "minimax_optimization",
    },

    # ── Experimental Design ──────────────────────────────────────────────
    "optimal_design": {
        "display_name": "Optimal Experiment Design",
        "domain": "Statistics",
        "equation": "D-optimal: max det F(ξ);  A-optimal: min tr F(ξ)⁻¹;  F(ξ) = Σ wᵢ f(xᵢ)f(xᵢ)ᵀ;  equivalence: D-optimal iff max d(x,ξ*) = p",
        "update_form": "design_measure_update",
        "optimization": "maximize_information_criterion",
        "fixed_points": "optimal_design_measure",
        "operators": {"fisher_information", "information_criterion",
                      "equivalence_theorem", "exchange_algorithm"},
        "patterns": {
            "information_gain",
            "variational_principle",
            "energy_minimization",
            "dual_variables",
            "bayesian_inference",
        },
        "variables": {
            "state": "design_measure",
            "energy": "negative_information",
            "information": "fisher_information_matrix",
            "coupling": "regression_functions",
        },
        "conservation": {"total_design_weight"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Multi-Objective ──────────────────────────────────────────────────
    "pareto_optimization": {
        "display_name": "Multi-Objective / Pareto Optimization",
        "domain": "Optimization",
        "equation": "min (f₁(x),...,fₖ(x));  Pareto: x* if ∄x: fᵢ(x)≤fᵢ(x*) ∀i, strict for some;  scalarization: min Σλᵢfᵢ(x);  ε-constraint",
        "update_form": "pareto_front_construction",
        "optimization": "find_pareto_front",
        "fixed_points": "pareto_optimal_set",
        "operators": {"dominance_check", "scalarization",
                      "hypervolume_indicator", "weighted_sum", "gradient"},
        "patterns": {
            "energy_minimization",
            "dual_variables",
            "variational_principle",
            "competitive_dynamics",
            "exploration_exploitation",
        },
        "variables": {
            "state": "solution_set",
            "energy": "scalarized_objective",
            "coupling": "objective_tradeoffs",
            "dynamics": "front_exploration",
        },
        "conservation": set(),
        "structure": "minimax_optimization",
    },

    # ── Distribution Shift ───────────────────────────────────────────────
    "domain_adaptation": {
        "display_name": "Domain Adaptation / Distribution Shift",
        "domain": "Machine Learning",
        "equation": "R_T(h) ≤ R_S(h) + d_H(S,T) + λ*;  importance weighting: E_T[ℓ] = E_S[w(x)ℓ], w=p_T/p_S;  DANN: min_θ max_d L_task − λL_domain",
        "update_form": "domain_adversarial_training",
        "optimization": "minimize_target_risk",
        "fixed_points": "domain_invariant_representation",
        "operators": {"importance_weighting", "domain_discriminator",
                      "distribution_distance", "gradient", "adversarial_alignment"},
        "patterns": {
            "gradient_descent",
            "dual_variables",
            "competitive_dynamics",
            "information_gain",
            "energy_minimization",
        },
        "variables": {
            "state": "feature_extractor",
            "energy": "domain_divergence",
            "coupling": "importance_weights",
            "dynamics": "adversarial_alignment",
        },
        "conservation": set(),
        "structure": "minimax_optimization",
    },

    # ── Statistical Learning ─────────────────────────────────────────────
    "empirical_risk_minimization": {
        "display_name": "Empirical Risk Minimization (ERM)",
        "domain": "Machine Learning",
        "equation": "R̂(h) = 1/n Σ ℓ(h(xᵢ),yᵢ);  h* = argmin R̂(h);  R(h) ≤ R̂(h) + O(√(VC(H)/n));  structural risk: min R̂ + Ω(H)",
        "update_form": "loss_minimization",
        "optimization": "minimize_empirical_risk",
        "fixed_points": "risk_minimizer",
        "operators": {"gradient", "loss_function", "regularizer",
                      "generalization_bound", "model_selection"},
        "patterns": {
            "gradient_descent",
            "energy_minimization",
            "variational_principle",
            "information_gain",
            "dual_variables",
        },
        "variables": {
            "state": "hypothesis",
            "energy": "empirical_risk",
            "prior": "regularization_penalty",
            "information": "generalization_gap",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Stochastic Analysis ──────────────────────────────────────────────
    "ito_calculus": {
        "display_name": "Itô Calculus / SDE Theory",
        "domain": "Mathematics",
        "equation": "dXₜ = μ(Xₜ)dt + σ(Xₜ)dWₜ;  Itô: df = (∂f/∂t + μ∂f/∂x + ½σ²∂²f/∂x²)dt + σ∂f/∂x dW;  Girsanov: dW̃ = dW + θdt",
        "update_form": "ito_integration",
        "optimization": "characterize_diffusion",
        "fixed_points": "stationary_distribution",
        "operators": {"ito_integral", "quadratic_variation",
                      "girsanov_transform", "generator", "martingale_representation"},
        "patterns": {
            "conservation_law",
            "energy_entropy_tradeoff",
            "structural_isomorphism",
            "variational_principle",
        },
        "variables": {
            "state": "diffusion_process",
            "energy": "quadratic_variation",
            "dynamics": "drift_and_diffusion",
            "coupling": "correlation_structure",
        },
        "conservation": {"martingale_property_under_girsanov"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Satisfiability ───────────────────────────────────────────────────
    "sat_solving": {
        "display_name": "Boolean Satisfiability / SAT Solving",
        "domain": "Computer Science",
        "equation": "φ = ∧ᵢ Cᵢ, Cᵢ = ∨ⱼ lᵢⱼ;  DPLL: unit propagation + branching;  CDCL: conflict analysis → learned clause;  random k-SAT: α_c(k) ≈ 2ᵏ ln2",
        "update_form": "conflict_driven_search",
        "optimization": "find_satisfying_assignment",
        "fixed_points": "satisfying_assignment",
        "operators": {"unit_propagation", "conflict_analysis",
                      "clause_learning", "branching_heuristic", "backtracking"},
        "patterns": {
            "fixed_point_iteration",
            "energy_minimization",
            "symmetry_breaking",
            "exploration_exploitation",
        },
        "variables": {
            "state": "partial_assignment",
            "energy": "number_of_unsatisfied_clauses",
            "dynamics": "search_tree_traversal",
            "coupling": "clause_variable_graph",
        },
        "conservation": set(),
        "structure": "energy_based_pairwise_model",
    },

    # ── Harmonic Analysis ────────────────────────────────────────────────
    "fourier_analysis": {
        "display_name": "Fourier Analysis / Spectral Decomposition",
        "domain": "Mathematics",
        "equation": "f(x) = Σ cₙ eⁱⁿˣ;  F(ω) = ∫f(t)e⁻ⁱωᵗdt;  Parseval: ∫|f|² = Σ|cₙ|²;  convolution: F(f*g) = F(f)·F(g);  sampling: f_s ≥ 2f_max",
        "update_form": "spectral_decomposition",
        "optimization": "optimal_frequency_representation",
        "fixed_points": "spectral_coefficients",
        "operators": {"fourier_transform", "convolution", "inner_product",
                      "spectral_decomposition", "windowing"},
        "patterns": {
            "structural_isomorphism",
            "compositional_structure",
            "dual_variables",
            "conservation_law",
            "energy_minimization",
        },
        "variables": {
            "state": "spectral_coefficients",
            "energy": "signal_energy",
            "spectrum": "frequency_spectrum",
            "coupling": "convolution_kernel",
        },
        "conservation": {"parseval_energy_conservation"},
        "structure": "hilbert_space_optimization",
    },

    # ── Multiscale Analysis ──────────────────────────────────────────────
    "wavelet_theory": {
        "display_name": "Wavelet Theory / Multiresolution",
        "domain": "Signal Processing",
        "equation": "f = Σ⟨f,ψⱼₖ⟩ψⱼₖ;  ψⱼₖ(t) = 2^{j/2}ψ(2ʲt−k);  MRA: V_j ⊂ V_{j+1};  φ(t) = √2 Σ hₖ φ(2t−k);  ||f||² = Σ|⟨f,ψⱼₖ⟩|²",
        "update_form": "multiresolution_decomposition",
        "optimization": "optimal_time_frequency_representation",
        "fixed_points": "wavelet_coefficients",
        "operators": {"dilation", "translation", "filter_bank",
                      "thresholding", "reconstruction"},
        "patterns": {
            "renormalization",
            "compositional_structure",
            "structural_isomorphism",
            "energy_minimization",
            "information_gain",
        },
        "variables": {
            "state": "wavelet_coefficients",
            "energy": "signal_energy",
            "spectrum": "scale_frequency_map",
            "dynamics": "multiresolution_ladder",
        },
        "conservation": {"parseval_frame_bound"},
        "structure": "renormalization_hierarchy",
    },

    # ── Financial Mathematics ────────────────────────────────────────────
    "black_scholes": {
        "display_name": "Black-Scholes / Option Pricing",
        "domain": "Economics",
        "equation": "∂V/∂t + ½σ²S²∂²V/∂S² + rS∂V/∂S − rV = 0;  C = SN(d₁) − Ke⁻ʳᵀN(d₂);  Δ-hedge: dΠ = rΠdt;  risk-neutral: E^Q[e⁻ʳᵀ payoff]",
        "update_form": "risk_neutral_pricing",
        "optimization": "replicate_payoff",
        "fixed_points": "arbitrage_free_price",
        "operators": {"ito_calculus", "risk_neutral_measure",
                      "delta_hedging", "pde_solution", "girsanov_transform"},
        "patterns": {
            "conservation_law",
            "dual_variables",
            "energy_entropy_tradeoff",
            "variational_principle",
        },
        "variables": {
            "state": "option_price",
            "energy": "hedging_error",
            "dynamics": "geometric_brownian_motion",
            "coupling": "volatility_surface",
        },
        "conservation": {"no_arbitrage"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Portfolio Theory ─────────────────────────────────────────────────
    "markowitz_portfolio": {
        "display_name": "Markowitz Portfolio / Mean-Variance",
        "domain": "Economics",
        "equation": "min wᵀΣw s.t. wᵀμ=r, wᵀ1=1;  efficient frontier: σ²(r) = a r² − 2br + c;  Sharpe: max (wᵀμ−r_f)/√(wᵀΣw);  CAPM: E[rᵢ]−r_f = βᵢ(E[r_m]−r_f)",
        "update_form": "mean_variance_optimization",
        "optimization": "minimize_portfolio_variance",
        "fixed_points": "efficient_portfolio",
        "operators": {"covariance_estimation", "quadratic_programming",
                      "lagrange_multiplier", "risk_decomposition"},
        "patterns": {
            "energy_minimization",
            "dual_variables",
            "variational_principle",
            "pairwise_coupling",
        },
        "variables": {
            "state": "portfolio_weights",
            "energy": "portfolio_variance",
            "coupling": "covariance_matrix",
            "dynamics": "efficient_frontier",
        },
        "conservation": {"budget_constraint"},
        "structure": "optimization_over_parameter_space",
    },

    # ── Epidemiological Models ───────────────────────────────────────────
    "sir_model": {
        "display_name": "SIR / Epidemiological Model",
        "domain": "Biology",
        "equation": "dS/dt = −βSI;  dI/dt = βSI − γI;  dR/dt = γI;  R₀ = β/γ;  herd immunity: S < 1/R₀;  final size: 1−R∞ = e^{−R₀R∞}",
        "update_form": "compartmental_ode",
        "optimization": "minimize_epidemic_size",
        "fixed_points": "disease_free_equilibrium",
        "operators": {"mass_action", "basic_reproduction_number",
                      "compartment_transition", "threshold_condition"},
        "patterns": {
            "population_dynamics",
            "fixed_point_iteration",
            "energy_minimization",
            "conservation_law",
            "symmetry_breaking",
        },
        "variables": {
            "state": "compartment_fractions",
            "energy": "epidemic_potential",
            "dynamics": "transmission_recovery",
            "coupling": "contact_rate",
        },
        "conservation": {"total_population"},
        "structure": "dynamical_system_on_simplex",
    },

    # ── Type Theory ──────────────────────────────────────────────────────
    "curry_howard": {
        "display_name": "Curry-Howard Correspondence / Type Theory",
        "domain": "Computer Science",
        "equation": "Γ ⊢ t : A  ≅  proof of A from Γ;  A→B ≅ implication;  A×B ≅ conjunction;  Π(x:A).B(x) ≅ ∀x.B;  Σ(x:A).B(x) ≅ ∃x.B",
        "update_form": "type_checking_inference",
        "optimization": "construct_proof_term",
        "fixed_points": "well_typed_program",
        "operators": {"type_inference", "substitution",
                      "abstraction", "application", "normalization"},
        "patterns": {
            "structural_isomorphism",
            "compositional_structure",
            "dual_variables",
            "conservation_law",
        },
        "variables": {
            "state": "typing_judgment",
            "energy": "proof_complexity",
            "dynamics": "beta_reduction",
            "coupling": "type_context",
        },
        "conservation": {"subject_reduction"},
        "structure": "renormalization_hierarchy",
    },

    # ── Quantum Algorithms ───────────────────────────────────────────────
    "quantum_computing": {
        "display_name": "Quantum Computing / Gate Model",
        "domain": "Physics",
        "equation": "|ψ⟩ = Σ αᵢ|i⟩;  U = Π Gⱼ;  Grover: O(√N) search;  Shor: period finding via QFT;  ||ψ||² = 1;  decoherence: ρ → Σ EₖρEₖ†",
        "update_form": "unitary_gate_sequence",
        "optimization": "minimize_circuit_depth",
        "fixed_points": "measurement_outcome",
        "operators": {"unitary_gate", "measurement", "tensor_product",
                      "quantum_fourier_transform", "error_correction"},
        "patterns": {
            "compositional_structure",
            "structural_isomorphism",
            "information_gain",
            "conservation_law",
            "symmetry_breaking",
        },
        "variables": {
            "state": "quantum_state_vector",
            "energy": "circuit_cost",
            "spectrum": "eigenvalues_of_observable",
            "dynamics": "gate_sequence",
        },
        "conservation": {"unitarity", "born_rule_normalization"},
        "structure": "hilbert_space_optimization",
    },

    # ── Network Community Structure ──────────────────────────────────────
    "community_detection": {
        "display_name": "Community Detection / Modularity",
        "domain": "Network Science",
        "equation": "Q = 1/(2m) Σ [Aᵢⱼ − kᵢkⱼ/(2m)] δ(cᵢ,cⱼ);  SBM: P(Aᵢⱼ=1) = p if cᵢ=cⱼ, q otherwise;  detection threshold: (p−q)²/[2(p+q)] = log n",
        "update_form": "modularity_optimization",
        "optimization": "maximize_modularity",
        "fixed_points": "optimal_partition",
        "operators": {"modularity_matrix", "louvain_merge",
                      "spectral_bisection", "likelihood_ratio"},
        "patterns": {
            "energy_minimization",
            "symmetry_breaking",
            "pairwise_coupling",
            "mean_field",
            "structural_isomorphism",
        },
        "variables": {
            "state": "community_assignment",
            "energy": "negative_modularity",
            "coupling": "adjacency_minus_null_model",
            "spectrum": "modularity_eigenvalues",
        },
        "conservation": set(),
        "structure": "energy_based_pairwise_model",
    },

    # ── Population Genetics ──────────────────────────────────────────────
    "wright_fisher": {
        "display_name": "Wright-Fisher / Population Genetics",
        "domain": "Biology",
        "equation": "E[pₜ₊₁] = p(1+s)/(1+sp);  drift: Var(Δp) = p(1−p)/(2N);  diffusion: ∂f/∂t = 1/(4N)∂²(p(1-p)f)/∂p² − s∂(p(1-p)f)/∂p;  fixation: u(p) ≈ (1−e⁻⁴ᴺˢᵖ)/(1−e⁻⁴ᴺˢ)",
        "update_form": "binomial_sampling_selection",
        "optimization": "characterize_allele_dynamics",
        "fixed_points": "fixation_or_loss",
        "operators": {"selection", "drift", "mutation",
                      "diffusion_approximation", "coalescent"},
        "patterns": {
            "population_dynamics",
            "energy_entropy_tradeoff",
            "symmetry_breaking",
            "fixed_point_iteration",
            "mean_field",
        },
        "variables": {
            "state": "allele_frequencies",
            "energy": "negative_fitness",
            "dynamics": "selection_drift_balance",
            "coupling": "population_size",
        },
        "conservation": {"total_allele_frequency"},
        "structure": "dynamical_system_on_simplex",
    },

    # ── Quantum Error Theory ─────────────────────────────────────────────
    "quantum_error_correction": {
        "display_name": "Quantum Error Correction",
        "domain": "Physics",
        "equation": "[[n,k,d]] code;  syndrome: s = Hε;  Knill-Laflamme: ⟨ψᵢ|E†ₐEᵦ|ψⱼ⟩ = Cₐᵦδᵢⱼ;  threshold: p < p_th → arbitrarily long computation;  toric code",
        "update_form": "syndrome_decoding",
        "optimization": "minimize_logical_error_rate",
        "fixed_points": "fault_tolerant_logical_qubit",
        "operators": {"stabilizer_measurement", "syndrome_extraction",
                      "error_correction", "code_distance", "threshold_theorem"},
        "patterns": {
            "conservation_law",
            "structural_isomorphism",
            "compositional_structure",
            "information_gain",
            "energy_minimization",
        },
        "variables": {
            "state": "code_space",
            "energy": "logical_error_rate",
            "coupling": "stabilizer_group",
            "information": "code_distance",
        },
        "conservation": {"logical_subspace_preservation"},
        "structure": "renormalization_hierarchy",
    },

    # ── Wave Mechanics ───────────────────────────────────────────────────
    "schrodinger_equation": {
        "display_name": "Schrödinger Equation",
        "domain": "Physics",
        "equation": "iℏ∂ψ/∂t = Ĥψ;  Ĥ = −ℏ²/2m ∇² + V;  E_n ψ_n = Ĥψ_n;  ⟨A⟩ = ⟨ψ|Â|ψ⟩;  ΔxΔp ≥ ℏ/2",
        "update_form": "unitary_time_evolution",
        "optimization": "minimize_energy_expectation",
        "fixed_points": "energy_eigenstates",
        "operators": {"hamiltonian", "unitary_evolution", "spectral_decomposition",
                      "commutator", "measurement"},
        "patterns": {
            "variational_principle",
            "conservation_law",
            "structural_isomorphism",
            "energy_minimization",
            "compositional_structure",
        },
        "variables": {
            "state": "wave_function",
            "energy": "hamiltonian_expectation",
            "spectrum": "energy_eigenvalues",
            "dynamics": "unitary_evolution",
        },
        "conservation": {"probability_conservation", "energy_conservation"},
        "structure": "hilbert_space_optimization",
    },

    # ── Heat/Diffusion PDE ───────────────────────────────────────────────
    "heat_equation": {
        "display_name": "Heat Equation / Diffusion PDE",
        "domain": "Physics",
        "equation": "∂u/∂t = α∇²u;  u(x,t) = ∫G(x−y,t)u₀(y)dy;  G(x,t) = (4παt)⁻ⁿ/² exp(−|x|²/4αt);  max principle: max on boundary",
        "update_form": "diffusion_kernel_convolution",
        "optimization": "dissipate_to_equilibrium",
        "fixed_points": "uniform_temperature",
        "operators": {"laplacian", "heat_kernel", "maximum_principle",
                      "spectral_decomposition", "green_function"},
        "patterns": {
            "energy_minimization",
            "energy_entropy_tradeoff",
            "conservation_law",
            "renormalization",
        },
        "variables": {
            "state": "temperature_field",
            "energy": "thermal_energy",
            "dynamics": "diffusive_transport",
            "dissipation": "entropy_production",
        },
        "conservation": {"total_heat_conservation"},
        "structure": "dynamical_system_on_manifold",
    },

    # ── Elastic Waves ────────────────────────────────────────────────────
    "wave_equation": {
        "display_name": "Wave Equation / d'Alembert",
        "domain": "Physics",
        "equation": "∂²u/∂t² = c²∇²u;  d'Alembert: u = f(x−ct) + g(x+ct);  energy: E = ½∫(u_t² + c²|∇u|²)dx;  dispersion: ω = ω(k)",
        "update_form": "wave_propagation",
        "optimization": "satisfy_wave_dynamics",
        "fixed_points": "standing_wave_modes",
        "operators": {"dalembert_operator", "fourier_mode_decomposition",
                      "wave_speed", "dispersion_relation", "green_function"},
        "patterns": {
            "conservation_law",
            "structural_isomorphism",
            "compositional_structure",
            "energy_minimization",
        },
        "variables": {
            "state": "displacement_field",
            "energy": "total_wave_energy",
            "spectrum": "frequency_wavenumber",
            "dynamics": "propagation",
        },
        "conservation": {"energy_conservation"},
        "structure": "hilbert_space_optimization",
    },

    # ── Gradient Estimation ──────────────────────────────────────────────
    "score_matching": {
        "display_name": "Score Matching / Score Function",
        "domain": "Machine Learning",
        "equation": "s_θ(x) ≈ ∇_x log p(x);  J(θ) = ½E_p[||s_θ − ∇log p||²] = E_p[½||s_θ||² + tr(∇s_θ)];  DSM: J = E[||s_θ(x̃) − ∇log p(x̃|x)||²]",
        "update_form": "score_network_training",
        "optimization": "minimize_score_matching_loss",
        "fixed_points": "learned_score_function",
        "operators": {"gradient", "trace_of_jacobian", "noise_perturbation",
                      "denoising", "langevin_sampling"},
        "patterns": {
            "gradient_descent",
            "energy_minimization",
            "energy_based",
            "information_gain",
            "variational_principle",
        },
        "variables": {
            "state": "score_network_parameters",
            "energy": "score_matching_loss",
            "dynamics": "score_field",
            "coupling": "noise_schedule",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Knowledge Compression ────────────────────────────────────────────
    "knowledge_distillation": {
        "display_name": "Knowledge Distillation",
        "domain": "Machine Learning",
        "equation": "L = (1−α)H(y,σ(z_s)) + α T² KL(σ(z_t/T)||σ(z_s/T));  student: small model;  teacher: large model;  dark knowledge in soft labels",
        "update_form": "soft_label_training",
        "optimization": "minimize_distillation_loss",
        "fixed_points": "compressed_student",
        "operators": {"temperature_scaling", "kl_divergence", "gradient",
                      "soft_targets", "feature_matching"},
        "patterns": {
            "energy_minimization",
            "gradient_descent",
            "information_gain",
            "energy_entropy_tradeoff",
            "pairwise_coupling",
        },
        "variables": {
            "state": "student_parameters",
            "energy": "distillation_loss",
            "coupling": "teacher_soft_labels",
            "temperature": "distillation_temperature",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Dynamical Systems (discrete) ─────────────────────────────────────
    "cellular_automaton": {
        "display_name": "Cellular Automaton / Rule Systems",
        "domain": "Computer Science",
        "equation": "s_i(t+1) = f(s_{i-r}(t),...,s_{i+r}(t));  Rule 110: Turing complete;  Game of Life: birth if 3, survive if 2-3;  class I-IV: fixed, periodic, chaotic, complex",
        "update_form": "local_rule_application",
        "optimization": "characterize_emergent_behavior",
        "fixed_points": "still_lifes_and_oscillators",
        "operators": {"local_rule", "neighborhood_sum",
                      "totalistic_function", "boundary_condition"},
        "patterns": {
            "fixed_point_iteration",
            "symmetry_breaking",
            "population_dynamics",
            "compositional_structure",
            "conservation_law",
        },
        "variables": {
            "state": "lattice_configuration",
            "energy": "pattern_complexity",
            "dynamics": "deterministic_update_rule",
            "coupling": "neighborhood_topology",
        },
        "conservation": {"rule_determinism"},
        "structure": "energy_based_pairwise_model",
    },

    # ── Robust Statistics ────────────────────────────────────────────────
    "robust_estimation": {
        "display_name": "Robust Estimation / M-Estimators",
        "domain": "Statistics",
        "equation": "θ̂ = argmin Σ ρ(xᵢ−θ);  influence: IF(x;T,F) = lim [T((1−ε)F+εδ_x)−T(F)]/ε;  breakdown: ε* = max ε s.t. bounded;  Huber: ρ(x) = x²/2 if |x|≤k, k|x|−k²/2 else",
        "update_form": "iteratively_reweighted_least_squares",
        "optimization": "minimize_robust_loss",
        "fixed_points": "robust_location_estimate",
        "operators": {"influence_function", "breakdown_point",
                      "weight_function", "huber_loss", "gradient"},
        "patterns": {
            "energy_minimization",
            "gradient_descent",
            "fixed_point_iteration",
            "variational_principle",
            "dual_variables",
        },
        "variables": {
            "state": "parameter_estimate",
            "energy": "robust_objective",
            "prior": "loss_function_shape",
            "dynamics": "irls_iteration",
        },
        "conservation": set(),
        "structure": "optimization_over_parameter_space",
    },

    # ── Quantum Annealing ────────────────────────────────────────────────
    "quantum_annealing": {
        "display_name": "Quantum Annealing / Adiabatic QC",
        "domain": "Physics",
        "equation": "H(s) = (1−s)H_0 + sH_P;  s: 0→1;  adiabatic: T ≥ O(1/Δ²_min);  Δ = E₁−E₀;  ground state of H_P = solution",
        "update_form": "adiabatic_evolution",
        "optimization": "find_ground_state",
        "fixed_points": "ground_state_of_problem_hamiltonian",
        "operators": {"hamiltonian", "adiabatic_schedule",
                      "spectral_gap", "tunneling", "transverse_field"},
        "patterns": {
            "energy_minimization",
            "variational_principle",
            "energy_entropy_tradeoff",
            "symmetry_breaking",
            "exploration_exploitation",
        },
        "variables": {
            "state": "quantum_state",
            "energy": "instantaneous_energy",
            "spectrum": "spectral_gap",
            "dynamics": "adiabatic_schedule",
        },
        "conservation": {"unitarity"},
        "structure": "hilbert_space_optimization",
    },

    # ── Graph Algorithms ─────────────────────────────────────────────────
    "shortest_path": {
        "display_name": "Shortest Path / Dijkstra-Bellman-Ford",
        "domain": "Computer Science",
        "equation": "d(v) = min_{u:(u,v)∈E} [d(u) + w(u,v)];  Dijkstra: greedy + priority queue O(E log V);  Bellman-Ford: relax all edges V−1 times;  Floyd: d[i][j] = min(d[i][j], d[i][k]+d[k][j])",
        "update_form": "relaxation_iteration",
        "optimization": "minimize_path_cost",
        "fixed_points": "shortest_path_tree",
        "operators": {"edge_relaxation", "priority_queue",
                      "dynamic_programming", "path_reconstruction"},
        "patterns": {
            "energy_minimization",
            "fixed_point_iteration",
            "compositional_structure",
            "conservation_law",
        },
        "variables": {
            "state": "distance_labels",
            "energy": "total_path_cost",
            "coupling": "edge_weights",
            "dynamics": "relaxation_order",
        },
        "conservation": {"triangle_inequality"},
        "structure": "bellman_recursion",
    },

    # ── Variational Quantum ──────────────────────────────────────────────
    "variational_quantum": {
        "display_name": "Variational Quantum Eigensolver (VQE)",
        "domain": "Physics",
        "equation": "E(θ) = ⟨ψ(θ)|H|ψ(θ)⟩;  |ψ(θ)⟩ = U(θ)|0⟩;  θ* = argmin E(θ);  ∂E/∂θᵢ = ½[E(θᵢ+π/2) − E(θᵢ−π/2)];  E(θ) ≥ E₀",
        "update_form": "parameter_shift_gradient",
        "optimization": "minimize_energy_expectation",
        "fixed_points": "approximate_ground_state",
        "operators": {"parameterized_circuit", "hamiltonian",
                      "parameter_shift", "measurement", "gradient"},
        "patterns": {
            "variational_principle",
            "energy_minimization",
            "gradient_descent",
            "compositional_structure",
            "exploration_exploitation",
        },
        "variables": {
            "state": "circuit_parameters",
            "energy": "hamiltonian_expectation",
            "spectrum": "energy_landscape",
            "dynamics": "quantum_classical_loop",
        },
        "conservation": {"unitarity"},
        "structure": "hilbert_space_optimization",
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
