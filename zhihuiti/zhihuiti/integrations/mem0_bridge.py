"""mem0 Bridge — persistent evolving memory with conflict resolution.

Adds semantic long-term memory with automatic fact extraction.
Wraps mem0 (https://github.com/mem0ai/mem0) to give agents durable
memory that persists across sessions and evolves over time.

Integration points:
  - After task execution: add results and learnings to memory
  - Before task execution: search for relevant past context
  - Agent-scoped: each agent can have its own memory namespace
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class Mem0Bridge:
    """Bridge to mem0 for persistent evolving agent memory."""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._available: bool | None = None
        self._client: Any = None

    def is_available(self) -> bool:
        """Check if mem0 is installed and accessible."""
        if self._available is not None:
            return self._available
        try:
            from mem0 import Memory  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def _get_client(self) -> Any:
        """Lazily initialize the mem0 Memory client."""
        if self._client is not None:
            return self._client
        if not self.is_available():
            return None
        try:
            from mem0 import Memory
            self._client = Memory.from_config(self._config) if self._config else Memory()
            return self._client
        except Exception as e:
            logger.warning("mem0 client init failed: %s", e)
            self._available = False
            return None

    def add(self, content: str, agent_id: str | None = None, metadata: dict | None = None) -> None:
        """Add a memory entry, optionally scoped to an agent.

        Args:
            content: Text content to store (fact, observation, result).
            agent_id: Optional agent ID for namespace scoping.
            metadata: Optional metadata dict attached to the memory.
        """
        client = self._get_client()
        if client is None:
            return
        try:
            kwargs: dict[str, Any] = {}
            if agent_id:
                kwargs["agent_id"] = agent_id
            if metadata:
                kwargs["metadata"] = metadata
            client.add(content, **kwargs)
        except Exception as e:
            logger.warning("mem0 add failed: %s", e)

    def search(self, query: str, agent_id: str | None = None, limit: int = 5) -> list[dict]:
        """Semantic search across stored memories.

        Args:
            query: Natural language search query.
            agent_id: Optional agent scope filter.
            limit: Maximum results to return.

        Returns:
            List of memory dicts with 'text', 'score', and 'metadata' keys.
        """
        client = self._get_client()
        if client is None:
            return []
        try:
            kwargs: dict[str, Any] = {"limit": limit}
            if agent_id:
                kwargs["agent_id"] = agent_id
            results = client.search(query, **kwargs)
            if isinstance(results, dict):
                return results.get("results", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.warning("mem0 search failed: %s", e)
            return []

    def get_agent_memories(self, agent_id: str, limit: int = 20) -> list[dict]:
        """Retrieve all memories for a specific agent.

        Args:
            agent_id: The agent whose memories to retrieve.
            limit: Maximum memories to return.

        Returns:
            List of memory dicts.
        """
        client = self._get_client()
        if client is None:
            return []
        try:
            results = client.get_all(agent_id=agent_id, limit=limit)
            if isinstance(results, dict):
                return results.get("results", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.warning("mem0 get_agent_memories failed: %s", e)
            return []

    def get_all(self, limit: int = 100) -> list[dict]:
        """Retrieve all stored memories across all agents.

        Args:
            limit: Maximum memories to return.

        Returns:
            List of memory dicts.
        """
        client = self._get_client()
        if client is None:
            return []
        try:
            results = client.get_all(limit=limit)
            if isinstance(results, dict):
                return results.get("results", [])
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.warning("mem0 get_all failed: %s", e)
            return []


# Singleton for lazy initialization
_bridge: Mem0Bridge | None = None


def get_bridge(config: dict[str, Any] | None = None) -> Mem0Bridge:
    """Get or create the global mem0 bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = Mem0Bridge(config=config)
    return _bridge
