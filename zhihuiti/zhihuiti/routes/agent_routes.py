"""Agent, economy, and system data routes for the dashboard."""

from __future__ import annotations

import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zhihuiti.orchestrator import Orchestrator


def gather_core_data(orch) -> dict:
    """Gather core system data: economy, realms, agents, inspection, etc."""
    data: dict = {}

    if not hasattr(orch, "economy"):
        data["economy"] = {"money_supply": 0, "total_minted": 0, "total_burned": 0, "treasury_balance": 0, "total_taxes_collected": 0, "total_rewards_paid": 0, "total_spawn_costs": 0, "transactions": 0, "tax_rate": "15%"}
        data["memory"] = orch.memory.get_stats() if hasattr(orch, "memory") else {}
        data["agents"] = []
        data["realms"] = {}
        data["bloodline"] = orch.memory.get_lineage_stats() if hasattr(orch, "memory") else {}
        data["auctions"] = orch.memory.get_auction_stats() if hasattr(orch, "memory") else {}
        data["transactions"] = {}
        data["inspection"] = {"total_inspections": 0, "accepted": 0, "rejected": 0, "acceptance_rate": 0, "avg_score": 0}
        data["circuit_breaker"] = {"total_trips": 0, "emergencies": 0, "halts": 0, "warnings": 0, "overridden": 0, "laws_active": 0}
        data["behavior"] = {"total_violations": 0, "agents_flagged": 0, "total_penalties": 0, "by_type": {}}
        data["relationships"] = {"total_relationships": 0, "agents_connected": 0, "by_type": {}}
        data["loans"] = {"total_loans": 0, "active": 0, "repaid": 0, "defaulted": 0, "total_principal": 0, "total_repaid": 0}
        data["market"] = {"total_orders": 0, "total_trades": 0, "total_volume": 0}
        data["futures"] = {"total_stakes": 0, "active": 0, "won": 0, "lost": 0, "total_staked": 0}
        data["arbitration"] = {"total_disputes": 0, "open": 0, "resolved": 0, "dismissed": 0}
        data["factory"] = {"total_orders": 0, "shipped": 0, "qa_fail": 0, "in_progress": 0, "total_revenue": 0}
        data["adaptation"] = {"thresholds": {"cull": 0.3, "promote": 0.8, "samples": 0, "history": []}, "performance": {}, "prompt_evolution": {}}
        data["goal_history"] = orch.memory.get_recent_goals(limit=10) if hasattr(orch, "memory") else []
        data["messaging"] = {"total_messages": 0, "unread": 0}
        from zhihuiti.collision import THEORIES
        data["theories"] = {k: {"label": v["label"], "description": v["description"]} for k, v in THEORIES.items()}
        return data

    # Economy
    data["economy"] = orch.economy.get_report()

    # Memory stats
    data["memory"] = orch.memory.get_stats()

    # Realms — reconcile counters from live agents before reading
    orch.realm_manager.reconcile_counts(orch.agent_manager.agents)
    realm_data = {}
    for realm, rs in orch.realm_manager.realms.items():
        realm_data[realm.value] = {
            "budget_allocated": round(rs.budget_allocated, 1),
            "budget_remaining": round(rs.budget_remaining, 1),
            "agents_active": rs.agents_active,
            "agents_frozen": rs.agents_frozen,
            "agents_bankrupt": rs.agents_bankrupt,
            "tasks_completed": rs.tasks_completed,
            "tasks_failed": rs.tasks_failed,
            "avg_score": round(rs.avg_score, 3),
        }
    data["realms"] = realm_data

    # Agents
    agents = []
    for a in orch.agent_manager.agents.values():
        agents.append({
            "id": a.id,
            "role": a.config.role.value,
            "budget": round(a.budget, 1),
            "avg_score": round(a.avg_score, 2),
            "alive": a.alive,
            "realm": a.realm.value,
            "life_state": a.life_state.value,
            "generation": a.config.generation,
            "tasks": len(a.scores),
        })
    data["agents"] = agents

    # Bloodline
    data["bloodline"] = orch.memory.get_lineage_stats()

    # Auction stats
    data["auctions"] = orch.memory.get_auction_stats()

    # Transaction summary
    data["transactions"] = orch.memory.get_transaction_summary()

    # Inspection
    data["inspection"] = orch.judge.inspection.get_stats()

    # Circuit breaker
    data["circuit_breaker"] = orch.circuit_breaker.get_stats()

    # Behavior
    data["behavior"] = orch.behavior.get_stats()

    # Relationships
    data["relationships"] = orch.rel_graph.get_stats()

    # Loans
    data["loans"] = orch.memory.get_loan_stats()

    # Market
    data["market"] = orch.market.get_stats()

    # Futures
    data["futures"] = orch.futures.get_stats()

    # Arbitration
    data["arbitration"] = orch.arbitration.get_stats()

    # Factory
    data["factory"] = orch.factory.get_stats()

    # Goal history
    data["goal_history"] = orch.memory.get_recent_goals(limit=10)

    # Collision theories available
    from zhihuiti.collision import THEORIES
    data["theories"] = {k: {"label": v["label"], "description": v["description"]} for k, v in THEORIES.items()}

    # Messages
    all_msgs = orch.memory._query("SELECT COUNT(*) as c FROM messages")
    unread = orch.memory._query("SELECT COUNT(*) as c FROM messages WHERE read = 0")
    data["messaging"] = {
        "total_messages": all_msgs[0]["c"] if all_msgs else 0,
        "unread": unread[0]["c"] if unread else 0,
    }

    # Adaptation Engine — feedback loop data
    if hasattr(orch.judge, "adaptive_thresholds"):
        at = orch.judge.adaptive_thresholds
        cull_t, promote_t = at.get_thresholds()
        data["adaptation"] = {
            "thresholds": {
                "cull": cull_t,
                "promote": promote_t,
                "samples": at.state.samples_used,
                "history": at.state.history[-20:],
            },
            "performance": {},
            "prompt_evolution": orch.judge.prompt_evolver.get_role_report(),
        }
        for role, rp in orch.judge.performance_tracker.roles.items():
            data["adaptation"]["performance"][role] = {
                "mean": round(rp.mean_score, 3),
                "trend": round(rp.score_trend, 4),
                "count": len(rp.scores),
                "mutation_rate": round(orch.judge.performance_tracker.suggest_mutation_rate(role), 3),
                "layer_means": {
                    layer: round(rp.layer_mean(layer), 3)
                    for layer in rp.layer_scores
                },
                "recent_scores": rp.scores[-30:],
            }
    else:
        data["adaptation"] = {
            "thresholds": {"cull": 0.3, "promote": 0.8, "samples": 0, "history": []},
            "performance": {},
            "prompt_evolution": {},
        }

    # P&L Score (real trading performance)
    aa_url_pnl = os.environ.get("ALPHAARENA_URL", "")
    aa_id_pnl = os.environ.get("ALPHAARENA_AGENT_ID", "")
    if aa_url_pnl and aa_id_pnl:
        try:
            from zhihuiti.pnl_scorer import PnLScorer
            scorer = PnLScorer(base_url=aa_url_pnl, agent_id=aa_id_pnl)
            data["pnl"] = scorer.score_cycle()
        except Exception:
            data["pnl"] = {"score": 0, "return_pct": 0, "equity": 0, "positions": 0}
    else:
        data["pnl"] = {"score": 0, "return_pct": 0, "equity": 0, "positions": 0}

    return data


