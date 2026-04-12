"""A2A Bridge — agent-to-agent interoperability protocol.

Exposes zhihuiti agents via Google's Agent-to-Agent (A2A) standard
(https://github.com/google/A2A) so external systems can discover,
communicate with, and delegate tasks to zhihuiti agents.

Integration points:
  - Register zhihuiti agents as A2A-discoverable services
  - Discover external A2A agents for task delegation
  - Send/receive tasks using the A2A task lifecycle
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class A2ABridge:
    """Bridge to Google A2A protocol for agent interoperability."""

    def __init__(self, host: str = "localhost", port: int = 5001):
        self._host = host
        self._port = port
        self._available: bool | None = None
        self._registered_agents: dict[str, dict] = {}
        self._server: Any = None

    def is_available(self) -> bool:
        """Check if A2A library is installed and accessible."""
        if self._available is not None:
            return self._available
        try:
            import a2a  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: list[str],
    ) -> None:
        """Register a zhihuiti agent as A2A-discoverable.

        Creates an Agent Card for the agent that external systems
        can discover via the A2A protocol.

        Args:
            agent_id: Unique agent identifier.
            name: Human-readable agent name.
            role: Agent role (e.g., 'coder', 'researcher').
            capabilities: List of capability strings the agent supports.
        """
        if not self.is_available():
            return
        try:
            card = {
                "id": agent_id,
                "name": name,
                "role": role,
                "capabilities": capabilities,
                "url": f"http://{self._host}:{self._port}/agents/{agent_id}",
                "protocol": "a2a/1.0",
            }
            self._registered_agents[agent_id] = card
            logger.info("A2A agent registered: %s (%s)", name, agent_id[:8])
        except Exception as e:
            logger.warning("A2A register_agent failed: %s", e)

    def discover_agents(self, capability_filter: str | None = None) -> list[dict]:
        """Discover available A2A agents, optionally filtered by capability.

        Args:
            capability_filter: If provided, only return agents that list
                               this capability.

        Returns:
            List of Agent Card dicts.
        """
        if not self.is_available():
            return []
        try:
            import a2a
            # Try A2A discovery if client supports it
            if hasattr(a2a, "discover"):
                agents = a2a.discover(host=self._host, port=self._port)
                if capability_filter and isinstance(agents, list):
                    agents = [
                        a for a in agents
                        if capability_filter in a.get("capabilities", [])
                    ]
                return agents if isinstance(agents, list) else []

            # Fallback: return locally registered agents
            agents = list(self._registered_agents.values())
            if capability_filter:
                agents = [
                    a for a in agents
                    if capability_filter in a.get("capabilities", [])
                ]
            return agents
        except Exception as e:
            logger.warning("A2A discover_agents failed: %s", e)
            return []

    def send_task(self, target_agent: str, task_description: str) -> dict:
        """Send a task to a target A2A agent.

        Args:
            target_agent: Agent ID or URL of the target agent.
            task_description: Natural language task description.

        Returns:
            Task status dict with keys: 'task_id', 'status', 'result'.
            Returns empty dict on failure.
        """
        if not self.is_available():
            return {}
        try:
            import a2a
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "target": target_agent,
                "description": task_description,
                "status": "submitted",
            }
            if hasattr(a2a, "Client"):
                client = a2a.Client(base_url=f"http://{self._host}:{self._port}")
                result = client.send_task(task)
                return result if isinstance(result, dict) else {"task_id": task_id, "status": "submitted"}
            return task
        except Exception as e:
            logger.warning("A2A send_task failed: %s", e)
            return {}

    def receive_task(self) -> dict | None:
        """Check for incoming tasks from external A2A agents.

        Returns:
            Task dict if a task is pending, None otherwise.
        """
        if not self.is_available():
            return None
        try:
            import a2a
            if hasattr(a2a, "Server") and self._server is not None:
                task = self._server.receive()
                return task if isinstance(task, dict) else None
            return None
        except Exception as e:
            logger.warning("A2A receive_task failed: %s", e)
            return None

    def get_agent_card(self, agent_id: str) -> dict:
        """Get the A2A Agent Card for a registered agent.

        Args:
            agent_id: The agent whose card to retrieve.

        Returns:
            Agent Card dict, or empty dict if not found.
        """
        return self._registered_agents.get(agent_id, {})


# Singleton for lazy initialization
_bridge: A2ABridge | None = None


def get_bridge(host: str = "localhost", port: int = 5001) -> A2ABridge:
    """Get or create the global A2A bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = A2ABridge(host=host, port=port)
    return _bridge
