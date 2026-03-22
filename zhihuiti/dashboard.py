"""Web dashboard for zhihuiti — lightweight HTTP server with live system status.

Serves a single-page HTML dashboard showing all system metrics:
- Economy (central bank, treasury, taxes)
- Three Realms status
- Agent pool with scores and budgets
- Bloodline / gene pool
- Auction history
- Inspection stats
- Circuit breaker status
- Behavioral violations
- Relationship graph
- Lending / Futures / Market / Factory stats

Uses only stdlib (http.server) — no Flask/FastAPI dependency.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.orchestrator import Orchestrator

console = Console()

DEFAULT_PORT = 8377  # 慧体 pinyin abbreviation


def _gather_data(orch) -> dict:
    """Gather all system data into a single dict for the dashboard."""
    data: dict = {}

    # Handle minimal orchestrator (no LLM available)
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
        data["goal_history"] = orch.memory.get_recent_goals(limit=10) if hasattr(orch, "memory") else []
        data["messaging"] = {"total_messages": 0, "unread": 0}
        from zhihuiti.collision import THEORIES
        data["theories"] = {k: {"label": v["label"], "description": v["description"]} for k, v in THEORIES.items()}
        return data

    # Economy
    data["economy"] = orch.economy.get_report()

    # Memory stats
    data["memory"] = orch.memory.get_stats()

    # Realms
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

    # AlphaArena external agents
    aa_url = os.environ.get("ALPHAARENA_URL", "")
    if aa_url:
        try:
            import httpx
            resp = httpx.get(f"{aa_url}/api/leaderboard", timeout=5)
            lb = resp.json()
            entries = lb if isinstance(lb, list) else lb.get("leaderboard", lb.get("entries", []))
            aa_agents = []
            for e in entries[:20]:
                agent_info = e.get("agent", {}) or {}
                aa_agents.append({
                    "id": e.get("agentId", "?"),
                    "name": agent_info.get("name", e.get("agentId", "?")),
                    "rank": e.get("rank", 0),
                    "totalReturn": e.get("totalReturn", 0),
                    "sharpeRatio": e.get("sharpeRatio", 0),
                    "winRate": e.get("winRate", 0),
                    "maxDrawdown": e.get("maxDrawdown", 0),
                    "compositeScore": e.get("compositeScore", 0),
                    "type": agent_info.get("type", "algo_bot"),
                })
            data["alphaarena"] = {
                "agents": aa_agents,
                "total": len(aa_agents),
                "url": aa_url,
            }
        except Exception:
            data["alphaarena"] = {"agents": [], "total": 0, "url": aa_url}
    else:
        data["alphaarena"] = {"agents": [], "total": 0, "url": ""}

    return data


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>智慧体 zhihuiti Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, system-ui, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 20px; }
  h1 { text-align: center; font-size: 2em; margin-bottom: 20px; color: #fff; }
  h1 span { color: #f0c040; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .card { background: #15151f; border: 1px solid #2a2a3a; border-radius: 8px; padding: 16px; }
  .card h2 { font-size: 1em; color: #a0a0b0; margin-bottom: 12px; border-bottom: 1px solid #2a2a3a; padding-bottom: 8px; }
  .card h2 .icon { margin-right: 6px; }
  .metric { display: flex; justify-content: space-between; padding: 4px 0; }
  .metric .label { color: #808090; }
  .metric .value { font-weight: 600; color: #fff; }
  .metric .value.green { color: #4ade80; }
  .metric .value.red { color: #f87171; }
  .metric .value.yellow { color: #fbbf24; }
  .metric .value.blue { color: #60a5fa; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 0.85em; }
  th { text-align: left; color: #808090; padding: 4px 8px; border-bottom: 1px solid #2a2a3a; }
  td { padding: 4px 8px; border-bottom: 1px solid #1a1a2a; }
  .alive { color: #4ade80; } .dead { color: #f87171; }
  .refresh { text-align: center; margin: 20px 0; }
  .refresh button { background: #2a2a3a; color: #e0e0e0; border: 1px solid #3a3a4a; padding: 8px 24px; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
  .refresh button:hover { background: #3a3a4a; }
  .sub { color: #606070; font-size: 0.85em; padding-left: 12px; }
</style>
</head>
<body>
<h1><span>智慧体</span> zhihuiti Dashboard</h1>
<div class="refresh"><button onclick="location.reload()">Refresh</button> <span style="color:#606070">Auto-refresh: 10s</span></div>
<div class="grid" id="dashboard"><p style="color:#606070;text-align:center;padding:40px">Loading...</p></div>
<script>
function loadAndRender() {
fetch('/api/data').then(r=>r.json()).then(DATA=>{renderDashboard(DATA)}).catch(e=>{
  document.getElementById('dashboard').innerHTML='<p style="color:red;padding:40px">Error loading data: '+e+'</p>';
});
}
loadAndRender();
setInterval(loadAndRender, 10000);
function renderDashboard(DATA) {

function m(label, value, cls) {
  return `<div class="metric"><span class="label">${label}</span><span class="value ${cls||''}">${value}</span></div>`;
}

function renderCard(icon, title, content) {
  return `<div class="card"><h2><span class="icon">${icon}</span>${title}</h2>${content}</div>`;
}

let html = '';

// Economy
let e = DATA.economy;
html += renderCard('🏦', 'Economy', [
  m('Money Supply', e.money_supply),
  m('Minted', '+' + e.total_minted, 'green'),
  m('Burned', '-' + e.total_burned, 'red'),
  m('Treasury', e.treasury_balance, 'blue'),
  m('Taxes Collected', e.total_taxes_collected),
  m('Rewards Paid', e.total_rewards_paid),
  m('Tax Rate', e.tax_rate),
  m('Transactions', e.transactions),
].join(''));

// Realms
let rn = {research:'🔬 研发界 Research', execution:'⚡ 执行界 Execution', central:'🏛 中枢界 Central'};
for (let [k,v] of Object.entries(DATA.realms)) {
  html += renderCard(rn[k]?.slice(0,2)||'', rn[k]||k, [
    m('Active', v.agents_active, 'green'),
    m('Frozen', v.agents_frozen, 'blue'),
    m('Bankrupt', v.agents_bankrupt, 'red'),
    m('Tasks Done', v.tasks_completed),
    m('Tasks Failed', v.tasks_failed, 'red'),
    m('Avg Score', v.avg_score || '—'),
    m('Budget', v.budget_remaining + ' / ' + v.budget_allocated),
  ].join(''));
}

// Agents
if (DATA.agents.length) {
  let rows = DATA.agents.map(a =>
    `<tr><td>${a.id.slice(0,8)}</td><td>${a.role}</td>` +
    `<td class="${a.alive?'alive':'dead'}">${a.life_state}</td>` +
    `<td>${a.budget}</td><td>${a.avg_score}</td><td>${a.generation}</td></tr>`
  ).join('');
  html += renderCard('🤖', `Agents (${DATA.agents.length})`,
    `<table><tr><th>ID</th><th>Role</th><th>State</th><th>Budget</th><th>Score</th><th>Gen</th></tr>${rows}</table>`
  );
}

// Bloodline
let bl = DATA.bloodline;
html += renderCard('🧬', 'Bloodline', [
  m('Total Genes', bl.total_genes),
  m('Alive Genes', bl.alive_genes, 'green'),
  m('Max Generation', bl.max_generation),
  m('Avg Score', bl.avg_score),
].join(''));

// Inspection
let ins = DATA.inspection;
html += renderCard('🔍', '3-Layer Inspection', [
  m('Total Inspections', ins.total_inspections),
  m('Accepted', ins.accepted, 'green'),
  m('Rejected', ins.rejected, 'red'),
  m('Acceptance Rate', (ins.acceptance_rate * 100).toFixed(1) + '%'),
  m('Avg Score', ins.avg_score),
].join(''));

// Circuit Breaker
let cb = DATA.circuit_breaker;
html += renderCard('🚨', 'Circuit Breaker', [
  m('Total Trips', cb.total_trips),
  m('Emergencies', cb.emergencies, 'red'),
  m('Halts', cb.halts, 'yellow'),
  m('Warnings', cb.warnings),
  m('Overridden', cb.overridden),
  m('Active Laws', cb.laws_active),
].join(''));

// Behavior
let bh = DATA.behavior;
html += renderCard('👁', 'Behavioral Detection', [
  m('Total Violations', bh.total_violations),
  m('Agents Flagged', bh.agents_flagged),
  m('Total Penalties', '-' + bh.total_penalties, 'red'),
].join('') + Object.entries(bh.by_type||{}).map(([t,c]) =>
  `<div class="metric sub"><span class="label">${t}</span><span class="value">${c}</span></div>`
).join(''));

// Relationships
let rel = DATA.relationships;
html += renderCard('🔗', 'Relationships', [
  m('Total', rel.total_relationships),
  m('Agents Connected', rel.agents_connected),
].join('') + Object.entries(rel.by_type||{}).map(([t,c]) =>
  `<div class="metric sub"><span class="label">${t}</span><span class="value">${c}</span></div>`
).join(''));

// Loans
let ln = DATA.loans;
html += renderCard('💳', 'Lending', [
  m('Total Loans', ln.total_loans),
  m('Active', ln.active, 'green'),
  m('Repaid', ln.repaid),
  m('Defaulted', ln.defaulted, 'red'),
  m('Total Principal', ln.total_principal),
  m('Total Repaid', ln.total_repaid),
].join(''));

// Market
let mk = DATA.market;
html += renderCard('💱', 'Trading Market', [
  m('Total Orders', mk.total_orders),
  m('Total Trades', mk.total_trades),
  m('Volume', mk.total_volume),
].join(''));

// Futures
let ft = DATA.futures;
html += renderCard('📈', 'Futures / Staking', [
  m('Total Stakes', ft.total_stakes),
  m('Active', ft.active),
  m('Won', ft.won, 'green'),
  m('Lost', ft.lost, 'red'),
  m('Total Staked', ft.total_staked),
].join(''));

// Auctions
let au = DATA.auctions;
html += renderCard('🏷', 'Auctions', [
  m('Total Auctions', au.total_auctions),
  m('Total Savings', au.total_savings, 'green'),
  m('Avg Savings', au.avg_savings),
  m('Avg Winning Bid', au.avg_winning_bid),
].join(''));

// Arbitration
let ar = DATA.arbitration;
html += renderCard('⚖', 'Arbitration', [
  m('Total Disputes', ar.total_disputes),
  m('Open', ar.open),
  m('Resolved', ar.resolved, 'green'),
  m('Dismissed', ar.dismissed),
].join(''));

// Factory
let fa = DATA.factory;
html += renderCard('🏭', 'Blood Sweat Factory', [
  m('Total Orders', fa.total_orders),
  m('Shipped', fa.shipped, 'green'),
  m('QA Fail', fa.qa_fail, 'red'),
  m('In Progress', fa.in_progress),
  m('Total Revenue', fa.total_revenue),
].join(''));

// Messaging
let msg = DATA.messaging;
html += renderCard('📨', 'Agent Messaging', [
  m('Total Messages', msg.total_messages),
  m('Unread', msg.unread, msg.unread > 0 ? 'yellow' : ''),
].join(''));

// AlphaArena Leaderboard
if (DATA.alphaarena && DATA.alphaarena.agents && DATA.alphaarena.agents.length) {
  let aaRows = DATA.alphaarena.agents.map(a =>
    `<tr><td>${a.rank}</td><td>${(a.name||a.id).slice(0,15)}</td>` +
    `<td class="${a.totalReturn>=0?'alive':'dead'}">${a.totalReturn>=0?'+':''}${a.totalReturn.toFixed(2)}%</td>` +
    `<td>${(a.sharpeRatio||0).toFixed(1)}</td>` +
    `<td>${((a.winRate||0)*100).toFixed(0)}%</td>` +
    `<td>${(a.compositeScore||0).toFixed(3)}</td></tr>`
  ).join('');
  html += renderCard('📈', `AlphaArena (${DATA.alphaarena.total} agents)`,
    `<table><tr><th>#</th><th>Agent</th><th>Return</th><th>Sharpe</th><th>Win</th><th>Score</th></tr>${aaRows}</table>`
  );
}

// Goal History
if (DATA.goal_history && DATA.goal_history.length) {
  let rows = DATA.goal_history.map(g =>
    `<tr><td>${(g.goal||'').slice(0,30)}</td><td>${g.task_count||0}</td><td>${(g.avg_score||0).toFixed(2)}</td></tr>`
  ).join('');
  html += renderCard('📚', `Goal History (${DATA.goal_history.length})`,
    `<table><tr><th>Goal</th><th>Tasks</th><th>Score</th></tr>${rows}</table>`
  );
}

// Memory
let mem = DATA.memory;
html += renderCard('💾', 'Memory', [
  m('Total Tasks', mem.total_tasks),
  m('Total Agents', mem.total_agents),
  m('Gene Pool Size', mem.gene_pool_size),
  m('Avg Task Score', mem.avg_task_score),
].join(''));

document.getElementById('dashboard').innerHTML = html;
} // end renderDashboard
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    orchestrator: Orchestrator | None = None

    def do_GET(self):
        if self.path == "/api/data":
            self._serve_json()
        elif self.path == "/api/theories":
            self._serve_theories()
        elif self.path.startswith("/api/job/"):
            job_id = self.path.split("/api/job/")[1]
            job = DashboardHandler._jobs.get(job_id)
            if job:
                self._send_json(job)
            else:
                self._send_json({"error": "job not found"}, 404)
        elif self.path == "/api/jobs":
            self._send_json(DashboardHandler._jobs)
        elif self.path == "/api/scheduler":
            sched = getattr(DashboardHandler, "_scheduler", None)
            self._send_json(sched.get_status() if sched else {"running": False, "goals": []})
        elif self.path == "/api/debug":
            self._send_json({
                "backend": getattr(getattr(self.orchestrator, "llm", None), "_backend", "unknown"),
                "model": getattr(getattr(self.orchestrator, "llm", None), "model", "unknown"),
                "has_deepseek_key": bool(os.environ.get("DEEPSEEK_API_KEY", "")),
                "has_openrouter_key": bool(os.environ.get("OPENROUTER_API_KEY", "")),
                "has_execute_goal": hasattr(self.orchestrator, "execute_goal"),
            })
        else:
            self._serve_html()

    def do_POST(self):
        if self.path == "/api/collide":
            self._handle_collide()
        elif self.path == "/api/run":
            self._handle_run()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._add_cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight for Lovable."""
        self.send_response(200)
        self._add_cors()
        self.end_headers()

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode())

    def _add_cors(self):
        """Add CORS headers to every response for Lovable cross-origin access."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_json(self):
        data = _gather_data(self.orchestrator) if self.orchestrator else {}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._add_cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_theories(self):
        from zhihuiti.collision import THEORIES
        data = {k: {"label": v["label"], "description": v["description"]} for k, v in THEORIES.items()}
        self._send_json(data)

    def _handle_collide(self):
        """POST /api/collide — trigger a theory collision.

        Body: {"goal": "...", "theory_a": "darwinian", "theory_b": "mutualist"}
        Returns collision result as JSON.
        """
        import threading as _threading

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}

        goal = body.get("goal", "")
        theory_a = body.get("theory_a", "darwinian")
        theory_b = body.get("theory_b", "mutualist")

        if not goal:
            self._send_json({"error": "goal is required"}, 400)
            return

        from zhihuiti.collision import CollisionEngine, THEORIES
        from zhihuiti.memory import Memory
        from zhihuiti.orchestrator import Orchestrator
        from zhihuiti import judge as judge_mod

        if theory_a not in THEORIES or theory_b not in THEORIES:
            self._send_json({"error": f"unknown theory, available: {list(THEORIES.keys())}"}, 400)
            return

        def make_orch(config):
            judge_mod.CULL_THRESHOLD = config["cull_threshold"]
            judge_mod.PROMOTE_THRESHOLD = config["promote_threshold"]
            orch = self.orchestrator
            # Use the existing orchestrator's LLM but fresh memory
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

            mem = Memory(":memory:")
            llm = self.orchestrator.llm

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
        self._send_json(result.to_dict())

    # Class-level storage for background job status
    _jobs: dict = {}

    def _handle_run(self):
        """POST /api/run — execute a goal in the background.

        Body: {"goal": "..."}
        Returns job ID immediately. Poll /api/job/<id> for results.
        """
        import threading as _t
        import uuid as _uuid

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}
        goal = body.get("goal", "")

        if not goal:
            self._send_json({"error": "goal is required"}, 400)
            return

        if not self.orchestrator or not hasattr(self.orchestrator, "execute_goal"):
            self._send_json({"error": "no orchestrator — set DEEPSEEK_API_KEY"}, 500)
            return

        job_id = _uuid.uuid4().hex[:12]
        DashboardHandler._jobs[job_id] = {"status": "running", "goal": goal, "result": None}

        def _run():
            try:
                result = self.orchestrator.execute_goal(goal)
                DashboardHandler._jobs[job_id] = {"status": "done", "goal": goal, "result": result}
            except Exception as e:
                DashboardHandler._jobs[job_id] = {"status": "error", "goal": goal, "error": str(e)}

        _t.Thread(target=_run, daemon=True).start()
        self._send_json({"job_id": job_id, "status": "running", "goal": goal})

    def log_message(self, format, *args):
        pass  # Suppress access logs


class AutoScheduler:
    """Background scheduler that runs goals on an interval."""

    def __init__(self, orch, interval_seconds: int = 7200):
        self.orch = orch
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        self.goals = []
        self.last_run = None
        self.run_count = 0

    def add_goal(self, goal: str):
        self.goals.append(goal)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        console.print(f"  [green]Auto-scheduler:[/green] {len(self.goals)} goals every {self.interval}s")

    def stop(self):
        self.running = False

    def _loop(self):
        import time
        import random
        while self.running:
            # Pick a random goal from the pool each cycle
            goal = random.choice(self.goals) if self.goals else None
            if goal and not self.running:
                break
            if goal:
                try:
                    console.print(f"  [cyan]Auto-run:[/cyan] {goal[:60]}...")
                    self.orch.execute_goal(goal)
                    self.run_count += 1
                    self.last_run = time.time()
                except Exception as e:
                    console.print(f"  [red]Auto-run failed:[/red] {e}")

            # Run hedge fund evolution every 3rd cycle
            if self.run_count > 0 and self.run_count % 3 == 0:
                aa_url = os.environ.get("ALPHAARENA_URL", "")
                if aa_url:
                    try:
                        from zhihuiti.hedge_manager import HedgeFundManager
                        manager = HedgeFundManager(base_url=aa_url)
                        result = manager.run_evolution_cycle()
                        console.print(f"  [green]Evolution:[/green] evolved {result['evolved']} agents")
                    except Exception as e:
                        console.print(f"  [red]Evolution failed:[/red] {e}")
            # Sleep in small increments so we can stop quickly
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "interval": self.interval,
            "goals": self.goals,
            "run_count": self.run_count,
            "last_run": self.last_run,
        }


def start_dashboard(orch: Orchestrator, port: int = DEFAULT_PORT,
                    background: bool = True, auto_trade: bool = False,
                    trade_interval: int = 7200) -> HTTPServer | None:
    """Start the web dashboard server.

    If background=True, runs in a daemon thread and returns the server.
    If background=False, blocks forever.
    """
    DashboardHandler.orchestrator = orch

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)

    console.print(
        f"  [bold green]Dashboard:[/bold green] http://localhost:{port}"
    )

    # Start auto-scheduler if requested or ALPHAARENA env vars are set
    if auto_trade or os.environ.get("ALPHAARENA_AUTO_TRADE"):
        interval = int(os.environ.get("ALPHAARENA_TRADE_INTERVAL", str(trade_interval)))
        scheduler = AutoScheduler(orch, interval_seconds=interval)

        # Add diverse goal pool — each cycle picks one randomly
        GOAL_POOL = [
            "Research the latest developments in AI agent frameworks. Compare at least 3 approaches and their trade-offs.",
            "Analyze current trends in DeFi and decentralized finance. Identify the top protocols and emerging risks.",
            "Compare different approaches to multi-agent coordination: auction-based, hierarchical, and evolutionary.",
            "Research the state of open-source LLMs. Compare Llama, Mistral, DeepSeek, and Qwen on coding tasks.",
            "Analyze the competitive landscape of AI coding assistants. What differentiates each product?",
            "Research blockchain scalability solutions: L2 rollups, sharding, and alternative consensus mechanisms.",
            "Evaluate strategies for building resilient distributed systems. Focus on fault tolerance and self-healing.",
            "Analyze the economics of AI inference: cloud vs local, cost per token trends, and optimization strategies.",
            "Research autonomous agent architectures used in production systems. What patterns work at scale?",
            "Compare approaches to AI safety and alignment. How do different frameworks handle agent autonomy?",
        ]

        aa_url = os.environ.get("ALPHAARENA_URL", "")
        aa_id = os.environ.get("ALPHAARENA_AGENT_ID", "")
        if aa_url and aa_id:
            GOAL_POOL.extend([
                f"AlphaArena: Check prices at {aa_url}/api/prices. Analyze top 3 movers. Trade if >3% move. Agent: {aa_id}.",
                f"AlphaArena: Review portfolio at {aa_url}/api/portfolio/{aa_id}. Rebalance if any position >25%.",
                f"AlphaArena: Analyze BTC and ETH momentum. Compare 24h trends. Trade the stronger one. Agent: {aa_id}.",
            ])

        for goal in GOAL_POOL:
            scheduler.add_goal(goal)

        scheduler.start()
        DashboardHandler._scheduler = scheduler

    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    else:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        server.server_close()
        return None
