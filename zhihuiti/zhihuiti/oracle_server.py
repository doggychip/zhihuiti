"""Combined Oracle + Agent API server.

When an LLM key is set (OPENROUTER_API_KEY, DEEPSEEK_API_KEY, etc.), this server
boots the FULL zhihuiti orchestrator — real LLM-powered agents with token economy,
competitive bidding, bloodline inheritance, 3-layer inspection, and evolution.

Without an LLM key it falls back to oracle-only mode (market scanning, no agents).

Usage:
  python -m zhihuiti.oracle_server              # port 8377
  python -m zhihuiti.oracle_server --port 9000  # custom port

Environment:
  PORT=8377              — port to listen on (overridden by --port)
  CORS_ORIGIN=*          — CORS origin header
  OPENROUTER_API_KEY     — enables full agent system via OpenRouter
  DEEPSEEK_API_KEY       — enables full agent system via DeepSeek
  ZHIHUITI_DB            — SQLite database path (default: /app/data/zhihuiti.db)
  ZHIHUITI_AUTO_EVOLVE=1 — enable background goal execution & evolution
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

# ── Real Agent System (lazy-initialized when LLM key is present) ─────────
_orchestrator = None
_orch_lock = threading.Lock()
_orch_goals: dict[str, dict] = {}
_orch_goals_lock = threading.Lock()


def _has_llm_key() -> bool:
    """Check if any LLM API key is configured."""
    return bool(
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
    )


def _get_orchestrator():
    """Lazy-initialize the full zhihuiti Orchestrator (LLM-powered agents)."""
    global _orchestrator
    if _orchestrator is None:
        with _orch_lock:
            if _orchestrator is None:
                db_path = os.environ.get("ZHIHUITI_DB", "/app/data/zhihuiti.db")
                try:
                    from zhihuiti.orchestrator import Orchestrator
                    _orchestrator = Orchestrator(db_path=db_path, tools_enabled=False)
                    console.print("[bold green]Real agent system initialized[/bold green]")
                except Exception as e:
                    console.print(f"[bold red]Failed to init orchestrator:[/bold red] {e}")
                    raise
    return _orchestrator


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

# In-memory alert + snapshot stores
_alerts: list[dict] = []
_alerts_lock = threading.Lock()
_prev_snapshots: list = []
_prev_lock = threading.Lock()


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
            mode = "full" if _has_llm_key() else "oracle-only"
            _json_response(self, {
                "status": "ok",
                "service": "zhihuiti",
                "mode": mode,
                "agents_enabled": _has_llm_key(),
            })

        elif path == "/api/oracle/scan":
            self._handle_scan(qs)
        elif path.startswith("/api/oracle/crypto/"):
            instrument = path.split("/")[-1]
            self._handle_crypto(instrument, qs)
        elif path.startswith("/api/oracle/instrument/"):
            symbol = path.split("/")[-1]
            self._handle_instrument(symbol, qs)
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
        # ── New: equities, forex, indices ──
        elif path == "/api/oracle/scan/equities":
            self._handle_scan_equities(qs)
        elif path == "/api/oracle/scan/forex":
            self._handle_scan_forex(qs)
        elif path == "/api/oracle/scan/indices":
            self._handle_scan_indices(qs)
        # ── New: alerts ──
        elif path == "/api/oracle/alerts":
            self._handle_alerts(qs)
        # ── New: cross-domain ──
        elif path == "/api/oracle/cross-domain":
            self._handle_cross_domain(qs)
        # ── Intelligence features ──
        elif path.startswith("/api/oracle/predict/"):
            instrument = path.split("/")[-1]
            self._handle_predict(instrument, qs)
        elif path == "/api/oracle/portfolio-risk":
            self._handle_portfolio_risk(qs)
        elif path == "/api/oracle/theory-confidence":
            self._handle_theory_confidence(qs)
        elif path == "/api/oracle/compare":
            self._handle_compare(qs)
        elif path == "/api/oracle/watchlist":
            self._handle_watchlist_get()
        # ── Agent endpoints ──
        elif path == "/api/oracle/agents":
            self._handle_agents_list()
        elif path.startswith("/api/oracle/agents/") and path.count("/") == 4:
            agent_id = path.split("/")[-1]
            self._handle_agent_get(agent_id)
        elif path == "/api/oracle/agents/roles":
            self._handle_agent_roles()
        # ── Real Agent System endpoints (requires LLM key) ──
        elif path == "/api/agents":
            self._handle_real_agents_list()
        elif path == "/api/status":
            self._handle_real_status()
        elif path.startswith("/api/goals/"):
            goal_id = path.split("/")[-1]
            self._handle_real_goal_get(goal_id)
        elif path == "/api/data":
            self._handle_real_dashboard_data()
        elif path == "/api/evolution":
            self._handle_evolution_status()
        else:
            _json_response(self, {"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/oracle/diagnose":
            self._handle_diagnose()
        elif path == "/api/oracle/csv":
            self._handle_csv_upload()
        elif path == "/api/oracle/watchlist":
            self._handle_watchlist_post()
        elif path == "/api/oracle/scan/all":
            self._handle_scan_all()
        # ── Agent POST endpoints ──
        elif path == "/api/oracle/agents":
            self._handle_agent_create()
        elif path.startswith("/api/oracle/agents/") and path.endswith("/run"):
            agent_id = path.split("/")[-2]
            self._handle_agent_run(agent_id)
        elif path.startswith("/api/oracle/agents/") and path.endswith("/delete"):
            agent_id = path.split("/")[-2]
            self._handle_agent_delete(agent_id)
        elif path.startswith("/api/oracle/agents/") and path.endswith("/pause"):
            agent_id = path.split("/")[-2]
            self._handle_agent_status(agent_id, "paused")
        elif path.startswith("/api/oracle/agents/") and path.endswith("/resume"):
            agent_id = path.split("/")[-2]
            self._handle_agent_status(agent_id, "active")
        # ── Real Agent System POST endpoints ──
        elif path == "/api/goals":
            self._handle_real_goal_create()
        elif path == "/api/tasks":
            self._handle_real_single_task()
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

    def _handle_instrument(self, symbol, qs):
        """Generic instrument detail — works for equities, forex, indices."""
        try:
            from zhihuiti.market_fetcher import fetch_yahoo_candles
            from zhihuiti.crypto_oracle import diagnose_market
            timeframe = qs.get("timeframe", ["1d"])[0]

            candles = fetch_yahoo_candles(symbol, timeframe)
            if not candles or len(candles) < 10:
                _json_response(self, {"error": f"no data for {symbol}"}, 404)
                return

            diagnosis = diagnose_market(candles, instrument=symbol)
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


    # ── New handlers ───────────────────────────────────────────

    def _handle_scan_equities(self, qs):
        try:
            from zhihuiti.market_fetcher import scan_equities, DEFAULT_EQUITIES
            symbols = qs.get("symbols", [None])[0]
            symbols = symbols.split(",") if symbols else None
            timeframe = qs.get("timeframe", ["1d"])[0]
            results = scan_equities(symbols=symbols, timeframe=timeframe)

            history = _get_history()
            transitions = history.record_scan(results)

            _json_response(self, {
                "domain": "equities",
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "transitions": [t.to_dict() for t in transitions],
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_scan_forex(self, qs):
        try:
            from zhihuiti.market_fetcher import scan_forex, DEFAULT_FOREX
            symbols = qs.get("symbols", [None])[0]
            symbols = symbols.split(",") if symbols else None
            timeframe = qs.get("timeframe", ["1d"])[0]
            results = scan_forex(symbols=symbols, timeframe=timeframe)

            history = _get_history()
            transitions = history.record_scan(results)

            _json_response(self, {
                "domain": "forex",
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "transitions": [t.to_dict() for t in transitions],
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_scan_indices(self, qs):
        try:
            from zhihuiti.market_fetcher import scan_indices, DEFAULT_INDICES
            symbols = qs.get("symbols", [None])[0]
            symbols = symbols.split(",") if symbols else None
            timeframe = qs.get("timeframe", ["1d"])[0]
            results = scan_indices(symbols=symbols, timeframe=timeframe)

            history = _get_history()
            transitions = history.record_scan(results)

            _json_response(self, {
                "domain": "indices",
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "transitions": [t.to_dict() for t in transitions],
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_csv_upload(self):
        """POST /api/oracle/csv — upload CSV or JSON array for universal diagnosis.

        Body: {"values": [1.2, 3.4, ...], "domain": "scientific", "label": "my data"}
          or: {"csv": "timestamp,value\\n...", "column": "value", "domain": "business"}
        """
        try:
            body = _read_body(self)

            # Parse values from JSON array or CSV string
            values = body.get("values", [])
            if not values and "csv" in body:
                values = _parse_csv_values(body["csv"], body.get("column", "value"))

            if not values or len(values) < 5:
                _json_response(self, {"error": "need at least 5 data points"}, 400)
                return

            domain = body.get("domain", "scientific")
            label = body.get("label", "uploaded data")

            from zhihuiti.universal_oracle import diagnose, DOMAINS
            if domain not in DOMAINS:
                _json_response(self, {"error": f"unknown domain: {domain}", "available": list(DOMAINS.keys())}, 400)
                return

            result = diagnose(values, domain=domain, label=label)
            _json_response(self, result.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_alerts(self, qs):
        """GET /api/oracle/alerts — get recent alerts."""
        try:
            limit = int(qs.get("limit", ["50"])[0])
            domain = qs.get("domain", [None])[0]

            with _alerts_lock:
                filtered = _alerts if not domain else [a for a in _alerts if a["domain"] == domain]
                result = filtered[-limit:]

            _json_response(self, {"alerts": list(reversed(result)), "count": len(result)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_cross_domain(self, qs):
        """GET /api/oracle/cross-domain — run cross-domain correlation on latest scans."""
        try:
            from zhihuiti.cross_domain import find_cross_domain_correlations, DomainSnapshot, generate_alerts
            from zhihuiti.scanner import scan_instruments, _compute_signal_score
            from zhihuiti.market_fetcher import scan_equities

            snapshots = []

            # Scan crypto live
            try:
                crypto_results = scan_instruments(fetch_fn=_fetch_crypto_candles)
                for r in crypto_results[:5]:  # Top 5
                    snapshots.append(DomainSnapshot(
                        domain="crypto",
                        label=r.instrument,
                        regime=r.regime,
                        top_pattern=r.top_pattern or "support_resistance",
                        top_pattern_strength=r.top_pattern_strength,
                        pattern_count=r.pattern_count,
                        signal_score=r.signal_score,
                    ))
            except Exception:
                pass

            # Scan equities live
            try:
                eq_results = scan_equities()
                for r in eq_results[:5]:  # Top 5
                    snapshots.append(DomainSnapshot(
                        domain="equities",
                        label=r.instrument,
                        regime=r.regime,
                        top_pattern=r.top_pattern or "support_resistance",
                        top_pattern_strength=r.top_pattern_strength,
                        pattern_count=r.pattern_count,
                        signal_score=r.signal_score,
                    ))
            except Exception:
                pass

            if len(snapshots) < 2:
                _json_response(self, {"correlations": [], "alerts": [], "snapshot_count": len(snapshots),
                                       "message": "Need data from at least 2 domains"})
                return

            correlations = find_cross_domain_correlations(snapshots)

            # Generate alerts
            global _prev_snapshots
            with _prev_lock:
                alerts = generate_alerts(snapshots, _prev_snapshots, correlations)
                _prev_snapshots = snapshots

            # Store alerts
            with _alerts_lock:
                _alerts.extend([a.to_dict() for a in alerts])
                if len(_alerts) > 200:
                    _alerts[:] = _alerts[-200:]

            _json_response(self, {
                "correlations": [c.to_dict() for c in correlations],
                "alerts": [a.to_dict() for a in alerts],
                "snapshot_count": len(snapshots),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    # ── Intelligence handlers ─────────────────────────────────

    def _handle_predict(self, instrument, qs):
        """GET /api/oracle/predict/:instrument — predict next regime."""
        try:
            from zhihuiti.oracle_intelligence import predict_regime

            history = _get_history()
            hist = history.get_history(instrument, limit=100)

            # Get current diagnosis for pattern info
            patterns = []
            current_regime = "quiet"
            if hist:
                current_regime = hist[-1].get("regime", "quiet")

            # Try to get live patterns
            try:
                domain = _guess_domain(instrument)
                if domain == "crypto":
                    candles = _fetch_crypto_candles(instrument, "4h")
                else:
                    from zhihuiti.market_fetcher import fetch_yahoo_candles
                    candles = fetch_yahoo_candles(instrument, "1d")

                if candles and len(candles) >= 10:
                    from zhihuiti.crypto_oracle import diagnose_market
                    diag = diagnose_market(candles, instrument=instrument)
                    current_regime = diag.regime
                    patterns = [{"name": p.name, "strength": p.strength} for p in diag.patterns]
            except Exception:
                pass

            prediction = predict_regime(instrument, hist, current_regime, patterns)
            _json_response(self, prediction.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_portfolio_risk(self, qs):
        """GET /api/oracle/portfolio-risk — analyze portfolio risk from latest scans."""
        try:
            from zhihuiti.oracle_intelligence import analyze_portfolio_risk
            from zhihuiti.scanner import scan_instruments
            from zhihuiti.market_fetcher import scan_equities

            all_results = []

            # Scan crypto
            try:
                crypto = scan_instruments(fetch_fn=_fetch_crypto_candles)
                all_results.extend([r.to_dict() for r in crypto])
            except Exception:
                pass

            # Scan equities
            try:
                eq = scan_equities()
                all_results.extend([r.to_dict() for r in eq])
            except Exception:
                pass

            risk = analyze_portfolio_risk(all_results)
            _json_response(self, risk.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_theory_confidence(self, qs):
        """GET /api/oracle/theory-confidence — rank theories by current market fit."""
        try:
            from zhihuiti.oracle_intelligence import score_theory_confidence
            from zhihuiti.scanner import scan_instruments

            results = scan_instruments(fetch_fn=_fetch_crypto_candles)
            scan_dicts = [r.to_dict() for r in results]

            scores = score_theory_confidence(scan_dicts)
            _json_response(self, {
                "theories": [s.to_dict() for s in scores],
                "count": len(scores),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_compare(self, qs):
        """GET /api/oracle/compare?instruments=BTC_USDT,ETH_USDT — compare regime histories."""
        try:
            from zhihuiti.oracle_intelligence import compare_regime_histories

            instruments_str = qs.get("instruments", [""])[0]
            if not instruments_str:
                _json_response(self, {"error": "instruments query param required (comma-separated)"}, 400)
                return

            instruments = instruments_str.split(",")
            history = _get_history()

            histories = {}
            for inst in instruments:
                histories[inst] = history.get_history(inst.strip(), limit=100)

            comparison = compare_regime_histories(histories)
            _json_response(self, comparison.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    _watchlist = None

    def _get_watchlist(self):
        if OracleHandler._watchlist is None:
            from zhihuiti.oracle_intelligence import Watchlist
            OracleHandler._watchlist = Watchlist()
        return OracleHandler._watchlist

    def _handle_watchlist_get(self):
        """GET /api/oracle/watchlist — list watchlist items."""
        try:
            wl = self._get_watchlist()
            _json_response(self, {"items": wl.list_all(), "count": len(wl.list_all())})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_watchlist_post(self):
        """POST /api/oracle/watchlist — add/remove watchlist item."""
        try:
            body = _read_body(self)
            action = body.get("action", "add")
            instrument = body.get("instrument", "")

            if not instrument:
                _json_response(self, {"error": "instrument required"}, 400)
                return

            wl = self._get_watchlist()
            if action == "add":
                item = wl.add(
                    instrument=instrument,
                    domain=body.get("domain", "crypto"),
                    alert_on_regime_change=body.get("alert_on_regime_change", True),
                    alert_on_signal_above=body.get("alert_on_signal_above", 0.8),
                    alert_on_pattern=body.get("alert_on_pattern", ""),
                )
                _json_response(self, {"status": "added", "item": item.to_dict()})
            elif action == "remove":
                removed = wl.remove(instrument)
                _json_response(self, {"status": "removed" if removed else "not_found"})
            else:
                _json_response(self, {"error": f"unknown action: {action}"}, 400)
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    # ── Agent handlers ─────────────────────────────────────────

    _agent_manager = None

    def _get_agent_manager(self):
        if OracleHandler._agent_manager is None:
            from zhihuiti.oracle_agents import AgentManager
            OracleHandler._agent_manager = AgentManager()
            OracleHandler._agent_manager.genesis()  # Auto-seed default agents
        return OracleHandler._agent_manager

    def _handle_agents_list(self):
        try:
            mgr = self._get_agent_manager()
            _json_response(self, {"agents": mgr.list_all(), "count": len(mgr.list_all())})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_agent_get(self, agent_id):
        try:
            mgr = self._get_agent_manager()
            agent = mgr.get(agent_id)
            if not agent:
                _json_response(self, {"error": "agent not found"}, 404)
                return
            _json_response(self, agent.to_dict())
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_agent_roles(self):
        try:
            from zhihuiti.oracle_agents import AGENT_ROLES
            _json_response(self, {"roles": AGENT_ROLES})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_agent_create(self):
        try:
            body = _read_body(self)
            name = body.get("name", "")
            role = body.get("role", "scanner")
            instruments = body.get("instruments", [])
            domains = body.get("domains", ["crypto"])
            rules = body.get("rules")

            if not name:
                _json_response(self, {"error": "name required"}, 400)
                return

            mgr = self._get_agent_manager()
            agent = mgr.create(name=name, role=role, instruments=instruments,
                               domains=domains, rules=rules)
            _json_response(self, {"status": "created", "agent": agent.to_dict()})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_agent_delete(self, agent_id):
        try:
            mgr = self._get_agent_manager()
            removed = mgr.delete(agent_id)
            _json_response(self, {"status": "deleted" if removed else "not_found"})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_agent_status(self, agent_id, status):
        try:
            mgr = self._get_agent_manager()
            updated = mgr.update_status(agent_id, status)
            _json_response(self, {"status": "updated" if updated else "not_found", "new_status": status})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_agent_run(self, agent_id):
        """POST /api/oracle/agents/:id/run — execute agent against live market data."""
        try:
            mgr = self._get_agent_manager()
            agent = mgr.get(agent_id)
            if not agent:
                _json_response(self, {"error": "agent not found"}, 404)
                return

            # Gather scan results from agent's domains
            all_results = []
            if "crypto" in agent.domains:
                from zhihuiti.scanner import scan_instruments
                crypto = scan_instruments(fetch_fn=_fetch_crypto_candles)
                all_results.extend([r.to_dict() for r in crypto])

            if "equities" in agent.domains:
                from zhihuiti.market_fetcher import scan_equities
                eq = scan_equities()
                all_results.extend([r.to_dict() for r in eq])

            if "forex" in agent.domains:
                from zhihuiti.market_fetcher import scan_forex
                fx = scan_forex()
                all_results.extend([r.to_dict() for r in fx])

            if "indices" in agent.domains:
                from zhihuiti.market_fetcher import scan_indices
                idx = scan_indices()
                all_results.extend([r.to_dict() for r in idx])

            # Get previous regimes from history
            history = _get_history()
            summary = history.get_summary()
            prev_regimes = {inst: info["regime"] for inst, info in summary.items()}

            # Record scan results to history
            from zhihuiti.scanner import ScanResult
            scan_objs = []
            for r in all_results:
                scan_objs.append(ScanResult(**{k: r[k] for k in ScanResult.__dataclass_fields__}))
            history.record_scan(scan_objs)

            # Run agent rules
            actions = mgr.run_agent(agent_id, all_results, prev_regimes)

            _json_response(self, {
                "agent_id": agent_id,
                "instruments_scanned": len(all_results),
                "actions": [a.to_dict() for a in actions],
                "action_count": len(actions),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_scan_all(self):
        """POST /api/oracle/scan/all — scan all domains at once."""
        try:
            body = _read_body(self)
            domains = body.get("domains", ["crypto", "equities", "forex", "indices"])

            all_results = {}
            all_transitions = []

            if "crypto" in domains:
                from zhihuiti.scanner import scan_instruments
                crypto_results = scan_instruments(fetch_fn=_fetch_crypto_candles)
                history = _get_history()
                transitions = history.record_scan(crypto_results)
                all_results["crypto"] = [r.to_dict() for r in crypto_results]
                all_transitions.extend([t.to_dict() for t in transitions])

            if "equities" in domains:
                from zhihuiti.market_fetcher import scan_equities
                eq_results = scan_equities()
                history = _get_history()
                transitions = history.record_scan(eq_results)
                all_results["equities"] = [r.to_dict() for r in eq_results]
                all_transitions.extend([t.to_dict() for t in transitions])

            if "forex" in domains:
                from zhihuiti.market_fetcher import scan_forex
                fx_results = scan_forex()
                history = _get_history()
                transitions = history.record_scan(fx_results)
                all_results["forex"] = [r.to_dict() for r in fx_results]
                all_transitions.extend([t.to_dict() for t in transitions])

            if "indices" in domains:
                from zhihuiti.market_fetcher import scan_indices
                idx_results = scan_indices()
                history = _get_history()
                transitions = history.record_scan(idx_results)
                all_results["indices"] = [r.to_dict() for r in idx_results]
                all_transitions.extend([t.to_dict() for t in transitions])

            _json_response(self, {
                "domains": all_results,
                "transitions": all_transitions,
                "total_instruments": sum(len(v) for v in all_results.values()),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)


    # ── Real Agent System handlers ───────────────────────────────

    def _handle_real_agents_list(self):
        """GET /api/agents — list REAL zhihuiti agents (LLM-powered)."""
        if not _has_llm_key():
            _json_response(self, {
                "agents": [], "count": 0,
                "mode": "oracle-only",
                "message": "No LLM key configured. Set OPENROUTER_API_KEY to enable real agents.",
            })
            return
        try:
            orch = _get_orchestrator()
            agents = []
            for agent in orch.agent_manager.agents.values():
                role = getattr(agent.config, 'role', None) if hasattr(agent, 'config') else None
                role_str = role.value if hasattr(role, 'value') else str(role or 'unknown')
                realm = getattr(agent, 'realm', None)
                realm_str = realm.value if hasattr(realm, 'value') else str(realm or 'execution')
                gen = getattr(agent.config, 'generation', 0) if hasattr(agent, 'config') else 0
                agents.append({
                    "id": agent.id,
                    "name": getattr(agent, "name", agent.id[:8]),
                    "role": role_str,
                    "alive": agent.alive,
                    "budget": round(agent.budget, 2),
                    "avg_score": round(agent.avg_score, 3) if hasattr(agent, 'avg_score') else 0,
                    "task_count": len(agent.task_ids) if hasattr(agent, 'task_ids') else 0,
                    "generation": gen,
                    "realm": realm_str,
                    "depth": getattr(agent, "depth", 0),
                })
            _json_response(self, {"agents": agents, "count": len(agents), "mode": "full"})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_real_status(self):
        """GET /api/status — full system health with economy snapshot."""
        if not _has_llm_key():
            _json_response(self, {
                "status": "ok",
                "mode": "oracle-only",
                "message": "Oracle-only mode. Set OPENROUTER_API_KEY for full agent system.",
            })
            return
        try:
            orch = _get_orchestrator()
            from zhihuiti.dashboard import _gather_data
            data = _gather_data(orch)
            _json_response(self, {
                "status": "ok",
                "mode": "full",
                "backend": orch.llm._backend if hasattr(orch.llm, '_backend') else "unknown",
                "model": orch.llm.model if hasattr(orch.llm, 'model') else "unknown",
                "economy": data.get("economy", {}),
                "agent_count": len(data.get("agents", [])),
                "realms": data.get("realms", {}),
                "bloodline": data.get("bloodline", {}),
                "inspection": data.get("inspection", {}),
                "memory": data.get("memory", {}),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_evolution_status(self):
        """GET /api/evolution — self-directed evolution loop status and goal log."""
        with _self_loop_lock:
            log_copy = list(_self_loop_log)
        completed = sum(1 for g in log_copy if g.get("status") == "completed")
        failed = sum(1 for g in log_copy if g.get("status") == "failed")
        _json_response(self, {
            "running": _self_loop_running,
            "total_goals_run": len(log_copy),
            "completed": completed,
            "failed": failed,
            "recent_goals": list(reversed(log_copy[-20:])),
        })

    def _handle_real_dashboard_data(self):
        """GET /api/data — full dashboard data (economy, agents, bloodline, etc.)."""
        if not _has_llm_key():
            _json_response(self, {"error": "No LLM key. Set OPENROUTER_API_KEY."}, 503)
            return
        try:
            orch = _get_orchestrator()
            from zhihuiti.dashboard import _gather_data
            data = _gather_data(orch)
            _json_response(self, data)
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_real_goal_create(self):
        """POST /api/goals — submit a goal for real multi-agent execution."""
        if not _has_llm_key():
            _json_response(self, {"error": "No LLM key. Set OPENROUTER_API_KEY."}, 503)
            return
        try:
            import uuid
            body = _read_body(self)
            goal_text = body.get("goal", "").strip()
            if not goal_text:
                _json_response(self, {"error": "goal is required"}, 400)
                return

            goal_id = uuid.uuid4().hex[:12]
            orch = _get_orchestrator()

            with _orch_goals_lock:
                _orch_goals[goal_id] = {
                    "id": goal_id,
                    "goal": goal_text,
                    "status": "running",
                    "result": None,
                    "error": None,
                }

            def _execute():
                try:
                    result = orch.execute_goal(goal_text)
                    with _orch_goals_lock:
                        _orch_goals[goal_id]["status"] = "completed"
                        _orch_goals[goal_id]["result"] = result
                except Exception as e:
                    with _orch_goals_lock:
                        _orch_goals[goal_id]["status"] = "failed"
                        _orch_goals[goal_id]["error"] = str(e)

            thread = threading.Thread(target=_execute, daemon=True)
            thread.start()

            _json_response(self, {
                "id": goal_id,
                "status": "running",
                "message": f"Goal submitted for multi-agent execution: {goal_text[:80]}",
            }, 202)
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_real_goal_get(self, goal_id: str):
        """GET /api/goals/:id — poll goal execution status."""
        with _orch_goals_lock:
            goal = _orch_goals.get(goal_id)
        if not goal:
            _json_response(self, {"error": "goal not found"}, 404)
            return
        _json_response(self, goal)

    def _handle_real_single_task(self):
        """POST /api/tasks — execute a single task with a real agent."""
        if not _has_llm_key():
            _json_response(self, {"error": "No LLM key. Set OPENROUTER_API_KEY."}, 503)
            return
        try:
            body = _read_body(self)
            task_text = body.get("task", "").strip()
            if not task_text:
                _json_response(self, {"error": "task is required"}, 400)
                return

            orch = _get_orchestrator()
            role_name = body.get("role", "custom")
            from zhihuiti.agents import ROLE_MAP
            from zhihuiti.models import AgentRole, Task
            role = ROLE_MAP.get(role_name, AgentRole.CUSTOM)

            config = orch.agent_manager.get_best_config(role)
            agent = orch.agent_manager.spawn(role=role, depth=0, config=config, budget=100.0)
            task = Task(description=task_text, metadata={"requested_role": role_name})

            output = orch.agent_manager.execute_task(agent, task)
            score = orch.judge.score_task(task, agent)

            _json_response(self, {
                "output": output,
                "score": score,
                "agent_id": agent.id,
                "role": role.value,
                "status": task.status.value,
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)


def _parse_csv_values(csv_text: str, column: str = "value") -> list[float]:
    """Parse a CSV string and extract a numeric column."""
    lines = csv_text.strip().split("\n")
    if not lines:
        return []

    header = lines[0].split(",")
    try:
        col_idx = header.index(column)
    except ValueError:
        # Try last column as fallback
        col_idx = len(header) - 1

    values = []
    for line in lines[1:]:
        parts = line.split(",")
        if col_idx < len(parts):
            try:
                values.append(float(parts[col_idx].strip()))
            except ValueError:
                continue
    return values


def _guess_domain(instrument: str) -> str:
    """Guess the domain from an instrument name."""
    inst = instrument.upper()
    if "_USDT" in inst or "_USD" in inst or inst in ("BTC", "ETH", "SOL"):
        return "crypto"
    if "=X" in inst:
        return "forex"
    if inst.startswith("^"):
        return "indices"
    return "equities"


# ── Self-Directed Evolution Loop ─────────────────────────────────────────

_self_loop_running = False
_self_loop_log: list[dict] = []
_self_loop_lock = threading.Lock()

SEED_GOALS = [
    "Analyze the current crypto market. Which coins have strongest momentum? Compare BTC, ETH, SOL.",
    "Review agent performance scores across all roles. Which roles consistently score above 0.8?",
    "Compare the three realms (Research, Execution, Central) by productivity and score-per-token.",
    "Analyze the gene pool. Are newer generations outperforming older ones? Is evolution working?",
    "Research macro economic indicators affecting crypto markets. How should trading strategies adapt?",
    "Evaluate risk-adjusted returns across different market conditions. Which strategies work best?",
    "Analyze cross-domain correlations between crypto and equities. Are there exploitable patterns?",
    "Review the auction system efficiency. Are agents bidding competitively? What's the average savings?",
    "Research the latest developments in AI agent frameworks. Compare approaches and trade-offs.",
    "Analyze S&P 500 tech sector: AAPL, MSFT, GOOGL, NVDA. Which has strongest fundamentals?",
]


def _start_self_directed_loop(orch, interval: int):
    """Start the self-directed evolution loop.

    Each cycle:
    1. Run seed goals (first cycle only)
    2. Ask the LLM to generate NEW goals based on current system state
    3. Execute those goals → agents compete, evolve, breed
    4. Repeat

    This is the real zhihuiti: agents that design their own training.
    """
    global _self_loop_running
    _self_loop_running = True

    def _generate_new_goals(orch, count: int = 5) -> list[str]:
        """Ask the LLM to generate new goals based on current system state."""
        try:
            from zhihuiti.dashboard import _gather_data
            data = _gather_data(orch)

            # Build a context summary for goal generation
            economy = data.get("economy", {})
            agents_data = data.get("agents", [])
            bloodline = data.get("bloodline", {})
            inspection = data.get("inspection", {})
            realms = data.get("realms", {})

            alive_agents = [a for a in agents_data if a.get("alive")]
            top_roles = {}
            for a in alive_agents:
                role = a.get("role", "unknown")
                score = a.get("avg_score", 0)
                if role not in top_roles or score > top_roles[role]:
                    top_roles[role] = score

            context = f"""Current system state:
