"""MemPalace Bridge — semantic memory archival and retrieval for zhihuiti agents.

Integrates with MemPalace (https://github.com/milla-jovovich/mempalace) to give
agents access to semantic search over past conversations and task results.

MemPalace stores verbatim content in ChromaDB and organizes it into a
Wing → Room → Hall → Drawer hierarchy (the "memory palace" metaphor).

Integration points:
  - Before task execution: search MemPalace for relevant past context
  - After task execution: mine results into MemPalace for future retrieval
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from rich.console import Console

console = Console()

# Default palace path
DEFAULT_PALACE_PATH = os.path.expanduser("~/.mempalace")


class MemPalaceBridge:
    """Bridge to MemPalace for semantic memory archival and retrieval.

    Supports two modes:
    1. MCP mode: calls MemPalace MCP tools via stdio (preferred)
    2. Direct mode: imports mempalace Python package directly (fallback)
    """

    def __init__(self, palace_path: str | None = None, mode: str = "auto"):
        self.palace_path = palace_path or DEFAULT_PALACE_PATH
        self._mode = mode  # "auto", "mcp", "direct"
        self._available: bool | None = None

    def is_available(self) -> bool:
        """Check if MemPalace is installed and accessible."""
        if self._available is not None:
            return self._available

        # Try direct import first
        try:
            import mempalace  # noqa: F401
            self._available = True
            self._mode = "direct"
            return True
        except ImportError:
            pass

        # Try MCP server check
        try:
            result = subprocess.run(
                ["mempalace", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self._available = True
                self._mode = "mcp"
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        self._available = False
        return False

    # === Core Operations ===

    def search(self, query: str, limit: int = 3) -> list[dict]:
        """Semantic search across all stored memories.

        Returns relevant past context for agent task execution.
        """
        if not self.is_available():
            return []

        try:
            if self._mode == "direct":
                return self._search_direct(query, limit)
            return self._search_mcp(query, limit)
        except Exception as e:
            console.print(f"  [dim]MemPalace search failed: {e}[/dim]")
            return []

    def mine(
        self,
        content: str,
        wing: str = "zhihuiti",
        room: str = "tasks",
        metadata: dict | None = None,
    ) -> bool:
        """Store content in MemPalace for future semantic retrieval.

        Args:
            content: The text to archive (task description + result).
            wing: Top-level category (default: "zhihuiti").
            room: Sub-category (e.g., agent role or task domain).
            metadata: Optional metadata (agent_id, score, goal_id, etc.).
        """
        if not self.is_available():
            return False

        try:
            if self._mode == "direct":
                return self._mine_direct(content, wing, room, metadata)
            return self._mine_mcp(content, wing, room, metadata)
        except Exception as e:
            console.print(f"  [dim]MemPalace mine failed: {e}[/dim]")
            return False

    def get_context_for_task(self, task_description: str, agent_role: str) -> str:
        """Build context string from MemPalace search for injection into agent prompt."""
        results = self.search(f"{agent_role}: {task_description}", limit=3)
        if not results:
            return ""

        lines = ["Relevant past context (from MemPalace):"]
        for r in results:
            text = r.get("text", r.get("content", ""))[:300]
            score = r.get("relevance", r.get("score", ""))
            source = r.get("source", r.get("room", ""))
            entry = f"  - [{source}] {text}"
            if score:
                entry += f" (relevance: {score})"
            lines.append(entry)

        return "\n".join(lines)

    def archive_task_result(
        self,
        task_description: str,
        result: str,
        agent_role: str,
        score: float,
        agent_id: str = "",
        goal_id: str = "",
    ) -> bool:
        """Archive a completed task result for future retrieval."""
        content = (
            f"Task: {task_description}\n"
            f"Agent: {agent_role} ({agent_id[:8]})\n"
            f"Score: {score:.2f}\n"
            f"Result: {result[:1000]}"
        )
        metadata = {
            "agent_role": agent_role,
            "agent_id": agent_id,
            "score": score,
            "goal_id": goal_id,
        }
        return self.mine(
            content=content,
            wing="zhihuiti",
            room=agent_role,
            metadata=metadata,
        )

    # === Direct Mode (import mempalace) ===

    def _search_direct(self, query: str, limit: int) -> list[dict]:
        from mempalace.searcher import search_memories  # type: ignore

        results = search_memories(
            query=query,
            palace_path=self.palace_path,
            limit=limit,
        )
        return results if isinstance(results, list) else []

    def _mine_direct(
        self, content: str, wing: str, room: str, metadata: dict | None
    ) -> bool:
        from mempalace.miner import mine_content  # type: ignore

        mine_content(
            content=content,
            palace_path=self.palace_path,
            wing=wing,
            room=room,
            metadata=metadata or {},
        )
        return True

    # === MCP Mode (subprocess call) ===

    def _search_mcp(self, query: str, limit: int) -> list[dict]:
        result = self._call_mcp_tool("mempalace_search", {
            "query": query,
            "limit": limit,
        })
        if result and isinstance(result, list):
            return result
        if result and isinstance(result, dict):
            return result.get("results", [])
        return []

    def _mine_mcp(
        self, content: str, wing: str, room: str, metadata: dict | None
    ) -> bool:
        result = self._call_mcp_tool("mempalace_mine", {
            "content": content,
            "wing": wing,
            "room": room,
            "metadata": json.dumps(metadata or {}),
        })
        return result is not None

    def _call_mcp_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a MemPalace MCP tool via subprocess stdio."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        raw = json.dumps(request)
        message = f"Content-Length: {len(raw)}\r\n\r\n{raw}"

        try:
            result = subprocess.run(
                ["python", "-m", "mempalace.mcp_server"],
                input=message,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "PALACE_PATH": self.palace_path},
            )
            if result.returncode == 0 and result.stdout:
                # Parse Content-Length framed response
                body = result.stdout.split("\r\n\r\n", 1)[-1]
                response = json.loads(body)
                content = response.get("result", {}).get("content", [])
                if content and content[0].get("type") == "text":
                    return json.loads(content[0]["text"])
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        return None


# Singleton for lazy initialization
_bridge: MemPalaceBridge | None = None


def get_bridge() -> MemPalaceBridge:
    """Get or create the global MemPalace bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = MemPalaceBridge()
    return _bridge
