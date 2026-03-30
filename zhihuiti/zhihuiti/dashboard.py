"""Web dashboard for zhihuiti — lightweight HTTP server with live system status.

Serves a single-page HTML dashboard showing all system metrics.
Route handlers are split into domain-specific modules under routes/.

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


# ── Backwards-compatible entry point for _gather_data ─────────────────────
# mcp_server.py and api.py import this directly.

def _gather_data(orch) -> dict:
    """Gather all system data into a single dict for the dashboard."""
    from zhihuiti.routes.agent_routes import gather_core_data
    from zhihuiti.routes.heartai_routes import gather_external_data
    data = gather_core_data(orch)
    if orch and hasattr(orch, "economy"):
        data.update(gather_external_data())
    return data


# ── Dashboard HTML ────────────────────────────────────────────────────────

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

// P&L Score (Real Trading Performance)
if (DATA.pnl) {
  let pnl = DATA.pnl;
  let c = pnl.components || {};
  html += renderCard('💰', 'Real P&L Score', [
    m('Composite Score', (pnl.score||0).toFixed(3), pnl.score > 0.6 ? 'green' : pnl.score > 0.3 ? 'yellow' : 'red'),
    m('Return', (pnl.return_pct||0).toFixed(2) + '%', pnl.return_pct >= 0 ? 'green' : 'red'),
    m('Equity', '$' + (pnl.equity||0).toLocaleString()),
    m('Positions', pnl.positions || 0),
    m('Rank', pnl.leaderboard_rank || '—'),
  ].join(''));
}

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

// HeartAI Cross-Project
if (DATA.heartai) {
  let ha = DATA.heartai;
  let statusColor = ha.online ? 'green' : 'red';
  let statusText = ha.online ? 'ONLINE' : 'OFFLINE';
  let content = [m('Status', statusText, statusColor), m('Agents', ha.total || 0)].join('');
  if (ha.online && ha.agents && ha.agents.length) {
    let haRows = ha.agents.slice(0, 10).map(a =>
      `<tr><td>${(a.name||a.id).slice(0,20)}</td><td>${a.posts||0}</td><td>${a.comments||0}</td></tr>`
    ).join('');
    content += `<table><tr><th>Agent</th><th>Posts</th><th>Comments</th></tr>${haRows}</table>`;
  }
  html += renderCard('❤️', `HeartAI (${statusText})`, content);
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


# ── Dashboard HTTP Handler ────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler — thin dispatcher to route modules."""

    orchestrator: Orchestrator | None = None
    _scheduler = None

    def do_GET(self):
        from zhihuiti.routes import agent_routes, oracle_routes, knowledge_routes

        if self.path == "/api/data":
            agent_routes.handle_data(self, self.orchestrator)
        elif self.path == "/api/theories":
            oracle_routes.handle_theories(self)
        elif self.path.startswith("/api/job/"):
            job_id = self.path.split("/api/job/")[1]
            agent_routes.handle_job(self, job_id)
        elif self.path == "/api/jobs":
            agent_routes.handle_jobs(self)
        elif self.path == "/api/scheduler":
            agent_routes.handle_scheduler(self, DashboardHandler._scheduler)
        elif self.path == "/api/reports":
            knowledge_routes.handle_reports(self, self.orchestrator)
        elif self.path.startswith("/api/knowledge"):
            knowledge_routes.handle_knowledge(self, self.orchestrator)
        elif self.path == "/api/debug":
            agent_routes.handle_debug(self, self.orchestrator)
        else:
            self._serve_html()

    def do_POST(self):
        from zhihuiti.routes import agent_routes, oracle_routes

        if self.path == "/api/collide":
            oracle_routes.handle_collide(self, self.orchestrator)
        elif self.path == "/api/run":
            agent_routes.handle_run(self, self.orchestrator)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight for Lovable."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode())

    def log_message(self, format, *args):
        pass  # Suppress access logs


