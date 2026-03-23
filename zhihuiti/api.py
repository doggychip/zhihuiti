"""HTTP API server — exposes zhihuiti orchestrator as a backend service.

Designed for integration with K-Dense BYOK and other agent frameworks.
Runs on port 8377 (慧体) by default.

Endpoints:
  POST /api/goals          — submit a goal for multi-agent execution
  GET  /api/goals/:id      — poll goal status and results
  GET  /api/agents         — list all agents with scores/budgets
  GET  /api/status         — system health and economy snapshot
  POST /api/tasks          — submit a single task (no decomposition)
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from rich.console import Console

console = Console()

# In-memory store for async goal execution
_goals: dict[str, dict] = {}
_goals_lock = threading.Lock()


def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode())


def _read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw)


def create_api_handler(orch):
    """Create a request handler class bound to the given Orchestrator instance."""

    class ZhihuiTiAPIHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress default logging

        def do_OPTIONS(self):
            _json_response(self, {})

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            if path == "/api/status":
                self._handle_status()
            elif path == "/api/agents":
                self._handle_list_agents()
            elif path.startswith("/api/goals/"):
                goal_id = path.split("/")[-1]
                self._handle_get_goal(goal_id)
            elif path == "/health":
                _json_response(self, {"status": "ok", "service": "zhihuiti"})
            else:
                _json_response(self, {"error": "not found"}, 404)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            if path == "/api/goals":
                self._handle_create_goal()
            elif path == "/api/tasks":
                self._handle_single_task()
            else:
                _json_response(self, {"error": "not found"}, 404)

        def _handle_status(self):
            """System health and economy snapshot."""
            try:
                from zhihuiti.dashboard import _gather_data
                data = _gather_data(orch)
                _json_response(self, {
                    "status": "ok",
                    "backend": orch.llm._backend if hasattr(orch.llm, '_backend') else "unknown",
                    "model": orch.llm.model if hasattr(orch.llm, 'model') else "unknown",
                    "economy": data.get("economy", {}),
                    "agent_count": len(data.get("agents", [])),
                    "memory": data.get("memory", {}),
                })
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_list_agents(self):
            """List all agents with scores and budgets."""
            try:
                agents = []
                for agent in orch.agent_manager.agents.values():
                    agents.append({
                        "id": agent.id,
                        "name": getattr(agent, "name", agent.id[:8]),
                        "role": agent.role.value if hasattr(agent.role, 'value') else str(agent.role),
                        "alive": agent.alive,
                        "budget": round(agent.budget, 2),
                        "avg_score": round(sum(agent.scores) / len(agent.scores), 3) if agent.scores else 0,
                        "task_count": len(agent.task_ids),
                        "generation": getattr(agent, "generation", 0),
                    })
                _json_response(self, {"agents": agents, "count": len(agents)})
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_create_goal(self):
            """Submit a goal for async multi-agent execution."""
            try:
                body = _read_body(self)
                goal_text = body.get("goal", "").strip()
                if not goal_text:
                    _json_response(self, {"error": "goal is required"}, 400)
                    return

                goal_id = uuid.uuid4().hex[:12]
                model = body.get("model")
                tools = body.get("tools", False)

                with _goals_lock:
                    _goals[goal_id] = {
                        "id": goal_id,
                        "goal": goal_text,
                        "status": "running",
                        "result": None,
                        "error": None,
                    }

                def _execute():
                    try:
                        if model:
                            orch.llm.model = model
                        if tools:
                            orch.tools_enabled = True
                        result = orch.execute_goal(goal_text)
                        with _goals_lock:
                            _goals[goal_id]["status"] = "completed"
                            _goals[goal_id]["result"] = result
                    except Exception as e:
                        with _goals_lock:
                            _goals[goal_id]["status"] = "failed"
                            _goals[goal_id]["error"] = str(e)

                thread = threading.Thread(target=_execute, daemon=True)
                thread.start()

                _json_response(self, {
                    "id": goal_id,
                    "status": "running",
                    "message": f"Goal submitted: {goal_text[:80]}",
                }, 202)

            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_get_goal(self, goal_id: str):
            """Poll goal status and results."""
            with _goals_lock:
                goal = _goals.get(goal_id)
            if not goal:
                _json_response(self, {"error": "goal not found"}, 404)
                return
            _json_response(self, goal)

        def _handle_single_task(self):
            """Execute a single task synchronously (no DAG decomposition)."""
            try:
                body = _read_body(self)
                task_text = body.get("task", "").strip()
                if not task_text:
                    _json_response(self, {"error": "task is required"}, 400)
                    return

                role_name = body.get("role", "custom")
                from zhihuiti.agents import ROLE_MAP
                from zhihuiti.models import AgentRole, Task
                role = ROLE_MAP.get(role_name, AgentRole.CUSTOM)

                config = orch.agent_manager.get_best_config(role)
                agent = orch.agent_manager.spawn(role=role, depth=0, config=config, budget=100.0)
                task = Task(description=task_text, metadata={"requested_role": role_name})

                output = orch.agent_manager.execute_task(agent, task)
                score = orch.judge.score_task(task, agent)

                _json_response(self, {
                    "output": output,
                    "score": score,
                    "agent_id": agent.id,
                    "role": role.value,
                    "status": task.status.value,
                })

            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

    return ZhihuiTiAPIHandler


def serve(port: int = 8377, db_path: str = "zhihuiti.db", model: str | None = None,
          tools: bool = False):
    """Start the zhihuiti API server."""
    from zhihuiti.orchestrator import Orchestrator

    console.print(f"\n[bold]智慧体 API Server[/bold] starting on port {port}")
    orch = Orchestrator(db_path=db_path, model=model, tools_enabled=tools)

    handler = create_api_handler(orch)
    server = HTTPServer(("0.0.0.0", port), handler)

    console.print(f"[green]✓[/green] Listening on http://0.0.0.0:{port}")
    console.print(f"  POST /api/goals   — submit goal for multi-agent execution")
    console.print(f"  POST /api/tasks   — execute single task")
    console.print(f"  GET  /api/agents  — list agents")
    console.print(f"  GET  /api/status  — system health")
    console.print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]Shutting down...[/dim]")
        server.shutdown()
