"""Theory collision and oracle routes for the dashboard."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler

from zhihuiti.routes.agent_routes import _send_json


def handle_theories(handler: BaseHTTPRequestHandler) -> None:
    """GET /api/theories — list collision theories."""
    from zhihuiti.collision import THEORIES
    data = {k: {"label": v["label"], "description": v["description"]} for k, v in THEORIES.items()}
    _send_json(handler, data)


def handle_collide(handler: BaseHTTPRequestHandler, orch) -> None:
    """POST /api/collide — trigger a theory collision.

    Body: {"goal": "...", "theory_a": "darwinian", "theory_b": "mutualist"}
    """
    content_length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(content_length)) if content_length else {}

    goal = body.get("goal", "")
    theory_a = body.get("theory_a", "darwinian")
    theory_b = body.get("theory_b", "mutualist")

    if not goal:
        _send_json(handler, {"error": "goal is required"}, 400)
        return

    from zhihuiti.collision import CollisionEngine, THEORIES

    if theory_a not in THEORIES or theory_b not in THEORIES:
        _send_json(handler, {"error": f"unknown theory, available: {list(THEORIES.keys())}"}, 400)
        return

    def make_orch(config):
        from zhihuiti import judge as judge_mod
        judge_mod.CULL_THRESHOLD = config["cull_threshold"]
        judge_mod.PROMOTE_THRESHOLD = config["promote_threshold"]

        from zhihuiti.economy import Economy
        from zhihuiti.bloodline import Bloodline
        from zhihuiti.realms import RealmManager
        from zhihuiti.agents import AgentManager
        from zhihuiti.judge import Judge
        from zhihuiti.circuit_breaker import CircuitBreaker
        from zhihuiti.behavior import BehaviorDetector
        from zhihuiti.relationships import LendingSystem, RelationshipGraph
        from zhihuiti.arbitration import ArbitrationBureau
        from zhihuiti.market import TradingMarket
        from zhihuiti.futures import FuturesMarket
        from zhihuiti.factory import Factory
        from zhihuiti.bidding import BiddingHouse
        from zhihuiti.messaging import MessageBoard
        from zhihuiti.memory import Memory
        from zhihuiti.orchestrator import Orchestrator

        mem = Memory(":memory:")
        llm = orch.llm

        o = Orchestrator.__new__(Orchestrator)
        o.llm = llm
        o.memory = mem
        o.economy = Economy(mem)
        o.bloodline = Bloodline(mem)
        o.realm_manager = RealmManager(mem)
        o.agent_manager = AgentManager(llm, mem, o.economy, o.bloodline, o.realm_manager)
        o.judge = Judge(llm, mem, o.agent_manager)
        o.circuit_breaker = CircuitBreaker(mem, interactive=False)
        o.behavior = BehaviorDetector(mem, llm)
        o.rel_graph = RelationshipGraph(mem)
        o.lending = LendingSystem(mem, o.rel_graph)
        o.arbitration = ArbitrationBureau(mem)
        o.market = TradingMarket(mem)
        o.futures = FuturesMarket(mem)
        o.factory = Factory(llm=llm, memory=mem)
        o.bidding = BiddingHouse(llm, mem, o.economy)
        o.messages = MessageBoard(mem) if config["messaging"] else type("Null", (), {
            "broadcast": lambda *a, **k: None,
            "collect_context": lambda *a, **k: "",
        })()
        o.tasks = {}
        o.max_workers = 4
        o.max_retries = 0
        o.tools_enabled = False
        for agent in o.bidding.pool.get_all_alive():
            if agent.id not in o.agent_manager.agents:
                o.agent_manager.agents[agent.id] = agent
        o.realm_manager.allocate_budgets(o.economy.treasury.balance * 0.5)
        return o

    engine = CollisionEngine()
    result = engine.collide(goal, theory_a, theory_b, make_orch)
    _send_json(handler, result.to_dict())
