"""Bloodline system for zhihuiti — agent lineage, merging, and 诛七族 punishment."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .bidding import AgentPool
from .economy import Economy
from .memory import Memory
from .models import AgentConfig, AgentRole


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


@dataclass
class Bloodline:
    child_id: str
    parent_ids: list = field(default_factory=list)  # 1 or 2 parents
    generation: int = 0
    lineage: list = field(default_factory=list)  # ancestor IDs, up to 7 generations
    timestamp: str = field(default_factory=_now_iso)


class BloodlineManager:
    """Manages agent lineage, merging, and punishment."""

    def merge(
        self,
        parent1: AgentConfig,
        parent2: AgentConfig,
        memory: Memory,
        economy: Economy,
    ) -> AgentConfig:
        """
        Create a child agent by merging two parents.

        - Child role: randomly pick from parents, or 'synthesizer' if different roles
        - Child budget: average of parents' budgets * 0.8
        - Child score: average of parents' scores
        - Child specialization: combination of both parents'
        - Lineage: merged, deduplicated, most recent 7 ancestors, prepend both parents
        - Generation: max(parent1.gen, parent2.gen) + 1
        """
        p1_role = parent1.role.value if isinstance(parent1.role, AgentRole) else str(parent1.role)
        p2_role = parent2.role.value if isinstance(parent2.role, AgentRole) else str(parent2.role)

        if p1_role == p2_role:
            child_role = AgentRole(p1_role)
        else:
            # Different roles → synthesizer or random pick
            pick = random.choice(["synthesizer", p1_role, p2_role])
            try:
                child_role = AgentRole(pick)
            except ValueError:
                child_role = AgentRole.synthesizer

        child_budget = (parent1.budget + parent2.budget) / 2.0 * 0.8
        child_score = (parent1.score + parent2.score) / 2.0

        # Combine specializations
        spec_parts = []
        if parent1.specialization:
            spec_parts.append(parent1.specialization)
        if parent2.specialization:
            spec_parts.append(parent2.specialization)
        child_specialization = " + ".join(spec_parts) if spec_parts else ""

        # Build lineage: merge parents' lineages, deduplicate, keep 7, prepend parent IDs
        merged_lineage: list[str] = []
        merged_lineage.append(parent1.id)
        merged_lineage.append(parent2.id)
        for ancestor in parent1.lineage + parent2.lineage:
            if ancestor not in merged_lineage:
                merged_lineage.append(ancestor)
        child_lineage = merged_lineage[:7]

        child_generation = max(parent1.generation, parent2.generation) + 1

        child = AgentConfig(
            role=child_role,
            generation=child_generation,
            parent_ids=[parent1.id, parent2.id],
            budget=child_budget,
            score=child_score,
            lineage=child_lineage,
            specialization=child_specialization,
        )

        # Save to memory
        memory.save_agent(child, status="active")
        memory.save_bloodline_event(
            child_id=child.id,
            generation=child_generation,
            parent1_id=parent1.id,
            parent2_id=parent2.id,
        )

        # Charge economy for merge spawn cost
        economy.charge_merge(child.id)

        return child

    def trace_lineage(self, agent_id: str, memory: Memory) -> list[AgentConfig]:
        """Return full ancestor chain up to 7 generations."""
        agent = memory.get_agent(agent_id)
        if agent is None:
            return []

        ancestors: list[AgentConfig] = []
        visited: set[str] = {agent_id}

        for ancestor_id in agent.lineage[:7]:
            if ancestor_id in visited:
                continue
            visited.add(ancestor_id)
            ancestor = memory.get_agent(ancestor_id)
            if ancestor is not None:
                ancestors.append(ancestor)

        return ancestors

    def punish_lineage(
        self,
        agent_id: str,
        memory: Memory,
        economy: Economy,
        depth: int = 7,
    ) -> list[str]:
        """
        诛七族 — cull the agent AND all ancestors up to `depth` generations.

        For each ancestor: mark as culled, burn remaining tokens.
        Returns list of culled agent IDs.
        """
        culled: list[str] = []

        # Gather agent and ancestors
        agent = memory.get_agent(agent_id)
        if agent is None:
            return culled

        targets: list[str] = [agent_id]
        for ancestor_id in agent.lineage[:depth]:
            if ancestor_id not in targets:
                targets.append(ancestor_id)

        for target_id in targets:
            target = memory.get_agent(target_id)
            if target is None:
                continue
            balance = economy.get_agent_balance(target_id)
            economy.burn_agent(target_id, balance)
            memory.update_agent_status(target_id, "culled")
            memory.update_agent_budget(target_id, 0.0)
            economy._memory.save_economy_event(
                "punish_lineage",
                balance,
                agent_id=target_id,
                description=f"诛七族 triggered by {agent_id}",
            )
            culled.append(target_id)

        return culled

    def find_best_pair(
        self,
        pool: AgentPool,
        role: Optional[str] = None,
    ) -> Optional[tuple[AgentConfig, AgentConfig]]:
        """
        Find two highest-scoring agents to merge.

        Optionally filter by role. Returns None if fewer than 2 agents available.
        """
        candidates = pool.get_available(role=role) if role else pool.all_agents()

        # Filter: budget > 10 and not culled
        candidates = [a for a in candidates if a.budget > 10.0]

        if len(candidates) < 2:
            return None

        # Sort by score descending
        candidates.sort(key=lambda a: a.score, reverse=True)
        return (candidates[0], candidates[1])

    def lineage_report(self, agent_id: str, memory: Memory) -> str:
        """Return a Rich-formatted string showing the agent's family tree."""
        agent = memory.get_agent(agent_id)
        if agent is None:
            return f"[red]Agent {agent_id} not found.[/red]"

        role = agent.role.value if isinstance(agent.role, AgentRole) else str(agent.role)
        lines = [
            f"[bold cyan]Lineage Report for Agent {agent_id}[/bold cyan]",
            f"  Role: [yellow]{role}[/yellow]  "
            f"Generation: [green]{agent.generation}[/green]  "
            f"Score: [magenta]{agent.score:.2f}[/magenta]  "
            f"Budget: [blue]{agent.budget:.1f}[/blue]",
        ]

        if agent.parent_ids:
            lines.append(f"  Parents: {', '.join(agent.parent_ids)}")

        ancestors = self.trace_lineage(agent_id, memory)
        if ancestors:
            lines.append("\n[bold]Ancestor Chain:[/bold]")
            for i, anc in enumerate(ancestors, 1):
                anc_role = anc.role.value if isinstance(anc.role, AgentRole) else str(anc.role)
                lines.append(
                    f"  {'  ' * i}└─ [{anc.id}] {anc_role} "
                    f"gen={anc.generation} score={anc.score:.2f}"
                )
        else:
            lines.append("  [dim]No known ancestors.[/dim]")

        return "\n".join(lines)
