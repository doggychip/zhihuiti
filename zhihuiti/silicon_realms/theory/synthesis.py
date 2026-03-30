"""
Theory Synthesis Engine
=======================
Given a collision between two theories, auto-generate a "new theory" by
combining their mathematical skeletons — the cross-domain breakthrough generator.

The synthesis process:
1. Identify the shared structural backbone (common patterns, operators, conservation laws)
2. Identify complementary structures (what each theory adds that the other lacks)
3. Combine: backbone + complements → new hybrid skeleton
4. Generate new equations by structural analogy
5. Predict novel properties from the combination
6. Score novelty and potential impact

Usage:
    from silicon_realms.theory.synthesis import synthesize
    result = synthesize("replicator_dynamics", "boltzmann_distribution")
    print(result)
"""
from __future__ import annotations

import hashlib
import textwrap
from dataclasses import dataclass, field
from typing import Optional

from .collision_engine import THEORY_REGISTRY, collide, CollisionReport


# ─────────────────────────────────────────────────────────────────────────────
# Structural templates for equation generation
# ─────────────────────────────────────────────────────────────────────────────

# Maps abstract patterns to equation fragments
PATTERN_EQUATIONS = {
    "energy_based": "E({state}) = −Σ J({coupling}) · {interaction}",
    "bayesian_inference": "P({hypothesis}|{data}) ∝ P({data}|{hypothesis}) · P({hypothesis})",
    "prediction_error_correction": "Δ{state} = {gain} · ({observed} − {predicted})",
    "variational_principle": "δF/δ{field} = 0  →  {state}* = argmin F[{field}]",
    "multiplicative_update": "d{state}/dt = {state} · ({fitness} − ⟨{fitness}⟩)",
    "exponential_family": "P({state}) = exp(−{energy}/{temperature}) / Z",
    "conservation_of_probability": "Σᵢ {state}ᵢ = 1,  d(Σ {state}ᵢ)/dt = 0",
    "gradient_descent": "d{state}/dt = −∇{potential}({state})",
    "fixed_point_stability": "f({state}*) = 0,  eigenvalues of Df({state}*) < 0",
    "pairwise_coupling": "H = −Σ_{⟨ij⟩} J_{ij} · {state}_i · {state}_j",
    "attractor_dynamics": "ẋ = f(x) with Lyapunov V: V̇ ≤ 0",
    "precision_weighted_update": "Δ{belief} = Π⁻¹ · ({observation} − g({belief}))",
    "hierarchical_inference": "{error}_l = {data}_l − f_l({belief}_{l+1})",
    "recursive_decomposition": "V({state}) = max_a [{reward} + γ · V({next_state})]",
    "phase_transition": "∃ T_c: for T < T_c → ordered, T > T_c → disordered",
    "scale_invariance": "f(λx) = λ^Δ f(x)  (power-law behavior at criticality)",
    "dual_variables": "L({state}, {dual}) = f({state}) + {dual}ᵀ g({state})",
    "mean_field": "⟨{state}_i⟩ ≈ f(⟨{state}⟩)  (self-consistency equation)",
    "critical_phenomena": "ξ ~ |T − T_c|^{−ν},  observable ~ |T − T_c|^β",
    "sum_over_histories": "Z = ∫ D[{path}] exp(i·S[{path}]/ℏ)",
    "selection": "{state}_i grows if fitness_i > mean fitness",
    "information_gain": "ΔI = D_KL(posterior ‖ prior)",
}

