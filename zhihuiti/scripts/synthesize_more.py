"""Synthesize new Ryan's Theories from cross-domain collisions in the expanded
400-theory knowledge base.

Uses the theories.json data directly (no dependency on silicon_realms registry).
"""
import json
from pathlib import Path


def jaccard(a, b):
    a, b = set(a), set(b)
    if not (a | b):
        return 0.0
    return len(a & b) / len(a | b)


def collide(ta, tb):
    """Compute collision score between two theories (from JSON format)."""
    pat = jaccard(ta.get("patterns", []), tb.get("patterns", []))
    op = jaccard(ta.get("operators", []), tb.get("operators", []))
    cons = jaccard(ta.get("conservation", []), tb.get("conservation", []))
    bonus = 0.18 if ta.get("update_form") == tb.get("update_form") else 0
    bonus += 0.12 if ta.get("optimization") == tb.get("optimization") else 0
    bonus += 0.05 if ta.get("domain") != tb.get("domain") else 0
    score = min(1.0, 0.5 * pat + 0.25 * op + 0.1 * cons + bonus)
    strength = (
        "deep" if score > 0.50
        else "significant" if score > 0.28
        else "resonance" if score > 0.10
        else "weak"
    )
    return score, strength


def merge_vars(va, vb):
    merged = {}
    for role in sorted(set(va.keys()) | set(vb.keys())):
        a, b = va.get(role), vb.get(role)
        if a and b and a != b:
            merged[role] = f"{a} ↔ {b}"
        else:
            merged[role] = a or b
    return merged


def short_name(t):
    return t["name"].split("(")[0].strip().split("/")[0].strip().split()[-1]


def synthesize(ta, tb):
    backbone = sorted(set(ta.get("patterns", [])) & set(tb.get("patterns", [])))
    only_a = sorted(set(ta.get("patterns", [])) - set(tb.get("patterns", [])))
    only_b = sorted(set(tb.get("patterns", [])) - set(ta.get("patterns", [])))
    complements = sorted(set(only_a[:4] + only_b[:4]))

    combined_ops = sorted(set(ta.get("operators", [])) | set(tb.get("operators", [])))
    merged_vars = merge_vars(ta.get("variables", {}), tb.get("variables", {}))
    conservation = sorted(set(ta.get("conservation", [])) | set(tb.get("conservation", [])))

    score, strength = collide(ta, tb)

    # Generate name
    a, b = short_name(ta), short_name(tb)
    if "energy_based" in backbone:
        name = f"{a}-{b} Energy Landscape"
    elif "variational_principle" in backbone:
        name = f"Variational {a}-{b} Principle"
    elif "bayesian_inference" in backbone:
        name = f"Bayesian {a}-{b} Inference"
    elif "attention_mechanism" in backbone:
        name = f"{a}-{b} Attention Network"
    elif "emergence" in backbone or "self_organization" in backbone:
        name = f"{a}-{b} Emergence Theory"
    elif "scale_invariance" in backbone or "power_law" in backbone:
        name = f"{a}-{b} Scale-Free Synthesis"
    elif "phase_transition" in backbone:
        name = f"{a}-{b} Critical Dynamics"
    else:
        name = f"{a}-{b} Synthesis"

    # Update mechanism
    uf_a = ta.get("update_form") or "?"
    uf_b = tb.get("update_form") or "?"
    update = f"{uf_a.replace('_',' ')} ⊗ {uf_b.replace('_',' ')}"

    # Optimization target
    opt_a = ta.get("optimization") or "?"
    opt_b = tb.get("optimization") or "?"
    optimization = opt_a.replace("_"," ") if opt_a == opt_b else f"{opt_a.replace('_',' ')} + {opt_b.replace('_',' ')}"

    # Scoring
    novelty = min(1.0, len(complements) / max(len(backbone) + len(complements), 1) * 1.3)
    depth = min(1.0, 0.3 * min(1.0, len(backbone) / 3) + 0.3 * min(1.0, len(complements) / 4) + 0.4 * score)
    cross = 0.3 if ta.get("domain") != tb.get("domain") else 0
    impact = min(1.0, score + cross + 0.1 * len(backbone))
    overall = 0.3 * novelty + 0.35 * depth + 0.35 * impact

    return {
        "name": name,
        "parent_a": ta["name"],
        "parent_b": tb["name"],
        "domain_a": ta.get("domain", ""),
        "domain_b": tb.get("domain", ""),
        "collision_score": round(score, 3),
        "collision_strength": strength,
        "backbone_patterns": backbone,
        "novel_patterns": complements,
        "combined_operators": combined_ops,
        "combined_variables": merged_vars,
        "conservation_laws": conservation,
        "update_mechanism": update,
        "optimization_target": optimization,
        "novelty_score": round(novelty, 3),
        "depth_score": round(depth, 3),
        "impact_score": round(impact, 3),
        "overall_score": round(overall, 3),
    }


