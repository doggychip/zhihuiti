"""Tests for the HTTP API server and MCP server."""

from __future__ import annotations

import json
import threading
import time
import pytest
from http.client import HTTPConnection
from unittest.mock import MagicMock

from zhihuiti.memory import Memory
from tests.conftest import make_stub_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUBTASK_LIST = [
    {"description": "Research the topic", "role": "researcher"},
    {"description": "Summarize findings", "role": "analyst"},
]

INSPECTION_PASS = {"score": 0.8, "reasoning": "good", "pass": True}


def _make_orchestrator():
    """Build an in-memory Orchestrator with stub LLM."""
    from zhihuiti.orchestrator import Orchestrator
    from zhihuiti.economy import Economy
    from zhihuiti.bloodline import Bloodline
    from zhihuiti.realms import RealmManager
    from zhihuiti.agents import AgentManager
    from zhihuiti.judge import Judge
    from zhihuiti.circuit_breaker import CircuitBreaker
    from zhihuiti.behavior import BehaviorDetector
    from zhihuiti.relationships import RelationshipGraph, LendingSystem
    from zhihuiti.arbitration import ArbitrationBureau
    from zhihuiti.market import TradingMarket
    from zhihuiti.futures import FuturesMarket
    from zhihuiti.factory import Factory
    from zhihuiti.bidding import BiddingHouse
    from zhihuiti.messaging import MessageBoard
    from zhihuiti.causal import CausalGraph, CausalReasoner, CausalValidator

    mem = Memory(":memory:")
    orch = Orchestrator.__new__(Orchestrator)

    stub = make_stub_llm(INSPECTION_PASS)
    orch.llm = stub
    orch.memory = mem
    orch.economy = Economy(mem)
    orch.bloodline = Bloodline(mem)
    orch.realm_manager = RealmManager(mem)
    orch.tools_enabled = False
    orch.agent_manager = AgentManager(stub, mem, orch.economy, orch.bloodline, orch.realm_manager)
    orch.judge = Judge(stub, mem, orch.agent_manager)
    orch.circuit_breaker = CircuitBreaker(mem, interactive=False)
    orch.behavior = BehaviorDetector(mem, stub)
    orch.rel_graph = RelationshipGraph(mem)
    orch.lending = LendingSystem(mem, orch.rel_graph)
    orch.arbitration = ArbitrationBureau(mem)
    orch.market = TradingMarket(mem)
    orch.futures = FuturesMarket(mem)
    orch.factory = Factory(llm=stub, memory=mem)
    orch.bidding = BiddingHouse(stub, mem, orch.economy)
    orch.messages = MessageBoard(mem)
    orch.causal_graph = CausalGraph()
    orch.causal_reasoner = CausalReasoner(stub, orch.causal_graph)
    orch.causal_validator = CausalValidator(stub, orch.causal_graph)
    orch.tasks = {}
    orch.max_workers = 1
    orch.max_retries = 0

    return orch


def _start_server(port: int):
    """Start the API server in a background thread and return the orchestrator."""
    from zhihuiti.api import create_api_handler
    from http.server import HTTPServer

    orch = _make_orchestrator()
    handler = create_api_handler(orch)
    server = HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)  # Let server bind
    return server, orch


# ---------------------------------------------------------------------------
# API handler tests
# ---------------------------------------------------------------------------

class TestAPIHandler:
    """Test the API request handler directly."""

    def test_create_handler(self):
        from zhihuiti.api import create_api_handler
        orch = _make_orchestrator()
        handler_class = create_api_handler(orch)
        assert handler_class is not None

    def test_json_response_helper(self):
        from zhihuiti.api import _json_response
        handler = MagicMock()
        handler.wfile = MagicMock()
        handler.wfile.write = MagicMock()
        _json_response(handler, {"test": True})
        handler.send_response.assert_called_once_with(200)
        handler.wfile.write.assert_called_once()

    def test_json_response_custom_status(self):
        from zhihuiti.api import _json_response
        handler = MagicMock()
        handler.wfile = MagicMock()
        _json_response(handler, {"error": "bad"}, 400)
        handler.send_response.assert_called_once_with(400)


