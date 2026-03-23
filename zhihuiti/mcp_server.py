"""MCP (Model Context Protocol) server — exposes zhihuiti as an MCP tool provider.

K-Dense BYOK and other ADK-based agents can connect to this server via stdio
or HTTP to delegate complex multi-agent tasks to zhihuiti's orchestrator.

Usage:
  # Stdio mode (for local MCP toolset integration)
  python -m zhihuiti.mcp_server

  # Or via CLI
  zhihuiti mcp-serve
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from typing import Any

# MCP protocol constants
JSONRPC_VERSION = "2.0"

# Lazy-initialized orchestrator
_orch = None
_orch_lock = threading.Lock()


def _get_orchestrator():
    """Lazy-init orchestrator on first tool call."""
    global _orch
    if _orch is None:
        with _orch_lock:
            if _orch is None:
                import os
                from zhihuiti.orchestrator import Orchestrator
                _orch = Orchestrator(
                    db_path=os.environ.get("ZHIHUITI_DB", ":memory:"),
                    model=os.environ.get("ZHIHUITI_MODEL"),
                    tools_enabled=os.environ.get("ZHIHUITI_TOOLS", "").lower() in ("1", "true"),
                )
    return _orch


# Tool definitions exposed via MCP
TOOLS = [
    {
        "name": "zhihuiti_execute_goal",
        "description": (
            "Execute a complex goal using zhihuiti's autonomous multi-agent system. "
            "The goal is decomposed into subtasks, auctioned to specialized agents "
            "(researcher, analyst, coder, trader, etc.), executed in parallel waves, "
            "and scored through 3-layer inspection. Best for multi-step research, "
            "analysis, and planning tasks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The goal to accomplish (e.g., 'research top 3 programming languages')",
                },
                "model": {
                    "type": "string",
                    "description": "Optional LLM model override (e.g., 'anthropic/claude-sonnet-4')",
                },
            },
            "required": ["goal"],
        },
    },
    {
        "name": "zhihuiti_execute_task",
        "description": (
            "Execute a single focused task with a specialized agent. "
            "No DAG decomposition — directly spawns one agent of the requested role. "
            "Roles: researcher, analyst, coder, trader, strategist, custom."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task description",
                },
                "role": {
                    "type": "string",
                    "description": "Agent role: researcher, analyst, coder, trader, strategist, custom",
                    "default": "custom",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "zhihuiti_list_agents",
        "description": "List all agents in the zhihuiti system with their scores, budgets, and roles.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "zhihuiti_system_status",
        "description": "Get zhihuiti system health: economy, agent count, memory stats.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _handle_tool_call(name: str, arguments: dict) -> dict:
    """Execute a tool and return the result."""
    orch = _get_orchestrator()

    if name == "zhihuiti_execute_goal":
        goal = arguments["goal"]
        model = arguments.get("model")
        if model:
            orch.llm.model = model
        result = orch.execute_goal(goal)
        # Format results for readability
        summary_parts = []
        for r in result.get("results", [result] if isinstance(result, dict) else []):
            task_desc = r.get("task", "unknown")[:80]
            score = r.get("score", 0)
            status = r.get("status", "unknown")
            summary_parts.append(f"- [{status}] {task_desc} (score: {score:.2f})")
        return {
            "content": [{"type": "text", "text": "\n".join(summary_parts) if summary_parts else json.dumps(result, default=str)}],
        }

    elif name == "zhihuiti_execute_task":
        task_text = arguments["task"]
        role_name = arguments.get("role", "custom")

        from zhihuiti.agents import ROLE_MAP
        from zhihuiti.models import AgentRole, Task

        role = ROLE_MAP.get(role_name, AgentRole.CUSTOM)
        config = orch.agent_manager.get_best_config(role)
        agent = orch.agent_manager.spawn(role=role, depth=0, config=config, budget=100.0)
        task = Task(description=task_text, metadata={"requested_role": role_name})

        output = orch.agent_manager.execute_task(agent, task)
        score = orch.judge.score_task(task, agent)

        return {
            "content": [{"type": "text", "text": f"[{role_name}, score={score:.2f}]\n{output}"}],
        }

    elif name == "zhihuiti_list_agents":
        agents = []
        for agent in orch.agent_manager.agents.values():
            agents.append({
                "id": agent.id,
                "name": getattr(agent, "name", agent.id[:8]),
                "role": agent.role.value,
                "alive": agent.alive,
                "budget": round(agent.budget, 2),
                "avg_score": round(sum(agent.scores) / len(agent.scores), 3) if agent.scores else 0,
            })
        return {
            "content": [{"type": "text", "text": json.dumps(agents, indent=2)}],
        }

    elif name == "zhihuiti_system_status":
        from zhihuiti.dashboard import _gather_data
        data = _gather_data(orch)
        status = {
            "backend": orch.llm._backend,
            "model": orch.llm.model,
            "agent_count": len(data.get("agents", [])),
            "economy": data.get("economy", {}),
        }
        return {
            "content": [{"type": "text", "text": json.dumps(status, indent=2)}],
        }

    else:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }


def _send(msg: dict):
    """Write a JSON-RPC message to stdout."""
    raw = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(raw)}\r\n\r\n{raw}")
    sys.stdout.flush()


def _read_message() -> dict | None:
    """Read a JSON-RPC message from stdin (Content-Length framing)."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.strip()
        if line == "":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        return None

    body = sys.stdin.read(content_length)
    return json.loads(body)


def _handle_request(msg: dict) -> dict | None:
    """Handle a JSON-RPC request and return a response."""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "zhihuiti",
                    "version": "0.1.0",
                },
            },
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    elif method == "tools/list":
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": {"tools": TOOLS},
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = _handle_tool_call(tool_name, arguments)
        except Exception as e:
            result = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "result": result,
        }

    elif method == "ping":
        return {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "result": {}}

    else:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def main():
    """Run the MCP server on stdio."""
    import sys as _sys
    _sys.stderr.write("zhihuiti MCP server starting (stdio mode)...\n")

    while True:
        msg = _read_message()
        if msg is None:
            break

        response = _handle_request(msg)
        if response is not None:
            _send(response)


if __name__ == "__main__":
    main()
