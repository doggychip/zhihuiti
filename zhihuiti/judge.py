"""Judge agent — scores outputs via 3-layer inspection and triggers cull/promote."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from zhihuiti.inspection import InspectionGate
from zhihuiti.models import AgentState, Task

if TYPE_CHECKING:
    from zhihuiti.agents import AgentManager
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()

CULL_THRESHOLD = 0.3
PROMOTE_THRESHOLD = 0.8


class Judge:
    """Evaluates agent outputs via 3-layer inspection and manages evolution."""

    def __init__(self, llm: LLM, memory: Memory, agent_manager: AgentManager):
        self.llm = llm
        self.memory = memory
        self.agent_manager = agent_manager
        self.inspection = InspectionGate(llm, memory)

    def score_task(self, task: Task, agent: AgentState) -> float:
        """Score a completed task through 3-layer inspection."""
        result = self.inspection.full_inspection(task, agent)

        score = result.final_score
        task.score = score
        agent.scores.append(score)

        # Record to memory
        self.memory.record_task_history(
            description=task.description,
            agent_role=agent.config.role.value,
            result=task.result[:500],
            score=score,
        )
        self.memory.save_task(
            task_id=task.id,
            description=task.description,
            status=task.status.value,
            result=task.result,
            score=score,
            agent_id=agent.id,
        )

        return score

    def evaluate_agent(self, agent: AgentState) -> None:
        """Check if an agent should be culled or promoted."""
        if len(agent.scores) < 1:
            return

        avg = agent.avg_score

        if avg < CULL_THRESHOLD:
            self.agent_manager.cull_agent(agent)
        elif avg >= PROMOTE_THRESHOLD:
            self.agent_manager.promote_to_gene_pool(agent)

    def run_evaluation_cycle(self, agents: list[AgentState]) -> dict:
        """Evaluate all agents after a round of work."""
        culled = 0
        promoted = 0

        for agent in agents:
            if not agent.alive:
                continue
            self.evaluate_agent(agent)
            if not agent.alive:
                culled += 1
            elif agent.avg_score >= PROMOTE_THRESHOLD:
                promoted += 1

        return {"culled": culled, "promoted": promoted, "alive": len([a for a in agents if a.alive])}
