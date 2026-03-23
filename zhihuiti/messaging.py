"""Agent-to-agent messaging — broadcast findings to collaborators.

Agents within the same goal share a message board.  After each task
completes, the agent broadcasts a summary of its output.  Other agents
in subsequent waves pick up these messages as additional context,
enabling collaboration beyond the DAG's explicit dependency edges.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState

console = Console()


class MessageBoard:
    """Per-goal message board for agent-to-agent communication."""

    def __init__(self, memory: Memory):
        self.memory = memory

    def broadcast(self, agent: AgentState, output: str,
                  goal_id: str, max_len: int = 300) -> str:
        """Agent broadcasts a summary of its output to the goal's board."""
        msg_id = uuid.uuid4().hex[:12]
        summary = output[:max_len].replace("\n", " ")
        self.memory.save_message(
            msg_id=msg_id,
            sender_id=agent.id,
            content=summary,
            goal_id=goal_id,
        )
        console.print(
            f"  [dim]📨 {agent.config.role.value} {agent.id[:8]} broadcasted "
            f"({len(summary)} chars)[/dim]"
        )
        return msg_id

    def send(self, sender: AgentState, receiver_id: str,
             content: str, goal_id: str | None = None) -> str:
        """Direct message between two agents."""
        msg_id = uuid.uuid4().hex[:12]
        self.memory.save_message(
            msg_id=msg_id,
            sender_id=sender.id,
            receiver_id=receiver_id,
            content=content[:500],
            goal_id=goal_id,
        )
        return msg_id

    def collect_context(self, agent: AgentState,
                        goal_id: str, limit: int = 5) -> str:
        """Collect unread messages relevant to this agent as context text.

        Marks messages as read so they aren't injected twice.
        Returns a context string (empty if no messages).
        """
        msgs = self.memory.get_unread_messages(goal_id=goal_id, limit=limit)
        # Filter out messages the agent sent itself
        msgs = [m for m in msgs if m["sender_id"] != agent.id]
        if not msgs:
            return ""

        self.memory.mark_messages_read([m["id"] for m in msgs])

        lines = []
        for m in msgs:
            lines.append(f"[{m['sender_id'][:8]}]: {m['content'][:300]}")

        return "Findings from collaborating agents:\n" + "\n".join(lines)
