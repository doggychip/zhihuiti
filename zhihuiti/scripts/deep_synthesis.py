"""Deep enrichment: exhaustive cross-domain collisions + 2nd-order synthesis.

Phase 1: Sweep ALL 400×400 theory pairs, keep cross-domain with score > threshold
Phase 2: Curated high-value pairs across unexplored bridges
Phase 3: 2nd-order synthesis — collide Ryan's theories with each other

Produces deeply enriched ryan_theories.json.
"""
import json
import sys
from pathlib import Path
from collections import Counter


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 0.0


def overlap(a, b):
    a, b = set(a), set(b)
    return len(a & b) / min(len(a), len(b)) if min(len(a), len(b)) > 0 else 0.0


def collide_score(ta, tb):
    pat_j = jaccard(ta.get("patterns", []), tb.get("patterns", []))
    pat_o = overlap(ta.get("patterns", []), tb.get("patterns", []))
    pat = 0.5 * pat_j + 0.5 * pat_o
    op = overlap(ta.get("operators", []), tb.get("operators", []))
    cons = jaccard(ta.get("conservation", []), tb.get("conservation", []))
    var_a = set(ta.get("variables", {}).keys())
    var_b = set(tb.get("variables", {}).keys())
    var_sim = jaccard(var_a, var_b)

    bonus = 0
    if ta.get("update_form") and ta.get("update_form") == tb.get("update_form"):
        bonus += 0.18
    if ta.get("optimization") and ta.get("optimization") == tb.get("optimization"):
        bonus += 0.12
    if ta.get("structure") and ta.get("structure") == tb.get("structure"):
        bonus += 0.12
    if ta.get("domain") != tb.get("domain"):
        bonus += 0.06

    return min(1.0, 0.40 * pat + 0.22 * op + 0.12 * var_sim + 0.08 * cons + bonus)


