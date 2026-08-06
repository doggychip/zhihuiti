"""Integration tests for the Oracle API server — HTTP endpoint tests."""

from __future__ import annotations

import io
import json
import os
import threading
from http.server import HTTPServer
from unittest.mock import patch

import pytest

import zhihuiti.oracle_server as oracle_server
from zhihuiti.oracle_server import (
    OracleHandler,
    _json_response,
    _parse_csv_values,
    _read_body,
)
from zhihuiti.env import env_enabled


# ── Helpers ────────────────────────────────────────────────────────────────

def _start_server(port: int = 0) -> tuple[HTTPServer, int]:
    """Start the oracle server on a random port. Returns (server, port)."""
    server = HTTPServer(("127.0.0.1", port), OracleHandler)
    actual_port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, actual_port


def _get(port: int, path: str) -> tuple[int, dict]:
    """Send a GET request and return (status_code, json_body)."""
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = json.loads(resp.read().decode())
    status = resp.status
    conn.close()
    return status, body


def _post(port: int, path: str, data: dict, token: str | None = "test-token") -> tuple[int, dict]:
    """Send a POST request with JSON body."""
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    resp_body = json.loads(resp.read().decode())
    status = resp.status
    conn.close()
    return status, resp_body


@pytest.fixture(scope="module")
def server():
    """Module-scoped test server."""
    previous_token = os.environ.get("ZHIHUITI_API_TOKEN")
    os.environ["ZHIHUITI_API_TOKEN"] = "test-token"
    srv, port = _start_server()
    yield port
    srv.shutdown()
    if previous_token is None:
        os.environ.pop("ZHIHUITI_API_TOKEN", None)
    else:
        os.environ["ZHIHUITI_API_TOKEN"] = previous_token


# ── Health endpoint ───────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self, server):
        status, body = _get(server, "/health")
        assert status == 200
        assert body["status"] == "ok"
        assert body["service"] == "zhihuiti"

    def test_healthz_reports_runtime_without_secrets(self, server, monkeypatch):
        monkeypatch.delenv("ZEABUR_GIT_COMMIT_SHA", raising=False)
        monkeypatch.setenv("ZHIHUITI_COMMIT_SHA", "abc123")
        status, body = _get(server, "/healthz")
        assert status == 200
        assert body["commit"] == "abc123"
        assert "api_key" not in body

    def test_healthz_prefers_zeabur_deployment_commit(self, server, monkeypatch):
        monkeypatch.setenv("ZHIHUITI_COMMIT_SHA", "stale-manual-value")
        monkeypatch.setenv("ZEABUR_GIT_COMMIT_SHA", "current-deployment")

        status, body = _get(server, "/healthz")

        assert status == 200
        assert body["commit"] == "current-deployment"

    def test_readyz_checks_configuration_without_model_call(self, server, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "configured-for-test")
        status, body = _get(server, "/readyz")
        assert status == 200
        assert body["status"] == "ready"
        assert body["provider"] == "deepseek"
        assert body["operator_api_configured"] is True


class TestOperatorProtection:
    def test_post_requires_bearer_token(self, server):
        status, body = _post(server, "/api/oracle/diagnose", {}, token=None)
        assert status == 401
        assert body["error"] == "operator authorization required"

    def test_post_rejects_wrong_bearer_token(self, server):
        status, _ = _post(server, "/api/oracle/diagnose", {}, token="wrong")
        assert status == 401

    def test_post_fails_closed_without_configured_token(self, server, monkeypatch):
        monkeypatch.delenv("ZHIHUITI_API_TOKEN")
        status, body = _post(server, "/api/oracle/diagnose", {})
        assert status == 503
        assert body["error"] == "operator API is not configured"

    def test_rejects_oversized_body(self, server, monkeypatch):
        monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "8")
        status, body = _post(server, "/api/oracle/diagnose", {"values": [1, 2, 3]})
        assert status == 413
        assert body["error"] == "request body too large"

    def test_goal_result_requires_bearer_token(self, server):
        status, body = _get(server, "/api/goals/example")
        assert status == 401
        assert body["error"] == "operator authorization required"


class TestCorsPolicy:
    def test_allows_configured_frontend_origin(self, server):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", server, timeout=5)
        conn.request("GET", "/healthz", headers={"Origin": "https://zhihuiti.lovable.app"})
        resp = conn.getresponse()
        resp.read()
        assert resp.getheader("Access-Control-Allow-Origin") == "https://zhihuiti.lovable.app"
        conn.close()

    def test_does_not_allow_unconfigured_origin(self, server):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", server, timeout=5)
        conn.request("GET", "/healthz", headers={"Origin": "https://example.invalid"})
        resp = conn.getresponse()
        resp.read()
        assert resp.getheader("Access-Control-Allow-Origin") is None
        conn.close()


