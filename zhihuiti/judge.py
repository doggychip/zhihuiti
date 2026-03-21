"""Judge system for scoring agents and tasks."""
from __future__ import annotations

import os
import re
from typing import Optional

from .economy import Economy
from .memory import Memory
from .models import AgentConfig, Task

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


MODEL = "claude-haiku-4-5-20251001"

CULL_THRESHOLD = 0.3
PROMOTE_THRESHOLD = 0.8
PROMOTE_BUDGET_BONUS = 50.0
CULL_PENALTY = 10.0


def _get_client() -> Optional[object]:
    if not _ANTHROPIC_AVAILABLE:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


class Judge:
    def __init__(self):
        self._client = _get_client()

    def _call_claude(self, prompt: str) -> str:
        if self._client is None:
            return "0.5"
        try:
            message = self._client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=(
                    "You are an impartial judge evaluating AI agent outputs. "
                    "Be concise and precise."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception:
            return "0.5"

    def score(self, task: Task, result: str) -> float:
        """Ask Claude to score result 0.0-1.0."""
        prompt = (
            f"Task: {task.description}\n\n"
            f"Result: {result}\n\n"
            "Score this result on a scale from 0.0 to 1.0, where:\n"
            "  0.0 = completely wrong, unhelpful, or empty\n"
            "  0.5 = partially correct or adequate\n"
            "  1.0 = excellent, comprehensive, and accurate\n\n"
            "Reply with ONLY a decimal number between 0.0 and 1.0. Nothing else."
        )
        raw = self._call_claude(prompt).strip()
        # Extract first float-like value
        match = re.search(r"\d+\.?\d*", raw)
        if match:
            val = float(match.group())
            return min(1.0, max(0.0, val))
        return 0.5

    def should_cull(self, agent: AgentConfig) -> bool:
        return agent.score < CULL_THRESHOLD

    def should_promote(self, agent: AgentConfig) -> bool:
        return agent.score > PROMOTE_THRESHOLD

    def cull(self, agent_id: str, memory: Memory, economy: Economy) -> None:
        """Mark agent as culled and burn its remaining tokens."""
        agent = memory.get_agent(agent_id)
        if agent is None:
            return
        balance = economy.get_agent_balance(agent_id)
        economy.burn_agent(agent_id, balance)
        memory.update_agent_status(agent_id, "culled")
        memory.update_agent_budget(agent_id, 0.0)

    def promote(self, agent_id: str, memory: Memory, economy: Economy) -> None:
        """Reward high-performing agent with extra budget."""
        agent = memory.get_agent(agent_id)
        if agent is None:
            return
        new_budget = agent.budget + PROMOTE_BUDGET_BONUS
        economy.pay_task_reward(agent_id, score=1.0, base=PROMOTE_BUDGET_BONUS)
        memory.update_agent_budget(agent_id, new_budget)
