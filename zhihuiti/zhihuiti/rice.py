"""RICE task prioritization (inspired by agency-agents' Sprint Prioritizer).

RICE = (Reach × Impact × Confidence) / Effort

Used to order tasks within a DAG wave so the highest-impact tasks
are auctioned and executed first. This matters because:
- Earlier tasks' outputs inform later tasks via messaging
- If budget runs low, high-impact tasks are already done
- Agents learn from high-value tasks first (via cross-goal memory)

Scoring is LLM-assisted: the orchestrator asks the LLM to estimate
RICE components for each task, then we sort by composite score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.models import Task

console = Console()


@dataclass
class RICEScore:
    """RICE score components for a single task."""
    task_id: str
    description: str
    reach: float = 1.0       # How many downstream tasks/agents benefit (1-5)
    impact: float = 1.0      # How much this moves the goal forward (1-3: low/med/high)
    confidence: float = 0.5  # How confident we are in the estimates (0.0-1.0)
    effort: float = 1.0      # Agent-hours / complexity (0.5-5.0, higher = more work)

    @property
    def score(self) -> float:
        """Composite RICE score. Higher = higher priority."""
        if self.effort <= 0:
            return 0.0
        return (self.reach * self.impact * self.confidence) / self.effort


def estimate_rice_scores(llm: LLM, tasks: list[Task], goal: str) -> list[RICEScore]:
    """Use the LLM to estimate RICE scores for a batch of tasks.

    Returns tasks sorted by RICE score (highest first).
    """
    if not tasks:
        return []

    # For single-task waves, skip LLM call
    if len(tasks) == 1:
        return [RICEScore(
            task_id=tasks[0].id,
            description=tasks[0].description,
            reach=1.0, impact=2.0, confidence=0.7, effort=1.0,
        )]

    task_list = "\n".join(
        f"- id={t.metadata.get('dag_id', t.id)}: {t.description[:120]}"
        for t in tasks
    )

    try:
        result = llm.chat_json(
            system=(
                "You are a task prioritizer. Score each task using RICE:\n"
                "- reach: How many downstream tasks or stakeholders benefit (1-5)\n"
                "- impact: How much this moves the overall goal forward (1=low, 2=medium, 3=high)\n"
                "- confidence: How sure you are about these estimates (0.0-1.0)\n"
                "- effort: Relative complexity/time needed (0.5=trivial, 1=normal, 3=hard, 5=very hard)\n\n"
                "Respond with a JSON array of objects, one per task:\n"
                '[{"id": "task_id", "reach": 2, "impact": 3, "confidence": 0.8, "effort": 1.5}]'
            ),
            user=(
                f"Goal: {goal}\n\n"
                f"Tasks to prioritize:\n{task_list}\n\n"
                "Score each task. Be realistic about effort and confidence."
            ),
            temperature=0.3,
        )
    except Exception as e:
        console.print(f"  [dim]RICE scoring failed ({e}), using default order[/dim]")
        return [
            RICEScore(task_id=t.id, description=t.description)
            for t in tasks
        ]

    if not isinstance(result, list):
        result = [result]

    # Map LLM output to RICEScore objects
    id_to_task = {t.metadata.get("dag_id", t.id): t for t in tasks}
    scores: list[RICEScore] = []
    scored_ids = set()

    for item in result:
        if not isinstance(item, dict):
            continue
        tid = item.get("id", "")
        task = id_to_task.get(tid)
        if not task:
            continue
        scored_ids.add(tid)
        scores.append(RICEScore(
            task_id=task.id,
            description=task.description,
            reach=max(1.0, min(5.0, float(item.get("reach", 1)))),
            impact=max(1.0, min(3.0, float(item.get("impact", 1)))),
            confidence=max(0.1, min(1.0, float(item.get("confidence", 0.5)))),
            effort=max(0.5, min(5.0, float(item.get("effort", 1)))),
        ))

    # Add any tasks the LLM missed with default scores
    for t in tasks:
        dag_id = t.metadata.get("dag_id", t.id)
        if dag_id not in scored_ids:
            scores.append(RICEScore(task_id=t.id, description=t.description))

    # Sort by RICE score descending
    scores.sort(key=lambda s: s.score, reverse=True)

    # Log the prioritization
    if len(scores) > 1:
        console.print("  [dim]RICE prioritization:[/dim]")
        for i, s in enumerate(scores, 1):
            console.print(
                f"    {i}. [dim]{s.description[:50]}[/dim] "
                f"(R={s.reach:.0f} I={s.impact:.0f} C={s.confidence:.1f} E={s.effort:.1f} "
                f"→ {s.score:.2f})"
            )

    return scores
