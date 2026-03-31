"""K-Dense BYOK ↔ zhihuiti bridge — drop this into k-dense-byok to connect Kady to zhihuiti.

This file provides two integration modes:

1. MCP Toolset (recommended) — add to kady_agent/mcps.py:
     from kady_bridge import zhihuiti_mcp
     all_mcps.append(zhihuiti_mcp)

2. ADK FunctionTool — add to kady_agent/agent.py tools list:
     from kady_bridge import delegate_to_zhihuiti
     tools=[delegate_to_zhihuiti, ...]

Both modes let Kady delegate complex multi-agent tasks to zhihuiti's
orchestration system (DAG decomposition, agent auctions, 3-layer scoring).

Setup:
  1. Install zhihuiti: pip install -e /path/to/zhihuiti
  2. Copy this file into your k-dense-byok project root
  3. Choose integration mode (MCP or FunctionTool) and wire it in
  4. Set OPENROUTER_API_KEY (shared between both systems)
"""

from __future__ import annotations

import json
import os
import sys

# ---------------------------------------------------------------------------
# Mode 1: MCP Toolset — zhihuiti runs as a subprocess MCP server
# ---------------------------------------------------------------------------

try:
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StdioConnectionParams,
        StdioServerParameters,
    )

    # Path to zhihuiti's MCP server module
    _zhihuiti_cmd = sys.executable  # Use same Python interpreter
    _zhihuiti_args = ["-m", "zhihuiti.mcp_server"]

    # Environment for the subprocess
    _env = {
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", ""),
        "ZHIHUITI_DB": os.getenv("ZHIHUITI_DB", ":memory:"),
        "ZHIHUITI_MODEL": os.getenv("ZHIHUITI_MODEL", ""),
        "PATH": os.environ.get("PATH", ""),
    }

    zhihuiti_mcp = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_zhihuiti_cmd,
                args=_zhihuiti_args,
                env=_env,
            ),
            timeout=300.0,  # Multi-agent execution can take time
        ),
    )

except ImportError:
    zhihuiti_mcp = None  # google.adk not installed — MCP mode unavailable


# ---------------------------------------------------------------------------
# Mode 2: Direct function tool — calls zhihuiti in-process
# ---------------------------------------------------------------------------

def delegate_to_zhihuiti(goal: str, role: str = "auto") -> str:
    """Delegate a complex task to zhihuiti's multi-agent orchestration system.

    zhihuiti decomposes the goal into subtasks, auctions them to specialized
    agents (researcher, analyst, coder, trader, etc.), executes in parallel
    waves, and scores results through 3-layer inspection.

    Args:
        goal: The goal or task to accomplish. Can be a complex multi-step
              objective like "research and compare top 3 cloud providers"
              or a focused task like "analyze this dataset for trends".
        role: Agent role hint. Use "auto" for automatic decomposition,
              or specify: researcher, analyst, coder, trader, strategist.

    Returns:
        Formatted results from the multi-agent execution including
        task outputs, scores, and agent performance metrics.
    """
    from zhihuiti.orchestrator import Orchestrator

    orch = Orchestrator(
        db_path=os.environ.get("ZHIHUITI_DB", ":memory:"),
        model=os.environ.get("ZHIHUITI_MODEL"),
    )

    if role != "auto" and role in ("researcher", "analyst", "coder", "trader", "strategist", "custom"):
        # Single-task mode: direct agent assignment
        from zhihuiti.agents import ROLE_MAP
        from zhihuiti.models import AgentRole, Task

        agent_role = ROLE_MAP.get(role, AgentRole.CUSTOM)
        config = orch.agent_manager.get_best_config(agent_role)
        agent = orch.agent_manager.spawn(role=agent_role, depth=0, config=config, budget=100.0)
        task = Task(description=goal, metadata={"requested_role": role})

        output = orch.agent_manager.execute_task(agent, task)
        score = orch.judge.score_task(task, agent)

        return f"[Agent: {role}, Score: {score:.2f}]\n{output}"

    # Full orchestration: decompose → auction → execute → judge
    result = orch.execute_goal(goal)

    # Format for Kady
    parts = []
    if isinstance(result, dict):
        for r in result.get("results", [result]):
            task_desc = r.get("task", "")[:100]
            score = r.get("score", 0)
            status = r.get("status", "")
            agent_role = r.get("role", "")
            parts.append(f"[{agent_role}, {status}, score={score:.2f}] {task_desc}")
    return "\n".join(parts) if parts else str(result)


# ---------------------------------------------------------------------------
# Mode 3: HTTP client — connect to a running zhihuiti API server
# ---------------------------------------------------------------------------

class ZhihuiTiClient:
    """HTTP client for a remote zhihuiti API server.

    Usage:
        client = ZhihuiTiClient("http://localhost:8377")
        result = client.execute_goal("research quantum computing trends")
    """

    def __init__(self, base_url: str = "http://localhost:8377"):
        self.base_url = base_url.rstrip("/")

    def execute_goal(self, goal: str, model: str | None = None) -> dict:
        """Submit a goal and poll until completion."""
        import httpx
        import time

        payload = {"goal": goal}
        if model:
            payload["model"] = model

        resp = httpx.post(f"{self.base_url}/api/goals", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        goal_id = data["id"]

        # Poll for completion
        for _ in range(120):  # Max 10 minutes
            time.sleep(5)
            status_resp = httpx.get(f"{self.base_url}/api/goals/{goal_id}", timeout=10)
            status_resp.raise_for_status()
            status = status_resp.json()
            if status["status"] in ("completed", "failed"):
                return status

        return {"status": "timeout", "id": goal_id}

    def execute_task(self, task: str, role: str = "custom") -> dict:
        """Execute a single task synchronously."""
        import httpx
        resp = httpx.post(
            f"{self.base_url}/api/tasks",
            json={"task": task, "role": role},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def list_agents(self) -> list[dict]:
        """List all agents."""
        import httpx
        resp = httpx.get(f"{self.base_url}/api/agents", timeout=10)
        resp.raise_for_status()
        return resp.json()["agents"]

    def status(self) -> dict:
        """Get system status."""
        import httpx
        resp = httpx.get(f"{self.base_url}/api/status", timeout=10)
        resp.raise_for_status()
        return resp.json()
