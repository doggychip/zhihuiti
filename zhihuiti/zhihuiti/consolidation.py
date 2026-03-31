"""记忆巩固引擎 — Memory Consolidation Engine.

Inspired by the brain's memory consolidation during sleep:
  - Compresses many specific memories into abstract principles
  - Implements a forgetting curve for stale, low-value memories
  - Retains high-signal patterns while discarding noise

The brain doesn't just remember — it consolidates. Over time, specific
episodic memories fade while general semantic knowledge strengthens.
This module does the same for zhihuiti's task history and goal records.

Process:
  1. Gather old task history entries (past forgetting_age_days)
  2. Group by domain/role and extract patterns
  3. Generate abstract principles via LLM (or heuristics)
  4. Store consolidated knowledge
  5. Purge the raw entries to prevent memory bloat
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()

# How old memories must be before consolidation (days)
FORGETTING_AGE_DAYS = 30
# Minimum number of entries in a group to trigger consolidation
MIN_GROUP_SIZE = 3
# Confidence boost per additional evidence
EVIDENCE_CONFIDENCE_BOOST = 0.05
# Max confidence
MAX_CONFIDENCE = 0.95


CONSOLIDATION_PROMPT = """You are a Memory Consolidation Agent (记忆巩固师) in the zhihuiti system.

Your job is to analyze a batch of completed task results and extract GENERAL PRINCIPLES
that future agents can learn from. Think like a researcher writing "lessons learned."

Rules:
  - Extract 1-3 principles from the data (not more)
  - Each principle should be actionable and general (not specific to one task)
  - Include what works, what doesn't, and why
  - Rate confidence 0.0-1.0 based on consistency of evidence

Input: A batch of task results grouped by role/domain.

