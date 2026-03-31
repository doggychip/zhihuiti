"""Theory Intelligence Engine — in-memory query layer over the theory knowledge graph.

Loads theories.json, collisions.json, skeletons.json, and historical.json once,
then provides fast lookups for cross-domain analogies, pattern matching, and
structural bridge discovery.

Used by the MCP server to expose theory intelligence to external projects.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent / "client" / "src" / "data"

_instance: "TheoryGraph | None" = None
_lock = threading.Lock()


def get_graph() -> "TheoryGraph":
    """Return the singleton TheoryGraph (lazy-loaded, thread-safe)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = TheoryGraph()
    return _instance


class TheoryGraph:
    """In-memory theory knowledge graph with fast lookup indexes."""

    def __init__(self, data_dir: str | Path | None = None):
        data_dir = Path(data_dir) if data_dir else _DATA_DIR

        with open(data_dir / "theories.json") as f:
            self.theories: dict[str, dict] = json.load(f)

        with open(data_dir / "collisions.json") as f:
            self.collisions: list[dict] = json.load(f)

        with open(data_dir / "skeletons.json") as f:
            self.skeletons: list[dict] = json.load(f)

        with open(data_dir / "historical.json") as f:
            self.historical: list[dict] = json.load(f)

        # Build indexes
        self._collisions_by_theory: dict[str, list[dict]] = {}
        self._collisions_by_pair: dict[tuple[str, str], dict] = {}
        self._theories_by_domain: dict[str, list[str]] = {}
        self._theories_by_pattern: dict[str, list[str]] = {}

        for c in self.collisions:
            for side in ("a", "b"):
                tid = c[side]
                self._collisions_by_theory.setdefault(tid, []).append(c)
            pair = tuple(sorted([c["a"], c["b"]]))
            self._collisions_by_pair[pair] = c

        for tid, t in self.theories.items():
            domain = t.get("domain", "")
            self._theories_by_domain.setdefault(domain, []).append(tid)
            for p in t.get("patterns", []):
                self._theories_by_pattern.setdefault(p, []).append(tid)

    # ── Core queries ──────────────────────────────────────────────

    def get_theory(self, theory_id: str) -> dict | None:
        """Get a single theory by ID."""
        return self.theories.get(theory_id)

    def search_theories(self, query: str, limit: int = 10) -> list[dict]:
        """Search theories by name, domain, or keyword in equation/patterns."""
        q = query.lower()
        scored = []
        for tid, t in self.theories.items():
            score = 0
            name = t.get("name", "").lower()
            domain = t.get("domain", "").lower()
            equation = t.get("equation", "").lower()
            patterns = " ".join(t.get("patterns", [])).lower()

            if q == tid.lower():
                score = 100
            elif q in name:
                score = 10 + (5 if name.startswith(q) else 0)
            elif q in domain:
                score = 6
            elif q in equation:
                score = 4
            elif q in patterns:
                score = 3

            if score > 0:
                scored.append((score, tid, t))

        scored.sort(key=lambda x: -x[0])
        return [{"id": tid, **t} for _, tid, t in scored[:limit]]

    def find_analogies(self, theory_id: str, min_score: float = 0.0, limit: int = 10) -> list[dict]:
        """Find cross-domain analogies for a theory, ranked by collision score."""
        collisions = self._collisions_by_theory.get(theory_id, [])
        results = []
        for c in collisions:
            if c["score"] < min_score:
                continue
            other_id = c["b"] if c["a"] == theory_id else c["a"]
            other = self.theories.get(other_id, {})
            results.append({
                "theory_id": other_id,
                "theory_name": other.get("name", other_id),
                "theory_domain": other.get("domain", ""),
                "score": c["score"],
                "strength": c["collision_strength"],
                "shared_patterns": c.get("shared_patterns", []),
                "shared_operators": c.get("shared_operators", []),
                "bridges": c.get("bridges", []),
                "interpretation": c.get("interpretation", ""),
            })
        results.sort(key=lambda x: -x["score"])
        return results[:limit]

    def get_bridges(self, theory_a: str, theory_b: str) -> dict | None:
        """Get the detailed bridge between two specific theories."""
        pair = tuple(sorted([theory_a, theory_b]))
        c = self._collisions_by_pair.get(pair)
        if not c:
            return None
        ta = self.theories.get(c["a"], {})
        tb = self.theories.get(c["b"], {})
        return {
            "theory_a": {"id": c["a"], "name": ta.get("name", c["a"]), "domain": ta.get("domain", "")},
            "theory_b": {"id": c["b"], "name": tb.get("name", c["b"]), "domain": tb.get("domain", "")},
            "score": c["score"],
            "strength": c["collision_strength"],
            "shared_patterns": c.get("shared_patterns", []),
            "shared_operators": c.get("shared_operators", []),
            "bridges": c.get("bridges", []),
            "interpretation": c.get("interpretation", ""),
        }

    def suggest_patterns(self, description: str, limit: int = 5) -> list[dict]:
        """Given a problem description, suggest relevant structural patterns and theories.

        Matches keywords in the description against theory names, domains,
        patterns, and operators to find the most relevant structural skeletons.
        """
        words = set(description.lower().split())
        # Also try multi-word substrings
        desc_lower = description.lower()

        # Score each theory by keyword overlap
        theory_scores: dict[str, float] = {}
        for tid, t in self.theories.items():
            score = 0.0
            name_lower = t.get("name", "").lower()
            domain_lower = t.get("domain", "").lower()
            patterns = t.get("patterns", [])
            operators = t.get("operators", [])
            equation = t.get("equation", "").lower()

            # Check if theory name appears in description
            for name_word in name_lower.split():
                if len(name_word) > 3 and name_word in words:
                    score += 3.0

            # Check domain match
            for dw in domain_lower.split():
                if len(dw) > 3 and dw in words:
                    score += 2.0

            # Check pattern match
            for p in patterns:
                p_words = set(p.lower().replace("_", " ").split())
                overlap = p_words & words
                if overlap:
                    score += len(overlap) * 1.5

            # Check operator match
            for op in operators:
                op_words = set(op.lower().replace("_", " ").split())
                overlap = op_words & words
                if overlap:
                    score += len(overlap) * 1.0

            # Substring match in description
            if tid.replace("_", " ") in desc_lower:
                score += 5.0

            if score > 0:
                theory_scores[tid] = score

        # Get top theories
        top_theories = sorted(theory_scores.items(), key=lambda x: -x[1])[:limit * 3]

        # For each top theory, find its best collisions to suggest cross-domain patterns
        results = []
        seen = set()
        for tid, tscore in top_theories:
            t = self.theories[tid]
            analogies = self.find_analogies(tid, min_score=0.5, limit=3)
            if tid not in seen:
                seen.add(tid)
                results.append({
                    "theory_id": tid,
                    "theory_name": t.get("name", tid),
                    "domain": t.get("domain", ""),
                    "relevance_score": round(tscore, 2),
                    "key_patterns": t.get("patterns", [])[:5],
                    "analogies": [
                        {
                            "to": a["theory_id"],
                            "name": a["theory_name"],
                            "domain": a["theory_domain"],
                            "score": a["score"],
                            "interpretation": a["interpretation"],
                        }
                        for a in analogies[:2]
                    ],
                })
            if len(results) >= limit:
                break

        return results

    def get_domain_map(self) -> dict[str, int]:
        """Return a map of domain -> theory count."""
        return {d: len(tids) for d, tids in sorted(self._theories_by_domain.items())}

    def get_stats(self) -> dict:
        """Return summary statistics about the knowledge graph."""
        domains = self.get_domain_map()
        strengths: dict[str, int] = {}
        for c in self.collisions:
            s = c.get("collision_strength", "unknown")
            strengths[s] = strengths.get(s, 0) + 1

        return {
            "theories": len(self.theories),
            "collisions": len(self.collisions),
            "skeletons": len(self.skeletons),
            "historical_cases": len(self.historical),
            "domains": len(domains),
            "domain_counts": domains,
            "collision_strengths": strengths,
        }