# ── Background job storage ────────────────────────────────────────────────

_jobs: dict = {}


def handle_data(handler: BaseHTTPRequestHandler, orch) -> None:
    """GET /api/data — serve all system data as JSON."""
    from zhihuiti.routes.heartai_routes import gather_external_data
    data = gather_core_data(orch) if orch else {}
    if orch and hasattr(orch, "economy"):
        data.update(gather_external_data())
    _send_json(handler, data)


def handle_debug(handler: BaseHTTPRequestHandler, orch) -> None:
    """GET /api/debug — debug info."""
    _send_json(handler, {
        "backend": getattr(getattr(orch, "llm", None), "_backend", "unknown"),
        "model": getattr(getattr(orch, "llm", None), "model", "unknown"),
        "has_deepseek_key": bool(os.environ.get("DEEPSEEK_API_KEY", "")),
        "has_openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY", "")),
        "has_execute_goal": hasattr(orch, "execute_goal"),
    })


def handle_jobs(handler: BaseHTTPRequestHandler) -> None:
    """GET /api/jobs — list all background jobs."""
    _send_json(handler, _jobs)


def handle_job(handler: BaseHTTPRequestHandler, job_id: str) -> None:
    """GET /api/job/<id> — get job status."""
    job = _jobs.get(job_id)
    if job:
        _send_json(handler, job)
    else:
        _send_json(handler, {"error": "job not found"}, 404)


def handle_scheduler(handler: BaseHTTPRequestHandler, scheduler) -> None:
    """GET /api/scheduler — scheduler status."""
    _send_json(handler, scheduler.get_status() if scheduler else {"running": False, "goals": []})


def handle_run(handler: BaseHTTPRequestHandler, orch) -> None:
    """POST /api/run — execute a goal in the background."""
    content_length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(content_length)) if content_length else {}
    goal = body.get("goal", "")

    if not goal:
        _send_json(handler, {"error": "goal is required"}, 400)
        return

    if not orch or not hasattr(orch, "execute_goal"):
        _send_json(handler, {"error": "no orchestrator — set DEEPSEEK_API_KEY"}, 500)
        return

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": "running", "goal": goal, "result": None}

    def _run():
        try:
            result = orch.execute_goal(goal)
            _jobs[job_id] = {"status": "done", "goal": goal, "result": result}
        except Exception as e:
            _jobs[job_id] = {"status": "error", "goal": goal, "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    _send_json(handler, {"job_id": job_id, "status": "running", "goal": goal})


def _send_json(handler: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())
