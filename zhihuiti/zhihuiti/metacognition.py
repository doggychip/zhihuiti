"""元认知引擎 — Metacognition Engine for automatic regime switching.

The brain's prefrontal cortex: reflects on which governance theory works
best for which domain and auto-selects the optimal regime per task.

How it works:
  1. Records every collision result with domain classification
  2. Builds a preference model: domain → best theory (win rate + avg score)
  3. When a new goal arrives, classifies its domain and recommends a theory
  4. Confidence grows with more observations; falls back to 'hybrid' when unsure

This closes the theory-collision feedback loop: instead of manually choosing
darwinian vs mutualist, the system learns from experience.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()

# Minimum collision observations before we trust a preference
MIN_OBSERVATIONS = 3
# Confidence threshold to auto-switch (below this, use default hybrid)
CONFIDENCE_THRESHOLD = 0.6
# Default theory when we don't have enough data
DEFAULT_THEORY = "hybrid"

# Domain keywords for classification (expandable)
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "trading": ["trade", "market", "price", "portfolio", "hedge", "alpha",
                "crypto", "stock", "futures", "options", "spread", "arb"],
    "research": ["research", "analyze", "study", "investigate", "review",
                 "literature", "survey", "hypothesis", "experiment"],
    "coding": ["code", "implement", "refactor", "debug", "fix", "build",
               "deploy", "test", "develop", "software", "api", "function"],
    "content": ["write", "draft", "article", "blog", "report", "summary",
                "document", "essay", "presentation", "explain"],
    "strategy": ["strategy", "plan", "roadmap", "design", "architect",
                 "optimize", "improve", "evaluate", "decide"],
}


@dataclass
class RegimeRecommendation:
    """A recommended theory for a given domain."""
    domain: str
    theory: str
    confidence: float
    win_rate: float
    avg_score: float
    observation_count: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "theory": self.theory,
            "confidence": round(self.confidence, 3),
            "win_rate": round(self.win_rate, 3),
            "avg_score": round(self.avg_score, 3),
            "observations": self.observation_count,
            "reason": self.reason,
        }


class MetacognitionEngine:
    """Learns which governance theory works best for each domain.

    The meta-cognitive layer that enables zhihuiti to self-tune its own
    governance regime based on empirical collision results.
    """

    def __init__(self, memory: "Memory", llm: "LLM | None" = None):
        self.memory = memory
        self.llm = llm
        # In-memory cache of preferences (loaded from DB)
        self._preferences: dict[str, dict] = {}
        self._load_preferences()

    def _load_preferences(self) -> None:
        """Load regime preferences from database."""
        prefs = self.memory.get_all_regime_preferences()
        for p in prefs:
            self._preferences[p["domain"]] = p

    # ------------------------------------------------------------------
    # Domain classification
    # ------------------------------------------------------------------

    def classify_domain(self, goal: str) -> str:
        """Classify a goal into a domain based on keyword matching.

        Returns the best-matching domain, or 'general' if no clear match.
        """
        goal_lower = goal.lower()
        scores: dict[str, int] = {}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                scores[domain] = score

        if not scores:
            return "general"

        return max(scores, key=scores.get)

    # ------------------------------------------------------------------
    # Record collision results
    # ------------------------------------------------------------------

    def record_collision(self, goal: str, theory_a: str, theory_b: str,
                         score_a: float, score_b: float, winner: str,
                         tasks_a: int = 0, tasks_b: int = 0) -> str:
        """Record a collision result and update domain preferences."""
        domain = self.classify_domain(goal)
        collision_id = uuid.uuid4().hex[:12]

        self.memory.save_collision(
            collision_id=collision_id,
            goal=goal,
            domain=domain,
            theory_a=theory_a,
            theory_b=theory_b,
            score_a=score_a,
            score_b=score_b,
            winner=winner,
            tasks_a=tasks_a,
            tasks_b=tasks_b,
        )

        # Update preferences for each theory that participated
        self._update_preference(domain, theory_a, score_a, winner == theory_a)
        self._update_preference(domain, theory_b, score_b, winner == theory_b)

        console.print(
            f"  [dim]元认知: Recorded collision for domain '{domain}' "
            f"— winner: {winner}[/dim]"
        )
        return collision_id

    def _update_preference(self, domain: str, theory: str,
                           score: float, won: bool) -> None:
        """Update the preference model for a domain+theory pair."""
        pref_id = hashlib.md5(f"{domain}:{theory}".encode()).hexdigest()[:12]

        # Get existing preference
        existing = self.memory.get_regime_preference(domain)
        # Check if we have a record for this specific theory
        all_prefs = self.memory.get_all_regime_preferences()
        theory_pref = None
        for p in all_prefs:
            if p["domain"] == domain and p["theory"] == theory:
                theory_pref = p
                break

        if theory_pref:
            win_count = theory_pref["win_count"] + (1 if won else 0)
            total = theory_pref["total_count"] + 1
            # Running average of scores
            old_avg = theory_pref["avg_score"]
            new_avg = (old_avg * (total - 1) + score) / total
            # Confidence = win_rate * sqrt(observations) / sqrt(MIN_OBS)
            win_rate = win_count / total if total > 0 else 0
            confidence = min(1.0, win_rate * (total / MIN_OBSERVATIONS) ** 0.5)
        else:
            win_count = 1 if won else 0
            total = 1
            new_avg = score
            win_rate = win_count / total
            confidence = win_rate * (1 / MIN_OBSERVATIONS) ** 0.5

        self.memory.save_regime_preference(
            pref_id=pref_id,
            domain=domain,
            theory=theory,
            win_count=win_count,
            total_count=total,
            avg_score=round(new_avg, 4),
            confidence=round(confidence, 4),
        )

        # Update cache
        self._preferences[f"{domain}:{theory}"] = {
            "domain": domain,
            "theory": theory,
            "win_count": win_count,
            "total_count": total,
            "avg_score": new_avg,
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Recommend theory for a goal
    # ------------------------------------------------------------------

    def recommend(self, goal: str) -> RegimeRecommendation:
        """Recommend the best theory for a given goal.

        Returns a RegimeRecommendation with the suggested theory and confidence.
        Falls back to 'hybrid' when insufficient data.
        """
        domain = self.classify_domain(goal)

        # Gather all preferences for this domain
        all_prefs = self.memory.get_all_regime_preferences()
        domain_prefs = [p for p in all_prefs if p["domain"] == domain]

        if not domain_prefs:
            return RegimeRecommendation(
                domain=domain,
                theory=DEFAULT_THEORY,
                confidence=0.0,
                win_rate=0.0,
                avg_score=0.0,
                observation_count=0,
                reason=f"No collision data for domain '{domain}' — using default",
            )

        # Find the best theory: highest confidence, then highest avg_score
        best = max(domain_prefs, key=lambda p: (p["confidence"], p["avg_score"]))

        total_obs = best["total_count"]
        win_rate = best["win_count"] / total_obs if total_obs > 0 else 0.0

        if best["confidence"] < CONFIDENCE_THRESHOLD:
            return RegimeRecommendation(
                domain=domain,
                theory=DEFAULT_THEORY,
                confidence=best["confidence"],
                win_rate=win_rate,
                avg_score=best["avg_score"],
                observation_count=total_obs,
                reason=(
                    f"Confidence too low ({best['confidence']:.2f} < {CONFIDENCE_THRESHOLD}) "
                    f"for '{best['theory']}' in domain '{domain}' — using default"
                ),
            )

        return RegimeRecommendation(
            domain=domain,
            theory=best["theory"],
            confidence=best["confidence"],
            win_rate=win_rate,
            avg_score=best["avg_score"],
            observation_count=total_obs,
            reason=(
                f"'{best['theory']}' wins {win_rate:.0%} of collisions in "
                f"domain '{domain}' (n={total_obs}, avg={best['avg_score']:.3f})"
            ),
        )

    def get_theory_config(self, goal: str) -> tuple[dict, RegimeRecommendation]:
        """Get the full theory config for a goal, auto-selected by metacognition.

        Returns (theory_config_dict, recommendation).
        """
        from zhihuiti.collision import THEORIES
        rec = self.recommend(goal)
        config = THEORIES.get(rec.theory, THEORIES[DEFAULT_THEORY])
        return config, rec

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_report(self) -> None:
        """Print metacognition status — learned regime preferences."""
        all_prefs = self.memory.get_all_regime_preferences()
        collisions = self.memory.get_collision_history()

        if not all_prefs and not collisions:
            console.print("  [dim]元认知: No collision data yet[/dim]")
            return

        table = Table(title="元认知 Metacognition — Learned Regime Preferences")
        table.add_column("Domain", style="cyan")
        table.add_column("Theory", style="bold")
        table.add_column("Wins", justify="center")
        table.add_column("Total", justify="center")
        table.add_column("Win Rate", justify="center")
        table.add_column("Avg Score", justify="center")
        table.add_column("Confidence", justify="center")

        for p in sorted(all_prefs, key=lambda x: (-x["confidence"], x["domain"])):
            total = p["total_count"]
            win_rate = p["win_count"] / total if total > 0 else 0
            conf = p["confidence"]
            conf_style = "green" if conf >= CONFIDENCE_THRESHOLD else "yellow" if conf > 0.3 else "red"
            table.add_row(
                p["domain"],
                p["theory"],
                str(p["win_count"]),
                str(total),
                f"{win_rate:.0%}",
                f"{p['avg_score']:.3f}",
                f"[{conf_style}]{conf:.3f}[/{conf_style}]",
            )

        console.print(Panel(table))

        if collisions:
            console.print(
                f"  [dim]Total collisions recorded: {len(collisions)}[/dim]"
            )