def synthesize(ta, tb):
    backbone = sorted(set(ta.get("patterns", [])) & set(tb.get("patterns", [])))
    only_a = sorted(set(ta.get("patterns", [])) - set(tb.get("patterns", [])))
    only_b = sorted(set(tb.get("patterns", [])) - set(ta.get("patterns", [])))
    complements = sorted(set(only_a[:4] + only_b[:4]))
    combined_ops = sorted(set(ta.get("operators", [])) | set(tb.get("operators", [])))
    merged_vars = {}
    for role in sorted(set(ta.get("variables", {}).keys()) | set(tb.get("variables", {}).keys())):
        a, b = ta.get("variables", {}).get(role), tb.get("variables", {}).get(role)
        if a and b and a != b:
            merged_vars[role] = f"{a} ↔ {b}"
        else:
            merged_vars[role] = a or b
    conservation = sorted(set(ta.get("conservation", [])) | set(tb.get("conservation", [])))
    score = collide_score(ta, tb)
    strength = "deep" if score > 0.50 else "significant" if score > 0.28 else "resonance" if score > 0.10 else "weak"

    a_short = ta["name"].split("(")[0].strip().split("/")[0].strip().split()[-1]
    b_short = tb["name"].split("(")[0].strip().split("/")[0].strip().split()[-1]

    name_map = [
        ("energy_based", f"{a_short}-{b_short} Energy Landscape"),
        ("bayesian_inference", f"Bayesian {a_short}-{b_short} Inference"),
        ("attention_mechanism", f"{a_short}-{b_short} Attention Network"),
        ("variational_principle", f"Variational {a_short}-{b_short}"),
        ("emergence", f"{a_short}-{b_short} Emergence"),
        ("phase_transition", f"{a_short}-{b_short} Critical Dynamics"),
        ("multiplicative_update", f"{a_short}-{b_short} Replicator"),
        ("gradient_descent", f"{a_short}-{b_short} Gradient Flow"),
        ("conservation_of_probability", f"{a_short}-{b_short} Probability Flow"),
        ("information_gain", f"{a_short}-{b_short} Information Engine"),
        ("scale_invariance", f"{a_short}-{b_short} Scale-Free Theory"),
        ("recursive_decomposition", f"{a_short}-{b_short} Recursive Dynamics"),
        ("fixed_point_stability", f"{a_short}-{b_short} Equilibrium Theory"),
    ]
    name = f"{a_short}-{b_short} Synthesis"
    for pat, candidate in name_map:
        if pat in backbone:
            name = candidate
            break

    uf_a = (ta.get("update_form") or "?").replace("_", " ")
    uf_b = (tb.get("update_form") or "?").replace("_", " ")
    update = f"{uf_a} ⊗ {uf_b}" if uf_a != uf_b else uf_a
    opt_a = (ta.get("optimization") or "?").replace("_", " ")
    opt_b = (tb.get("optimization") or "?").replace("_", " ")
    optimization = opt_a if opt_a == opt_b else f"{opt_a} + {opt_b}"

    novelty = min(1.0, len(complements) / max(len(backbone) + len(complements), 1) * 1.3)
    depth = min(1.0, 0.3 * min(1.0, len(backbone) / 3) + 0.3 * min(1.0, len(complements) / 4) + 0.4 * score)
    cross = 0.3 if ta.get("domain") != tb.get("domain") else 0
    impact = min(1.0, score + cross + 0.1 * len(backbone))
    overall = 0.3 * novelty + 0.35 * depth + 0.35 * impact

    backbone_str = ", ".join(p.replace("_", " ") for p in backbone[:3]) or "shared structure"
    da, db = ta.get("domain", ""), tb.get("domain", "")

    return {
        "name": name,
        "parent_a": ta["name"], "parent_b": tb["name"],
        "parent_a_id": ta["id"], "parent_b_id": tb["id"],
        "domain_a": da, "domain_b": db,
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
        "plain_explanation": (
            f"This theory unifies {ta['name']} ({da}) with {tb['name']} ({db}). "
            f"Both share {backbone_str}, revealing that the same mathematical structure "
            f"solves problems in both fields."
        ),
        "governance_application": (
            f"Agent regime: optimize for '{optimization}'. Score agents on "
            f"{backbone_str}. Works best for tasks spanning {da} and {db}."
        ),
        "implementation_hint": (
            f"Add scoring_modifier rewarding agents that demonstrate "
            f"{backbone[0].replace('_', ' ') if backbone else 'shared structure'} in output."
        ),
        "_source": "template",
    }


