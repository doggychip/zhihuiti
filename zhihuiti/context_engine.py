"""Context Engine — auto-assembles rich context for agent task execution.

Pulls together relevant information from multiple sources:
- Related past task results (keyword search)
- Consolidated knowledge (institutional memory)
- Agent history (scores, past tasks)
- Sibling agent outputs (multi-agent decomposition)
- Realm-specific framing

Also extracts and stores reusable learnings after successful tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

from zhihuiti.memory import Memory
from zhihuiti.models import AgentState, Realm, Task, ROLE_TO_REALM

console = Console()


@dataclass
class ContextBlock:
    """A labeled block of context to inject into an agent prompt."""

    label: str
    content: str
    source: str  # e.g. "task_history", "knowledge", "agent_history", "sibling", "realm"
    relevance: float = 1.0  # 0.0–1.0, used to prioritize/trim

    def render(self) -> str:
        return f"[{self.label}]\n{self.content}"


@dataclass
class ContextBundle:
    """Assembled context ready for injection into an agent prompt."""

    blocks: list[ContextBlock] = field(default_factory=list)
    max_chars: int = 4000

    def add(self, block: ContextBlock) -> None:
        """Add a context block to the bundle."""
        if block.content.strip():
            self.blocks.append(block)

    def render(self) -> str:
        """Render all blocks into a single context string, respecting max_chars.

        Blocks are sorted by relevance (highest first) and trimmed if the
        total exceeds the character budget.
        """
        if not self.blocks:
            return ""

        sorted_blocks = sorted(self.blocks, key=lambda b: b.relevance, reverse=True)

        parts: list[str] = []
        remaining = self.max_chars

        for block in sorted_blocks:
            rendered = block.render()
            if len(rendered) <= remaining:
                parts.append(rendered)
                remaining -= len(rendered) + 1  # +1 for newline separator
            elif remaining > 100:
                # Truncate the block to fit
                parts.append(rendered[:remaining - 20] + "\n  (...truncated)")
                remaining = 0
                break

        if not parts:
            return ""

        return "Context for this task:\n\n" + "\n\n".join(parts)

    @property
    def total_chars(self) -> int:
        return sum(len(b.content) for b in self.blocks)

    @property
    def source_summary(self) -> dict[str, int]:
        """Count of blocks by source type."""
        counts: dict[str, int] = {}
        for b in self.blocks:
            counts[b.source] = counts.get(b.source, 0) + 1
        return counts


def _extract_keywords(text: str, max_keywords: int = 6) -> list[str]:
    """Extract meaningful keywords from a text string for search.

    Uses simple heuristics — no external NLP libraries.
    """
    # Common stopwords to filter out
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "ought",
        "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
        "neither", "each", "every", "all", "any", "few", "more", "most",
        "other", "some", "such", "no", "only", "own", "same", "than", "too",
        "very", "just", "because", "as", "until", "while", "of", "at", "by",
        "for", "with", "about", "against", "between", "through", "during",
        "before", "after", "above", "below", "to", "from", "up", "down",
        "in", "out", "on", "off", "over", "under", "again", "further",
        "then", "once", "here", "there", "when", "where", "why", "how",
        "this", "that", "these", "those", "it", "its", "i", "me", "my",
        "we", "our", "you", "your", "he", "him", "his", "she", "her",
        "they", "them", "their", "what", "which", "who", "whom",
        "task", "create", "make", "write", "build", "implement", "use",
    }

    # Tokenize: split on non-alphanumeric, keep words >= 3 chars
    words = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
    keywords = [w for w in words if w not in stopwords]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)

    return unique[:max_keywords]


# Realm descriptions for framing
_REALM_FRAMING: dict[Realm, str] = {
    Realm.RESEARCH: (
        "You operate in the Research realm (研发界). "
        "Prioritize thoroughness, accuracy, and novel insights. "
        "Your outputs feed into execution and coordination."
    ),
    Realm.EXECUTION: (
        "You operate in the Execution realm (执行界). "
        "Prioritize speed, correctness, and actionable results. "
        "Follow established patterns and deliver concrete outputs."
    ),
    Realm.CENTRAL: (
        "You operate in the Central realm (中枢界). "
        "Prioritize coordination, oversight, and quality control. "
        "Your decisions affect other agents and system integrity."
    ),
}


class ContextEngine:
    """Assembles rich context for agent task execution and extracts learnings.

    The engine pulls from multiple sources to give each agent the most
    relevant context for its current task, without requiring embeddings
    or external NLP libraries.
    """

    def __init__(self, memory: Memory, max_context_chars: int = 4000):
        self.memory = memory
        self.max_context_chars = max_context_chars

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    def build_context(
        self,
        agent: AgentState,
        task: Task,
        *,
        sibling_outputs: dict[str, str] | None = None,
        goal_id: str | None = None,
    ) -> str:
        """Auto-assemble context for an agent about to execute a task.

        Pulls from:
          1. Related past task results (keyword search by task description)
          2. Consolidated knowledge (institutional memory for this role)
          3. Agent's own history (scores, past performance)
          4. Sibling agent outputs (if multi-agent decomposition)
          5. Realm-specific framing

        Args:
            agent: The agent that will execute the task.
            task: The task to be executed.
            sibling_outputs: Outputs from sibling tasks in the same goal,
                keyed by dag_id.
            goal_id: Optional goal identifier for scoping.

        Returns:
            Formatted context string ready for prompt injection.
        """
        bundle = ContextBundle(max_chars=self.max_context_chars)

        # 1. Related past task results
        past_block = self._build_past_tasks_context(task)
        if past_block:
            bundle.add(past_block)

        # 2. Consolidated knowledge
        knowledge_block = self._build_knowledge_context(agent)
        if knowledge_block:
            bundle.add(knowledge_block)

        # 3. Agent's own history
        history_block = self._build_agent_history_context(agent)
        if history_block:
            bundle.add(history_block)

        # 4. Sibling agent outputs
        if sibling_outputs:
            sibling_block = self._build_sibling_context(sibling_outputs)
            if sibling_block:
                bundle.add(sibling_block)

        # 5. Realm-specific framing
        realm_block = self._build_realm_context(agent)
        if realm_block:
            bundle.add(realm_block)

        rendered = bundle.render()

        if rendered:
            sources = bundle.source_summary
            source_str = ", ".join(f"{k}={v}" for k, v in sources.items())
            console.print(
                f"  [dim]Context engine: {len(bundle.blocks)} blocks, "
                f"{bundle.total_chars} chars ({source_str})[/dim]"
            )

        return rendered

    def _build_past_tasks_context(self, task: Task) -> ContextBlock | None:
        """Search task_history for related past results using keyword matching."""
        keywords = _extract_keywords(task.description)
        if not keywords:
            return None

        # Search for each keyword and collect unique results
        seen_ids: set[int] = set()
        matches: list[dict[str, Any]] = []

        for kw in keywords[:4]:  # Limit searches to avoid excessive queries
            try:
                rows = self.memory._query(
                    """SELECT rowid, task_description, agent_role, result, score
                       FROM task_history
                       WHERE task_description LIKE ?
                         AND success = 1
                       ORDER BY score DESC
                       LIMIT 5""",
                    (f"%{kw}%",),
                )
                for row in rows:
                    rid = row["rowid"]
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        matches.append(dict(row))
            except Exception:
                continue

        if not matches:
            return None

        # Sort by score descending, take top results
        matches.sort(key=lambda m: m.get("score", 0) or 0, reverse=True)
        top = matches[:3]

        lines: list[str] = []
        for m in top:
            score = m.get("score", 0) or 0
            desc = (m.get("task_description") or "")[:80]
            result = (m.get("result") or "")[:200]
            lines.append(f"  - [{score:.2f}] {desc}")
            if result:
                lines.append(f"    Result: {result}")

        return ContextBlock(
            label="Related past tasks (successful)",
            content="\n".join(lines),
            source="task_history",
            relevance=0.8,
        )

    def _build_knowledge_context(self, agent: AgentState) -> ContextBlock | None:
        """Pull consolidated knowledge for this agent's role."""
        role_name = agent.config.role.value

        try:
            knowledge = self.memory.get_consolidated_knowledge(
                domain=role_name, limit=5,
            )
        except Exception:
            return None

        if not knowledge:
            return None

        lines: list[str] = []
        for k in knowledge:
            conf = k.get("confidence", 0)
            principle = k.get("principle", "")
            lines.append(f"  - [{conf:.0%}] {principle}")

        return ContextBlock(
            label="Institutional knowledge",
            content="\n".join(lines),
            source="knowledge",
            relevance=0.9,
        )

    def _build_agent_history_context(self, agent: AgentState) -> ContextBlock | None:
        """Summarize the agent's own performance history."""
        if not agent.scores:
            return None

        avg = agent.avg_score
        recent = agent.scores[-5:]
        trend = "improving" if len(recent) >= 2 and recent[-1] > recent[0] else "stable"
        if len(recent) >= 2 and recent[-1] < recent[0]:
            trend = "declining"

        task_count = len(agent.task_ids)
        alive_str = "active" if agent.alive else "terminated"

        lines = [
            f"  Agent {agent.id} ({agent.config.role.value})",
            f"  Average score: {avg:.2f} | Tasks completed: {task_count} | Status: {alive_str}",
            f"  Recent scores: {', '.join(f'{s:.2f}' for s in recent)} (trend: {trend})",
            f"  Budget remaining: {agent.budget:.1f}",
        ]

        # Add past successes for this role from DB
        try:
            successes = self.memory.get_similar_successes(
                agent.config.role.value, limit=2,
            )
            if successes:
                lines.append("  Top past successes for this role:")
                for s in successes:
                    desc = (s.get("task_description") or "")[:60]
                    score = s.get("score", 0)
                    lines.append(f"    - [{score:.2f}] {desc}")
        except Exception:
            pass

        return ContextBlock(
            label="Your performance history",
            content="\n".join(lines),
            source="agent_history",
            relevance=0.6,
        )

    def _build_sibling_context(
        self, sibling_outputs: dict[str, str],
    ) -> ContextBlock | None:
        """Format outputs from sibling tasks for cross-reference."""
        if not sibling_outputs:
            return None

        lines: list[str] = []
        for dag_id, output in sibling_outputs.items():
            truncated = output[:300] if len(output) > 300 else output
            lines.append(f"  [{dag_id}]: {truncated}")

        return ContextBlock(
            label="Sibling task outputs",
            content="\n".join(lines),
            source="sibling",
            relevance=0.7,
        )

    def _build_realm_context(self, agent: AgentState) -> ContextBlock | None:
        """Add realm-specific framing and guidance."""
        realm = agent.realm
        framing = _REALM_FRAMING.get(realm)
        if not framing:
            return None

        return ContextBlock(
            label="Realm context",
            content=framing,
            source="realm",
            relevance=0.5,
        )

    # ------------------------------------------------------------------
    # Learning extraction
    # ------------------------------------------------------------------

    def extract_learnings(
        self,
        task: Task,
        agent: AgentState,
        score: float,
        *,
        min_score: float = 0.7,
    ) -> bool:
        """Extract and store reusable learnings from a completed task.

        Only extracts learnings when the task score meets the threshold,
        ensuring we only learn from successful executions.

        Args:
            task: The completed task.
            agent: The agent that executed the task.
            score: The task's score (0.0–1.0).
            min_score: Minimum score to extract learnings (default 0.7).

        Returns:
            True if a learning was stored, False otherwise.
        """
        if score < min_score:
            return False

        if not task.result or not task.result.strip():
            return False

        # Build a learning principle from the successful task
        role_name = agent.config.role.value
        description = task.description[:200]
        result_summary = task.result[:300]

        # Extract a concise learning principle
        principle = self._synthesize_learning(description, result_summary, score)
        if not principle:
            return False

        # Generate a deterministic ID so we don't duplicate learnings
        # for essentially the same task pattern
        keywords = _extract_keywords(description, max_keywords=4)
        learning_id = f"ctx_{role_name}_{'_'.join(keywords[:3])}"

        try:
            # Check if we already have this learning
            existing = self.memory.get_consolidated_knowledge(
                domain=role_name, limit=50,
            )
            for k in existing:
                if k.get("id") == learning_id:
                    # Update if new score is higher (more confident)
                    old_conf = k.get("confidence", 0)
                    new_conf = min(1.0, (old_conf + score) / 2)
                    evidence = k.get("evidence_count", 1) + 1
                    self.memory.save_consolidated_knowledge(
                        knowledge_id=learning_id,
                        principle=principle,
                        domain=role_name,
                        evidence_count=evidence,
                        confidence=new_conf,
                    )
                    console.print(
                        f"  [dim]Context engine: updated learning "
                        f"'{principle[:50]}...' (evidence={evidence})[/dim]"
                    )
                    return True

            # Store new learning
            self.memory.save_consolidated_knowledge(
                knowledge_id=learning_id,
                principle=principle,
                domain=role_name,
                evidence_count=1,
                confidence=score,
            )
            console.print(
                f"  [dim]Context engine: stored new learning "
                f"'{principle[:50]}...'[/dim]"
            )
            return True

        except Exception as exc:
            console.print(
                f"  [dim yellow]Context engine: failed to store learning: {exc}[/dim yellow]"
            )
            return False

    def _synthesize_learning(
        self, description: str, result_summary: str, score: float,
    ) -> str:
        """Synthesize a concise learning principle from task description and result.

        Uses simple heuristic extraction rather than LLM calls to keep
        this lightweight and dependency-free.
        """
        # Extract the core action from the description
        desc_clean = description.strip().rstrip(".")

        # Build a principle: "When doing X, approach Y works well (score Z)"
        # Take the first sentence of the result as the approach summary
        first_sentence = result_summary.split(".")[0].strip()
        if len(first_sentence) > 150:
            first_sentence = first_sentence[:147] + "..."

        if first_sentence:
            principle = (
                f"For '{desc_clean[:80]}': "
                f"{first_sentence} (scored {score:.2f})"
            )
        else:
            principle = (
                f"Task '{desc_clean[:80]}' completed successfully "
                f"(scored {score:.2f})"
            )

        return principle
