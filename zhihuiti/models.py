"""Core data models for zhihuiti."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    COORDINATOR = "coordinator"
    AUDITOR = "auditor"
    STRATEGIST = "strategist"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    CODER = "coder"
    TRADER = "trader"
    JUDGE = "judge"
    ALPHAARENA_TRADER = "alphaarena_trader"
    CAUSAL_REASONER = "causal_reasoner"
    CUSTOM = "custom"


class Realm(str, Enum):
    """三界 — the three realms of agent governance."""
    RESEARCH = "research"       # 研发界 — R&D, develops new products/tech
    EXECUTION = "execution"     # 执行界 — task distribution and execution
    CENTRAL = "central"         # 中枢界 — management and coordination (government)


class AgentLifeState(str, Enum):
    """Agent lifecycle states within a realm."""
    ACTIVE = "active"           # 全状态活跃 — fully active, taking tasks
    FROZEN = "frozen"           # 沙盘中冻结 — frozen in sandbox, preserved but inactive
    BANKRUPT = "bankrupt"       # 已破产 — bankrupt, out of tokens


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Which roles belong to which realm by default
ROLE_TO_REALM: dict[AgentRole, Realm] = {
    AgentRole.ORCHESTRATOR: Realm.CENTRAL,
    AgentRole.COORDINATOR: Realm.CENTRAL,
    AgentRole.AUDITOR: Realm.CENTRAL,
    AgentRole.STRATEGIST: Realm.CENTRAL,
    AgentRole.RESEARCHER: Realm.RESEARCH,
    AgentRole.ANALYST: Realm.RESEARCH,
    AgentRole.CODER: Realm.RESEARCH,
    AgentRole.TRADER: Realm.EXECUTION,
    AgentRole.JUDGE: Realm.CENTRAL,
    AgentRole.ALPHAARENA_TRADER: Realm.EXECUTION,
    AgentRole.CAUSAL_REASONER: Realm.RESEARCH,
    AgentRole.CUSTOM: Realm.EXECUTION,
}


@dataclass
class AgentConfig:
    """Configuration template for an agent."""

    role: AgentRole
    system_prompt: str
    budget: float = 100.0
    max_depth: int = 3
    temperature: float = 0.7
    # Gene pool metadata
    gene_id: str | None = None
    parent_gene_id: str | None = None
    mutation_notes: str = ""
    # Bloodline metadata (multi-parent lineage)
    lineage_id: str | None = None
    parent_a_gene: str | None = None
    parent_b_gene: str | None = None
    generation: int = 0
    # Model tier — None means use the LLM default; a string overrides per-call
    model: str | None = None
    # Tool access — agents with tools can execute whitelisted shell commands
    tools_enabled: bool = False

    def mutate(self, mutation_notes: str = "") -> AgentConfig:
        """Create a slightly mutated copy of this config."""
        import random

        new_temp = max(0.1, min(1.0, self.temperature + random.uniform(-0.1, 0.1)))
        return AgentConfig(
            role=self.role,
            system_prompt=self.system_prompt,
            budget=self.budget,
            max_depth=self.max_depth,
            temperature=round(new_temp, 2),
            gene_id=uuid.uuid4().hex[:12],
            parent_gene_id=self.gene_id,
            mutation_notes=mutation_notes or "temperature mutation",
            lineage_id=self.lineage_id,
            parent_a_gene=self.parent_a_gene,
            parent_b_gene=self.parent_b_gene,
            generation=self.generation,
            model=self.model,  # inherit model tier on mutation
            tools_enabled=self.tools_enabled,
        )


@dataclass
class Task:
    """A unit of work to be performed by an agent."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    parent_task_id: str | None = None
    assigned_agent_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    score: float | None = None
    subtask_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)


@dataclass
class AgentState:
    """Runtime state of a live agent."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    config: AgentConfig = field(default_factory=lambda: AgentConfig(role=AgentRole.CUSTOM, system_prompt=""))
    budget: float = 100.0
    depth: int = 0
    parent_agent_id: str | None = None
    task_ids: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    alive: bool = True
    realm: Realm = Realm.EXECUTION
    life_state: AgentLifeState = AgentLifeState.ACTIVE

    @property
    def avg_score(self) -> float:
        if not self.scores:
            return 0.5
        return sum(self.scores) / len(self.scores)

    def deduct_budget(self, amount: float) -> bool:
        if self.budget >= amount:
            self.budget -= amount
            return True
        return False
