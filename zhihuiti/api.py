"""HTTP API server — exposes zhihuiti orchestrator as a backend service.

Designed for integration with K-Dense BYOK, Big Brain, and other agent frameworks.
Runs on port 8377 (慧体) by default.

Endpoints:
  POST /api/goals                   — submit a goal for multi-agent execution
  GET  /api/goals/:id               — poll goal status and results
  GET  /api/agents                  — list all agents with scores/budgets
  GET  /api/status                  — system health and economy snapshot
  POST /api/tasks                   — submit a single task (no decomposition)

  Oracle endpoints:
  POST /api/oracle/diagnose         — universal time series diagnosis
  GET  /api/oracle/crypto/:instrument — live crypto diagnosis (fetches data)
  GET  /api/oracle/domains          — list available domain profiles
  GET  /api/oracle/theories/stats   — knowledge graph statistics
  GET  /api/oracle/theories/search  — search theories by keyword
  GET  /api/oracle/scan             — multi-pair market scan
  GET  /api/oracle/history/:instrument — regime history for an instrument
  GET  /api/oracle/transitions      — recent regime transitions
  GET  /api/oracle/summary          — current regime across all instruments
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

# Lazy-initialized regime history tracker
_history = None
_history_lock = threading.Lock()


def _get_history():
    global _history
    if _history is None:
        with _history_lock:
            if _history is None:
                from zhihuiti.scanner import RegimeHistory
                _history = RegimeHistory()
    return _history


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


def _fetch_crypto_candles(instrument: str, timeframe: str) -> list[dict]:
    """Fetch OHLCV candles from Crypto.com public API."""
    try:
        import httpx
        resp = httpx.get(
            "https://api.crypto.com/exchange/v1/public/get-candlestick",
            params={"instrument_name": instrument, "timeframe": timeframe},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("result", {}).get("data", data.get("data", []))
        return [
            {
                "open": c.get("o", c.get("open", 0)),
                "high": c.get("h", c.get("high", 0)),
                "low": c.get("l", c.get("low", 0)),
                "close": c.get("c", c.get("close", 0)),
                "volume": c.get("v", c.get("volume", 0)),
            }
            for c in raw
        ]
    except Exception:
        return []


def _fetch_crypto_book(instrument: str) -> dict | None:
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
        return {"bids": result.get("bids", []), "asks": result.get("asks", [])}
    except Exception:
        return None


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
            qs = parse_qs(parsed.query)

            if path == "/api/status":
                self._handle_status()
            elif path == "/api/agents":
                self._handle_list_agents()
            elif path.startswith("/api/goals/"):
                goal_id = path.split("/")[-1]
                self._handle_get_goal(goal_id)
            elif path.startswith("/api/oracle/crypto/"):
                instrument = path.split("/")[-1]
                timeframe = qs.get("timeframe", ["4h"])[0]
                include_book = qs.get("book", ["0"])[0] in ("1", "true")
                self._handle_oracle_crypto(instrument, timeframe, include_book)
            elif path == "/api/oracle/domains":
                self._handle_oracle_domains()
            elif path == "/api/oracle/theories/stats":
                self._handle_oracle_theory_stats()
            elif path == "/api/oracle/theories/search":
                query = qs.get("q", [""])[0]
                limit = int(qs.get("limit", ["10"])[0])
                self._handle_oracle_theory_search(query, limit)
            elif path == "/api/oracle/scan":
                timeframe = qs.get("timeframe", ["4h"])[0]
                pairs = qs.get("pairs", [None])[0]
                self._handle_oracle_scan(timeframe, pairs)
            elif path.startswith("/api/oracle/history/"):
                instrument = path.split("/")[-1]
                limit = int(qs.get("limit", ["50"])[0])
                self._handle_oracle_history(instrument, limit)
            elif path == "/api/oracle/transitions":
                instrument = qs.get("instrument", [None])[0]
                limit = int(qs.get("limit", ["20"])[0])
                self._handle_oracle_transitions(instrument, limit)
            elif path == "/api/oracle/summary":
                self._handle_oracle_summary()
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
            elif path == "/api/oracle/diagnose":
                self._handle_oracle_diagnose()
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

        # ── Oracle endpoints ──────────────────────────────────────

        def _handle_oracle_diagnose(self):
            """POST /api/oracle/diagnose — universal time series diagnosis.

            Body: {"values": [1.0, 2.0, ...], "domain": "system_perf", "label": "latency"}
            """
            try:
                body = _read_body(self)
                values = body.get("values", [])
                if not values or len(values) < 5:
                    _json_response(self, {"error": "need at least 5 data points in 'values'"}, 400)
                    return
                domain = body.get("domain", "scientific")
                label = body.get("label", "time series")

                from zhihuiti.universal_oracle import diagnose, DOMAINS
                if domain not in DOMAINS:
                    _json_response(self, {"error": f"unknown domain: {domain}", "available": list(DOMAINS.keys())}, 400)
                    return

                result = diagnose(values, domain=domain, label=label)
                _json_response(self, result.to_dict())
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_crypto(self, instrument: str, timeframe: str, include_book: bool):
            """GET /api/oracle/crypto/:instrument — live crypto diagnosis."""
            try:
                from zhihuiti.crypto_oracle import diagnose_market

                candles = _fetch_crypto_candles(instrument, timeframe)
                if not candles:
                    _json_response(self, {"error": f"no candle data for {instrument} ({timeframe})"}, 404)
                    return

                book = None
                if include_book:
                    book = _fetch_crypto_book(instrument)

                diagnosis = diagnose_market(candles, instrument=instrument, book=book)
                _json_response(self, diagnosis.to_dict())
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_domains(self):
            """GET /api/oracle/domains — list available domain profiles."""
            try:
                from zhihuiti.universal_oracle import DOMAINS
                domains = {}
                for key, profile in DOMAINS.items():
                    domains[key] = {
                        "name": profile.name,
                        "description": profile.description,
                        "pattern_count": len(profile.pattern_theories),
                        "regime_count": len(profile.regime_theories),
                    }
                _json_response(self, {"domains": domains})
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_theory_stats(self):
            """GET /api/oracle/theories/stats — knowledge graph statistics."""
            try:
                from zhihuiti.theory_intelligence import get_graph
                graph = get_graph()
                _json_response(self, graph.get_stats())
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_scan(self, timeframe: str, pairs: str | None):
            """GET /api/oracle/scan — scan multiple pairs, rank by signal."""
            try:
                from zhihuiti.scanner import scan_instruments, DEFAULT_PAIRS

                instruments = pairs.split(",") if pairs else DEFAULT_PAIRS
                results = scan_instruments(instruments=instruments, timeframe=timeframe)

                # Record to history and detect transitions
                history = _get_history()
                transitions = history.record_scan(results)

                _json_response(self, {
                    "results": [r.to_dict() for r in results],
                    "count": len(results),
                    "transitions": [t.to_dict() for t in transitions],
                })
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_history(self, instrument: str, limit: int):
            """GET /api/oracle/history/:instrument — regime history."""
            try:
                history = _get_history()
                snapshots = history.get_history(instrument, limit=limit)
                _json_response(self, {"instrument": instrument, "snapshots": snapshots, "count": len(snapshots)})
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_transitions(self, instrument: str | None, limit: int):
            """GET /api/oracle/transitions — recent regime transitions."""
            try:
                history = _get_history()
                transitions = history.get_transitions(instrument=instrument, limit=limit)
                _json_response(self, {"transitions": transitions, "count": len(transitions)})
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_summary(self):
            """GET /api/oracle/summary — current regime per instrument."""
            try:
                history = _get_history()
                summary = history.get_summary()
                _json_response(self, {"instruments": summary, "count": len(summary)})
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)

        def _handle_oracle_theory_search(self, query: str, limit: int):
            """GET /api/oracle/theories/search?q=keyword — search theories."""
            try:
                if not query:
                    _json_response(self, {"error": "query parameter 'q' is required"}, 400)
                    return
                from zhihuiti.theory_intelligence import get_graph
                graph = get_graph()
                results = graph.search_theories(query, limit=min(limit, 50))
                compact = [{"id": r["id"], "name": r.get("name", ""), "domain": r.get("domain", "")} for r in results]
                _json_response(self, {"results": compact, "count": len(compact)})
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

    console.print(f"[green]Listening on http://0.0.0.0:{port}[/green]")
    console.print(f"  POST /api/goals                    — submit goal")
    console.print(f"  POST /api/tasks                    — execute single task")
    console.print(f"  GET  /api/agents                   — list agents")
    console.print(f"  GET  /api/status                   — system health")
    console.print(f"  POST /api/oracle/diagnose           — universal time series diagnosis")
    console.print(f"  GET  /api/oracle/crypto/:instrument — live crypto diagnosis")
    console.print(f"  GET  /api/oracle/domains            — list domain profiles")
    console.print(f"  GET  /api/oracle/theories/stats     — knowledge graph stats")
    console.print(f"  GET  /api/oracle/theories/search    — search theories")
    console.print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]Shutting down...[/dim]")
        server.shutdown()
