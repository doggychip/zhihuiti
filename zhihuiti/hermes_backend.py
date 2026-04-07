"""Hermes Agent backend — uses NousResearch/hermes-agent as the execution engine.

When enabled, zhihuiti agents are backed by full Hermes AIAgent instances
with tool use, persistent memory, and skill learning. The orchestration
layer (auctions, economy, breeding, inspection) stays in zhihuiti.

Requires: pip install hermes-agent  (or clone + pip install -e .)
Enable:   HERMES_ENABLED=1
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.models import AgentRole, AgentState, Task

console = Console()

# ─── Feature flag ────────────────────────────────────────
HERMES_ENABLED = os.environ.get("HERMES_ENABLED", "").strip() in ("1", "true", "yes")

# ─── Role → Hermes toolset mapping ──────────────────────
ROLE_TOOLSETS: dict[str, list[str]] = {
    "researcher": ["web", "file"],
    "analyst": ["web", "file", "terminal"],
    "coder": ["file", "terminal"],
    "trader": ["web", "terminal"],
    "alphaarena_trader": ["web", "terminal"],
    "coordinator": ["file", "memory"],
    "auditor": ["file"],
    "strategist": ["web", "file"],
    "causal_reasoner": ["web", "file"],
    "judge": [],
    "orchestrator": [],
    "custom": ["web", "file"],
}

# Max tool iterations per task (prevents runaway)
MAX_HERMES_ITERATIONS = 30


class HermesBackend:
    """Adapter between zhihuiti agent execution and Hermes AIAgent."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self._model = model or os.environ.get("HERMES_MODEL", "deepseek/deepseek-chat")
        self._base_url = base_url or os.environ.get("HERMES_BASE_URL")
        self._api_key = os.environ.get("HERMES_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        self._available = False
        self._AIAgent = None

        if not HERMES_ENABLED:
            return

        try:
            from run_agent import AIAgent
            self._AIAgent = AIAgent
            self._available = True
            console.print("[bold green]✓[/bold green] Hermes Agent backend loaded")
        except ImportError:
            console.print(
                "[yellow]⚠ HERMES_ENABLED=1 but hermes-agent not installed. "
                "Falling back to raw LLM.[/yellow]"
            )

    @property
    def available(self) -> bool:
        return self._available

    def execute_task(
        self,
        agent: AgentState,
        task: Task,
        system_prompt: str,
    ) -> dict:
        """Execute a task using a Hermes AIAgent instance.

        Returns:
            dict with keys:
                - response: str (the agent's final output)
                - tool_calls: int (number of tool calls made)
                - cost: float (estimated USD cost)
                - api_calls: int (number of LLM turns)
                - duration: float (seconds)
        """
        if not self._available:
            raise RuntimeError("Hermes backend not available")

        role = agent.config.role.value
        toolsets = ROLE_TOOLSETS.get(role, ["file"])

        # Build Hermes agent instance
        agent_kwargs = {
            "model": agent.config.model or self._model,
            "enabled_toolsets": toolsets,
            "max_iterations": MAX_HERMES_ITERATIONS,
            "skip_context_files": True,  # zhihuiti manages its own prompts
            "quiet_mode": True,
        }
        if self._base_url:
            agent_kwargs["base_url"] = self._base_url
        if self._api_key:
            agent_kwargs["api_key"] = self._api_key

        hermes = self._AIAgent(**agent_kwargs)

        start = time.time()
        try:
            result = hermes.run_conversation(
                user_message=task.description,
                system_message=system_prompt,
                task_id=task.id,
            )

            duration = time.time() - start
            response = result.get("final_response", "")
            tool_calls = result.get("tool_calls_count", 0)
            cost = result.get("cost", 0.0)
            api_calls = result.get("api_calls", 0)

            console.print(
                f"  [dim]🧠 Hermes: {api_calls} turns, "
                f"{tool_calls} tools, ${cost:.4f}, {duration:.1f}s[/dim]"
            )

            return {
                "response": response,
                "tool_calls": tool_calls,
                "cost": cost,
                "api_calls": api_calls,
                "duration": duration,
            }

        except Exception as e:
            duration = time.time() - start
            console.print(f"  [red]✗ Hermes error: {e}[/red]")
            return {
                "response": f"Error: {e}",
                "tool_calls": 0,
                "cost": 0.0,
                "api_calls": 0,
                "duration": duration,
                "error": str(e),
            }


# Singleton instance
_backend: HermesBackend | None = None


def get_hermes_backend() -> HermesBackend:
    """Get or create the Hermes backend singleton."""
    global _backend
    if _backend is None:
        _backend = HermesBackend()
    return _backend
