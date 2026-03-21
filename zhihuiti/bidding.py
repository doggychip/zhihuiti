"""Bidding and auction system for zhihuiti."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .memory import Memory
from .models import AgentConfig, AgentRole, Task

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


MODEL = "claude-haiku-4-5-20251001"


def _get_client() -> Optional[object]:
    if not _ANTHROPIC_AVAILABLE:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


@dataclass
class Bid:
    agent_id: str
    role: str
    amount: float
    confidence: float


class AgentPool:
    """Manages a pool of reusable agents per role."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentConfig] = {}

    def add(self, agent: AgentConfig) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[AgentConfig]:
        return self._agents.get(agent_id)

    def release(self, agent_id: str) -> None:
        """Mark agent as available again (no-op currently, pool just holds refs)."""
        pass

    def get_available(self, role: Optional[str] = None) -> list[AgentConfig]:
        """Return agents with budget > 10, optionally filtered by role."""
        result = []
        for agent in self._agents.values():
            if agent.budget <= 10.0:
                continue
            if role is not None:
                agent_role = agent.role.value if isinstance(agent.role, AgentRole) else agent.role
                if agent_role != role:
                    continue
            result.append(agent)
        return result

    def all_agents(self) -> list[AgentConfig]:
        return list(self._agents.values())

    def remove(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)


class BiddingHouse:
    """Runs auctions to assign tasks to agents."""

    def __init__(self) -> None:
        self._client = _get_client()

    def _ask_bid(self, agent: AgentConfig, task: Task) -> Optional[Bid]:
        """Ask an agent to bid on a task. Returns Bid or None on failure."""
        if self._client is None:
            # No API — make a simple heuristic bid
            return Bid(
                agent_id=agent.id,
                role=agent.role.value if isinstance(agent.role, AgentRole) else str(agent.role),
                amount=agent.budget * 0.2,
                confidence=agent.score,
            )

        role_name = agent.role.value if isinstance(agent.role, AgentRole) else str(agent.role)
        system = (
            f"You are agent {agent.id} ({role_name}, generation {agent.generation}). "
            f"Your current budget is {agent.budget:.1f} tokens and score is {agent.score:.2f}. "
            "You are bidding to execute a task. Respond with ONLY valid JSON."
        )
        user = (
            f"Task: {task.description}\n\n"
            "How much would you bid (in tokens) and how confident are you (0.0-1.0) "
            "that you can complete this task well?\n"
            'Reply with ONLY JSON: {"bid": <float>, "confidence": <float>}'
        )
        try:
            message = self._client.messages.create(
                model=MODEL,
                max_tokens=128,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = message.content[0].text.strip()
            # Extract JSON even if wrapped in markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            bid_amount = float(data.get("bid", agent.budget * 0.2))
            confidence = float(data.get("confidence", 0.5))
            confidence = min(1.0, max(0.0, confidence))
            bid_amount = min(agent.budget, max(0.1, bid_amount))
            return Bid(
                agent_id=agent.id,
                role=role_name,
                amount=bid_amount,
                confidence=confidence,
            )
        except Exception:
            return None

    def run_auction(
        self,
        task: Task,
        pool: AgentPool,
        memory: Memory,
        needed_roles: Optional[list[str]] = None,
    ) -> Optional[tuple[AgentConfig, float]]:
        """
        Run an auction for a task.

        Returns (winning_agent, bid_amount) or None if no qualified bids.
        Saves auction record to memory.
        """
        # Gather candidate agents
        candidates: list[AgentConfig] = []
        if needed_roles:
            for role in needed_roles:
                candidates.extend(pool.get_available(role))
        else:
            candidates = pool.get_available()

        # Deduplicate
        seen: set[str] = set()
        unique_candidates: list[AgentConfig] = []
        for c in candidates:
            if c.id not in seen:
                seen.add(c.id)
                unique_candidates.append(c)

        bids: list[Bid] = []
        for agent in unique_candidates:
            bid = self._ask_bid(agent, task)
            if bid is not None and bid.confidence > 0.5:
                bids.append(bid)

        winner_agent: Optional[AgentConfig] = None
        winning_bid: Optional[float] = None

        if bids:
            # Winner: lowest bid among qualified
            best_bid = min(bids, key=lambda b: b.amount)
            winner_agent = pool.get(best_bid.agent_id)
            winning_bid = best_bid.amount

        memory.save_auction(
            task_id=task.id,
            winner_agent_id=winner_agent.id if winner_agent else None,
            winning_bid=winning_bid,
            num_bidders=len(bids),
        )

        if winner_agent is not None and winning_bid is not None:
            return (winner_agent, winning_bid)
        return None