- Agents: {len(alive_agents)} alive, {len(agents_data) - len(alive_agents)} dead
- Max generation: {bloodline.get('max_generation', 0)}
- Avg bloodline score: {bloodline.get('avg_score', 0)}
- Economy: {economy.get('money_supply', 0)} supply, {economy.get('treasury_balance', 0)} treasury
- Inspection acceptance rate: {inspection.get('acceptance_rate', 0):.1%}
- Top roles by score: {', '.join(f'{r}={s:.2f}' for r, s in sorted(top_roles.items(), key=lambda x: -x[1])[:5])}
- Realms: Research({realms.get('research', {}).get('tasks_completed', 0)} tasks), Execution({realms.get('execution', {}).get('tasks_completed', 0)} tasks), Central({realms.get('central', {}).get('tasks_completed', 0)} tasks)

Previous goal log (last 10):
{chr(10).join(f'- {g.get("goal", "?")[:60]} → {g.get("status", "?")}' for g in _self_loop_log[-10:])}
"""

            result = orch.llm.chat_json(
                system="""You are the zhihuiti meta-orchestrator. Your job is to generate training goals
that will push the agent swarm to evolve and improve. Goals should:
1. Test different agent roles (researcher, analyst, strategist, auditor, coder)
2. Cover diverse domains (crypto, equities, macro, AI research, system analysis)
3. Increase in difficulty as agents improve
4. Include self-reflection goals (analyze own performance, find weaknesses)
5. Include creative goals that force agents to think beyond patterns
6. NOT repeat recent goals

