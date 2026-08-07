#!/usr/bin/env python3
"""Read-only production verification for the public Zhihuiti runtime."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request


def fetch_json(base_url: str, path: str) -> dict:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        headers={"User-Agent": "zhihuiti-production-smoke/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def verify(base_url: str, expected_commit: str = "") -> dict:
    health = fetch_json(base_url, "/health")
    ready = fetch_json(base_url, "/readyz")
    status = fetch_json(base_url, "/api/status")
    theories = fetch_json(base_url, "/api/oracle/theories/stats")
    scan = fetch_json(base_url, "/api/oracle/scan/status")
    accuracy = fetch_json(base_url, "/api/backtest/accuracy")
    alerts = fetch_json(base_url, "/api/oracle/alerts?limit=50")
    governance = status.get("governance", {})
    realms = status.get("realms", {})

    checks = {
        "health": health.get("status") == "ok",
        "ready": ready.get("status") == "ready",
        "commit": not expected_commit or health.get("commit") == expected_commit,
        "governance": (
            governance.get("autonomous_evolution") is False
            and governance.get("auto_mint_enabled") is False
            and governance.get("active_agents", 1)
            <= governance.get("max_active_agents", 0)
        ),
        "realm_budgets": all(
            realm.get("budget_remaining", -1) >= 0 for realm in realms.values()
        ),
        "theory_graph": theories.get("theories", 0) >= 296,
        "scan_completed": bool(scan.get("last_completed_at")),
        "scan_errors": not scan.get("errors"),
        "forecast_benchmark": "persistence_baseline_accuracy" in accuracy,
        "observation_only": all(
            alert.get("execution") == "observation_only"
            for alert in alerts.get("alerts", [])
            if alert.get("source") == "oracle_agent"
        ),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "commit": health.get("commit"),
        "scan_completed_at": scan.get("last_completed_at"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url", default="https://zhihuiti-oracle.zeabur.app",
    )
    parser.add_argument("--expected-commit", default="")
    parser.add_argument("--timeout", type=int, default=0)
    args = parser.parse_args()

    deadline = time.time() + max(0, args.timeout)
    last_error = ""
    while True:
        try:
            result = verify(args.base_url, args.expected_commit)
            if result["ok"]:
                print(json.dumps(result, sort_keys=True))
                return 0
            last_error = json.dumps(result, sort_keys=True)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if time.time() >= deadline:
            print(json.dumps({"ok": False, "error": last_error}, sort_keys=True))
            return 1
        time.sleep(15)


if __name__ == "__main__":
    raise SystemExit(main())