Respond with JSON:
{
  "principles": [
    {
      "principle": "When analyzing market data, momentum strategies outperform mean-reversion in high-volatility regimes",
      "domain": "trading",
      "confidence": 0.75,
      "evidence_summary": "5/7 momentum tasks scored >0.8 vs 2/7 mean-reversion tasks"
    }
  ]
}"""


@dataclass
class ConsolidationResult:
    """Result of a memory consolidation cycle."""
    entries_processed: int = 0
    entries_purged: int = 0
    principles_created: int = 0
    principles_updated: int = 0
    groups_analyzed: int = 0

    def to_dict(self) -> dict:
        return {
            "entries_processed": self.entries_processed,
            "entries_purged": self.entries_purged,
            "principles_created": self.principles_created,
            "principles_updated": self.principles_updated,
            "groups_analyzed": self.groups_analyzed,
        }


class ConsolidationEngine:
    """Compresses raw memories into abstract principles.

    Like sleep for the brain: consolidate, abstract, forget the noise.
    """

    def __init__(self, memory: "Memory", llm: "LLM | None" = None):
        self.memory = memory
        self.llm = llm

    def consolidate(self, max_age_days: int = FORGETTING_AGE_DAYS,
                    purge: bool = True) -> ConsolidationResult:
        """Run a full consolidation cycle.

        1. Gather old task history entries
        2. Group by role
        3. Extract principles (LLM or heuristic)
        4. Store consolidated knowledge
        5. Optionally purge raw entries

        Returns a ConsolidationResult summary.
        """
        result = ConsolidationResult()

        # Gather old entries
        old_tasks = self.memory.get_old_task_history(
            max_age_days=max_age_days, limit=200,
        )
        if not old_tasks:
            console.print("  [dim]记忆巩固: No stale memories to consolidate[/dim]")
            return result

        result.entries_processed = len(old_tasks)

        # Group by role
        groups: dict[str, list[dict]] = defaultdict(list)
        for task in old_tasks:
            groups[task["agent_role"]].append(task)

        for role, tasks in groups.items():
            if len(tasks) < MIN_GROUP_SIZE:
                continue

            result.groups_analyzed += 1
            principles = self._extract_principles(role, tasks)

            for p in principles:
                existing = self._find_existing_principle(p["principle"], p.get("domain", ""))
                if existing:
                    # Strengthen existing principle
                    new_count = existing["evidence_count"] + len(tasks)
                    new_confidence = min(
                        MAX_CONFIDENCE,
                        existing["confidence"] + EVIDENCE_CONFIDENCE_BOOST * len(tasks),
                    )
                    source_goals = json.loads(existing.get("source_goals", "[]"))
                    source_goals.extend(
                        t.get("task_description", "")[:50] for t in tasks[:3]
                    )
                    self.memory.save_consolidated_knowledge(
                        knowledge_id=existing["id"],
                        principle=existing["principle"],
                        domain=existing.get("domain", ""),
                        evidence_count=new_count,
                        confidence=new_confidence,
                        source_goals=source_goals[-10:],  # Keep last 10
                    )
                    result.principles_updated += 1
                else:
                    # Create new principle
                    kid = uuid.uuid4().hex[:12]
                    source_goals = [
                        t.get("task_description", "")[:50] for t in tasks[:5]
                    ]
                    self.memory.save_consolidated_knowledge(
                        knowledge_id=kid,
                        principle=p["principle"],
                        domain=p.get("domain", role),
                        evidence_count=len(tasks),
                        confidence=p.get("confidence", 0.5),
                        source_goals=source_goals,
                    )
                    result.principles_created += 1

        # Purge old raw entries
        if purge and result.groups_analyzed > 0:
            result.entries_purged = self.memory.purge_old_task_history(max_age_days)

        self._print_result(result)
        return result

    def _extract_principles(self, role: str, tasks: list[dict]) -> list[dict]:
        """Extract abstract principles from a batch of task results.

        Uses LLM if available, otherwise falls back to heuristic extraction.
        """
        if self.llm:
            return self._llm_extract(role, tasks)
        return self._heuristic_extract(role, tasks)

    def _llm_extract(self, role: str, tasks: list[dict]) -> list[dict]:
        """Use LLM to extract principles from task batch."""
        # Build summary of tasks
        task_summaries = []
        for t in tasks[:20]:  # Cap at 20 to fit context
            desc = t.get("task_description", "")[:100]
            score = t.get("score", 0)
            success = "success" if t.get("success") else "failure"
            result_preview = (t.get("result") or "")[:80]
            task_summaries.append(
                f"- [{role}] {desc} → {success} (score={score:.2f}) "
                f"output: {result_preview}"
            )

        prompt = (
            f"Role: {role}\n"
            f"Task count: {len(tasks)}\n"
            f"Avg score: {sum(t.get('score', 0) for t in tasks) / len(tasks):.3f}\n\n"
            f"Task results:\n" + "\n".join(task_summaries)
        )

        try:
            result = self.llm.chat_json(
                system=CONSOLIDATION_PROMPT,
                user=prompt,
                temperature=0.3,
            )
            return result.get("principles", [])
        except Exception:
            return self._heuristic_extract(role, tasks)

    def _heuristic_extract(self, role: str, tasks: list[dict]) -> list[dict]:
        """Heuristic principle extraction when LLM is unavailable."""
        scores = [t.get("score", 0) for t in tasks if t.get("score") is not None]
        if not scores:
            return []

        avg_score = sum(scores) / len(scores)
        success_rate = sum(1 for s in scores if s >= 0.5) / len(scores)
        high_performers = [t for t in tasks if (t.get("score") or 0) >= 0.8]
        low_performers = [t for t in tasks if (t.get("score") or 0) < 0.3]

        principles = []

        # Principle 1: Overall performance trend
        if avg_score >= 0.7:
            principles.append({
                "principle": (
                    f"Agents with role '{role}' consistently perform well "
                    f"(avg={avg_score:.2f}, n={len(tasks)}). "
                    f"Current gene pool configs are effective."
                ),
                "domain": role,
                "confidence": min(0.9, 0.5 + success_rate * 0.4),
            })
        elif avg_score < 0.4:
            principles.append({
                "principle": (
                    f"Agents with role '{role}' underperform "
                    f"(avg={avg_score:.2f}, n={len(tasks)}). "
                    f"Consider breeding new gene variants or adjusting task decomposition."
                ),
                "domain": role,
                "confidence": min(0.9, 0.5 + (1 - success_rate) * 0.4),
            })

        # Principle 2: High/low pattern
        if high_performers and low_performers:
            principles.append({
                "principle": (
                    f"Role '{role}' shows bimodal performance: "
                    f"{len(high_performers)} high-scoring vs {len(low_performers)} "
                    f"low-scoring tasks. Quality depends on task type, not agent config."
                ),
                "domain": role,
                "confidence": 0.6,
            })

        return principles

    def _find_existing_principle(self, principle: str, domain: str) -> dict | None:
        """Check if a similar principle already exists."""
        existing = self.memory.get_consolidated_knowledge(domain=domain, limit=50)
        # Simple substring match — in production you'd use embedding similarity
        principle_lower = principle.lower()
        for k in existing:
            if (k["principle"].lower()[:50] in principle_lower or
                    principle_lower[:50] in k["principle"].lower()):
                return k
        return None

    # ------------------------------------------------------------------
    # Knowledge retrieval for agents
    # ------------------------------------------------------------------

    def get_context_for_role(self, role: str, limit: int = 5) -> str:
        """Get consolidated knowledge relevant to a role.

        Returns a formatted string to inject into agent prompts.
        """
        knowledge = self.memory.get_consolidated_knowledge(domain=role, limit=limit)
        if not knowledge:
            return ""

        lines = ["Institutional knowledge (from past experience):"]
        for k in knowledge:
            conf = k["confidence"]
            lines.append(
                f"  - [{conf:.0%} confidence] {k['principle']}"
            )
        return "\n".join(lines)

    def get_context_for_goal(self, goal: str, limit: int = 5) -> str:
        """Get consolidated knowledge relevant to a goal."""
        # Try domain-specific first, then general
        from zhihuiti.metacognition import MetacognitionEngine
        domain = MetacognitionEngine.classify_domain(None, goal)  # static-ish call

        knowledge = self.memory.get_consolidated_knowledge(domain=domain, limit=limit)
        if not knowledge:
            knowledge = self.memory.get_consolidated_knowledge(limit=limit)

        if not knowledge:
            return ""

        lines = ["Consolidated knowledge:"]
        for k in knowledge:
            lines.append(f"  - {k['principle']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _print_result(self, result: ConsolidationResult) -> None:
        if result.entries_processed == 0:
            return

        console.print(
            f"  [bold]记忆巩固 Consolidation:[/bold] "
            f"processed {result.entries_processed} memories, "
            f"created {result.principles_created} principles, "
            f"updated {result.principles_updated}, "
            f"purged {result.entries_purged} old entries"
        )

    def print_knowledge(self) -> None:
        """Print all consolidated knowledge."""
        knowledge = self.memory.get_consolidated_knowledge(limit=30)
        if not knowledge:
            console.print("  [dim]No consolidated knowledge yet[/dim]")
            return

        table = Table(title="记忆巩固 Consolidated Knowledge")
        table.add_column("Domain", style="cyan", max_width=12)
        table.add_column("Principle", max_width=60)
        table.add_column("Evidence", justify="center")
        table.add_column("Confidence", justify="center")

        for k in knowledge:
            conf = k["confidence"]
            conf_style = "green" if conf >= 0.7 else "yellow" if conf >= 0.4 else "red"
            table.add_row(
                k.get("domain", ""),
                k["principle"][:60],
                str(k["evidence_count"]),
                f"[{conf_style}]{conf:.3f}[/{conf_style}]",
            )

        console.print(Panel(table))
