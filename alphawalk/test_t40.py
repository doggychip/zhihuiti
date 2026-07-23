#!/usr/bin/env python3
"""Offline structural and deterministic golden tests for T40."""
import ast
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "T40---AlphaWalk-Morning-Command-Center-v1.1.0.json")
with open(PATH, encoding="utf-8") as handle:
    template = json.load(handle)

nodes = {n["id"]: n for n in template["dag_definition"]["nodes"]}
checks = []


def check(name, condition):
    checks.append((name, bool(condition)))
    print(("PASS " if condition else "FAIL ") + name)


class FakeNode:
    def __init__(self, inputs=None, params=None):
        self.inputs = inputs or {}
        self.params = params or {}
        self.outputs = {}

    def input(self, name):
        if name not in self.inputs:
            raise KeyError(name)
        return self.inputs[name]

    def workflow_param(self, name, default=None):
        return self.params.get(name, default)

    def output(self, name, value):
        self.outputs[name] = value


def run_utility(node_id, inputs, params=None):
    fake = FakeNode(inputs, params)
    code = nodes[node_id]["config"]["code"]
    exec(compile(code, node_id, "exec"), {"node": fake})
    return fake.outputs


def closes(drift, count=70, seed=1):
    random.seed(seed)
    price = 100.0
    values = []
    for _ in range(count):
        price *= 1.0 + drift + random.gauss(0, 0.001)
        values.append("%.2f" % price)
    return "\n".join(values)


def hlcv(drift, count=60, seed=1):
    random.seed(seed)
    price = 100.0
    rows = []
    for _ in range(count):
        price *= 1.0 + drift + random.gauss(0, 0.001)
        rows.append("%.2f,%.2f,%.2f,%d" %
                    (price * 1.01, price * 0.99, price, 1_000_000 + random.randint(0, 100_000)))
    return "\n".join(rows)


# Structural contract.
node_ids = list(nodes)
edge_ids = [e["id"] for e in template["dag_definition"]["edges"]]
check("schema marker", template["$schema"] == "xtrader-workflow-template/v1")
check("unique node ids", len(node_ids) == len(set(node_ids)))
check("unique edge ids", len(edge_ids) == len(set(edge_ids)))
check("cron weekday 07:00 ET", template["default_trigger"] == {
    "kind": "cron", "cron_expr": "0 7 * * 1-5", "timezone": "America/New_York"})
check("recommendations wired directly to notifier",
      any(e.get("from") == "command_engine" and e.get("from_slot") == "recommendations"
          and e.get("to") == "notifier" and e.get("to_slot") == "recommendations"
          for e in template["dag_definition"]["edges"]))
check("brief output has string contract",
      nodes["brief_writer"]["config"]["output_schema"]["brief_body"]["type"] == "string")
python_parses = True
for candidate in template["dag_definition"]["nodes"]:
    if candidate["kind"] == "utility" and candidate["config"].get("utility_kind") == "python":
        try:
            ast.parse(candidate["config"]["code"])
        except SyntaxError:
            python_parses = False
check("all utility Python parses", python_parses)

# Constructive market, strengthening watchlist, high-impact calendar.
market_names = [
    {"symbol": symbol, "closes": closes(0.002, seed=i)}
    for i, symbol in enumerate(("SPY", "QQQ", "IWM", "TLT", "GLD", "USO"), 1)
]
base_inputs = {
    "market_bars": {
        "names": market_names, "as_of": "2026-07-23T11:00:00Z", "data_source_status": "ok"},
    "watch_a": {
        "names": [{"symbol": "AAA", "hlcv": hlcv(0.003, seed=10)}],
        "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"},
    "watch_b": {
        "names": [], "assigned": [], "skipped": [], "data_source_status": "ok"},
    "overnight_context": {
        "items": [{"headline": "Verified item", "fact": "A dated fact",
                   "source": "Example", "source_date": "2026-07-23"}],
        "data_source_status": "ok"},
    "today_calendar": {
        "events": [{"time_et": "08:30", "kind": "macro", "title": "CPI",
                    "impact": "high", "source": "BLS"}],
        "data_source_status": "ok"},
}
result = run_utility("command_engine", base_inputs, {"portfolio": "AAA 25%"})["command_read"]
check("constructive regime", result["market_regime"] == "constructive")
check("strengthening classification", result["watchlist"][0]["status"] == "strengthening")
check("portfolio weight normalized", result["watchlist"][0]["portfolio_weight_pct"] == 25.0)
check("calendar has first priority", result["priorities"][0]["type"] == "calendar")
check("healthy run status", result["overall_status"] == "ok")
check("watchlist coverage", result["coverage"]["watchlist_resolved"] == 1
      and result["coverage"]["watchlist_total"] == 1)
