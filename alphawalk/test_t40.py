#!/usr/bin/env python3
"""Offline structural and deterministic golden tests for T40."""
import ast
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "T40---AlphaWalk-Morning-Command-Center-v1.0.0.json")
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
check("no recommendation output or edge",
      all(e.get("from_slot") != "recommendations" for e in template["dag_definition"]["edges"])
      and all("recommendations" not in n["config"].get("output_schema", {})
              for n in template["dag_definition"]["nodes"]))
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

# Defensive market and degraded non-market lanes remain explicit.
defensive_inputs = dict(base_inputs)
defensive_inputs["market_bars"] = {
    "names": [{"symbol": symbol, "closes": closes(-0.002, seed=i)}
              for i, symbol in enumerate(("SPY", "QQQ", "IWM"), 20)],
    "as_of": "2026-07-23T11:00:00Z", "data_source_status": "partial"}
defensive_inputs["watch_a"] = {
    "names": [{"symbol": "AAA", "hlcv": hlcv(-0.003, seed=11)}],
    "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"}
defensive_inputs["overnight_context"] = {"items": [], "data_source_status": "failed"}
degraded = run_utility("command_engine", defensive_inputs, {"portfolio": "AAA 0.25"})["command_read"]
check("defensive regime", degraded["market_regime"] == "defensive")
check("weakening classification", degraded["watchlist"][0]["status"] == "weakening")
check("degraded run remains partial", degraded["overall_status"] == "partial")
check("weakening portfolio priority", any(p["type"] == "portfolio_structure"
                                          for p in degraded["priorities"]))

# Narration verifier passes anchored output and loudly marks omissions.
headings = [
    "## Executive Read", "## Market Dashboard", "## Watchlist Changes",
    "## Today's Calendar", "## Overnight Context", "## Monitor Queue",
    "## Data Quality & Method",
]
good_body = ("📋 Data: ok · market ok/watchlist ok/overnight ok/calendar ok\n\n" +
             "\n\n".join(headings) + "\nAAA\n" +
             "Disclaimer: observational morning information brief")
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