class TestAPIServer:
    """Integration tests using a real HTTP server on a random port."""

    @pytest.fixture(autouse=True)
    def setup_server(self):
        import socket
        # Find a free port
        with socket.socket() as s:
            s.bind(("", 0))
            self.port = s.getsockname()[1]
        self.server, self.orch = _start_server(self.port)
        yield
        self.server.shutdown()

    def _get(self, path: str) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.port)
        conn.request("GET", path)
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return resp.status, data

    def _post(self, path: str, body: dict) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.port)
        payload = json.dumps(body)
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return resp.status, data

    def test_health(self):
        status, data = self._get("/health")
        assert status == 200
        assert data["status"] == "ok"
        assert data["service"] == "zhihuiti"

    def test_status(self):
        status, data = self._get("/api/status")
        assert status == 200
        assert data["status"] == "ok"
        assert "agent_count" in data

    def test_list_agents_empty(self):
        status, data = self._get("/api/agents")
        assert status == 200
        assert data["agents"] == []
        assert data["count"] == 0

    def test_create_goal(self):
        status, data = self._post("/api/goals", {"goal": "test goal"})
        assert status == 202
        assert "id" in data
        assert data["status"] == "running"

    def test_create_goal_empty(self):
        status, data = self._post("/api/goals", {"goal": ""})
        assert status == 400

    def test_get_goal_not_found(self):
        status, data = self._get("/api/goals/nonexistent")
        assert status == 404

    def test_create_and_poll_goal(self):
        status, data = self._post("/api/goals", {"goal": "test goal"})
        goal_id = data["id"]

        # Should be findable immediately
        status2, data2 = self._get(f"/api/goals/{goal_id}")
        assert status2 == 200
        assert data2["id"] == goal_id

    def test_single_task_missing_body(self):
        status, data = self._post("/api/tasks", {"task": ""})
        assert status == 400

    def test_not_found(self):
        status, data = self._get("/api/nonexistent")
        assert status == 404

    def test_options_cors(self):
        conn = HTTPConnection("127.0.0.1", self.port)
        conn.request("OPTIONS", "/api/status")
        resp = conn.getresponse()
        assert resp.status == 200
        conn.close()


# ---------------------------------------------------------------------------
# MCP server tests
# ---------------------------------------------------------------------------

class TestMCPServer:
    """Test MCP protocol message handling."""

    def test_tool_definitions(self):
        from zhihuiti.mcp_server import TOOLS
        names = [t["name"] for t in TOOLS]
        assert "zhihuiti_execute_goal" in names
        assert "zhihuiti_execute_task" in names
        assert "zhihuiti_list_agents" in names
        assert "zhihuiti_system_status" in names

    def test_handle_initialize(self):
        from zhihuiti.mcp_server import _handle_request
        resp = _handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert resp["id"] == 1
        assert resp["result"]["serverInfo"]["name"] == "zhihuiti"

    def test_handle_tools_list(self):
        from zhihuiti.mcp_server import _handle_request
        resp = _handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        assert len(resp["result"]["tools"]) == 4

    def test_handle_ping(self):
        from zhihuiti.mcp_server import _handle_request
        resp = _handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "ping",
        })
        assert resp["result"] == {}

    def test_handle_notification(self):
        from zhihuiti.mcp_server import _handle_request
        resp = _handle_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        assert resp is None  # Notifications get no response

    def test_handle_unknown_method(self):
        from zhihuiti.mcp_server import _handle_request
        resp = _handle_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "unknown/method",
        })
        assert "error" in resp
        assert resp["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Bridge tests
# ---------------------------------------------------------------------------

class TestKadyBridge:
    """Test the kady_bridge module."""

    def test_zhihuiti_client_init(self):
        import sys
        sys.path.insert(0, "/home/user/zhihuiti")
        from kady_bridge import ZhihuiTiClient
        client = ZhihuiTiClient("http://localhost:8377")
        assert client.base_url == "http://localhost:8377"

    def test_zhihuiti_client_strips_trailing_slash(self):
        import sys
        sys.path.insert(0, "/home/user/zhihuiti")
        from kady_bridge import ZhihuiTiClient
        client = ZhihuiTiClient("http://localhost:8377/")
        assert client.base_url == "http://localhost:8377"

    def test_delegate_function_exists(self):
        import sys
        sys.path.insert(0, "/home/user/zhihuiti")
        from kady_bridge import delegate_to_zhihuiti
        assert callable(delegate_to_zhihuiti)
