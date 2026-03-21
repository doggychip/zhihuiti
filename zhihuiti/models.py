"""Data models for zhihuiti (智慧体) multi-agent system."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AgentRole(str, Enum):
    orchestrator = "orchestrator"
    researcher = "researcher"
    analyst = "analyst"
    coder = "coder"
    trader = "trader"
    judge = "judge"
    synthesizer = "synthesizer"


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


@dataclass
class AgentConfig:
    id: str = field(default_factory=_new_id)
    role: AgentRole = AgentRole.researcher
    generation: int = 0
    parent_ids: list = field(default_factory=list)
    budget: float = 100.0
    score: float = 0.5
    lineage: list = field(default_factory=list)  # ancestor IDs up to 7 generations
    specialization: str = ""


@dataclass
class Task:
    id: str = field(default_factory=_new_id)
    description: str = ""
    assigned_agent_id: Optional[str] = None
    status: str = "pending"  # pending / running / done / failed
    result: Optional[str] = None
    score: Optional[float] = None
    bid_amount: Optional[float] = None


@dataclass
class AgentState:
    """Agent config plus runtime metrics."""
    config: AgentConfig = field(default_factory=AgentConfig)
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_earned: float = 0.0
    total_spent: float = 0.0
    is_active: bool = True
