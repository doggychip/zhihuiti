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
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.orchestrator import Orchestrator

console = Console()

DEFAULT_PORT = 8377  # 慧体 pinyin abbreviation


def _gather_data(orch: Orchestrator) -> dict:
    """Gather all system data into a single dict for the dashboard."""
    data: dict = {}

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
<div class="grid" id="dashboard"></div>
<script>
let DATA = __DATA__;

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

// Memory
let mem = DATA.memory;
html += renderCard('💾', 'Memory', [
  m('Total Tasks', mem.total_tasks),
  m('Total Agents', mem.total_agents),
  m('Gene Pool Size', mem.gene_pool_size),
  m('Avg Task Score', mem.avg_task_score),
].join(''));

document.getElementById('dashboard').innerHTML = html;

// Auto-refresh every 10 seconds
setTimeout(() => location.reload(), 10000);
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    orchestrator: Orchestrator | None = None

    def do_GET(self):
        if self.path == "/api/data":
            self._serve_json()
        else:
            self._serve_html()

    def _serve_html(self):
        data = _gather_data(self.orchestrator) if self.orchestrator else {}
        html = DASHBOARD_HTML.replace("__DATA__", json.dumps(data))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_json(self):
        data = _gather_data(self.orchestrator) if self.orchestrator else {}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # Suppress access logs


def start_dashboard(orch: Orchestrator, port: int = DEFAULT_PORT,
                    background: bool = True) -> HTTPServer | None:
    """Start the web dashboard server.

    If background=True, runs in a daemon thread and returns the server.
    If background=False, blocks forever.
    """
    DashboardHandler.orchestrator = orch

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)

    console.print(
        f"  [bold green]Dashboard:[/bold green] http://localhost:{port}"
    )

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
