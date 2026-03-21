"""Agent class wrapping Anthropic API calls."""
from __future__ import annotations

import json
import os
from typing import Optional

from .economy import Economy
from .memory import Memory
from .models import AgentConfig, AgentRole, Task

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


MODEL = "claude-haiku-4-5-20251001"

ROLE_MAP: dict[str, AgentRole] = {r.value: r for r in AgentRole}

ROLE_DESCRIPTIONS: dict[str, str] = {
    AgentRole.orchestrator.value: "You are an orchestrator agent. You decompose complex goals into subtasks and coordinate other agents.",
    AgentRole.researcher.value: "You are a researcher agent. You gather information, synthesize knowledge, and produce detailed research summaries.",
    AgentRole.analyst.value: "You are an analyst agent. You analyze data, identify patterns, and provide insights.",
    AgentRole.coder.value: "You are a coder agent. You write clean, working code and explain technical implementations.",
    AgentRole.trader.value: "You are a trader agent. You analyze markets, evaluate opportunities, and make strategic trading decisions.",
    AgentRole.judge.value: "You are a judge agent. You evaluate work quality, assign scores, and provide constructive feedback.",
    AgentRole.synthesizer.value: "You are a synthesizer agent. You combine multiple sources of information into coherent, comprehensive outputs.",
}

TASK_COST = 5.0  # tokens per task execution


def _get_client() -> Optional[object]:
    if not _ANTHROPIC_AVAILABLE:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


class Agent:
    def __init__(self, config: AgentConfig, memory: Memory, economy: Economy):
        self.config = config
        self._memory = memory
        self._economy = economy
        self._client = _get_client()

    def _call_claude(self, system: str, user: str) -> str:
        """Make a single Claude API call. Returns empty string on failure."""
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                return "[ERROR: ANTHROPIC_API_KEY not set. Please export your API key.]"
            if not _ANTHROPIC_AVAILABLE:
                return "[ERROR: anthropic package not installed. Run: pip install anthropic]"
        try:
            message = self._client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return message.content[0].text
        except Exception as exc:
            return f"[API ERROR: {exc}]"

    def _build_system_prompt(self) -> str:
        role_desc = ROLE_DESCRIPTIONS.get(
            self.config.role.value if isinstance(self.config.role, AgentRole) else self.config.role,
            "You are a helpful agent.",
        )
        spec = f" Your specialization: {self.config.specialization}." if self.config.specialization else ""
        return (
            f"{role_desc}{spec}\n\n"
            f"You are agent {self.config.id} (generation {self.config.generation}), "
            f"budget: {self.config.budget:.1f} tokens.\n\n"
            "You may respond with plain text to answer directly, OR with JSON to delegate:\n"
            '{"action": "delegate", "subtasks": [{"description": "...", "role": "researcher"}, ...]}\n\n'
            "Only delegate when the task genuinely benefits from specialization. "
            "Available roles: orchestrator, researcher, analyst, coder, trader, judge, synthesizer."
        )

    def execute(self, task: Task, depth: int = 0, max_depth: int = 3) -> str:
        """Execute a task, potentially delegating to sub-agents."""
        # Update task status
        task.status = "running"
        task.assigned_agent_id = self.config.id
        self._memory.save_task(task)

        # Deduct task cost
        self._economy.charge_task(self.config.id, TASK_COST)

        system = self._build_system_prompt()
        response = self._call_claude(system, task.description)

        # Try to parse delegation response
        if depth < max_depth and response.strip().startswith("{"):
            try:
                data = json.loads(response.strip())
                if data.get("action") == "delegate" and data.get("subtasks"):
                    return self._delegate(task, data["subtasks"], depth, max_depth)
            except (json.JSONDecodeError, KeyError):
                pass  # Not valid delegation JSON — treat as plain text

        # Plain text result
        task.status = "done"
        task.result = response
        self._memory.save_task(task)
        return response

    def _delegate(self, parent_task: Task, subtask_specs: list[dict], depth: int, max_depth: int) -> str:
        """Spawn sub-agents for each subtask, collect results, synthesize."""
        results: list[str] = []

        for spec in subtask_specs:
            sub_desc = spec.get("description", "")
            sub_role_name = spec.get("role", "researcher")
            sub_role = ROLE_MAP.get(sub_role_name, AgentRole.researcher)

            # Spawn minimal sub-agent (no economy charge for depth spawns)
            sub_config = AgentConfig(
                role=sub_role,
                generation=self.config.generation + 1,
                parent_ids=[self.config.id],
                budget=self.config.budget * 0.3,
                score=0.5,
                lineage=[self.config.id] + self.config.lineage[:6],
                specialization=f"subtask for {parent_task.id}",
            )
            sub_task = Task(description=sub_desc)
            self._memory.save_task(sub_task)

            sub_agent = Agent(sub_config, self._memory, self._economy)
            result = sub_agent.execute(sub_task, depth=depth + 1, max_depth=max_depth)
            results.append(f"[{sub_role_name}] {result}")

        # Synthesize
        combined = "\n\n".join(results)
        synth_prompt = (
            f"Original task: {parent_task.description}\n\n"
            f"Sub-agent results:\n{combined}\n\n"
            "Synthesize these results into a coherent, comprehensive answer."
        )
        synthesis = self._call_claude(self._build_system_prompt(), synth_prompt)

        parent_task.status = "done"
        parent_task.result = synthesis
        self._memory.save_task(parent_task)
        return synthesis
