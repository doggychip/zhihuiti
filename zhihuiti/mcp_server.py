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
    # ── Theory Intelligence tools ───────────────────────────────
    {
        "name": "zhihuiti_find_analogies",
        "description": (
            "Find cross-domain structural analogies for a theory. "
            "Given a theory ID (e.g., 'replicator_dynamics', 'bellman_equation', 'sir_model'), "
            "returns ranked analogous theories from other domains with collision scores, "
            "shared patterns, bridging operators, and interpretations. "
            "Use this to discover unexpected connections between fields."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "theory_id": {
                    "type": "string",
                    "description": "Theory ID (e.g., 'bellman_equation', 'free_energy_principle', 'nash_equilibrium_econ')",
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum collision score filter (0.0-1.0, default 0.0)",
                    "default": 0.0,
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": ["theory_id"],
        },
    },
    {
        "name": "zhihuiti_get_bridges",
        "description": (
            "Get the detailed structural bridge between two specific theories. "
            "Returns shared patterns, operators, role-mappings, and a one-sentence "
            "interpretation of their deep connection. Returns null if no collision exists."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "theory_a": {
                    "type": "string",
                    "description": "First theory ID",
                },
                "theory_b": {
                    "type": "string",
                    "description": "Second theory ID",
                },
            },
            "required": ["theory_a", "theory_b"],
        },
    },
    {
        "name": "zhihuiti_suggest_patterns",
        "description": (
            "Given a problem description in natural language, suggest relevant "
            "structural patterns and cross-domain theories that may apply. "
            "Example: 'optimizing a multi-agent auction with budget constraints' → "
            "returns mechanism design, game theory, optimal transport analogies. "
            "Use this to get fresh perspectives on any problem."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Natural language description of the problem or concept",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                    "default": 5,
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "zhihuiti_search_theories",
        "description": (
            "Search the theory knowledge graph by keyword. Matches against theory names, "
            "domains, equations, and patterns. Returns theory IDs you can use with "
            "find_analogies and get_bridges."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'reinforcement learning', 'entropy', 'bifurcation')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "zhihuiti_graph_stats",
        "description": (
            "Get summary statistics about the theory knowledge graph: "
            "theory count, collision count, domains, strength distribution."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    # ── Crypto Oracle tools ────────────────────────────────────────
    {
        "name": "zhihuiti_crypto_diagnose",
        "description": (
            "Diagnose the current market state of a crypto instrument using structural "
            "pattern detection mapped to theories. Pulls live OHLCV candles, detects "
            "patterns (momentum, mean reversion, volatility clustering, fat tails, "
            "support/resistance, orderbook imbalance), classifies the market regime, "
            "and maps each finding to the most relevant theory from the 378-theory "
            "knowledge graph with cross-domain analogies. "
            "Returns: regime, detected patterns with strength scores, and theory details."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "instrument": {
                    "type": "string",
                    "description": "Instrument name (e.g., 'BTC_USDT', 'ETH_USDT')",
                    "default": "BTC_USDT",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Candle timeframe (e.g., '4h', '1h', '1D')",
                    "default": "4h",
                },
                "include_book": {
                    "type": "boolean",
                    "description": "Also analyze order book for microstructure patterns",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "zhihuiti_universal_diagnose",
        "description": (
            "Diagnose any time series using structural pattern detection mapped to "
            "domain-specific theories from the 378-theory knowledge graph. "
            "Detects momentum, mean reversion, volatility clustering, and fat tails "
            "in any numeric data. Domains: crypto, system_perf (server latency, error "
            "rates), social (cascades, virality), business (revenue, churn), scientific "
            "(sensor data, experiments). Returns regime classification, detected patterns, "
            "collision insights with cross-domain analogies, and actionable interpretations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Ordered numeric values (oldest first). Minimum 20 data points recommended.",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain for theory mapping: 'crypto', 'system_perf', 'social', 'business', 'scientific'",
                    "default": "scientific",
                    "enum": ["crypto", "system_perf", "social", "business", "scientific"],
                },
                "label": {
                    "type": "string",
                    "description": "Human-readable label (e.g., 'API latency (ms)', 'DAU count', 'temperature (K)')",
                    "default": "time series",
                },
            },
            "required": ["values"],
        },
    },
]


def _fetch_candles(instrument: str, timeframe: str) -> list[dict]:
    """Fetch OHLCV candles from Crypto.com public API."""
    try:
        import httpx
        # Crypto.com public API v2
        resp = httpx.get(
            "https://api.crypto.com/exchange/v1/public/get-candlestick",
            params={"instrument_name": instrument, "timeframe": timeframe},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("result", {}).get("data", data.get("data", []))
        if not raw:
            return []
        # Normalize keys
        candles = []
        for c in raw:
            candles.append({
                "open": c.get("o", c.get("open", 0)),
                "high": c.get("h", c.get("high", 0)),
                "low": c.get("l", c.get("low", 0)),
                "close": c.get("c", c.get("close", 0)),
                "volume": c.get("v", c.get("volume", 0)),
            })
        return candles
    except Exception:
        return []


def _fetch_book(instrument: str) -> dict | None:
    """Fetch order book from Crypto.com public API."""
    try:
        import httpx
        resp = httpx.get(
            "https://api.crypto.com/exchange/v1/public/get-book",
            params={"instrument_name": instrument, "depth": 20},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {}).get("data", [data.get("result", {})])
        if isinstance(result, list) and result:
            result = result[0]
        return {
            "bids": result.get("bids", []),
            "asks": result.get("asks", []),
        }
    except Exception:
        return None


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

    # ── Theory Intelligence tools ───────────────────────────────
    elif name == "zhihuiti_find_analogies":
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
        theory_id = arguments["theory_id"]
        if theory_id not in graph.theories:
            return {"content": [{"type": "text", "text": f"Unknown theory: {theory_id}. Use zhihuiti_search_theories to find valid IDs."}], "isError": True}
        analogies = graph.find_analogies(
            theory_id,
            min_score=arguments.get("min_score", 0.0),
            limit=arguments.get("limit", 10),
        )
        t = graph.theories[theory_id]
        header = f"Analogies for {t.get('name', theory_id)} ({t.get('domain', '')}):\n\n"
        return {"content": [{"type": "text", "text": header + json.dumps(analogies, indent=2, ensure_ascii=False)}]}

    elif name == "zhihuiti_get_bridges":
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
        bridge = graph.get_bridges(arguments["theory_a"], arguments["theory_b"])
        if bridge is None:
            return {"content": [{"type": "text", "text": f"No collision found between {arguments['theory_a']} and {arguments['theory_b']}."}]}
        return {"content": [{"type": "text", "text": json.dumps(bridge, indent=2, ensure_ascii=False)}]}

    elif name == "zhihuiti_suggest_patterns":
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
        results = graph.suggest_patterns(
            arguments["description"],
            limit=arguments.get("limit", 5),
        )
        return {"content": [{"type": "text", "text": json.dumps(results, indent=2, ensure_ascii=False)}]}

    elif name == "zhihuiti_search_theories":
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
        results = graph.search_theories(
            arguments["query"],
            limit=arguments.get("limit", 10),
        )
        # Compact output: id, name, domain
        compact = [{"id": r["id"], "name": r.get("name", ""), "domain": r.get("domain", "")} for r in results]
        return {"content": [{"type": "text", "text": json.dumps(compact, indent=2, ensure_ascii=False)}]}

    elif name == "zhihuiti_graph_stats":
        from zhihuiti.theory_intelligence import get_graph
        graph = get_graph()
        stats = graph.get_stats()
        return {"content": [{"type": "text", "text": json.dumps(stats, indent=2, ensure_ascii=False)}]}

    # ── Crypto Oracle tool ─────────────────────────────────────────
    elif name == "zhihuiti_crypto_diagnose":
        from zhihuiti.crypto_oracle import diagnose_market
        instrument = arguments.get("instrument", "BTC_USDT")
        timeframe = arguments.get("timeframe", "4h")
        include_book = arguments.get("include_book", False)

        # Fetch candle data via internal HTTP call to Crypto.com API
        candles = _fetch_candles(instrument, timeframe)
        if not candles:
            return {"content": [{"type": "text", "text": f"No candle data for {instrument} ({timeframe})"}], "isError": True}

        book = None
        if include_book:
            book = _fetch_book(instrument)

        diagnosis = diagnose_market(candles, instrument=instrument, book=book)
        return {"content": [{"type": "text", "text": json.dumps(diagnosis.to_dict(), indent=2, ensure_ascii=False)}]}

    # ── Universal Oracle tool ──────────────────────────────────────
    elif name == "zhihuiti_universal_diagnose":
        from zhihuiti.universal_oracle import diagnose
        values = arguments.get("values", [])
        domain = arguments.get("domain", "scientific")
        label = arguments.get("label", "time series")

        if not values or len(values) < 5:
            return {"content": [{"type": "text", "text": "Need at least 5 data points."}], "isError": True}

        result = diagnose(values, domain=domain, label=label)
        return {"content": [{"type": "text", "text": json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}]}

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