# Maps update_form combinations to synthesis verbs
UPDATE_SYNTHESIS = {
    ("multiplicative_error_correction", "exponential_weighting"):
        "multiplicative-exponential selection",
    ("multiplicative_error_correction", "predict_then_correct"):
        "fitness-weighted prediction-correction",
    ("predict_then_correct", "hierarchical_error_propagation"):
        "hierarchical precision-weighted estimation",
    ("exponential_weighting", "constrained_entropy_maximization"):
        "thermodynamic entropy optimization",
    ("energy_minimization", "multiplicative_error_correction"):
        "energy-fitness landscape descent",
    ("recursive_value_propagation", "exponential_weighting"):
        "Boltzmann-Bellman value optimization",
    ("correlation_based_weight_update", "multiplicative_error_correction"):
        "Hebbian-replicator co-evolution",
    ("variational_inference", "predict_then_correct"):
        "active inference estimation",
    ("coarse_graining_iteration", "threshold_cascade"):
        "multi-scale critical dynamics",
}


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SynthesizedTheory:
    """A new theory generated from the collision of two existing theories."""
    name: str
    parent_a: str
    parent_b: str
    collision_score: float
    collision_strength: str

    # Mathematical skeleton
    backbone_patterns: list[str]       # shared structure
    novel_patterns: list[str]          # combined from complements
    combined_operators: list[str]
    combined_variables: dict[str, str] # role → new semantic meaning
    conservation_laws: list[str]
    update_mechanism: str
    optimization_target: str

    # Generated equations
    core_equation: str
    auxiliary_equations: list[str]

    # Predictions
    predicted_properties: list[str]
    research_directions: list[str]

    # Scoring
    novelty_score: float     # 0–1: how different from parents
    depth_score: float       # 0–1: structural richness
    impact_score: float      # 0–1: predicted importance
    overall_score: float     # weighted combination

    def __str__(self) -> str:
        stars = "★" * max(1, round(self.overall_score * 5))
        lines = [
            f"\n{'═' * 70}",
            f"  SYNTHESIZED THEORY: {self.name}",
            f"  Score: {stars} ({self.overall_score:.3f})",
            f"{'═' * 70}",
            f"",
            f"  Parents: {self.parent_a}  ×  {self.parent_b}",
            f"  Collision: {self.collision_strength} ({self.collision_score:.3f})",
            f"",
            f"  ── Core Equation ──",
            f"  {self.core_equation}",
            f"",
        ]

        if self.auxiliary_equations:
            lines.append("  ── Auxiliary Equations ──")
            for eq in self.auxiliary_equations:
                lines.append(f"    {eq}")
            lines.append("")

        lines.append(f"  ── Update Mechanism ──")
        lines.append(f"  {self.update_mechanism}")
        lines.append(f"  Optimizes: {self.optimization_target}")
        lines.append("")

        lines.append(f"  ── Mathematical Backbone ({len(self.backbone_patterns)} shared patterns) ──")
        for p in self.backbone_patterns:
            lines.append(f"    · {p.replace('_', ' ')}")
        lines.append("")

        if self.novel_patterns:
            lines.append(f"  ── Novel Combined Patterns ({len(self.novel_patterns)}) ──")
            for p in self.novel_patterns:
                lines.append(f"    ✦ {p.replace('_', ' ')}")
            lines.append("")

        lines.append(f"  ── Variable Mapping ──")
        for role, meaning in sorted(self.combined_variables.items()):
            lines.append(f"    {role}: {meaning.replace('_', ' ')}")
        lines.append("")

        if self.conservation_laws:
            lines.append(f"  ── Conservation Laws ──")
            for c in self.conservation_laws:
                lines.append(f"    ∂/∂t [{c.replace('_', ' ')}] = 0")
            lines.append("")

        lines.append(f"  ── Predicted Properties ──")
        for p in self.predicted_properties:
            lines.append(f"    → {p}")
        lines.append("")

        lines.append(f"  ── Research Directions ──")
        for r in self.research_directions:
            lines.append(f"    ◆ {r}")

        lines.append("")
        lines.append(f"  Novelty: {self.novelty_score:.2f}  "
                      f"Depth: {self.depth_score:.2f}  "
                      f"Impact: {self.impact_score:.2f}")
        lines.append(f"{'═' * 70}\n")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Synthesis engine
# ─────────────────────────────────────────────────────────────────────────────

def _merge_variables(va: dict, vb: dict) -> dict[str, str]:
    """Merge variable mappings, creating hybrid semantic meanings."""
    merged = {}
    all_roles = set(va.keys()) | set(vb.keys())
    for role in sorted(all_roles):
        a_val = va.get(role)
        b_val = vb.get(role)
        if a_val and b_val and a_val != b_val:
            merged[role] = f"{a_val} ↔ {b_val}"
        elif a_val:
            merged[role] = a_val
        elif b_val:
            merged[role] = b_val
    return merged


