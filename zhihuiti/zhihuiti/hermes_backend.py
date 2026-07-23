"""Optional Hermes Agent execution backend.

Hermes is loaded only when ``HERMES_ENABLED`` is set. Keeping the adapter
inside the package makes normal zhihuiti imports work when the optional
``hermes-agent`` distribution is absent.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.models import AgentState, Task

console = Console()

HERMES_ENABLED = os.environ.get("HERMES_ENABLED", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

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

MAX_HERMES_ITERATIONS = 30


class HermesBackend:
    """Adapter between zhihuiti agent execution and Hermes AIAgent."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self._model = model or os.environ.get(
            "HERMES_MODEL", "deepseek/deepseek-chat"
        )
        self._base_url = base_url or os.environ.get("HERMES_BASE_URL")
        self._api_key = os.environ.get("HERMES_API_KEY") or os.environ.get(
            "OPENROUTER_API_KEY"
        )
        self._available = False
        self._agent_class: Any = None

        if not HERMES_ENABLED:
            return
        try:
            from run_agent import AIAgent
        except ImportError:
            console.print(
                "[yellow]HERMES_ENABLED=1 but hermes-agent is not installed; "
                "falling back to the configured LLM.[/yellow]"
            )
        else:
            self._agent_class = AIAgent
            self._available = True
            console.print("[bold green]Hermes Agent backend loaded[/bold green]")

    @property
    def available(self) -> bool:
        return self._available

    def execute_task(
        self,
        agent: AgentState,
        task: Task,
        system_prompt: str,
    ) -> dict[str, Any]:
        if not self._available:
            raise RuntimeError("Hermes backend not available")

        role = agent.config.role.value
        agent_kwargs: dict[str, Any] = {
            "model": agent.config.model or self._model,
            "enabled_toolsets": ROLE_TOOLSETS.get(role, ["file"]),
            "max_iterations": MAX_HERMES_ITERATIONS,
            "skip_context_files": True,
            "quiet_mode": True,
        }
        if self._base_url:
            agent_kwargs["base_url"] = self._base_url
        if self._api_key:
            agent_kwargs["api_key"] = self._api_key

        hermes = self._agent_class(**agent_kwargs)
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
                f"  [dim]Hermes: {api_calls} turns, {tool_calls} tools, "
                f"${cost:.4f}, {duration:.1f}s[/dim]"
            )
            return {
                "response": response,
                "tool_calls": tool_calls,
                "cost": cost,
                "api_calls": api_calls,
                "duration": duration,
            }
        except Exception as exc:
            duration = time.time() - start
            console.print(f"  [red]Hermes error: {exc}[/red]")
            return {
                "response": f"Error: {exc}",
                "tool_calls": 0,
                "cost": 0.0,
                "api_calls": 0,
                "duration": duration,
                "error": str(exc),
            }


_backend: HermesBackend | None = None


def get_hermes_backend() -> HermesBackend:
    """Return the process-wide optional backend adapter."""
    global _backend
    if _backend is None:
        _backend = HermesBackend()
    return _backend
