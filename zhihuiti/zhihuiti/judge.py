"""Judge agent — scores outputs via 3-layer inspection and triggers cull/promote.

Now integrated with the Adaptation Engine:
- AdaptiveThresholds: cull/promote thresholds calibrate to population
- PromptEvolver: inspection failures drive prompt improvement
- PerformanceTracker: per-role score trends guide mutation rates
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from zhihuiti.adaptation import (
    AdaptiveThresholds,
    PerformanceTracker,
    PromptEvolver,
)
from zhihuiti.inspection import InspectionGate, LAYER_THRESHOLDS
from zhihuiti.models import AgentState, Task

if TYPE_CHECKING:
    from zhihuiti.agents import AgentManager
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()

# Fallback thresholds (used only before adaptation kicks in)
DEFAULT_CULL_THRESHOLD = 0.3
DEFAULT_PROMOTE_THRESHOLD = 0.8


class Judge:
    """Evaluates agent outputs via 3-layer inspection and manages evolution.

    Integrates three feedback systems:
    1. Score → AdaptiveThresholds → calibrated cull/promote decisions
    2. Score → PromptEvolver → improved prompts for weak roles
    3. Score → PerformanceTracker → adaptive mutation rates for breeding
    """

    def __init__(self, llm: LLM, memory: Memory, agent_manager: AgentManager):
        self.llm = llm
        self.memory = memory
        self.agent_manager = agent_manager
        self.inspection = InspectionGate(llm, memory)

        # Adaptation systems
        self.adaptive_thresholds = AdaptiveThresholds()
        self.prompt_evolver = PromptEvolver()
        self.performance_tracker = PerformanceTracker()

    @property
    def cull_threshold(self) -> float:
        return self.adaptive_thresholds.state.cull

    @property
    def promote_threshold(self) -> float:
        return self.adaptive_thresholds.state.promote

    def score_task(self, task: Task, agent: AgentState) -> float:
        """Score a completed task through 3-layer inspection.

        Also feeds the result into the adaptation systems.
        """
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

        # Feed into adaptation systems
        layer_scores = result.scores_by_layer
        role = agent.config.role.value

        # 1. Track per-role performance
        self.performance_tracker.record(role, score, layer_scores)

        # 2. Record inspection pattern for prompt evolution
        layer_thresh = {layer.value: thresh for layer, thresh in LAYER_THRESHOLDS.items()}
        self.prompt_evolver.record_inspection(role, layer_scores, layer_thresh)

        return score

    def evaluate_agent(self, agent: AgentState) -> None:
        """Check if an agent should be culled or promoted.

        Uses adaptive thresholds instead of fixed constants.
        """
        if len(agent.scores) < 1:
            return

        avg = agent.avg_score
        cull_t, promote_t = self.adaptive_thresholds.get_thresholds()

        if avg < cull_t:
            self.agent_manager.cull_agent(agent)
        elif avg >= promote_t:
            self.agent_manager.promote_to_gene_pool(agent)

    def run_evaluation_cycle(self, agents: list[AgentState]) -> dict:
        """Evaluate all agents after a round of work.

        Also recalibrates thresholds based on the current population.
        """
        # Recalibrate thresholds from population scores
        all_scores = [a.avg_score for a in agents if a.alive and a.scores]
        if all_scores:
            self.adaptive_thresholds.update(all_scores)

        culled = 0
        promoted = 0
        cull_t, promote_t = self.adaptive_thresholds.get_thresholds()

        for agent in agents:
            if not agent.alive:
                continue
            self.evaluate_agent(agent)
            if not agent.alive:
                culled += 1
            elif agent.avg_score >= promote_t:
                promoted += 1

        return {
            "culled": culled,
            "promoted": promoted,
            "alive": len([a for a in agents if a.alive]),
            "cull_threshold": cull_t,
            "promote_threshold": promote_t,
        }

    def get_evolved_prompt(self, base_prompt: str, role: str) -> str:
        """Get a prompt with targeted improvement directives.

        Call this when spawning a new agent to give it a prompt
        that addresses known weaknesses for its role.
        """
        return self.prompt_evolver.evolve_prompt(base_prompt, role)

    def get_mutation_rate(self, role: str) -> float:
        """Get the adaptive mutation rate for breeding agents of this role.

        High performers → low mutation (don't break what works)
        Low/declining performers → high mutation (try something different)
        """
        return self.performance_tracker.suggest_mutation_rate(role)