def _generate_name(ta: dict, tb: dict, backbone: list[str]) -> str:
    """Generate a name for the synthesized theory."""
    a_short = ta["display_name"].split("(")[0].strip().split()[-1]
    b_short = tb["display_name"].split("(")[0].strip().split()[-1]

    if "bayesian_inference" in backbone and "prediction_error_correction" in backbone:
        return f"Bayesian {a_short}-{b_short} Inference"
    if "energy_based" in backbone:
        return f"{a_short}-{b_short} Energy Landscape"
    if "variational_principle" in backbone:
        return f"Variational {a_short}-{b_short} Principle"
    if "multiplicative_update" in backbone:
        return f"{a_short}-{b_short} Replicator System"
    if "conservation_of_probability" in backbone:
        return f"{a_short}-{b_short} Probability Flow"
    if "fixed_point_stability" in backbone:
        return f"{a_short}-{b_short} Equilibrium Theory"
    if "pairwise_coupling" in backbone:
        return f"{a_short}-{b_short} Interaction Network"
    return f"{a_short}-{b_short} Synthesis"


def _generate_core_equation(ta: dict, tb: dict, backbone: list[str],
                            complements: list[str], merged_vars: dict) -> str:
    """Generate a core equation from structural combination."""
    # Try to find a template that matches backbone patterns
    for pattern in backbone:
        if pattern in PATTERN_EQUATIONS:
            template = PATTERN_EQUATIONS[pattern]
            # Substitute variable roles
            for role, meaning in merged_vars.items():
                template = template.replace(f"{{{role}}}", meaning.split(" ↔ ")[0])
            # Fill remaining placeholders with generic terms
            import re
            remaining = re.findall(r'\{(\w+)\}', template)
            for r in remaining:
                if r in merged_vars:
                    template = template.replace(f"{{{r}}}", merged_vars[r].split(" ↔ ")[0])
                else:
                    template = template.replace(f"{{{r}}}", r)
            return template

    # Fallback: construct from update forms
    a_eq = ta.get("equation", "?")
    b_eq = tb.get("equation", "?")
    return f"Combines: [{a_eq}] with [{b_eq}]"


def _generate_auxiliary_equations(ta: dict, tb: dict, complements: list[str],
                                  merged_vars: dict) -> list[str]:
    """Generate auxiliary equations from complement patterns."""
    aux = []
    for pattern in complements[:3]:
        if pattern in PATTERN_EQUATIONS:
            template = PATTERN_EQUATIONS[pattern]
            for role, meaning in merged_vars.items():
                template = template.replace(f"{{{role}}}", meaning.split(" ↔ ")[0])
            import re
            remaining = re.findall(r'\{(\w+)\}', template)
            for r in remaining:
                template = template.replace(f"{{{r}}}", r)
            aux.append(template)
    return aux


def _predict_properties(ta: dict, tb: dict, backbone: list[str],
                        complements: list[str], collision: CollisionReport) -> list[str]:
    """Predict properties of the synthesized theory."""
    props = []

    # From backbone
    if "bayesian_inference" in backbone:
        props.append("Optimal inference under uncertainty (Bayesian)")
    if "energy_based" in backbone:
        props.append("Energy landscape with well-defined equilibria")
    if "conservation_of_probability" in backbone:
        props.append("Probability-preserving dynamics on simplex")
    if "variational_principle" in backbone:
        props.append("Variational formulation enables optimization algorithms")
    if "prediction_error_correction" in backbone:
        props.append("Self-correcting dynamics driven by prediction errors")
    if "fixed_point_stability" in backbone:
        props.append("Stable equilibria exist and can be characterized")

    # From complements (novel predictions)
    if "phase_transition" in complements:
        props.append("NOVEL: Exhibits phase transitions at critical parameters")
    if "scale_invariance" in complements:
        props.append("NOVEL: Scale-free behavior near critical points")
    if "attractor_dynamics" in complements:
        props.append("NOVEL: Multiple attractor states with basin structure")
    if "hierarchical_inference" in complements:
        props.append("NOVEL: Hierarchical structure enables multi-scale inference")
    if "recursive_decomposition" in complements:
        props.append("NOVEL: Dynamic programming decomposition possible")
    if "exponential_family" in complements:
        props.append("NOVEL: Belongs to exponential family — efficient sufficient statistics")
    if "selection" in complements:
        props.append("NOVEL: Selection dynamics — above-average components amplified")

    # Cross-domain prediction
    if ta["domain"] != tb["domain"]:
        props.append(
            f"CROSS-DOMAIN: Results from {ta['domain']} transfer to {tb['domain']} "
            f"via shared {backbone[0].replace('_', ' ') if backbone else 'structure'}"
        )

    return props[:8]


