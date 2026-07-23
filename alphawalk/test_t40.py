#!/usr/bin/env python3
"""Offline structural and deterministic golden tests for T40."""
import ast
import datetime
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backtest_t40
import validate_t40_live_capture

PATH = os.path.join(HERE, "T40---AlphaWalk-Morning-Command-Center-v1.3.0.json")
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


def closes(drift, count=70, seed=1, end_date=datetime.date(2026, 7, 22)):
    random.seed(seed)
    price = 100.0
    values = []
    start = end_date - datetime.timedelta(days=count - 1)
    for index in range(count):
        price *= 1.0 + drift + random.gauss(0, 0.001)
        values.append("%s,%.2f" % ((start + datetime.timedelta(days=index)).isoformat(), price))
    return "\n".join(values)


def hlcv(drift, count=60, seed=1, end_date=datetime.date(2026, 7, 22)):
    random.seed(seed)
    price = 100.0
    rows = []
    start = end_date - datetime.timedelta(days=count - 1)
    for index in range(count):
        price *= 1.0 + drift + random.gauss(0, 0.001)
        rows.append("%s,%.2f,%.2f,%.2f,%d" %
                    ((start + datetime.timedelta(days=index)).isoformat(),
                     price * 1.01, price * 0.99, price,
                     1_000_000 + random.randint(0, 100_000)))
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
      any(e.get("from") == "publication_gate" and e.get("from_slot") == "approved_recommendations"
          and e.get("to") == "notifier" and e.get("to_slot") == "recommendations"
          for e in template["dag_definition"]["edges"]))
check("recommendations default to shadow mode",
      template["workflow_param_schema"]["recommendation_mode"]["default"] == "shadow")
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
    {"symbol": symbol, "dated_closes": closes(0.002, seed=i),
     "exchange_timezone": "America/New_York", "session": "regular"}
    for i, symbol in enumerate(("SPY", "QQQ", "IWM", "TLT", "GLD", "USO"), 1)
]
def watch_name(symbol, drift, seed, end_date=datetime.date(2026, 7, 22)):
    return {
        "symbol": symbol,
        "price_identity": {
            "symbol": symbol, "legal_company_name": symbol + " Corp",
            "exchange": "NASDAQ", "currency": "USD"},
        "fundamental_identity": {
            "symbol": symbol, "issuer_id": "issuer-" + symbol.lower(),
            "legal_company_name": symbol + " Corporation",
            "exchange": "NASDAQ", "currency": "USD"},
        "exchange_timezone": "America/New_York",
        "session": "regular",
        "dated_hlcv": hlcv(drift, seed=seed, end_date=end_date),
    }


base_inputs = {
    "market_bars": {
        "names": market_names, "as_of": "2026-07-23T11:00:00Z", "data_source_status": "ok"},
    "watch_a": {
        "names": [watch_name("AAA", 0.003, 10)],
        "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"},
    "watch_b": {
        "names": [], "assigned": [], "skipped": [], "data_source_status": "ok"},
    "overnight_context": {
        "items": [{"headline": "Verified item", "fact": "A dated fact",
                   "source": "Example", "source_date": "2026-07-23"}],
        "data_source_status": "ok"},
    "today_calendar": {
        "date": "2026-07-23",
        "events": [{"time_et": "08:30", "kind": "macro", "title": "CPI",
                    "impact": "high", "source": "BLS"}],
        "data_source_status": "ok"},
}
result = run_utility("command_engine", base_inputs, {
    "portfolio": "AAA 25%", "recommendation_mode": "live"})["command_read"]
check("constructive regime", result["market_regime"] == "constructive")
check("strengthening classification", result["watchlist"][0]["status"] == "strengthening")
check("portfolio weight normalized", result["watchlist"][0]["portfolio_weight_pct"] == 25.0)
check("calendar has first priority", result["priorities"][0]["type"] == "calendar")
check("healthy run status", result["overall_status"] == "ok")
check("complete creation contract is verified",
      result["prepublication_state"] == "verified"
      and result["expected_latest_session"] == "2026-07-22"
      and result["coverage"]["coverage_ratio"] == 1.0
      and result["creation_contract"]["minimum_coverage_threshold"] == 0.8)
check("watchlist coverage", result["coverage"]["watchlist_resolved"] == 1
      and result["coverage"]["watchlist_total"] == 1)
check("constructive structure emits capped Tier-B Buy",
      len(result["recommendation_panel"]["recommendations"]) == 1
      and result["recommendation_panel"]["recommendations"][0]["action"] == "Buy"
      and len(result["recommendation_panel"]["recommendations"][0]["rationale"]) <= 200)

