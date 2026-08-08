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


def verify(
    base_url: str,
    expected_commit: str = "",
    expected_backend_id: str = "canonical",
    expected_instance_id: str = "",
) -> dict:
    health = fetch_json(base_url, "/health")
    ready = fetch_json(base_url, "/readyz")
    status = fetch_json(base_url, "/api/status")
    theories = fetch_json(base_url, "/api/oracle/theories/stats")
    scan = fetch_json(base_url, "/api/oracle/scan/status")
    accuracy = fetch_json(base_url, "/api/backtest/accuracy")
    alerts = fetch_json(base_url, "/api/oracle/alerts?limit=50")
    operations = fetch_json(base_url, "/api/operations/status")
    governance = status.get("governance", {})
    realms = status.get("realms", {})
    storage = health.get("storage", {})
    operation_warnings = set(operations.get("warnings", []))
    non_incident_warnings = {
        "forecast_collecting",
        "forecast_not_better_than_baseline",
    }
    scan_age = operations.get("scan", {}).get("age_seconds")
    stale_after = operations.get("scan", {}).get("stale_after_seconds")

    checks = {
        "health": health.get("status") == "ok",
        "ready": ready.get("status") == "ready",
        "commit": not expected_commit or health.get("commit") == expected_commit,
        "canonical_backend": (
            not expected_backend_id or health.get("backend_id") == expected_backend_id
        ),
        "persistent_instance": (
            storage.get("identity_persisted") is True
            and storage.get("database", {}).get("exists") is True
            and (
                not expected_instance_id
                or storage.get("instance_id") == expected_instance_id
            )
        ),
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
        "scan_fresh": (
            isinstance(scan_age, int)
            and isinstance(stale_after, int)
            and scan_age <= stale_after
        ),
        "operations": not (operation_warnings - non_incident_warnings),
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
        "backend_id": health.get("backend_id"),
        "instance_id": storage.get("instance_id"),
        "scan_completed_at": scan.get("last_completed_at"),
        "operations_warnings": sorted(operation_warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url", default="https://zhihuiti.zeabur.app",
    )
    parser.add_argument("--expected-commit", default="")
    parser.add_argument("--expected-backend-id", default="canonical")
    parser.add_argument("--expected-instance-id", default="")
    parser.add_argument("--timeout", type=int, default=0)
    args = parser.parse_args()

    deadline = time.time() + max(0, args.timeout)
    last_error = ""
    while True:
        try:
            result = verify(
                args.base_url,
                args.expected_commit,
                args.expected_backend_id,
                args.expected_instance_id,
            )
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