check("constructive structure emits capped Tier-B Buy",
      len(result["recommendation_panel"]["recommendations"]) == 1
      and result["recommendation_panel"]["recommendations"][0]["action"] == "Buy"
      and len(result["recommendation_panel"]["recommendations"][0]["rationale"]) <= 200)

# Defensive market emits Sell under the symmetric fixed rule.
defensive_inputs = dict(base_inputs)
defensive_inputs["market_bars"] = {
    "names": [{"symbol": symbol, "closes": closes(-0.002, seed=i)}
              for i, symbol in enumerate(("SPY", "QQQ", "IWM", "TLT", "GLD", "USO"), 20)],
    "as_of": "2026-07-23T11:00:00Z", "data_source_status": "ok"}
defensive_inputs["watch_a"] = {
    "names": [{"symbol": "AAA", "hlcv": hlcv(-0.003, seed=11)}],
    "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"}
defensive = run_utility("command_engine", defensive_inputs, {"portfolio": "AAA 0.25"})["command_read"]
check("defensive regime", defensive["market_regime"] == "defensive")
check("weakening classification", defensive["watchlist"][0]["status"] == "weakening")
check("weakening portfolio priority", any(p["type"] == "portfolio_structure"
                                          for p in defensive["priorities"]))
check("defensive structure emits Tier-B Sell",
      defensive["recommendation_panel"]["recommendations"][0]["action"] == "Sell")

# Degraded core data and explicit toggle both suppress recommendations.
degraded_inputs = dict(base_inputs)
degraded_inputs["market_bars"] = dict(base_inputs["market_bars"], data_source_status="partial")
degraded = run_utility("command_engine", degraded_inputs, {"portfolio": "AAA 25%"})["command_read"]
disabled = run_utility("command_engine", base_inputs, {
    "portfolio": "AAA 25%", "recommendations_enabled": False})["command_read"]
check("degraded core lane suppresses recommendations",
      degraded["recommendation_panel"]["count"] == 0
      and degraded["recommendation_panel"]["suppression_reason"] ==
      "market_or_watchlist_data_degraded")
check("workflow toggle suppresses recommendations",
      disabled["recommendation_panel"]["count"] == 0
      and disabled["recommendation_panel"]["suppression_reason"] ==
      "disabled_by_workflow_parameter")

# Cap and dedupe hold across both watchlist shards.
many_inputs = dict(base_inputs)
many_inputs["watch_a"] = {
    "names": [{"symbol": symbol, "hlcv": hlcv(0.003, seed=i)}
              for i, symbol in enumerate(("AAA", "BBB", "CCC"), 30)],
    "assigned": ["AAA", "BBB", "CCC"], "skipped": [], "data_source_status": "ok"}
many_inputs["watch_b"] = {
    "names": [{"symbol": symbol, "hlcv": hlcv(0.003, seed=i)}
              for i, symbol in enumerate(("DDD", "EEE", "FFF"), 40)],
    "assigned": ["DDD", "EEE", "FFF"], "skipped": [], "data_source_status": "ok"}
many = run_utility("command_engine", many_inputs)["command_read"]
many_recs = many["recommendation_panel"]["recommendations"]
check("recommendations capped at three and deduplicated",
      len(many_recs) == 3 and len({r["symbol"] for r in many_recs}) == 3)

# Narration verifier passes anchored output and loudly marks omissions.
headings = [
    "## Executive Read", "## Market Dashboard", "## Watchlist Changes",
    "## Today's Calendar", "## Overnight Context", "## Monitor Queue",
    "## Recommendation Panel", "## Data Quality & Method",
]
good_body = ("📋 Data: ok · market ok/watchlist ok/overnight ok/calendar ok\n\n" +
             "\n\n".join(headings) + "\nAAA Buy\n" +
             "Disclaimer: deterministic screening leads")
verified = run_utility("report_verifier", {
    "filtered_body": good_body, "command_read": result})
check("verifier accepts anchored report", verified["verification_status"] == "pass")
bad = run_utility("report_verifier", {
    "filtered_body": "short report", "command_read": result})
check("verifier loudly marks drift",
      bad["verification_status"] == "review" and "🔧 Verification: REVIEW" in bad["verified_body"])
delivery_ok = run_utility("delivery_gate", {"delivery_status_in": "sent"})
delivery_bad = run_utility("delivery_gate", {"delivery_status_in": "failed"})
check("delivery gate distinguishes success and failure",
      delivery_ok["delivery_status"] == "delivered"
      and delivery_bad["delivery_status"] == "degraded_agent_profile_only")

failed = [name for name, passed in checks if not passed]
print("\n%d/%d checks passed" % (len(checks) - len(failed), len(checks)))
if failed:
    raise SystemExit("failed: " + ", ".join(failed))