def main():
    path = Path("client/src/data/theories.json")
    with open(path) as f:
        theories = json.load(f)

    # Curated cross-domain collision pairs to synthesize
    # Each pair represents a meaningful conceptual bridge
    pairs = [
        # AI/ML × Other
        ("transformer_attention", "global_workspace", "Attention IS consciousness"),
        ("graph_neural_network", "spectral_graph_theory", "GNNs ARE spectral analysis"),
        ("meta_learning_maml", "bayesian_brain", "Meta-learning IS Bayesian adaptation"),
        ("topic_modeling_lda", "community_detection", "Topics ARE communities"),

        # Bio × ML
        ("alphafold_msa", "transformer_attention", "Protein folding via attention"),
        ("hopfield_network", "protein_folding", "Neural memory IS protein folding"),
        ("phylogenetic_tree", "decision_tree_random_forest", "Evolution IS tree learning"),

        # Decision × RL
        ("expected_utility", "q_learning", "Utility IS Q-value"),
        ("regret_minimization", "multi_armed_bandit", "Regret IS bandit"),
        ("prospect_theory", "ppo", "Loss aversion meets policy gradient"),
        ("minimax_decision", "soft_actor_critic", "Worst-case meets max-entropy"),

        # Cryptography × Information
        ("rsa_cryptosystem", "kolmogorov_ait", "Cryptography IS hardness"),
        ("zero_knowledge_proof", "information_bottleneck", "ZKP IS info compression"),
        ("merkle_tree", "huffman_coding", "Merkle IS optimal coding"),

        # Complex Systems × EGT
        ("cellular_automata", "spatial_evolution", "CA IS spatial evolution"),
        ("synchronization_kuramoto", "replicator_dynamics", "Sync IS replicator"),
        ("tipping_points", "phase_transition_ising", "Tipping IS phase transition"),

        # Sociology × Network
        ("schelling_segregation", "preferential_attachment", "Segregation IS network growth"),
        ("collective_action", "nash_equilibrium", "Free riding IS Nash"),
        ("diffusion_of_innovation", "sir_model", "Innovation spreads like virus"),
        ("homophily", "community_detection", "Homophily IS community"),

        # Behavioral × Game Theory
        ("hyperbolic_discounting", "bellman_equation", "Discounting meets Bellman"),
        ("herd_behavior", "mean_field_game", "Herding IS mean-field game"),
        ("anchoring_bias", "bayesian_brain", "Anchoring IS slow updating"),

        # Robotics × RL
        ("model_predictive_control", "dqn", "MPC IS deep RL"),
        ("slam", "active_inference", "SLAM IS active inference"),
        ("imitation_learning", "free_energy_principle", "Imitation IS FEP"),

        # Causal × ML
        ("do_calculus", "structural_causal_model", "Do-calculus IS SCM"),
        ("instrumental_variables", "two_stage_least_squares", "IV IS 2SLS"),
        ("propensity_score", "matching_methods", "Propensity IS matching"),

        # Astrophysics × Statistical Physics
        ("black_hole_thermodynamics", "free_energy_thermo", "BH IS thermodynamics"),
        ("dark_matter_halo", "percolation_theory", "Halo IS percolation"),
        ("cmb_anisotropy", "renormalization_group", "CMB IS RG"),

        # Chemistry × Physics
        ("arrhenius_kinetics", "boltzmann_distribution", "Arrhenius IS Boltzmann"),
        ("marcus_theory", "path_integral", "Marcus IS path integral"),
        ("chemical_equilibrium", "free_energy_thermo", "Equilibrium IS free energy min"),

        # Linguistics × ML
        ("word2vec", "matrix_factorization_nmf", "Embeddings ARE factorization"),
        ("edit_distance", "dynamic_programming", "Edit distance IS DP"),

        # OR × Optimization
        ("integer_programming", "branch_and_bound", "IP IS B&B"),
        ("shortest_path_dijkstra", "bellman_equation", "Dijkstra IS Bellman"),
        ("queueing_theory", "fokker_planck", "Queues IS Fokker-Planck"),

        # EGT × Game Theory
        ("hawk_dove", "nash_equilibrium", "Hawk-Dove IS Nash"),
        ("kin_selection", "shapley_value", "Kin selection IS Shapley"),
        ("group_selection", "price_equation", "Group selection IS Price equation"),
        ("moran_process", "wright_fisher", "Moran IS Wright-Fisher"),

        # Pharmacology × Other
        ("dose_response", "michaelis_menten", "Hill IS Michaelis-Menten"),
        ("pk_pd_modeling", "fokker_planck", "PK IS Fokker-Planck"),
    ]

    results = []
    skipped = []
    for a, b, label in pairs:
        if a not in theories:
            skipped.append((a, "not found"))
            continue
        if b not in theories:
            skipped.append((b, "not found"))
            continue
        s = synthesize(theories[a], theories[b])
        s["label"] = label
        s["parent_a_id"] = a
        s["parent_b_id"] = b
        results.append(s)

    # Sort by overall score
    results.sort(key=lambda x: x["overall_score"], reverse=True)

    # Save
    out_path = Path("client/src/data/ryan_theories.json")
    if out_path.exists():
        with open(out_path) as f:
            existing = json.load(f)
    else:
        existing = []

    # Append, deduplicating by name
    existing_names = {r.get("name") for r in existing}
    new_added = 0
    for r in results:
        if r["name"] not in existing_names:
            existing.append(r)
            new_added += 1

    existing.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    with open(out_path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"Synthesized {len(results)} theories from new cross-domain collisions")
    print(f"Added {new_added} new theories to ryan_theories.json (skipping duplicates)")
    print(f"Total Ryan's theories: {len(existing)}")
    if skipped:
        print(f"Skipped {len(skipped)} pairs (theory not found):")
        for s, reason in skipped[:5]:
            print(f"  - {s}: {reason}")

    print(f"\nTop 15 new Ryan's Theories:\n")
    for i, r in enumerate(results[:15], 1):
        stars = "★" * max(1, round(r["overall_score"] * 5))
        print(f"  #{i} {stars} ({r['overall_score']:.3f}) {r['name']}")
        print(f"      [{r['label']}]")
        print(f"      {r['parent_a']} × {r['parent_b']}")
        print(f"      {r['domain_a']} × {r['domain_b']}")
        print()


if __name__ == "__main__":
    main()