# ── Auto Scheduler ────────────────────────────────────────────────────────

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
            goals_per_cycle = int(os.environ.get("GOALS_PER_CYCLE", "5"))
            if not self.goals:
                time.sleep(self.interval)
                continue
            selected = random.sample(self.goals, min(goals_per_cycle, len(self.goals)))
            for goal in selected:
                if not self.running:
                    break
                try:
                    console.print(f"  [cyan]Auto-run:[/cyan] {goal[:60]}...")
                    result = self.orch.execute_goal(goal)
                    self.run_count += 1
                    self.last_run = time.time()

                    if hasattr(self.orch, 'context_engine'):
                        for task_result in result.get("tasks", []):
                            score = task_result.get("score", 0)
                            if score >= 0.7:
                                task_id = task_result.get("task", "")
                                agent_id = task_result.get("agent_id", "")
                                task_obj = self.orch.tasks.get(task_id)
                                agent_obj = self.orch.agent_manager.agents.get(agent_id)
                                if task_obj and agent_obj:
                                    self.orch.context_engine.extract_learnings(
                                        task_obj, agent_obj, score,
                                    )
                except Exception as e:
                    console.print(f"  [red]Auto-run failed:[/red] {e}")

            # Direct AlphaArena trading
            aa_url = os.environ.get("ALPHAARENA_URL", "")
            aa_key = os.environ.get("ALPHAARENA_API_KEY", "")
            aa_id = os.environ.get("ALPHAARENA_AGENT_ID", "")
            if aa_url and aa_key and aa_id:
                try:
                    from zhihuiti.alphaarena import AlphaArenaBridge
                    bridge = AlphaArenaBridge(base_url=aa_url, api_key=aa_key, agent_id=aa_id)
                    prices = bridge.get_prices()
                    portfolio = bridge.get_portfolio()

                    if prices:
                        top_mover = max(prices, key=lambda p: abs(p.get("change24h", 0)))
                        change = top_mover.get("change24h", 0)
                        pair = top_mover.get("pair", "")
                        price = top_mover.get("price", 0)
                        cash = portfolio.get("cashBalance", 0)

                        if abs(change) > 1.0 and cash > 1000 and pair:
                            max_spend = cash * 0.1
                            quantity = round(max_spend / price, 4) if price > 0 else 0
                            side = "buy" if change > 0 else "sell"

                            if quantity > 0:
                                result = bridge.trade(pair, side, quantity)
                                console.print(
                                    f"  [green]Trade executed:[/green] {side} {quantity} {pair} "
                                    f"@ ${price:,.2f} (24h: {change:+.1f}%)"
                                )
                except Exception as e:
                    console.print(f"  [red]Direct trade failed:[/red] {e}")

            # Multi-agent trading
            if aa_url and aa_key:
                try:
                    from zhihuiti.multi_agent import MultiAgentManager
                    multi = MultiAgentManager(base_url=aa_url, api_key=aa_key)
                    multi_results = multi.run_all()
                    total_trades = sum(len(r.get("trades", [])) for r in multi_results.values())
                    if total_trades > 0:
                        console.print(f"  [green]Multi-agent:[/green] {total_trades} trades across {len(multi_results)} agents")
                except Exception as e:
                    console.print(f"  [red]Multi-agent failed:[/red] {e}")

            # HeartAI health check
            heartai_url = os.environ.get("HEARTAI_URL", "")
            if heartai_url:
                try:
                    import httpx as _hx2
                    resp = _hx2.get(f"{heartai_url}/health", timeout=10)
                    health = resp.json()
                    status = health.get("status", "unknown")
                    if status != "ok" and status != "healthy":
                        console.print(f"  [yellow]HeartAI:[/yellow] health={status} — may need attention")
                    else:
                        console.print(f"  [dim]HeartAI:[/dim] healthy")
                except Exception as e:
                    console.print(f"  [red]HeartAI down:[/red] {e}")

            # CriticAI content generation
            criticai_url = os.environ.get("CRITICAI_URL", "")
            if criticai_url:
                try:
                    import httpx as _httpx
                    resp = _httpx.post(f"{criticai_url}/api/generate-activity",
                                       json={}, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        agent_name = data.get("agent", {}).get("name", "?") if isinstance(data.get("agent"), dict) else "?"
                        activity = data.get("activityType", data.get("type", "activity"))
                        console.print(f"  [magenta]CriticAI:[/magenta] {agent_name} generated {activity}")
                except Exception as e:
                    console.print(f"  [red]CriticAI failed:[/red] {e}")

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


# ── Entry point ───────────────────────────────────────────────────────────

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

        GOAL_POOL = [
            "Analyze the current crypto market. Which coins have strongest momentum? Compare BTC, ETH, SOL, AVAX, LINK. Identify the best entry points.",
            "Review our AlphaArena portfolio positions. Which are winning and which are losing? Recommend which to close and which to hold.",
            "Research macro economic indicators affecting crypto markets this week. How should our trading strategies adapt?",
            "Compare momentum vs mean reversion strategies in the current market regime. Which is performing better and why?",
            "Analyze correlation between our stock positions (NVDA, TSM, TSLA) and crypto positions. Are we overexposed to any sector?",
            "Research the top 5 highest-volume trading pairs in the last 24 hours. What's driving the volume? Should we trade them?",
            "Evaluate risk-adjusted returns of our 5 trading strategies: momentum, mean_reversion, accumulate, scalp, diversify. Rank them by Sharpe ratio.",
            "Analyze agent performance scores across all roles. Which roles consistently score above 0.8? Which need improvement? Recommend breeding priorities.",
            "Review the causal graph for patterns: what agent behaviors cause the highest task scores? What causes failures?",
            "Compare the three realms (Research, Execution, Central) by productivity. Which realm has the best score-per-token efficiency?",
            "Analyze the gene pool. How many generations deep are we? Are newer generations outperforming older ones? Is evolution working?",
            "Review the auction system efficiency. What's the average savings per auction? Are agents bidding competitively?",
            "Evaluate the lending system. How many loans are active? What's the default rate? Should we adjust interest rates?",
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
            "Analyze the S&P 500 tech sector: AAPL, MSFT, GOOGL, META, AMZN. Which has the strongest fundamentals right now?",
            "Research emerging trends in semiconductor stocks. Compare NVDA, AMD, TSM, INTC. Who will lead the next cycle?",
            "Analyze energy sector movements: CVX, XOM. How do oil prices affect our portfolio? Should we increase or reduce exposure?",
            "Research the impact of Federal Reserve policy on both crypto and stock markets. What's the consensus outlook?",
            "Compare healthcare stocks: JNJ, PFE, MRK, ABBV, LLY. Which has the best risk/reward for the next quarter?",
            "Analyze HeartAI community posts and identify trending topics in Chinese metaphysics. What are users most interested in: BaZi, feng shui, astrology, or divination?",
            "Review the quality of BaZi (八字) readings on HeartAI. What common mistakes do agents make? How can accuracy be improved?",
            "Research the intersection of AI and traditional Chinese astrology. How can LLMs improve ZiWei Dou Shu (紫微斗数) predictions?",
            "Analyze the HeartAI agent ecosystem: 玄机总管, 风水先知, 命理参谋, 星象观测员. How can their domain expertise be improved?",
            "Compare Western astrology and Chinese BaZi systems. What are the key differences in methodology? How can HeartAI bridge both traditions?",
            "Research feng shui principles for modern architecture. What advice should the 风水先知 agent give for apartment layouts and office design?",
            "Analyze engagement patterns on HeartAI: which types of posts get the most comments? What content strategy should agents follow?",
            "Review the 观星小助手 agent's 195 posts on HeartAI. What topics resonate most? Suggest new discussion themes for the community.",
        ]

        aa_url = os.environ.get("ALPHAARENA_URL", "")
        aa_id = os.environ.get("ALPHAARENA_AGENT_ID", "")
        aa_key = os.environ.get("ALPHAARENA_API_KEY", "")
        if aa_url and aa_id:
            trade_history = ""
            try:
                import httpx as _hx
                trades_resp = _hx.get(f"{aa_url}/api/trades?agentId={aa_id}&limit=10", timeout=10)
                trades = trades_resp.json()
                trades_list = trades if isinstance(trades, list) else trades.get("trades", [])
                if trades_list:
                    lines = ["## Recent Trade History (learn from these):"]
                    for t in trades_list[:10]:
                        pair = t.get("pair", "?")
                        side = t.get("side", "?")
                        qty = t.get("quantity", 0)
                        price = t.get("price", 0)
                        lines.append(f"  {side} {qty} {pair} @ ${price:,.2f}")
                    trade_history = "\n".join(lines) + "\n\n"
            except Exception:
                pass

            portfolio_context = ""
            try:
                port_resp = _hx.get(f"{aa_url}/api/portfolio/{aa_id}", timeout=10)
                port = port_resp.json()
                cash = port.get("cashBalance", 0)
                equity = port.get("totalEquity", 0)
                positions = port.get("positions", [])
                pos_str = ", ".join(f"{p.get('pair','?')} {p.get('side','?')} {p.get('quantity',0)}" for p in positions)
                portfolio_context = f"Current portfolio: ${equity:,.0f} equity, ${cash:,.0f} cash. Positions: {pos_str or 'none'}.\n"
            except Exception:
                pass

            GOAL_POOL.extend([
                f"AlphaArena Trading: {portfolio_context}{trade_history}Check prices at {aa_url}/api/prices. Analyze top 3 movers. If any moved >3%, trade. API key: {aa_key}. Agent: {aa_id}.",
                f"AlphaArena Portfolio Review: {portfolio_context}{trade_history}Review current positions. Close any losing positions (negative unrealizedPnl). API: {aa_url}. Key: {aa_key}. Agent: {aa_id}.",
                f"AlphaArena Stock Analysis: {portfolio_context}{trade_history}Compare AAPL, TSLA, NVDA performance. Buy the strongest stock. API: {aa_url}. Key: {aa_key}. Agent: {aa_id}.",
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
