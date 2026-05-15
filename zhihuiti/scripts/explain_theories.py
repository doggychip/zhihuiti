"""Generate rich LLM explanations for each Ryan Theory.

For every theory in ryan_theories.json, produces:
- plain_explanation: 2-3 sentences in plain language
- worked_example: concrete real-world example
- governance_application: how this theory would shape agent governance
- implementation_hint: code-level suggestion

Uses zhihuiti.llm (DeepSeek/OpenRouter/Ollama). If no LLM key is available,
falls back to template-based explanations built from the theory structure.

Run:
    python scripts/explain_theories.py
    python scripts/explain_theories.py --force      # overwrite existing
    python scripts/explain_theories.py --limit 5    # only first 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROMPT_TEMPLATE = """You are explaining a synthesized cross-domain theory to a smart practitioner.

Theory: {name}
Parent theories: {parent_a} × {parent_b}
Cross-domain bridge: {label}
Domains: {domain_a} × {domain_b}
Collision score: {collision_score} ({collision_strength})

Shared mathematical backbone: {backbone}
Novel combined patterns: {novel}
Variable mapping: {variables}
Conservation laws: {conservation}
Optimization target: {optimization}
Update mechanism: {update}

Generate JSON with these four fields (no other text):
- "plain_explanation": 2-3 sentences in plain language describing what this synthesized theory means and why the cross-domain link is non-trivial
- "worked_example": one concrete real-world example showing the theory in action (1 paragraph)
- "governance_application": how this theory could shape multi-agent governance in zhihuiti — be specific about cull thresholds, messaging, or scoring mechanics
- "implementation_hint": 1-2 sentence concrete code-level suggestion

Respond ONLY with valid JSON. No markdown fences, no preamble."""


def template_fallback(theory: dict) -> dict:
    """Build template-based explanations when no LLM is available."""
    name = theory.get("name", "")
    pa, pb = theory.get("parent_a", ""), theory.get("parent_b", "")
    da, db = theory.get("domain_a", ""), theory.get("domain_b", "")
    label = theory.get("label", "")
    backbone = theory.get("backbone_patterns", [])
    optimization = theory.get("optimization_target", "")

    backbone_str = ", ".join(p.replace("_", " ") for p in backbone[:3]) or "shared structure"

    return {
        "plain_explanation": (
            f"This theory unifies {pa} from {da} with {pb} from {db}. "
            f"Both share the structural backbone of {backbone_str}, "
            f"suggesting that the same mathematical machinery solves problems in both fields. "
            f"The deep insight: {label}."
        ),
        "worked_example": (
            f"Consider a system that exhibits {backbone_str}. In {da}, this appears as {pa.lower()}. "
            f"In {db}, the same pattern appears as {pb.lower()}. "
            f"The synthesis tells us that solutions to one problem transfer to the other through "
            f"the variable mapping. For instance, optimizing for '{optimization}' in one domain "
            f"often implies optimizing for it in the other."
        ),
        "governance_application": (
            f"For zhihuiti agent governance: implement a regime where agents optimize for "
            f"'{optimization}'. Use the backbone patterns ({backbone_str}) as scoring criteria. "
            f"This works particularly well when tasks naturally span {da} and {db} domains."
        ),
        "implementation_hint": (
            f"Add a scoring_modifier in theory_governance.py that rewards agents demonstrating "
            f"{backbone[0].replace('_', ' ') if backbone else 'the shared backbone'} in their output."
        ),
        "_source": "template",
    }


def llm_explain(theory: dict, llm) -> dict:
    """Generate explanations via LLM. Falls back to template on error."""
    prompt = PROMPT_TEMPLATE.format(
        name=theory.get("name", ""),
        parent_a=theory.get("parent_a", ""),
        parent_b=theory.get("parent_b", ""),
        label=theory.get("label", ""),
        domain_a=theory.get("domain_a", ""),
        domain_b=theory.get("domain_b", ""),
        collision_score=theory.get("collision_score", 0),
        collision_strength=theory.get("collision_strength", ""),
        backbone=", ".join(theory.get("backbone_patterns", [])) or "none",
        novel=", ".join(theory.get("novel_patterns", [])) or "none",
        variables=json.dumps(theory.get("combined_variables", {}), ensure_ascii=False),
        conservation=", ".join(theory.get("conservation_laws", [])) or "none",
        optimization=theory.get("optimization_target", ""),
        update=theory.get("update_mechanism", ""),
    )

    try:
        response = llm.chat([{"role": "user", "content": prompt}])
        text = response.strip()
        # Strip optional markdown fences if model added them anyway
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text.strip())
        required = {"plain_explanation", "worked_example", "governance_application", "implementation_hint"}
        if not required.issubset(data.keys()):
            return template_fallback(theory)
        data["_source"] = "llm"
        return data
    except Exception as e:
        print(f"    LLM error: {e}; using template", file=sys.stderr)
        return template_fallback(theory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing explanations")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N theories")
    parser.add_argument("--in", dest="in_path", default="client/src/data/ryan_theories.json")
    parser.add_argument("--out", dest="out_path", default="client/src/data/ryan_theories.json")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    with open(in_path) as f:
        theories = json.load(f)

    # Try to load LLM; fall back to templates if no key
    llm = None
    if any(os.environ.get(k) for k in ["DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY"]):
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from zhihuiti.llm import LLM
            llm = LLM()
            print(f"Using LLM backend: {llm._backend} (model: {llm.model})")
        except Exception as e:
            print(f"LLM init failed ({e}); using templates", file=sys.stderr)
    else:
        print("No LLM API key found; using template explanations")

    to_process = theories
    if args.limit:
        to_process = theories[: args.limit]

    enriched = 0
    skipped = 0
    for i, t in enumerate(to_process, 1):
        name = t.get("name", "?")
        has_explanation = "plain_explanation" in t
        if has_explanation and not args.force:
            skipped += 1
            continue
        print(f"[{i}/{len(to_process)}] {name}")
        explanation = llm_explain(t, llm) if llm else template_fallback(t)
        t.update(explanation)
        enriched += 1

    with open(out_path, "w") as f:
        json.dump(theories, f, indent=2, ensure_ascii=False)

    print(f"\nEnriched {enriched} theories, skipped {skipped} (already explained)")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