def main():
    with open("client/src/data/theories.json") as f:
        theories = json.load(f)
    with open("client/src/data/ryan_theories.json") as f:
        existing = json.load(f)

    existing_pairs = set()
    for t in existing:
        a, b = t.get("parent_a_id", ""), t.get("parent_b_id", "")
        existing_pairs.add((a, b))
        existing_pairs.add((b, a))

    print(f"Starting: {len(existing)} existing Ryan theories, {len(theories)} base theories")

    # ── Phase 1: Exhaustive sweep for strong cross-domain collisions ──
    print("\n=== Phase 1: Exhaustive cross-domain sweep ===")
    keys = sorted(theories.keys())
    phase1 = []
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            if (ka, kb) in existing_pairs:
                continue
            ta, tb = theories[ka], theories[kb]
            if ta.get("domain") == tb.get("domain"):
                continue
            score = collide_score(ta, tb)
            if score >= 0.35:
                phase1.append((score, ka, kb))

    phase1.sort(reverse=True)
    print(f"Found {len(phase1)} cross-domain collisions with score >= 0.35")

    # Take top 60 new ones
    new_theories = []
    for score, ka, kb in phase1[:60]:
        s = synthesize(theories[ka], theories[kb])
        new_theories.append(s)
        existing_pairs.add((ka, kb))
        existing_pairs.add((kb, ka))

    print(f"Phase 1: synthesized {len(new_theories)} new theories")

    # ── Phase 2: Curated high-value unexplored bridges ──
    print("\n=== Phase 2: Curated unexplored bridges ===")
    curated_pairs = [
        # Quantum × ML
        ("quantum_computing", "gradient_descent_sgd"),
        ("quantum_information", "information_bottleneck"),
        ("density_matrix", "graph_neural_network"),
        ("quantum_error_correction", "error_correcting_code"),

        # Physics × Biology
        ("fokker_planck", "population_genetics"),
        ("ising_model", "gene_regulatory_network"),
        ("reaction_diffusion", "morphogenesis"),

        # Thermodynamics × Economics
        ("carnot_efficiency", "pareto_optimality"),
        ("free_energy_thermo", "markowitz_portfolio"),
        ("maximum_entropy_principle", "rational_expectations"),

        # Signal Processing × Neuroscience
        ("fourier_transform", "eeg_spectral_analysis"),
        ("kalman_filter", "bayesian_brain"),
        ("compressed_sensing", "sparse_coding"),
        ("matched_filter", "neural_coding"),

        # Computer Science × Biology
        ("genetic_algorithm", "replicator_dynamics"),
        ("cellular_automata", "gene_regulatory_network"),
        ("turing_machine", "rna_folding"),

        # Game Theory × Cryptography
        ("mechanism_design", "zero_knowledge_proof"),
        ("nash_equilibrium", "blockchain_consensus"),

        # Topology × Networks
        ("persistent_homology", "community_detection"),
        ("betti_numbers", "preferential_attachment"),

        # Dynamic Systems × Economics
        ("lotka_volterra", "market_microstructure"),
        ("bifurcation_theory", "business_cycle"),
        ("chaos_theory", "financial_time_series"),

        # Causal Inference × ML
        ("do_calculus", "decision_tree_random_forest"),
        ("potential_outcomes", "gradient_boosting"),
        ("instrumental_variables", "deep_learning"),

        # Decision Theory × Cognitive Science
        ("expected_utility", "dual_process_theory"),
        ("regret_minimization", "memory_consolidation"),

        # OR × Game Theory
        ("assignment_problem", "stable_matching"),
        ("queueing_theory", "mean_field_game"),
        ("shortest_path_dijkstra", "network_formation_game"),

        # Robotics × Control
        ("slam", "kalman_filter"),
        ("swarm_robotics", "consensus_dynamics"),

        # Pharmacology × ML
        ("dose_response", "logistic_regression"),
        ("pk_pd_modeling", "recurrent_neural_network"),
        ("drug_synergy_combination", "ensemble_methods"),

        # Astrophysics × Quantum
        ("black_hole_thermodynamics", "quantum_information"),
        ("gravitational_waves", "signal_detection_theory"),

        # Cryptography × Quantum
        ("lattice_cryptography", "quantum_computing"),
        ("rsa_cryptosystem", "quantum_algorithm"),

        # Sociology × Game Theory
        ("collective_action", "mechanism_design"),
        ("schelling_segregation", "evolutionary_dynamics_pairwise"),
        ("social_capital", "network_formation_game"),

        # Behavioral Econ × Neuroscience
        ("prospect_theory", "dopamine_prediction_error"),
        ("hyperbolic_discounting", "bayesian_brain"),
        ("herd_behavior", "mirror_neuron"),

        # Info Theory × Statistics
        ("rate_distortion", "pca_svd"),
        ("channel_capacity", "hypothesis_testing"),
        ("huffman_coding", "minimum_description_length"),

        # ML × Statistics
        ("meta_learning_maml", "empirical_bayes"),
        ("soft_actor_critic", "maximum_entropy_principle"),
        ("transformer_attention", "gaussian_process"),

        # Chemistry × Biology
        ("arrhenius_kinetics", "enzyme_kinetics"),
        ("supramolecular_self_assembly", "protein_folding"),
        ("marcus_theory", "photosynthesis"),

        # Complex × Physics
        ("power_law_distribution", "renormalization_group"),
        ("tipping_points", "bifurcation_theory"),
        ("synchronization_kuramoto", "ising_model"),

        # EGT × Social
        ("hawk_dove", "collective_action"),
        ("kin_selection", "social_capital"),
        ("group_selection", "diffusion_of_innovation"),
        ("moran_process", "voter_model"),
    ]

    phase2_count = 0
    for ka, kb in curated_pairs:
        if (ka, kb) in existing_pairs:
            continue
        if ka not in theories or kb not in theories:
            continue
        s = synthesize(theories[ka], theories[kb])
        new_theories.append(s)
        existing_pairs.add((ka, kb))
        existing_pairs.add((kb, ka))
        phase2_count += 1

    print(f"Phase 2: synthesized {phase2_count} curated theories")

    # ── Phase 3: 2nd-order synthesis (Ryan × Ryan) ──
    print("\n=== Phase 3: 2nd-order synthesis (Ryan × Ryan) ===")
    all_ryan = existing + new_theories
    # Create pseudo-theories from Ryan for collision
    ryan_as_theories = {}
    for rt in all_ryan:
        rid = f"ryan_{rt['name'].lower().replace(' ', '_').replace('-', '_')[:40]}"
        ryan_as_theories[rid] = {
            "id": rid,
            "name": f"[Ryan] {rt['name']}",
            "domain": f"{rt.get('domain_a', '')}×{rt.get('domain_b', '')}",
            "patterns": rt.get("backbone_patterns", []) + rt.get("novel_patterns", []),
            "operators": rt.get("combined_operators", []),
            "variables": rt.get("combined_variables", {}),
            "conservation": rt.get("conservation_laws", []),
            "update_form": rt.get("update_mechanism", ""),
            "optimization": rt.get("optimization_target", ""),
        }

    rkeys = sorted(ryan_as_theories.keys())
    phase3 = []
    for i, ka in enumerate(rkeys):
        for kb in rkeys[i + 1:]:
            ta, tb = ryan_as_theories[ka], ryan_as_theories[kb]
            if ta.get("domain") == tb.get("domain"):
                continue
            score = collide_score(ta, tb)
            if score >= 0.30:
                phase3.append((score, ka, kb))

    phase3.sort(reverse=True)
    print(f"Found {len(phase3)} 2nd-order collisions with score >= 0.30")

    phase3_count = 0
    for score, ka, kb in phase3[:20]:
        ta, tb = ryan_as_theories[ka], ryan_as_theories[kb]
        s = synthesize(ta, tb)
        s["_order"] = 2
        new_theories.append(s)
        phase3_count += 1

    print(f"Phase 3: synthesized {phase3_count} 2nd-order theories")

    # ── Merge and save ──
    existing_names = {t["name"] for t in existing}
    added = 0
    for t in new_theories:
        if t["name"] not in existing_names:
            existing.append(t)
            existing_names.add(t["name"])
            added += 1

    existing.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    with open("client/src/data/ryan_theories.json", "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"TOTAL Ryan's theories: {len(existing)} (added {added} new)")
    print(f"{'='*60}")

    # Domain bridge summary
    bridges = Counter()
    for t in existing:
        da, db = t.get("domain_a", ""), t.get("domain_b", "")
        if da and db and da != db:
            bridges[tuple(sorted([da, db]))] += 1
    print(f"\nDomain bridges ({len(bridges)} unique):")
    for (a, b), c in sorted(bridges.items(), key=lambda x: -x[1])[:30]:
        print(f"  {c:3d}  {a} × {b}")

    # Top 10 new theories
    print(f"\nTop 10 newly synthesized:")
    new_sorted = sorted(new_theories, key=lambda x: x.get("overall_score", 0), reverse=True)
    for i, t in enumerate(new_sorted[:10], 1):
        order = " [2nd-order]" if t.get("_order") == 2 else ""
        print(f"  #{i} ({t['overall_score']:.3f}) {t['name']}{order}")
        print(f"      {t['parent_a'][:40]} × {t['parent_b'][:40]}")
        print(f"      {t.get('domain_a','')} × {t.get('domain_b','')}")


if __name__ == "__main__":
    main()
