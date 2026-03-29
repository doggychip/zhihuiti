"""Standalone Oracle API server — serves oracle endpoints without requiring an LLM.

This is a lightweight HTTP server that only exposes the oracle, scanner, and
theory intelligence endpoints. No orchestrator, no agents, no LLM needed.

Usage:
  python -m zhihuiti.oracle_server              # port 8377
  python -m zhihuiti.oracle_server --port 9000  # custom port

Environment:
  PORT=8377          — port to listen on (overridden by --port)
  CORS_ORIGIN=*      — CORS origin header
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from rich.console import Console

console = Console()


def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200):
    handler.send_response(status)
    origin = os.environ.get("CORS_ORIGIN", "*")
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", origin)
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode())


def _read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw)


# Lazy-initialized history tracker
_history = None
_history_lock = threading.Lock()


def _get_history():
    global _history
    if _history is None:
        with _history_lock:
            if _history is None:
                from zhihuiti.scanner import RegimeHistory
                _history = RegimeHistory()
    return _history


def _fetch_crypto_candles(instrument: str, timeframe: str) -> list[dict]:
    try:
        import httpx
        resp = httpx.get(
            "https://api.crypto.com/exchange/v1/public/get-candlestick",
            params={"instrument_name": instrument, "timeframe": timeframe},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("result", {}).get("data", data.get("data", []))
        return [
            {
                "open": c.get("o", c.get("open", 0)),
                "high": c.get("h", c.get("high", 0)),
                "low": c.get("l", c.get("low", 0)),
                "close": c.get("c", c.get("close", 0)),
                "volume": c.get("v", c.get("volume", 0)),
            }
            for c in raw
        ]
    except Exception:
        return []


def _fetch_crypto_book(instrument: str) -> dict | None:
    try:
        import httpx
        resp = httpx.get(
            "https://api.crypto.com/exchange/v1/public/get-book",
            params={"instrument_name": instrument, "depth": 20},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {}).get("data", [data.get("result", {})])
        if isinstance(result, list) and result:
            result = result[0]
        return {"bids": result.get("bids", []), "asks": result.get("asks", [])}
    except Exception:
        return None


class OracleHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _json_response(self, {})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            _json_response(self, {"status": "ok", "service": "zhihuiti-oracle"})

        elif path == "/api/oracle/scan":
            self._handle_scan(qs)
        elif path.startswith("/api/oracle/crypto/"):
            instrument = path.split("/")[-1]
            self._handle_crypto(instrument, qs)
        elif path == "/api/oracle/domains":
            self._handle_domains()
        elif path == "/api/oracle/theories/stats":
            self._handle_theory_stats()
        elif path == "/api/oracle/theories/search":
            q = qs.get("q", [""])[0]
            limit = int(qs.get("limit", ["10"])[0])
            self._handle_theory_search(q, limit)
        elif path.startswith("/api/oracle/history/"):
            instrument = path.split("/")[-1]
            limit = int(qs.get("limit", ["50"])[0])
            self._handle_history(instrument, limit)
        elif path == "/api/oracle/transitions":
            instrument = qs.get("instrument", [None])[0]
            limit = int(qs.get("limit", ["20"])[0])
            self._handle_transitions(instrument, limit)
        elif path == "/api/oracle/summary":
            self._handle_summary()
        else:
            _json_response(self, {"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/oracle/diagnose":
            self._handle_diagnose()
        else:
            _json_response(self, {"error": "not found"}, 404)

    # ── Handlers ───────────────────────────────────────────────

    def _handle_scan(self, qs):
        try:
            from zhihuiti.scanner import scan_instruments
            timeframe = qs.get("timeframe", ["4h"])[0]
            pairs = qs.get("pairs", [None])[0]
            instruments = pairs.split(",") if pairs else None

            results = scan_instruments(
                instruments=instruments,
                timeframe=timeframe,
                fetch_fn=_fetch_crypto_candles,
            )

            history = _get_history()
            transitions = history.record_scan(results)

            _json_response(self, {
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "transitions": [t.to_dict() for t in transitions],
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_crypto(self, instrument, qs):
        try:
            from zhihuiti.crypto_oracle import diagnose_market
            timeframe = qs.get("timeframe", ["4h"])[0]
            include_book = qs.get("book", ["0"])[0] in ("1", "true")

            candles = _fetch_crypto_candles(instrument, timeframe)
            if not candles:
                _json_response(self, {"error": f"no candle data for {instrument}"}, 404)
                return

            book = _fetch_crypto_book(instrument) if include_book else None
            diagnosis = diagnose_market(candles, instrument=instrument, book=book)
            _json_response(self, diagnosis.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_domains(self):
        try:
            from zhihuiti.universal_oracle import DOMAINS
            domains = {}
            for key, profile in DOMAINS.items():
                domains[key] = {
                    "name": profile.name,
                    "description": profile.description,
                    "pattern_count": len(profile.pattern_theories),
                    "regime_count": len(profile.regime_theories),
                }
            _json_response(self, {"domains": domains})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_theory_stats(self):
        try:
            from zhihuiti.theory_intelligence import get_graph
            _json_response(self, get_graph().get_stats())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_theory_search(self, query, limit):
        try:
            if not query:
                _json_response(self, {"error": "query parameter 'q' is required"}, 400)
                return
            from zhihuiti.theory_intelligence import get_graph
            results = get_graph().search_theories(query, limit=min(limit, 50))
            compact = [{"id": r["id"], "name": r.get("name", ""), "domain": r.get("domain", "")} for r in results]
            _json_response(self, {"results": compact, "count": len(compact)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_diagnose(self):
        try:
            body = _read_body(self)
            values = body.get("values", [])
            if not values or len(values) < 5:
                _json_response(self, {"error": "need at least 5 data points"}, 400)
                return
            domain = body.get("domain", "scientific")
            label = body.get("label", "time series")

            from zhihuiti.universal_oracle import diagnose, DOMAINS
            if domain not in DOMAINS:
                _json_response(self, {"error": f"unknown domain: {domain}", "available": list(DOMAINS.keys())}, 400)
                return

            result = diagnose(values, domain=domain, label=label)
            _json_response(self, result.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_history(self, instrument, limit):
        try:
            history = _get_history()
            snapshots = history.get_history(instrument, limit=limit)
            _json_response(self, {"instrument": instrument, "snapshots": snapshots, "count": len(snapshots)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_transitions(self, instrument, limit):
        try:
            history = _get_history()
            transitions = history.get_transitions(instrument=instrument, limit=limit)
            _json_response(self, {"transitions": transitions, "count": len(transitions)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_summary(self):
        try:
            history = _get_history()
            summary = history.get_summary()
            _json_response(self, {"instruments": summary, "count": len(summary)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)


def serve(port: int | None = None):
    """Start the standalone Oracle API server."""
    port = port or int(os.environ.get("PORT", 8377))

    console.print(f"\n[bold]Oracle API Server[/bold]")
    console.print(f"  Listening on http://0.0.0.0:{port}")
    console.print(f"  GET  /api/oracle/scan")
    console.print(f"  GET  /api/oracle/crypto/:instrument")
    console.print(f"  POST /api/oracle/diagnose")
    console.print(f"  GET  /api/oracle/domains")
    console.print(f"  GET  /api/oracle/theories/stats")
    console.print(f"  GET  /api/oracle/theories/search?q=...")
    console.print(f"  GET  /api/oracle/summary")
    console.print(f"  GET  /api/oracle/transitions")
    console.print(f"  GET  /api/oracle/history/:instrument")
    console.print(f"  GET  /health")
    console.print()

    server = HTTPServer(("0.0.0.0", port), OracleHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="zhihuiti Oracle API Server")
    parser.add_argument("--port", type=int, default=None, help="Port (default: $PORT or 8377)")
    args = parser.parse_args()
    serve(port=args.port)