# Defensive market emits Sell under the symmetric fixed rule.
defensive_inputs = dict(base_inputs)
defensive_inputs["market_bars"] = {
    "names": [{"symbol": symbol, "dated_closes": closes(-0.002, seed=i),
               "exchange_timezone": "America/New_York", "session": "regular"}
              for i, symbol in enumerate(("SPY", "QQQ", "IWM", "TLT", "GLD", "USO"), 20)],
    "as_of": "2026-07-23T11:00:00Z", "data_source_status": "ok"}
defensive_inputs["watch_a"] = {
    "names": [watch_name("AAA", -0.003, 11)],
    "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"}
defensive = run_utility("command_engine", defensive_inputs, {
    "portfolio": "AAA 0.25", "recommendation_mode": "live"})["command_read"]
check("defensive regime", defensive["market_regime"] == "defensive")
check("weakening classification", defensive["watchlist"][0]["status"] == "weakening")
check("weakening portfolio priority", any(p["type"] == "portfolio_structure"
                                          for p in defensive["priorities"]))
check("defensive structure emits Tier-B Sell",
      defensive["recommendation_panel"]["recommendations"][0]["action"] == "Sell")

# Degraded core data and explicit toggle both suppress recommendations.
degraded_inputs = dict(base_inputs)
degraded_inputs["market_bars"] = dict(base_inputs["market_bars"], data_source_status="partial")
degraded = run_utility("command_engine", degraded_inputs, {
    "portfolio": "AAA 25%", "recommendation_mode": "live"})["command_read"]
disabled = run_utility("command_engine", base_inputs, {
    "portfolio": "AAA 25%", "recommendations_enabled": False})["command_read"]
check("degraded core lane suppresses recommendations",
      degraded["recommendation_panel"]["count"] == 0
      and degraded["recommendation_panel"]["suppression_reason"] ==
      "publication_contract_not_verified")
check("workflow toggle suppresses recommendations",
      disabled["recommendation_panel"]["count"] == 0
      and disabled["recommendation_panel"]["suppression_reason"] ==
      "disabled_by_workflow_parameter")
missing_identity_inputs = dict(base_inputs)
bad_name = watch_name("AAA", 0.003, 10)
bad_name["fundamental_identity"]["issuer_id"] = None
missing_identity_inputs["watch_a"] = {
    "names": [bad_name], "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"}
missing_identity = run_utility("command_engine", missing_identity_inputs)["command_read"]
check("missing issuer identity creates data exception",
      missing_identity["prepublication_state"] == "data_exception"
      and missing_identity["watchlist"][0]["entity_validity"] == "missing")
identity_mismatch_inputs = dict(base_inputs)
mismatch_name = watch_name("AAA", 0.003, 10)
mismatch_name["price_identity"]["legal_company_name"] = "Different Issuer Inc"
identity_mismatch_inputs["watch_a"] = {
    "names": [mismatch_name], "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"}
identity_mismatch = run_utility("command_engine", identity_mismatch_inputs)["command_read"]
check("cross-source issuer mismatch creates data exception",
      identity_mismatch["prepublication_state"] == "data_exception"
      and identity_mismatch["watchlist"][0]["entity_reason"] ==
      "cross-source identity mismatch")
shadow = run_utility("command_engine", base_inputs, {
    "portfolio": "AAA 25%", "recommendation_mode": "shadow"})["command_read"]
killed = run_utility("command_engine", base_inputs, {
    "portfolio": "AAA 25%", "recommendation_mode": "live",
    "emergency_kill_switch": True})["command_read"]
check("shadow computes candidates while kill switch suppresses",
      shadow["recommendation_panel"]["count"] == 1
      and shadow["recommendation_panel"]["mode"] == "shadow"
      and killed["recommendation_panel"]["count"] == 0
      and killed["recommendation_panel"]["suppression_reason"] ==
      "emergency_kill_switch_active")

# Monday after observed Independence Day resolves to Thursday's completed session.
holiday_end = datetime.date(2026, 7, 2)
holiday_inputs = dict(base_inputs)
holiday_inputs["market_bars"] = {
    "names": [{"symbol": symbol, "dated_closes": closes(0.002, seed=i, end_date=holiday_end),
               "exchange_timezone": "America/New_York", "session": "regular"}
              for i, symbol in enumerate(("SPY", "QQQ", "IWM", "TLT", "GLD", "USO"), 50)],
    "as_of": "2026-07-06T11:00:00Z", "data_source_status": "ok"}
holiday_inputs["watch_a"] = {
    "names": [watch_name("AAA", 0.003, 60, end_date=holiday_end)],
    "assigned": ["AAA"], "skipped": [], "data_source_status": "ok"}
holiday_inputs["overnight_context"] = {
    "items": [], "data_source_status": "ok"}
holiday_inputs["today_calendar"] = {
    "date": "2026-07-06", "events": [], "data_source_status": "ok"}
holiday = run_utility("command_engine", holiday_inputs)["command_read"]
check("exchange calendar handles observed holiday weekend",
      holiday["expected_latest_session"] == "2026-07-02"
      and holiday["prepublication_state"] == "verified")