def _research_directions(ta: dict, tb: dict, backbone: list[str],
                          complements: list[str], merged_vars: dict) -> list[str]:
    """Generate suggested research directions."""
    dirs = []

    # Variable bridge explorations
    for role, meaning in merged_vars.items():
        if " ↔ " in meaning:
            a_term, b_term = meaning.split(" ↔ ")
            dirs.append(
                f"Investigate: when does {a_term.replace('_', ' ')} behave like "
                f"{b_term.replace('_', ' ')}?"
            )

    # Pattern-driven directions
    if "phase_transition" in backbone or "phase_transition" in complements:
        dirs.append("Map the phase diagram: identify order parameter and critical exponents")
    if "variational_principle" in backbone:
        dirs.append("Derive variational bound and design efficient approximation algorithms")
    if "bayesian_inference" in backbone and "energy_based" in (backbone + complements):
        dirs.append("Connect energy minimization to posterior inference (Boltzmann machine analogy)")
    if "multiplicative_update" in backbone:
        dirs.append("Analyze convergence rate and characterize Nash/ESS equilibria")
    if "conservation_of_probability" in backbone:
        dirs.append("Prove probability conservation and derive continuity equation")
    if ta["domain"] != tb["domain"]:
        dirs.append(
            f"Test whether theorems from {ta['domain']} hold in {tb['domain']} "
            f"under the variable mapping"
        )
        dirs.append(
            f"Design experiments in {tb['domain']} guided by {ta['domain']} predictions"
        )

    return dirs[:6]


def _compute_update_mechanism(ta: dict, tb: dict) -> str:
    """Determine the synthesized update mechanism."""
    key = (ta["update_form"], tb["update_form"])
    if key in UPDATE_SYNTHESIS:
        return UPDATE_SYNTHESIS[key]
    key_rev = (tb["update_form"], ta["update_form"])
    if key_rev in UPDATE_SYNTHESIS:
        return UPDATE_SYNTHESIS[key_rev]
    return (
        f"{ta['update_form'].replace('_', ' ')} "
        f"⊗ {tb['update_form'].replace('_', ' ')}"
    )


def _compute_optimization_target(ta: dict, tb: dict) -> str:
    """Combine optimization targets."""
    a_opt = ta.get("optimization")
    b_opt = tb.get("optimization")
    if a_opt and b_opt:
        if a_opt == b_opt:
            return a_opt.replace("_", " ")
        return f"{a_opt.replace('_', ' ')} + {b_opt.replace('_', ' ')}"
    return (a_opt or b_opt or "unknown").replace("_", " ")


def _score_synthesis(backbone: list[str], complements: list[str],
                     collision: CollisionReport, ta: dict, tb: dict) -> tuple[float, float, float, float]:
    """Score the synthesized theory on novelty, depth, and impact."""
    # Novelty: how much new structure comes from complements
    total_patterns = len(backbone) + len(complements)
    novelty = len(complements) / max(total_patterns, 1)
    novelty = min(1.0, novelty * 1.3)  # slight boost

    # Depth: structural richness of the synthesis
    depth = min(1.0, (
        0.3 * min(1.0, len(backbone) / 3) +
        0.3 * min(1.0, len(complements) / 4) +
        0.2 * collision.similarity_score +
        0.2 * min(1.0, len(collision.structural_bridges) / 3)
    ))

    # Impact: cross-domain bonus + collision strength
    cross_domain_bonus = 0.3 if ta["domain"] != tb["domain"] else 0.0
    impact = min(1.0, collision.similarity_score + cross_domain_bonus + 0.1 * len(backbone))

    # Overall
    overall = 0.3 * novelty + 0.35 * depth + 0.35 * impact

    return novelty, depth, impact, overall


