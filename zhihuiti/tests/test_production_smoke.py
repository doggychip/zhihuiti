from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[2] / "scripts" / "production_smoke.py"
SPEC = importlib.util.spec_from_file_location("production_smoke", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _responses(scan_age: int = 60, warnings: list[str] | None = None):
    return {
        "/health": {
            "status": "ok",
            "commit": "abc123",
            "backend_id": "canonical",
            "storage": {
                "identity_persisted": True,
                "instance_id": "instance-1",
                "database": {"exists": True},
            },
        },
        "/readyz": {"status": "ready"},
        "/api/status": {
            "governance": {
                "autonomous_evolution": False,
                "auto_mint_enabled": False,
                "active_agents": 1,
                "max_active_agents": 36,
            },
            "realms": {"macro": {"budget_remaining": 1}},
        },
        "/api/oracle/theories/stats": {"theories": 296},
        "/api/oracle/scan/status": {
            "last_completed_at": "2026-08-08T00:00:00+00:00",
            "errors": [],
        },
        "/api/backtest/accuracy": {"persistence_baseline_accuracy": 0.96},
        "/api/oracle/alerts?limit=50": {
            "alerts": [{"source": "oracle_agent", "execution": "observation_only"}],
        },
        "/api/operations/status": {
            "warnings": warnings or ["forecast_not_better_than_baseline"],
            "scan": {"age_seconds": scan_age, "stale_after_seconds": 3600},
        },
    }


def test_known_forecast_warning_does_not_mask_healthy_production(monkeypatch):
    responses = _responses()
    monkeypatch.setattr(MODULE, "fetch_json", lambda _base, path: responses[path])

    result = MODULE.verify("https://example.test", expected_instance_id="instance-1")

    assert result["ok"] is True
    assert result["checks"]["scan_fresh"] is True
    assert result["operations_warnings"] == ["forecast_not_better_than_baseline"]


def test_stale_scan_fails_production_monitor(monkeypatch):
    responses = _responses(scan_age=4000, warnings=["scan_stale"])
    monkeypatch.setattr(MODULE, "fetch_json", lambda _base, path: responses[path])

    result = MODULE.verify("https://example.test")

    assert result["ok"] is False
    assert result["checks"]["scan_fresh"] is False
    assert result["checks"]["operations"] is False