# Cap and dedupe hold across both watchlist shards.
many_inputs = dict(base_inputs)
many_inputs["watch_a"] = {
    "names": [watch_name(symbol, 0.003, i)
              for i, symbol in enumerate(("AAA", "BBB", "CCC"), 30)],
    "assigned": ["AAA", "BBB", "CCC"], "skipped": [], "data_source_status": "ok"}
many_inputs["watch_b"] = {
    "names": [watch_name(symbol, 0.003, i)
              for i, symbol in enumerate(("DDD", "EEE", "FFF"), 40)],
    "assigned": ["DDD", "EEE", "FFF"], "skipped": [], "data_source_status": "ok"}
many = run_utility("command_engine", many_inputs, {"recommendation_mode": "live"})["command_read"]
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
             result["recommendation_panel"]["recommendations"][0]["rationale"] + "\n" +
             "Disclaimer: deterministic screening leads")
verified = run_utility("report_verifier", {
    "filtered_body": good_body, "command_read": result})
check("verifier accepts anchored report", verified["verification_status"] == "pass")
bad = run_utility("report_verifier", {
    "filtered_body": "short report", "command_read": result})
check("verifier loudly marks drift",
      bad["verification_status"] == "review" and "🔧 Verification: REVIEW" in bad["verified_body"])
invented_number = run_utility("report_verifier", {
    "filtered_body": good_body + "\nInvented metric 987654.321", "command_read": result})
check("verifier rejects unreproducible number",
      invented_number["verification_status"] == "review"
      and any("unreproducible rendered numbers" in issue
              for issue in invented_number["verification_issues"]))
published = run_utility("publication_gate", {
    "verified_body": verified["verified_body"],
    "verification_status": "pass",
    "compliance_status": "ok",
    "command_read": result,
})
blocked = run_utility("publication_gate", {
    "verified_body": bad["verified_body"],
    "verification_status": "review",
    "compliance_status": "ok",
    "command_read": result,
})
shadow_published = run_utility("publication_gate", {
    "verified_body": verified["verified_body"],
    "verification_status": "pass",
    "compliance_status": "ok",
    "command_read": shadow,
})
check("publication gate approves verified recommendations only",
      published["publication_state"] == "verified"
      and len(published["approved_recommendations"]) == 1
      and blocked["publication_state"] == "blocked"
      and blocked["approved_recommendations"] == [])
check("shadow mode withholds notifier actions and records audit",
      shadow_published["publication_state"] == "verified"
      and shadow_published["approved_recommendations"] == []
      and shadow_published["audit_record"]["candidate_count"] == 1
      and shadow_published["audit_record"]["approved_count"] == 0)
audit_terminal = run_utility("audit_sink", {"audit_record": published["audit_record"]})
check("terminal audit exposes monitoring state",
      audit_terminal["run_audit"]["recommendation_rule_version"] == "t40-structure-v1"
      and audit_terminal["monitoring_status"] == "ok")

# The point-in-time evaluator implements the same fixed rule without future rows.
price_map = {}
for symbol, drift in {"SPY": 0.002, "QQQ": 0.002, "IWM": 0.002, "AAA": 0.003}.items():
    rows = {}
    for line in closes(drift, count=70, seed=len(symbol)).splitlines():
        day, value = line.split(",")
        rows[datetime.date.fromisoformat(day)] = float(value)
    price_map[symbol] = rows
signal_day = datetime.date(2026, 7, 22)
check("point-in-time evaluator reproduces Buy rule",
      backtest_t40.candidates_on(price_map, ["AAA"], signal_day, "constructive")[0][2] == "Buy")

valid_capture = {
    "command_read": result,
    "verification_status": "pass",
    "compliance_status": "ok",
    "publication_state": published["publication_state"],
    "approved_recommendations": published["approved_recommendations"],
    "notifier_recommendations": published["approved_recommendations"],
    "delivery_status": "delivered",
}
bad_capture = dict(valid_capture, notifier_recommendations=[])
check("live capture gate detects notifier payload drift",
      validate_t40_live_capture.validate_capture(valid_capture) == []
      and "notifier recommendation payload differs from approved payload"
      in validate_t40_live_capture.validate_capture(bad_capture))
delivery_ok = run_utility("delivery_gate", {"delivery_status_in": "sent"})
delivery_bad = run_utility("delivery_gate", {"delivery_status_in": "failed"})
check("delivery gate distinguishes success and failure",
      delivery_ok["delivery_status"] == "delivered"
      and delivery_bad["delivery_status"] == "degraded_agent_profile_only")

failed = [name for name, passed in checks if not passed]
print("\n%d/%d checks passed" % (len(checks) - len(failed), len(checks)))
if failed:
    raise SystemExit("failed: " + ", ".join(failed))