def synthesize(theory_a: str, theory_b: str) -> SynthesizedTheory:
    """
    Synthesize a new theory from the collision of two existing theories.

    This is the core "breakthrough generator": it identifies the shared mathematical
    skeleton, merges complementary structures, generates new equations, and predicts
    novel properties.

    Args:
        theory_a: key from THEORY_REGISTRY
        theory_b: key from THEORY_REGISTRY

    Returns:
        SynthesizedTheory with equations, predictions, and research directions
    """
    if theory_a not in THEORY_REGISTRY:
        raise ValueError(f"Unknown theory '{theory_a}'. Available: {list(THEORY_REGISTRY.keys())}")
    if theory_b not in THEORY_REGISTRY:
        raise ValueError(f"Unknown theory '{theory_b}'. Available: {list(THEORY_REGISTRY.keys())}")

    ta = THEORY_REGISTRY[theory_a]
    tb = THEORY_REGISTRY[theory_b]

    # 1. Compute collision
    collision = collide(theory_a, theory_b)

    # 2. Identify backbone (shared) and complements (unique to each)
    backbone = sorted(ta["patterns"] & tb["patterns"])
    only_a = sorted(ta["patterns"] - tb["patterns"])
    only_b = sorted(tb["patterns"] - ta["patterns"])
    complements = sorted(set(only_a[:4] + only_b[:4]))  # top complements from each

    # 3. Merge structures
    combined_ops = sorted(ta["operators"] | tb["operators"])
    merged_vars = _merge_variables(ta["variables"], tb["variables"])
    conservation = sorted(ta["conservation"] | tb["conservation"])

    # 4. Generate name
    name = _generate_name(ta, tb, backbone)

    # 5. Generate equations
    core_eq = _generate_core_equation(ta, tb, backbone, complements, merged_vars)
    aux_eqs = _generate_auxiliary_equations(ta, tb, complements, merged_vars)

    # 6. Update mechanism and optimization
    update = _compute_update_mechanism(ta, tb)
    optimization = _compute_optimization_target(ta, tb)

    # 7. Predictions and research directions
    properties = _predict_properties(ta, tb, backbone, complements, collision)
    directions = _research_directions(ta, tb, backbone, complements, merged_vars)

    # 8. Score
    novelty, depth, impact, overall = _score_synthesis(
        backbone, complements, collision, ta, tb
    )

    return SynthesizedTheory(
        name=name,
        parent_a=ta["display_name"],
        parent_b=tb["display_name"],
        collision_score=collision.similarity_score,
        collision_strength=collision.collision_strength,
        backbone_patterns=backbone,
        novel_patterns=complements,
        combined_operators=combined_ops,
        combined_variables=merged_vars,
        conservation_laws=conservation,
        update_mechanism=update,
        optimization_target=optimization,
        core_equation=core_eq,
        auxiliary_equations=aux_eqs,
        predicted_properties=properties,
        research_directions=directions,
        novelty_score=novelty,
        depth_score=depth,
        impact_score=impact,
        overall_score=overall,
    )


def synthesize_top(n: int = 5) -> list[SynthesizedTheory]:
    """Synthesize new theories from the top-n strongest collisions."""
    from .collision_engine import top_collisions
    collisions = top_collisions(n)
    results = []
    for c in collisions:
        # Find keys from display names
        key_a = key_b = None
        for k, v in THEORY_REGISTRY.items():
            if v["display_name"] == c.theory_a:
                key_a = k
            if v["display_name"] == c.theory_b:
                key_b = k
        if key_a and key_b:
            results.append(synthesize(key_a, key_b))
    results.sort(key=lambda s: s.overall_score, reverse=True)
    return results


def synthesize_all() -> list[SynthesizedTheory]:
    """Synthesize from all pairwise collisions with score > 0.1."""
    keys = sorted(THEORY_REGISTRY.keys())
    results = []
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            collision = collide(ka, kb)
            if collision.similarity_score > 0.1:
                results.append(synthesize(ka, kb))
    results.sort(key=lambda s: s.overall_score, reverse=True)
    return results


if __name__ == "__main__":
    print("Theory Synthesis Engine — Top 10 Breakthroughs\n")
    for i, synth in enumerate(synthesize_top(10), 1):
        print(f"#{i}")
        print(synth)