class TestPublicEvolutionStatus:
    def test_exposes_aggregate_status_without_goal_content(self, server):
        status, body = _get(server, "/api/evolution")
        assert status == 200
        assert set(body) == {
            "running",
            "total_goals_run",
            "completed",
            "failed",
            "autonomous_evolution",
        }
        assert "recent_goals" not in body


class TestMacroRefreshStatus:
    def test_history_is_empty_before_first_refresh(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZHIHUITI_DB", str(tmp_path / "new.db"))

        assert oracle_server._macro_history_query() == []

    def test_pending_feed_is_explicitly_fallback_data(self, monkeypatch):
        monkeypatch.setattr(oracle_server, "_ensure_refresher", lambda: None)
        monkeypatch.setattr(oracle_server, "_MACRO_META", {
            "last_attempt_at": None,
            "refreshed_at": None,
            "sources": {},
            "errors": [],
            "live_fields": 0,
        })

        feed = oracle_server._macro_feed()

        assert feed["refresh_status"] == "pending"
        assert feed["data_mode"] == "fallback"
        assert "fallback" in feed["source"].lower()

    def test_live_feed_reports_provenance(self, monkeypatch):
        monkeypatch.setattr(oracle_server, "_ensure_refresher", lambda: None)
        monkeypatch.setattr(oracle_server, "_MACRO_META", {
            "last_attempt_at": "2026-08-04T02:00:00+00:00",
            "refreshed_at": "2026-08-04T02:00:10+00:00",
            "sources": {"y10": "FRED"},
            "errors": ["gold:TimeoutError"],
            "live_fields": 1,
        })

        feed = oracle_server._macro_feed()

        assert feed["refresh_status"] == "partial"
        assert feed["data_mode"] == "live"
        assert feed["refresh_errors"] == ["gold:TimeoutError"]

    def test_failed_refresh_does_not_redate_fallback_snapshot(self, tmp_path, monkeypatch):
        snapshot = {
            **oracle_server._MACRO_SNAPSHOT,
            "asof": "2026-06-29",
            "curveDate": "2026-06-26",
        }
        monkeypatch.setattr(oracle_server, "_MACRO_SNAPSHOT", snapshot)
        monkeypatch.setattr(oracle_server, "_MACRO_META", {
            "last_attempt_at": None,
            "refreshed_at": None,
            "sources": {},
            "errors": [],
            "live_fields": 0,
        })
        monkeypatch.setenv("ZHIHUITI_DB", str(tmp_path / "macro.db"))
        monkeypatch.setattr(oracle_server, "_fred_series", lambda *args, **kwargs: None)
        monkeypatch.setattr(oracle_server, "_stooq_close", lambda *args, **kwargs: None)
        monkeypatch.setattr(oracle_server, "_yahoo_price", lambda *args, **kwargs: None)
        monkeypatch.setattr(oracle_server, "_yahoo_chg_pct", lambda *args, **kwargs: None)

        oracle_server._refresh_macro_snapshot()

        assert oracle_server._MACRO_SNAPSHOT["asof"] == "2026-06-29"
        assert oracle_server._MACRO_META["refreshed_at"] is None
        assert oracle_server._MACRO_META["live_fields"] == 0
        assert not (tmp_path / "macro.db").exists()


class TestEnvironmentFlags:
    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_explicit_true_values_enable_flag(self, monkeypatch, value):
        monkeypatch.setenv("TEST_FEATURE_FLAG", value)
        assert env_enabled("TEST_FEATURE_FLAG") is True

    @pytest.mark.parametrize("value", ["", "0", "false", "FALSE", "no", "off", "disabled"])
    def test_false_and_unknown_values_do_not_enable_flag(self, monkeypatch, value):
        monkeypatch.setenv("TEST_FEATURE_FLAG", value)
        assert env_enabled("TEST_FEATURE_FLAG") is False


# ── 404 handling ──────────────────────────────────────────────────────────

class TestNotFound:
    def test_unknown_path_returns_404(self, server):
        status, body = _get(server, "/api/nonexistent")
        assert status == 404
        assert "error" in body

    def test_unknown_post_returns_404(self, server):
        status, body = _post(server, "/api/nonexistent", {})
        assert status == 404


# ── Domains endpoint ──────────────────────────────────────────────────────

class TestDomainsEndpoint:
    def test_lists_all_five_domains(self, server):
        status, body = _get(server, "/api/oracle/domains")
        assert status == 200
        assert "domains" in body
        assert set(body["domains"].keys()) == {"crypto", "system_perf", "social", "business", "scientific"}

    def test_each_domain_has_metadata(self, server):
        status, body = _get(server, "/api/oracle/domains")
        for key, domain in body["domains"].items():
            assert "name" in domain, f"{key} missing name"
            assert "description" in domain, f"{key} missing description"
            assert domain["pattern_count"] >= 3


# ── Diagnose endpoint (POST) ─────────────────────────────────────────────

class TestDiagnoseEndpoint:
    def test_happy_path_scientific(self, server):
        values = [100 + i * 2 for i in range(50)]
        status, body = _post(server, "/api/oracle/diagnose", {
            "values": values,
            "domain": "scientific",
            "label": "temperature (K)",
        })
        assert status == 200
        assert body["domain"] == "scientific"
        assert body["label"] == "temperature (K)"
        assert body["regime"] in ("trending_up", "trending_down", "mean_reverting", "volatile", "quiet")
        assert isinstance(body["patterns"], list)

    def test_system_perf_domain(self, server):
        values = [50 + i * 0.5 for i in range(50)]
        status, body = _post(server, "/api/oracle/diagnose", {
            "values": values,
            "domain": "system_perf",
            "label": "API latency (ms)",
        })
        assert status == 200
        assert body["domain_name"] == "System Performance"

    def test_rejects_too_few_values(self, server):
        status, body = _post(server, "/api/oracle/diagnose", {
            "values": [1, 2, 3],
            "domain": "scientific",
        })
        assert status == 400
        assert "at least 5" in body["error"]

    def test_rejects_unknown_domain(self, server):
        status, body = _post(server, "/api/oracle/diagnose", {
            "values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "domain": "nonexistent",
        })
        assert status == 400
        assert "unknown domain" in body["error"]
        assert "available" in body

    def test_empty_body(self, server):
        status, body = _post(server, "/api/oracle/diagnose", {})
        assert status == 400


# ── CSV upload endpoint ───────────────────────────────────────────────────

class TestCSVUploadEndpoint:
    def test_json_values_upload(self, server):
        values = [100 + i for i in range(30)]
        status, body = _post(server, "/api/oracle/csv", {
            "values": values,
            "domain": "business",
            "label": "MRR ($)",
        })
        assert status == 200
        assert body["domain"] == "business"

    def test_csv_string_upload(self, server):
        csv = "timestamp,value\n" + "\n".join(f"2026-01-{i+1:02d},{100+i}" for i in range(30))
        status, body = _post(server, "/api/oracle/csv", {
            "csv": csv,
            "column": "value",
            "domain": "scientific",
            "label": "sensor reading",
        })
        assert status == 200
        assert body["domain"] == "scientific"

    def test_rejects_too_few_csv_values(self, server):
        status, body = _post(server, "/api/oracle/csv", {
            "values": [1, 2],
        })
        assert status == 400


# ── Theory search endpoint ────────────────────────────────────────────────

class TestTheorySearchEndpoint:
    def test_search_requires_query(self, server):
        status, body = _get(server, "/api/oracle/theories/search")
        assert status == 400
        assert "required" in body["error"]

    def test_search_returns_results(self, server):
        status, body = _get(server, "/api/oracle/theories/search?q=entropy")
        assert status == 200
        assert "results" in body
        assert isinstance(body["results"], list)


# ── Theory stats endpoint ────────────────────────────────────────────────

class TestTheoryStatsEndpoint:
    def test_returns_stats(self, server):
        status, body = _get(server, "/api/oracle/theories/stats")
        assert status == 200
        assert isinstance(body, dict)


# ── Alerts endpoint ───────────────────────────────────────────────────────

class TestAlertsEndpoint:
    def test_alerts_initially_empty(self, server):
        status, body = _get(server, "/api/oracle/alerts")
        assert status == 200
        assert isinstance(body["alerts"], list)


# ── CSV parser unit tests ─────────────────────────────────────────────────

class TestParseCsv:
    def test_basic_csv(self):
        csv = "ts,value\n1,10.5\n2,20.3\n3,30.1"
        result = _parse_csv_values(csv, "value")
        assert result == [10.5, 20.3, 30.1]

    def test_fallback_to_last_column(self):
        csv = "ts,reading\n1,10\n2,20"
        result = _parse_csv_values(csv, "nonexistent")
        assert result == [10.0, 20.0]

    def test_empty_csv(self):
        assert _parse_csv_values("", "value") == []

    def test_skips_non_numeric(self):
        csv = "ts,value\n1,10\n2,bad\n3,30"
        result = _parse_csv_values(csv, "value")
        assert result == [10.0, 30.0]