Return a JSON array of goal strings. Each goal should be 1-2 sentences.""",
                user=f"Generate {count} new training goals for the agent swarm.\n\n{context}",
                temperature=0.8,
            )

            if isinstance(result, list):
                return [str(g) for g in result[:count]]
            return []
        except Exception as e:
            console.print(f"  [red]Goal generation failed:[/red] {e}")
            return []

    def _loop():
        import time
        import random

        cycle = 0
        while _self_loop_running:
            cycle += 1
            console.print(f"\n  [bold cyan]═══ Self-Directed Cycle {cycle} ═══[/bold cyan]")

            # Pick goals: seed goals for first 2 cycles, then self-generated
            if cycle <= 2:
                goals = random.sample(SEED_GOALS, min(5, len(SEED_GOALS)))
                console.print(f"  [dim]Using {len(goals)} seed goals[/dim]")
            else:
                goals = _generate_new_goals(orch, count=5)
                if not goals:
                    goals = random.sample(SEED_GOALS, min(3, len(SEED_GOALS)))
                    console.print(f"  [yellow]Fallback to seed goals[/yellow]")
                else:
                    console.print(f"  [green]Generated {len(goals)} self-directed goals[/green]")

            for goal in goals:
                if not _self_loop_running:
                    break
                try:
                    console.print(f"  [cyan]Running:[/cyan] {goal[:80]}...")
                    result = orch.execute_goal(goal)
                    entry = {"goal": goal, "status": "completed", "cycle": cycle}
                    with _self_loop_lock:
                        _self_loop_log.append(entry)
                        if len(_self_loop_log) > 100:
                            _self_loop_log[:] = _self_loop_log[-100:]
                    console.print(f"  [green]Done:[/green] {goal[:60]}")
                except Exception as e:
                    entry = {"goal": goal, "status": "failed", "error": str(e), "cycle": cycle}
                    with _self_loop_lock:
                        _self_loop_log.append(entry)
                    console.print(f"  [red]Failed:[/red] {e}")

            # Sleep until next cycle
            console.print(f"  [dim]Next cycle in {interval}s...[/dim]")
            for _ in range(interval):
                if not _self_loop_running:
                    break
                time.sleep(1)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    console.print(f"  [bold green]Self-directed evolution started[/bold green]")
    console.print(f"  Cycle 1-2: seed goals | Cycle 3+: agents design their own goals")
    console.print(f"  Interval: {interval}s between cycles")


def serve(port: int | None = None):
    """Start the combined Oracle + Agent API server."""
    port = port or int(os.environ.get("PORT", 8377))
    has_llm = _has_llm_key()

    console.print(f"\n[bold]智慧体 zhihuiti Server[/bold]")
    mode = "[bold green]FULL (LLM + Agents + Oracle)[/bold green]" if has_llm else "[yellow]Oracle-only (no LLM key)[/yellow]"
    console.print(f"  Mode: {mode}")
    console.print(f"  Listening on http://0.0.0.0:{port}")

    # Oracle endpoints (always available)
    console.print(f"\n  [dim]── Oracle endpoints ──[/dim]")
    console.print(f"  GET  /api/oracle/scan")
    console.print(f"  GET  /api/oracle/crypto/:instrument")
    console.print(f"  GET  /api/oracle/scan/equities")
    console.print(f"  GET  /api/oracle/scan/forex")
    console.print(f"  GET  /api/oracle/scan/indices")
    console.print(f"  GET  /api/oracle/cross-domain")
    console.print(f"  GET  /api/oracle/predict/:instrument")
    console.print(f"  GET  /api/oracle/portfolio-risk")
    console.print(f"  GET  /api/oracle/theory-confidence")

    if has_llm:
        # Real agent endpoints
        console.print(f"\n  [dim]── Real Agent endpoints (LLM-powered) ──[/dim]")
        console.print(f"  GET  /api/agents                   — list real agents")
        console.print(f"  GET  /api/status                   — economy + system health")
        console.print(f"  GET  /api/data                     — full dashboard data")
        console.print(f"  POST /api/goals                    — submit goal for multi-agent execution")
        console.print(f"  GET  /api/goals/:id                — poll goal status")
        console.print(f"  POST /api/tasks                    — execute single task")

        # Pre-initialize orchestrator on startup so agents are ready
        try:
            console.print(f"\n  [dim]Initializing orchestrator...[/dim]")
            _get_orchestrator()
        except Exception as e:
            console.print(f"  [red]Warning: orchestrator init failed: {e}[/red]")
            console.print(f"  [red]Real agent endpoints will retry on first request[/red]")

        # Optional: start background evolution with self-directed goals
        if os.environ.get("ZHIHUITI_AUTO_EVOLVE"):
            try:
                orch = _get_orchestrator()
                interval = int(os.environ.get("ZHIHUITI_EVOLVE_INTERVAL", "7200"))
                _start_self_directed_loop(orch, interval)
            except Exception as e:
                console.print(f"  [red]Auto-evolve failed: {e}[/red]")

    console.print(f"\n  GET  /health")
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
