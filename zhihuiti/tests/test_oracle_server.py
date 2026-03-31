"""Integration tests for the Oracle API server — HTTP endpoint tests."""

from __future__ import annotations

import io
import json
import threading
from http.server import HTTPServer
from unittest.mock import patch

import pytest

from zhihuiti.oracle_server import OracleHandler, _json_response, _read_body, _parse_csv_values


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


def _post(port: int, path: str, data: dict) -> tuple[int, dict]:
    """Send a POST request with JSON body."""
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(data).encode()
    conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    resp_body = json.loads(resp.read().decode())
    status = resp.status
    conn.close()
    return status, resp_body


@pytest.fixture(scope="module")
def server():
    """Module-scoped test server."""
    srv, port = _start_server()
    yield port
    srv.shutdown()


# ── Health endpoint ───────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self, server):
        status, body = _get(server, "/health")
        assert status == 200
        assert body["status"] == "ok"
        assert body["service"] == "zhihuiti-oracle"


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
