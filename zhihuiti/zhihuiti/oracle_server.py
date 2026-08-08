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
  CORS_ORIGIN=https://zhihuiti.lovable.app — comma-separated browser origins
  ZHIHUITI_API_TOKEN     — bearer token required by protected operator routes
  MAX_REQUEST_BODY_BYTES — JSON request limit (default: 1 MiB)
  OPENROUTER_API_KEY     — enables full agent system via OpenRouter
  DEEPSEEK_API_KEY       — enables full agent system via DeepSeek
  ZHIHUITI_DB            — SQLite database path (default: /app/data/zhihuiti.db)
  ZHIHUITI_BACKEND_ID    — deployment role shown in health responses
  ZHIHUITI_PUBLIC_BASE_URL — canonical public API URL
  ZHIHUITI_MAX_SNAPSHOTS — retained rollback checkpoints (default: 50)
  ZHIHUITI_ALERT_WEBHOOK_URL — optional operator alert destination
  ZHIHUITI_ALERT_WEBHOOK_TOKEN — optional bearer token for that destination
  ZHIHUITI_AUTO_EVOLVE=1 — enable background goal execution & evolution
  ZHIHUITI_ORACLE_SCAN=0 — disable scheduled read-only market collection
  ZHIHUITI_ORACLE_SCAN_INTERVAL — collection interval in seconds (default: 1800)
  ZHIHUITI_SCAN_CRYPTO / _EQUITIES / _FOREX / _INDICES — CSV watchlists
  ZHIHUITI_MACRO_HTTP_RETRIES — macro source attempts (default: 3)
"""

from __future__ import annotations

import json
import hmac
import os
import sqlite3
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen

from rich.console import Console

from zhihuiti.env import env_enabled

console = Console()

# ── Real Agent System (lazy-initialized when LLM key is present) ─────────
_orchestrator = None
_orch_lock = threading.Lock()
_orch_goals: dict[str, dict] = {}
_orch_goals_lock = threading.Lock()

DEFAULT_CORS_ORIGIN = "https://zhihuiti.lovable.app"
DEFAULT_MAX_REQUEST_BODY_BYTES = 1024 * 1024


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


def _configured_cors_origins() -> list[str]:
    value = os.environ.get("CORS_ORIGIN", DEFAULT_CORS_ORIGIN)
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def _allowed_cors_origin(handler: BaseHTTPRequestHandler) -> str | None:
    request_origin = handler.headers.get("Origin", "").strip()
    configured = _configured_cors_origins()
    if "*" in configured:
        return request_origin or "*"
    if request_origin in configured:
        return request_origin
    return None


def _runtime_commit() -> str:
    """Prefer the deployment platform's immutable source revision."""
    return (
        os.environ.get("ZEABUR_GIT_COMMIT_SHA", "").strip()
        or os.environ.get("ZHIHUITI_COMMIT_SHA", "").strip()
        or "unknown"
    )


def _backend_id() -> str:
    return os.environ.get("ZHIHUITI_BACKEND_ID", "unconfigured").strip() or "unconfigured"


def _canonical_base_url() -> str:
    return (
        os.environ.get("ZHIHUITI_PUBLIC_BASE_URL", "https://zhihuiti.zeabur.app")
        .strip()
        .rstrip("/")
    )


def _snapshot_limit() -> int:
    try:
        return max(1, int(os.environ.get("ZHIHUITI_MAX_SNAPSHOTS", "50")))
    except ValueError:
        return 50


def _storage_status() -> dict[str, Any]:
    """Return non-secret persistent identity and bounded database diagnostics."""
    data_dir = Path(os.environ.get("ZHIHUITI_DATA", "/app/data"))
    identity_path = data_dir / "instance.json"
    identity: dict[str, Any]
    identity_error = None
    try:
        identity = json.loads(identity_path.read_text())
        if not isinstance(identity, dict) or not identity.get("instance_id"):
            raise ValueError("invalid instance identity")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        identity = {
            "instance_id": uuid.uuid4().hex,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            temporary = identity_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(identity, sort_keys=True))
            os.replace(temporary, identity_path)
        except OSError as exc:
            identity_error = type(exc).__name__

    db_path = Path(os.environ.get("ZHIHUITI_DB", str(data_dir / "zhihuiti.db")))
    database = {
        "exists": db_path.exists(),
        "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "snapshots": None,
        "tasks": None,
        "agents": None,
    }
    if database["exists"]:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1)
            try:
                for table in ("snapshots", "tasks", "agents"):
                    database[table] = conn.execute(
                        f"SELECT COUNT(*) FROM {table}"  # noqa: S608
                    ).fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    return {
        "instance_id": identity.get("instance_id"),
        "created_at": identity.get("created_at"),
        "identity_persisted": identity_error is None,
        "identity_error": identity_error,
        "database": database,
        "max_snapshots": _snapshot_limit(),
    }


def _json_response(handler: BaseHTTPRequestHandler, data: Any, status: int = 200):
    if status == 500 and isinstance(data, dict) and "error" in data:
        data = {**data, "error": "internal server error"}
    body = json.dumps(data, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    origin = _allowed_cors_origin(handler)
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("X-Zhihuiti-Commit", _runtime_commit())
    handler.send_header("X-Zhihuiti-Backend", _backend_id())
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler: BaseHTTPRequestHandler) -> dict:
    cached = getattr(handler, "_json_body", None)
    if cached is not None:
        return cached
    try:
        length = int(handler.headers.get("Content-Length", 0))
        limit = int(os.environ.get("MAX_REQUEST_BODY_BYTES", DEFAULT_MAX_REQUEST_BODY_BYTES))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid Content-Length") from exc
    if length < 0:
        raise ValueError("invalid Content-Length")
    if length > max(1, limit):
        raise OverflowError("request body too large")
    if length == 0:
        handler._json_body = {}
        return handler._json_body
    raw = handler.rfile.read(length)
    try:
        body = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    handler._json_body = body
    return body


def _require_operator_auth(handler: BaseHTTPRequestHandler) -> bool:
    expected = os.environ.get("ZHIHUITI_API_TOKEN", "").strip()
    if not expected:
        _json_response(handler, {"error": "operator API is not configured"}, 503)
        return False
    authorization = handler.headers.get("Authorization", "")
    scheme, _, provided = authorization.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(provided.strip(), expected):
        _json_response(handler, {"error": "operator authorization required"}, 401)
        return False
    return True


def _runtime_status() -> dict[str, Any]:
    provider = "none"
    if os.environ.get("DEEPSEEK_API_KEY"):
        provider = "deepseek"
    elif os.environ.get("OPENROUTER_API_KEY"):
        provider = "openrouter"
    elif os.environ.get("OPENAI_API_KEY"):
        provider = "openai"
    elif os.environ.get("LLM_API_KEY"):
        provider = "custom"
    try:
        max_active_agents = max(1, int(os.environ.get("ZHIHUITI_MAX_ACTIVE_AGENTS", "36")))
    except ValueError:
        max_active_agents = 36
    return {
        "service": "zhihuiti",
        "commit": _runtime_commit(),
        "backend_id": _backend_id(),
        "canonical_base_url": _canonical_base_url(),
        "provider": provider,
        "llm_configured": _has_llm_key(),
        "operator_api_configured": bool(os.environ.get("ZHIHUITI_API_TOKEN", "").strip()),
        "autonomous_evolution": env_enabled("ZHIHUITI_AUTO_EVOLVE"),
        "max_active_agents": max_active_agents,
        "auto_mint_enabled": env_enabled("ZHIHUITI_ALLOW_AUTO_MINT"),
    }


# Lazy-initialized history tracker
_history = None
_history_lock = threading.Lock()

# In-memory alert + snapshot stores
_alerts: list[dict] = []
_alerts_lock = threading.Lock()
_ALERT_DELIVERY_META = {
    "last_attempt_at": None,
    "last_success_at": None,
    "last_error": None,
}
_prev_snapshots: list = []
_prev_lock = threading.Lock()

_ORACLE_SCAN_META = {
    "running": False,
    "last_attempt_at": None,
    "last_completed_at": None,
    "interval_seconds": 1800,
    "domains": {},
    "instruments": 0,
    "transitions": 0,
    "agent_actions": 0,
    "errors": [],
    "backtest": {},
    "watchlist": {},
}
_oracle_scan_meta_lock = threading.Lock()
_oracle_scan_start_lock = threading.Lock()
_oracle_scan_thread = None


def _alerts_path() -> Path:
    return Path(os.environ.get("ZHIHUITI_DATA", "/app/data")) / "oracle_alerts.json"


def _persist_alerts_locked() -> None:
    """Persist alert lifecycle state; caller must hold ``_alerts_lock``."""
    try:
        path = _alerts_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(_alerts[-500:]))
        os.replace(temporary, path)
    except OSError:
        pass


def _load_alerts() -> None:
    try:
        payload = json.loads(_alerts_path().read_text())
        if isinstance(payload, list):
            _alerts.extend(item for item in payload[-500:] if isinstance(item, dict))
    except (OSError, ValueError, TypeError):
        pass


def _alert_severity(alert: dict) -> str:
    explicit = str(alert.get("severity", "")).lower()
    if explicit in {"info", "warning", "critical"}:
        return explicit
    action_type = str(alert.get("action_type", "alert")).lower()
    if action_type in {"halt", "emergency", "critical"}:
        return "critical"
    data = alert.get("data", {})
    try:
        signal = abs(float(data.get("signal_score", 0))) if isinstance(data, dict) else 0
    except (TypeError, ValueError):
        signal = 0
    return "warning" if action_type == "alert" or signal >= 0.8 else "info"


def _deliver_alerts(alerts: list[dict]) -> None:
    """Deliver newly created alerts to an optional operator-owned webhook."""
    webhook_url = os.environ.get("ZHIHUITI_ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url or not alerts:
        return
    _ALERT_DELIVERY_META["last_attempt_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    payload = json.dumps({
        "source": "zhihuiti",
        "backend_id": _backend_id(),
        "canonical_base_url": _canonical_base_url(),
        "alerts": alerts,
    }, default=str).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "zhihuiti-alerts/1.0"}
    token = os.environ.get("ZHIHUITI_ALERT_WEBHOOK_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(webhook_url, data=payload, headers=headers), timeout=5) as response:
            if response.status < 200 or response.status >= 300:
                raise OSError(f"webhook returned {response.status}")
        _ALERT_DELIVERY_META["last_success_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        _ALERT_DELIVERY_META["last_error"] = None
    except OSError as exc:
        _ALERT_DELIVERY_META["last_error"] = type(exc).__name__


def _record_alerts(alerts: list[dict], now: float | None = None) -> dict[str, int]:
    """Create or coalesce alerts using a configurable cooldown and expiry."""
    now = now or time.time()
    cooldown = max(60, int(os.environ.get("ZHIHUITI_ALERT_COOLDOWN_SECONDS", "21600")))
    ttl = max(cooldown, int(os.environ.get("ZHIHUITI_ALERT_TTL_SECONDS", "86400")))
    created = 0
    updated = 0
    created_alerts: list[dict] = []
    with _alerts_lock:
        for existing in _alerts:
            if existing.get("status", "active") == "active" and existing.get("expires_at", 0) <= now:
                existing["status"] = "expired"

        for raw in alerts:
            alert = dict(raw)
            identity = (
                alert.get("instrument", ""),
                alert.get("action_type", "alert"),
                alert.get("message", ""),
            )
            duplicate = next((
                existing for existing in reversed(_alerts)
                if existing.get("status", "active") == "active"
                and (
                    existing.get("instrument", ""),
                    existing.get("action_type", "alert"),
                    existing.get("message", ""),
                ) == identity
                and now - existing.get("last_seen_at", existing.get("timestamp", 0)) < cooldown
            ), None)
            if duplicate:
                duplicate["last_seen_at"] = now
                duplicate["timestamp"] = now
                duplicate["occurrences"] = int(duplicate.get("occurrences", 1)) + 1
                duplicate["expires_at"] = now + ttl
                duplicate["data"] = alert.get("data", duplicate.get("data", {}))
                updated += 1
                continue

            alert.update({
                "id": alert.get("id") or uuid.uuid4().hex[:16],
                "severity": _alert_severity(alert),
                "timestamp": now,
                "first_seen_at": now,
                "last_seen_at": now,
                "occurrences": 1,
                "expires_at": now + ttl,
                "status": "active",
            })
            _alerts.append(alert)
            created_alerts.append(dict(alert))
            created += 1

        if len(_alerts) > 500:
            _alerts[:] = _alerts[-500:]
        _persist_alerts_locked()
    _deliver_alerts(created_alerts)
    return {"created": created, "updated": updated}


_load_alerts()


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
            params={
                "instrument_name": instrument,
                "timeframe": timeframe,
                "count": 300,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("result", {}).get("data", data.get("data", []))
        return [
            {
                "timestamp": c.get("t", c.get("timestamp", 0)),
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


# ── Macro factor layer (cross-asset cockpit feed) ───────────────────────────
# Mirrors server/core/macro.ts. The price-regime oracle has no macro factor read
# (rates / USD index / gold-as-macro / inflation); this fills that gap and speaks
# the same regime vocabulary as /api/oracle/summary. Daily-snapshot cadence.
_MACRO_SNAPSHOT = {
    "asof": "2026-06-29", "curveDate": "2026-06-26",
    "curve": {
        "cur": {"3M": 3.83, "1Y": 3.94, "2Y": 4.07, "3Y": 4.09, "5Y": 4.12, "7Y": 4.23, "10Y": 4.38, "20Y": 4.87, "30Y": 4.87},
        "w1":  {"3M": 3.83, "1Y": 4.00, "2Y": 4.19, "3Y": 4.19, "5Y": 4.23, "7Y": 4.34, "10Y": 4.46, "20Y": 4.91, "30Y": 4.90},
    },
    "y10": 4.38, "y2": 4.07, "y30": 4.87, "y3m": 3.83, "bei10": 2.35, "real10": 2.03,
    "dxy": 100.94, "dxyChg": -0.42, "gold": 4036.5, "goldChg": -1.46,
    "wti": 70.52, "brent": 73.68, "wtiChg": -1.95,
    "spx": 7399.4, "spxChg": 0.62, "ndx": 29426, "rut": 2981.2, "rutChg": -0.96,
    "vix": 18.27, "vixChg": -0.76, "move": 66.8, "gvz": 28.15, "gvzChg": 3.57, "ovx": 46.6,
    "btc": 59253, "btcChg": -0.41, "coreCPI": 3.8, "cpi": 3.2, "fiscalDef": 6.3,
}

# The seed above is the calibration baseline + offline fallback. A background
# thread (below) refreshes it from keyless sources; failed fields keep their seed
# value, so the endpoint never breaks. _MACRO_META records refresh provenance.
_MACRO_META = {
    "last_attempt_at": None,
    "refreshed_at": None,
    "sources": {},
    "errors": [],
    "live_fields": 0,
}
_MACRO_REFRESHER_STARTED = False
_MACRO_REFRESHER_LOCK = threading.Lock()


def _macro_clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _macro_composite(facs):
    s = sum(f["s"] * f["w"] for f in facs)
    w = sum(f["w"] for f in facs)
    return round(s / w)


def _macro_confidence(facs, score):
    w = sum(f["w"] for f in facs)
    v = sum(f["w"] * (f["s"] - score) ** 2 for f in facs)
    disp = (v / w) ** 0.5
    return round(_macro_clamp(1 - disp / 120, 0.8, 0.99), 3)


def _macro_regime(score, mom, vol):
    """Map composite + momentum + vol onto the oracle regime vocabulary."""
    strong = abs(mom) >= 2
    if vol == "crisis":
        return "crisis"
    if mom > 0 and score >= 60:
        return "trending_up"
    if mom < 0 and score <= 42:
        return "trending_down"
    if vol == "high" and not strong:
        return "volatile"
    if vol == "low" and abs(mom) <= 1 and 44 <= score <= 56:
        return "quiet"
    return "mean_reverting"


def _lin(x, x0, s0, x1, s1):
    """Clamped linear transfer: input value -> 0..100 score. None in -> None out."""
    if x is None:
        return None
    t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
    return int(_macro_clamp(round(s0 + t * (s1 - s0)), 0, 100))


def _macro_http_get(url, timeout=6, ua="zhihuiti-macro/1.0"):
    import urllib.request
    # ua=None sends urllib's default User-Agent — FRED's WAF hangs on custom UAs
    req = urllib.request.Request(url, headers={"User-Agent": ua} if ua else {})
    try:
        attempts = max(1, min(5, int(os.environ.get("ZHIHUITI_MACRO_HTTP_RETRIES", "3"))))
    except ValueError:
        attempts = 3
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if attempt + 1 >= attempts:
                raise
            time.sleep(0.2 * (2 ** attempt))


def _fred_series(series_id, days_back=0):
    """Latest value of a FRED series (keyless CSV), or the value ~days_back rows back."""
    txt = _macro_http_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}", ua=None)
    vals = []
    for ln in txt.strip().splitlines()[1:]:
        p = ln.split(",")
        if len(p) >= 2 and p[1] not in (".", ""):
            vals.append(p[1])
    if not vals:
        return None
    idx = max(0, len(vals) - 1 - days_back) if days_back > 0 else len(vals) - 1
    return float(vals[idx])


def _stooq_close(sym):
    # Fail soft (None) so `_stooq_close(x) or _yahoo_price(y)` fallbacks actually run
    try:
        txt = _macro_http_get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&e=csv")
        p = txt.strip().splitlines()[-1].split(",")   # Symbol,Date,Time,O,H,L,Close,Vol
        if len(p) >= 7 and p[6] not in ("", "N/D"):
            return float(p[6])
    except Exception:
        pass
    return None


def _yahoo_meta(sym):
    import json as _json
    txt = _macro_http_get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d")
    return _json.loads(txt)["chart"]["result"][0]["meta"]


def _yahoo_price(sym):
    return float(_yahoo_meta(sym)["regularMarketPrice"])


def _yahoo_chg_pct(sym):
    m = _yahoo_meta(sym)
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    px = m.get("regularMarketPrice")
    return round((px / prev - 1) * 100, 2) if prev and px else None


def _refresh_macro_snapshot():
    """Pull live data into a fresh snapshot and atomically swap it in. Fully guarded:
    any failed field keeps its previous value; the endpoint never breaks."""
    import copy as _copy, datetime as _dt
    global _MACRO_SNAPSHOT
    _MACRO_META["last_attempt_at"] = _dt.datetime.now(
        _dt.timezone.utc).isoformat(timespec="seconds")
    s = _copy.deepcopy(_MACRO_SNAPSHOT)
    src, errs = {}, []

    def setf(field, fn, source):
        try:
            v = fn()
            if v is not None:
                s[field] = round(v, 4) if isinstance(v, float) else v
                src[field] = source
        except Exception as e:
            errs.append(f"{field}:{type(e).__name__}")

    fred_curve = {"3M": "DGS3MO", "1Y": "DGS1", "2Y": "DGS2", "3Y": "DGS3", "5Y": "DGS5",
                  "7Y": "DGS7", "10Y": "DGS10", "20Y": "DGS20", "30Y": "DGS30"}
    for tenor, fid in fred_curve.items():
        try:
            c = _fred_series(fid)
            if c is not None:
                s["curve"]["cur"][tenor] = c
                src[f"curve.{tenor}"] = "FRED"
            w = _fred_series(fid, days_back=5)
            if w is not None:
                s["curve"]["w1"][tenor] = w
        except Exception as e:
            errs.append(f"curve.{tenor}:{type(e).__name__}")
    for k, t in (("y10", "10Y"), ("y2", "2Y"), ("y30", "30Y"), ("y3m", "3M")):
        s[k] = s["curve"]["cur"].get(t, s.get(k))

    setf("bei10", lambda: _fred_series("T10YIE"), "FRED")
    setf("real10", lambda: _fred_series("DFII10"), "FRED")
    setf("vix", lambda: _fred_series("VIXCLS"), "FRED")
    setf("gvz", lambda: _fred_series("GVZCLS"), "FRED")
    setf("ovx", lambda: _fred_series("OVXCLS"), "FRED")
    setf("move", lambda: _yahoo_price("%5EMOVE"), "Yahoo")
    setf("wti", lambda: _fred_series("DCOILWTICO"), "FRED")
    setf("brent", lambda: _fred_series("DCOILBRENTEU"), "FRED")
    setf("spx", lambda: _fred_series("SP500"), "FRED")
    setf("ndx", lambda: _fred_series("NASDAQ100"), "FRED")
    setf("btc", lambda: _fred_series("CBBTCUSD"), "FRED")
    setf("rut", lambda: _stooq_close("^rut") or _yahoo_price("%5ERUT"), "Stooq/Yahoo")
    setf("gold", lambda: _stooq_close("xauusd") or _yahoo_price("GC=F"), "Stooq/Yahoo")
    setf("dxy", lambda: _stooq_close("^dxy") or _yahoo_price("DX-Y.NYB"), "Stooq/Yahoo")
    setf("dxyChg", lambda: _yahoo_chg_pct("DX-Y.NYB"), "Yahoo")
    setf("goldChg", lambda: _yahoo_chg_pct("GC=F"), "Yahoo")
    setf("spxChg", lambda: _yahoo_chg_pct("%5EGSPC"), "Yahoo")
    setf("wtiChg", lambda: _yahoo_chg_pct("CL=F"), "Yahoo")
    setf("rutChg", lambda: _yahoo_chg_pct("%5ERUT"), "Yahoo")
    setf("vixChg", lambda: _yahoo_chg_pct("%5EVIX"), "Yahoo")
    setf("gvzChg", lambda: _yahoo_chg_pct("%5EGVZ"), "Yahoo")
    setf("btcChg", lambda: _yahoo_chg_pct("BTC-USD"), "Yahoo")

    # core CPI YoY from the monthly index level (latest vs 12 rows back)
    def _core_cpi_yoy():
        cur, ago = _fred_series("CPILFESL"), _fred_series("CPILFESL", days_back=12)
        return round((cur / ago - 1) * 100, 2) if cur and ago else None
    setf("coreCpiYoY", _core_cpi_yoy, "FRED")
    # foreign 10Y (monthly OECD series) → US rate differential for the USD board
    setf("de10", lambda: _fred_series("IRLTLT01DEM156N"), "FRED")
    setf("jp10", lambda: _fred_series("IRLTLT01JPM156N"), "FRED")

    # derive real rate if BEI came through but TIPS didn't
    if s.get("bei10") is not None and s["curve"]["cur"].get("10Y") is not None and "real10" not in src:
        s["real10"] = round(s["curve"]["cur"]["10Y"] - s["bei10"], 3)

    _MACRO_META["sources"] = src
    _MACRO_META["errors"] = errs[:15]
    _MACRO_META["live_fields"] = len(src)
    if src:
        today = _dt.date.today().isoformat()
        s["asof"], s["curveDate"] = today, today
        _MACRO_META["refreshed_at"] = _dt.datetime.now(
            _dt.timezone.utc).isoformat(timespec="seconds")
        _MACRO_SNAPSHOT = s
        _macro_history_save(s, _MACRO_META)
    return _MACRO_META


def _macro_db_path():
    return os.environ.get("ZHIHUITI_DB", "/app/data/zhihuiti.db")


def _macro_history_save(snapshot, meta):
    """Append the refreshed snapshot to SQLite. Never breaks the refresh."""
    import sqlite3
    try:
        con = sqlite3.connect(_macro_db_path(), timeout=5)
        con.execute("""CREATE TABLE IF NOT EXISTS macro_history (
            ts TEXT PRIMARY KEY, live_fields INTEGER, snapshot TEXT)""")
        con.execute("INSERT OR REPLACE INTO macro_history VALUES (?,?,?)",
                    (meta["refreshed_at"], meta["live_fields"], json.dumps(snapshot)))
        con.commit()
        con.close()
    except Exception:
        pass


def _macro_history_query(hours=168, fields=None, limit=2000):
    import sqlite3, datetime as _dt
    db_path = _macro_db_path()
    if not os.path.exists(db_path):
        return []
    since = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=hours)).isoformat(timespec="seconds")
    con = sqlite3.connect(db_path, timeout=5)
    try:
        table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='macro_history'"
        ).fetchone()
        if table is None:
            return []
        rows = con.execute(
            "SELECT ts, live_fields, snapshot FROM macro_history WHERE ts >= ? ORDER BY ts LIMIT ?",
            (since, limit)).fetchall()
    finally:
        con.close()
    out = []
    for ts, lf, snap in rows:
        s = json.loads(snap)
        row = {"ts": ts, "live_fields": lf}
        for f in (fields or ["y10", "y2", "dxy", "gold", "vix", "bei10", "real10", "spx", "wti"]):
            row[f] = s.get(f)
        out.append(row)
    return out


def _refresh_loop(interval):
    import time as _time
    while True:
        try:
            _refresh_macro_snapshot()
        except Exception as exc:
            import datetime as _dt
            _MACRO_META["last_attempt_at"] = _dt.datetime.now(
                _dt.timezone.utc).isoformat(timespec="seconds")
            _MACRO_META["errors"] = [f"refresh:{type(exc).__name__}"]
        _time.sleep(interval)


def _ensure_refresher(interval=1800):
    """Start the daemon refresher once (idempotent). 30-min cadence by default."""
    global _MACRO_REFRESHER_STARTED
    if _MACRO_REFRESHER_STARTED:
        return
    with _MACRO_REFRESHER_LOCK:
        if _MACRO_REFRESHER_STARTED:
            return
        _MACRO_REFRESHER_STARTED = True
        threading.Thread(target=_refresh_loop, args=(interval,), daemon=True,
                         name="macro-refresh").start()


def _macro_feed():
    _ensure_refresher()
    s = _MACRO_SNAPSHOT
    cur, w1 = s["curve"]["cur"], s["curve"]["w1"]
    d10 = round((s["y10"] - w1.get("10Y", s["y10"])) * 100)   # weekly 10Y change, bp

    def dv(x, args, carried):
        """Data-driven sub-score from a live input, falling back to a carried constant.
        Anchors are calibrated so the seed snapshot reproduces the baseline scores."""
        v = _lin(x, *args)
        return v if v is not None else carried

    ips_facs = [
        ("P 价格 (核心CPI %)", dv(s.get("coreCPI"), (2.0, 31, 5.0, 76), 58), .25, "服务+住房粘性", False),
        ("E 预期 (10Y BEI %)", dv(s.get("bei10"), (2.0, 40, 2.8, 63), 50), .20, "长端锚定", False),
        ("D 驱动 (油价/工资)", 55, .20, "油价回落降温", True),
        ("F 财政 (赤字 ~6.3%)", 72, .15, "暗刺激仍在", True),
        ("N 叙事 (Fed 偏鹰)", 62, .20, "粘性自我强化", True),
    ]
    dur_facs = [
        ("实际利率 (10Y real %)", dv(s.get("real10"), (1.5, 55, 2.5, 30), 42), .30, "高实际利率封顶久期", False),
        ("曲线动能 (10Y 周变 bp)", dv(d10, (15, 22, -15, 78), 64), .22, "前端领涨·牛陡", False),
        ("债券波动 MOVE", dv(s.get("move"), (60, 70, 120, 30), 66), .18, "低位·偏支撑", False),
        ("增长/风险 (VIX)", dv(s.get("vix"), (12, 28, 30, 56), 38), .18, "risk-on 抽水", False),
        ("供给/财政", 40, .12, "长端供给压力", True),
    ]
    usd_facs = [
        ("r_f 利率差 (Fed vs ECB/BOJ)", 62, .35, "利差仍宽·支撑", True),
        ("π_risk 风险溢价 (VIX)", dv(s.get("vix"), (12, 30, 35, 68), 40), .25, "避险买盘", False),
        ("cy 便利收益 (黄金强)", 40, .25, "去美元化拖累", True),
        ("σ_alert 波动预警 (MOVE)", dv(s.get("move"), (60, 30, 120, 70), 34), .15, "低波·中性", False),
    ]
    gold_facs = [
        ("实际利率 (逆风)", dv(s.get("real10"), (1.5, 58, 2.5, 32), 44), .25, "高实际利率压制", False),
        ("美元 (软美元顺风)", dv(s.get("dxyChg"), (1.0, 46, -1.0, 74), 66), .22, "DXY 动能", False),
        ("价格动能 (创新高)", 82, .23, "强势·超买", True),
        ("恐慌溢价 GVZ", dv(s.get("gvz"), (15, 48, 35, 88), 74), .15, "避险升温", False),
        ("地缘/油波 OVX", dv(s.get("ovx"), (30, 52, 60, 84), 70), .15, "尾部对冲需求", False),
    ]

    gold_vol = "high" if (s.get("gvz") or 0) >= 24 else "low"
    dur_vol = "high" if (s.get("move") or 0) >= 100 else "low"
    dur_mom = 1 if d10 <= 0 else -1
    usd_mom = -1 if (s.get("dxyChg") or 0) < 0 else 1

    defs = [
        ("inflation", "通胀压力 IPS", "Inflation Pressure", "IPS = P + E + D + F + N", "#fbbf24",
         ips_facs, ["回落", "温和", "粘性", "再加速"], 1, "low"),
        ("duration", "美债久期立场", "Duration Stance", "Dur = −real − growth + mom + (低)vol", "#38bdf8",
         dur_facs, ["强空", "偏空", "中性", "偏多"], dur_mom, dur_vol),
        ("usd", "美元估值 γ", "USD Valuation", "γ = r_f + π_risk − cy + σ_alert", "#34d399",
         usd_facs, ["弱", "偏弱", "中性", "强"], usd_mom, "low"),
        ("gold", "黄金信号", "Gold Signal", "Au = −real + softUSD + mom + haven", "#e0b53c",
         gold_facs, ["看空", "中性", "偏多", "强多"], 2, gold_vol),
    ]
    monitors, sc = [], {}
    for (mid, name, en, formula, accent, facs, zones, mom, vol) in defs:
        factors = [{"key": k, "score": v, "weight": w, "note": note, "est": est} for (k, v, w, note, est) in facs]
        fc = [{"s": v, "w": w} for (k, v, w, note, est) in facs]
        score = _macro_composite(fc)
        sc[mid] = score
        monitors.append({
            "id": mid, "name": name, "nameEn": en, "formula": formula, "accent": accent,
            "score": score, "stance": zones[min(3, score // 25)],
            "regime": _macro_regime(score, mom, vol), "signal_score": _macro_confidence(fc, score),
            "factors": factors,
        })

    spx_score = _lin(s.get("vix"), 12, 74, 30, 44)
    spx_score = spx_score if spx_score is not None else 64

    def tow(score, mom, vol):
        return _macro_regime(score, mom, vol), round(_macro_clamp(0.82 + abs(score - 50) / 250, 0.8, 0.99), 3)

    tg, tu, td, ts = tow(sc["gold"], 2, gold_vol), tow(sc["usd"], usd_mom, "low"), tow(sc["duration"], dur_mom, dur_vol), tow(spx_score, 2, "low")
    d10s = f"{d10:+d}bp/wk"
    tower = [
        {"asset": "黄金", "symbol": "XAU/USD", "price": f"${s['gold']:,.0f} · {s.get('goldChg', 0)}%", "bias": "偏多", "lean": "long",
         "regime": tg[0], "signal_score": tg[1], "strength": 4,
         "chain": "软美元 + 实际利率见顶预期 + 去美元化/避险 资金流", "window": "1–3 月", "risk": "超买回撤;实际利率反弹或 GVZ 退潮则首当其冲"},
        {"asset": "美元", "symbol": "DXY", "price": f"{s['dxy']:.2f} · {s.get('dxyChg', 0)}%", "bias": "偏空", "lean": "short",
         "regime": tu[0], "signal_score": tu[1], "strength": 2,
         "chain": "前端 dovish drift + 动能转弱;利差宽但边际收敛", "window": "1–3 月", "risk": "外部避险事件 → 美元冲高;Fed 重新转鹰"},
        {"asset": "美债", "symbol": "UST 10Y", "price": f"{s['y10']:.2f}% · {d10s}", "bias": "中性偏多", "lean": "neutral",
         "regime": td[0], "signal_score": td[1], "strength": 3,
         "chain": "前端领涨牛陡 + MOVE 低位;实际利率高位封住上行空间", "window": "3–6 月", "risk": "通胀/供给反扑 → 长端再定价;财政发债压力"},
        {"asset": "美股", "symbol": "SPX", "price": f"{s['spx']:,.0f} · {s.get('spxChg', 0)}%", "bias": "偏多·拥挤", "lean": "long",
         "regime": ts[0], "signal_score": ts[1], "strength": 3,
         "chain": "软美元 melt-up + 低 VIX 流动性顺风", "window": "1–3 月", "risk": "广度恶化(RUT 落后) + 黄金/油波 stress 传导"},
    ]

    vix_stress = _lin(s.get("vix"), 12, 15, 40, 95)
    vix_stress = vix_stress if vix_stress is not None else 33
    gvz_f = _lin(s.get("gvz"), 15, 20, 40, 90) or 57
    ovx_f = _lin(s.get("ovx"), 25, 25, 70, 90) or 56
    vix_calm = 100 - (_lin(s.get("vix"), 12, 20, 40, 95) or 37)
    risk = int(_macro_clamp(round(0.55 * spx_score + 0.25 * (100 - vix_stress) + 0.20 * (100 - sc["usd"])), 0, 100))
    frag = int(_macro_clamp(round(0.40 * gvz_f + 0.30 * ovx_f + 0.30 * vix_calm), 0, 100))

    live_fields = _MACRO_META.get("live_fields", 0)
    refresh_errors = list(_MACRO_META.get("errors", []))
    if live_fields:
        refresh_status = "partial" if refresh_errors else "live"
        data_mode = "live"
        source_mode = "live FRED/Stooq/Yahoo data"
    else:
        refresh_status = "degraded" if _MACRO_META.get("last_attempt_at") else "pending"
        data_mode = "fallback"
        source_mode = "dated fallback snapshot"

    return {
        "asof": s["asof"],
        "last_attempt_at": _MACRO_META.get("last_attempt_at"),
        "refreshed_at": _MACRO_META.get("refreshed_at"),
        "refresh_status": refresh_status,
        "data_mode": data_mode,
        "refresh_errors": refresh_errors,
        "live_fields": live_fields,
        "sources": _MACRO_META.get("sources", {}),
        "source": f"zhihuiti macro cockpit · {source_mode} · score-based · scheduled refresh(30m)",
        "regime_label": "软美元 · 风险偏好回升 · 黄金避险并存",
        "regime_en": "Soft-USD Risk-On with a Parallel Gold Hedge",
        "risk_appetite": risk, "fragility": frag,
        "read": ("权益逼近历史高位 + VIX 低位、美元动能转弱、前端收益率领涨透出 dovish drift——表面顺畅 risk-on;"
                 "但黄金近历史高位叠加 GVZ/OVX 偏高,存在一条避险/去美元化暗线。MOVE 低位说明债市尚未定价这层背离。"),
        "monitors": monitors, "tower": tower, "snapshot": s,
    }


def _macro_summary(feed):
    by = {m["id"]: m for m in feed["monitors"]}
    s = feed["snapshot"]
    inst = {
        "INFL_IPS": {"regime": by["inflation"]["regime"], "signal_score": by["inflation"]["signal_score"],
                     "score": by["inflation"]["score"], "stance": by["inflation"]["stance"], "snapshots": 1},
        "UST_10Y": {"regime": by["duration"]["regime"], "price": s["y10"], "signal_score": by["duration"]["signal_score"],
                    "score": by["duration"]["score"], "stance": by["duration"]["stance"], "snapshots": 1},
        "USD_IDX": {"regime": by["usd"]["regime"], "price": s["dxy"], "signal_score": by["usd"]["signal_score"],
                    "score": by["usd"]["score"], "stance": by["usd"]["stance"], "snapshots": 1},
        "GOLD_MACRO": {"regime": by["gold"]["regime"], "price": s["gold"], "signal_score": by["gold"]["signal_score"],
                       "score": by["gold"]["score"], "stance": by["gold"]["stance"], "snapshots": 1},
    }
    return {"instruments": inst, "count": len(inst), "regime_label": feed["regime_label"],
            "asof": feed["asof"], "source": feed["source"]}


class OracleHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        _json_response(self, {})

    _HTML_PAGES = {
        "/macro-cockpit": "macro_cockpit.html",
        "/monitor/rates": "monitor_rates.html",
        "/monitor/usd": "monitor_usd.html",
        "/monitor/gold": "monitor_gold.html",
        "/monitor/inflation": "monitor_inflation.html",
    }

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path in {"/health", "/healthz"}:
            runtime = _runtime_status()
            _json_response(self, {
                **runtime,
                "status": "ok",
                "mode": "full" if runtime["llm_configured"] else "oracle-only",
                "agents_enabled": runtime["llm_configured"],
                "storage": _storage_status(),
            })

        elif path == "/readyz":
            runtime = _runtime_status()
            ready = runtime["llm_configured"] and runtime["operator_api_configured"]
            _json_response(self, {
                **runtime,
                "status": "ready" if ready else "not_ready",
                "orchestrator_initialized": _orchestrator is not None,
            }, 200 if ready else 503)

        elif path in self._HTML_PAGES:
            try:
                with open(os.path.join(os.path.dirname(__file__), self._HTML_PAGES[path]), "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                _json_response(self, {"error": "page not bundled"}, 404)

        elif path == "/api/oracle/scan":
            self._handle_scan(qs)
        elif path == "/api/oracle/scan/status":
            self._handle_scan_status()
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
        elif path == "/api/oracle/macro":
            self._handle_macro(qs)
        elif path == "/api/oracle/macro/history":
            try:
                hours = int(qs.get("hours", ["168"])[0])
                fields = qs.get("fields", [None])[0]
                fields = [f.strip() for f in fields.split(",")] if fields else None
                _json_response(self, {"rows": _macro_history_query(hours=hours, fields=fields)})
            except Exception as e:
                _json_response(self, {"error": str(e)}, 500)
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
            if not _require_operator_auth(self):
                return
            goal_id = path.split("/")[-1]
            self._handle_real_goal_get(goal_id)
        elif path == "/api/data":
            self._handle_real_dashboard_data()
        elif path == "/api/evolution":
            self._handle_evolution_status()
        elif path == "/api/harness":
            self._handle_harness_status()
        elif path == "/api/operations/status":
            self._handle_operations_status()
        # ── Backtest endpoints ──
        elif path == "/api/backtest/run":
            self._handle_backtest_run()
        elif path == "/api/backtest/results":
            self._handle_backtest_results(qs)
        elif path == "/api/backtest/accuracy":
            self._handle_backtest_accuracy()
        # ── Content feed endpoints ──
        elif path == "/api/content/feed":
            self._handle_content_feed(qs)
        elif path == "/api/content/topics":
            self._handle_content_topics()
        elif path.startswith("/api/content/") and path.count("/") == 3:
            content_id = path.split("/")[-1]
            self._handle_content_get(content_id)
        else:
            _json_response(self, {"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if not _require_operator_auth(self):
            return
        try:
            _read_body(self)
        except OverflowError:
            _json_response(self, {"error": "request body too large"}, 413)
            return
        except ValueError as exc:
            _json_response(self, {"error": str(exc)}, 400)
            return

        if path == "/api/oracle/diagnose":
            self._handle_diagnose()
        elif path == "/api/oracle/csv":
            self._handle_csv_upload()
        elif path == "/api/oracle/watchlist":
            self._handle_watchlist_post()
        elif path == "/api/oracle/scan/all":
            self._handle_scan_all()
        elif path == "/api/oracle/alerts/ack":
            self._handle_alert_ack()
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
        # ── Content generation ──
        elif path == "/api/content/generate":
            self._handle_content_generate()
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

            # Auto-record predictions and verify old ones
            backtest_info = {}
            try:
                from zhihuiti.backtest import auto_record_and_verify
                backtest_info = auto_record_and_verify(results)
            except Exception:
                pass

            _json_response(self, {
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "transitions": [t.to_dict() for t in transitions],
                "backtest": backtest_info,
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_scan_status(self):
        with _oracle_scan_meta_lock:
            data = json.loads(json.dumps(_ORACLE_SCAN_META))
        if data["running"]:
            status = "running"
        elif data["last_completed_at"] and data["errors"]:
            status = "partial"
        elif data["last_completed_at"]:
            status = "live"
        else:
            status = "pending"
        _json_response(self, {"status": status, **data})

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

    def _handle_macro(self, qs):
        # Cross-asset macro factor feed (mirrors server/core/macro.ts).
        # ?format=summary flattens into the /api/oracle/summary shape.
        try:
            feed = _macro_feed()
            fmt = qs.get("format", [""])[0]
            _json_response(self, _macro_summary(feed) if fmt == "summary" else feed)
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
            limit = max(1, min(200, int(qs.get("limit", ["50"])[0])))
            domain = qs.get("domain", [None])[0]
            include_inactive = qs.get("include_inactive", ["false"])[0].lower() == "true"
            now = time.time()

            with _alerts_lock:
                for alert in _alerts:
                    if alert.get("status", "active") == "active" and alert.get("expires_at", 0) <= now:
                        alert["status"] = "expired"
                filtered = [
                    alert for alert in _alerts
                    if (not domain or alert.get("domain") == domain)
                    and (include_inactive or alert.get("status", "active") == "active")
                ]
                result = sorted(
                    filtered,
                    key=lambda alert: alert.get("last_seen_at", alert.get("timestamp", 0)),
                )[-limit:]

            _json_response(self, {
                "alerts": list(reversed(result)),
                "count": len(result),
                "active_total": sum(
                    1 for alert in _alerts if alert.get("status", "active") == "active"
                ),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_alert_ack(self):
        """POST /api/oracle/alerts/ack — acknowledge one or many alerts by ID."""
        body = _read_body(self)
        single_id = str(body.get("id", "")).strip()
        raw_ids = body.get("ids", [])
        if raw_ids and not isinstance(raw_ids, list):
            _json_response(self, {"error": "ids must be a list"}, 400)
            return
        alert_ids = [single_id] if single_id else []
        alert_ids.extend(str(item).strip() for item in raw_ids if str(item).strip())
        alert_ids = list(dict.fromkeys(alert_ids))[:100]
        if not alert_ids:
            _json_response(self, {"error": "id or ids is required"}, 400)
            return

        with _alerts_lock:
            selected = [item for item in _alerts if item.get("id") in alert_ids]
            if not selected and single_id and not raw_ids:
                _json_response(self, {"error": "alert not found"}, 404)
                return
            acknowledged_at = time.time()
            for alert in selected:
                alert["status"] = "acknowledged"
                alert["acknowledged_at"] = acknowledged_at
            _persist_alerts_locked()
            results = [dict(alert) for alert in selected]
        if single_id and not raw_ids:
            _json_response(self, results[0])
        else:
            found = {alert["id"] for alert in results}
            _json_response(self, {
                "acknowledged": len(results),
                "alerts": results,
                "missing_ids": [alert_id for alert_id in alert_ids if alert_id not in found],
            })

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

            # Store alerts with lifecycle-aware deduplication.
            _record_alerts([a.to_dict() for a in alerts])

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
    _agent_manager_lock = threading.Lock()

    @classmethod
    def _get_agent_manager(cls):
        if cls._agent_manager is None:
            with cls._agent_manager_lock:
                if cls._agent_manager is None:
                    from zhihuiti.oracle_agents import AgentManager
                    cls._agent_manager = AgentManager()
                    cls._agent_manager.genesis()  # Auto-seed default agents
        return cls._agent_manager

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
                "governance": data.get("governance", {}),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    # ── Content feed handlers ─────────────────────────────────────

    def _handle_content_feed(self, qs):
        """GET /api/content/feed — latest content feed."""
        try:
            from zhihuiti.content_agent import get_feed
            limit = int(qs.get("limit", ["20"])[0])
            tag = qs.get("tag", [""])[0]
            feed = get_feed(limit=limit, tag=tag)
            _json_response(self, {"content": feed, "count": len(feed)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_content_topics(self):
        """GET /api/content/topics — available topic categories."""
        try:
            from zhihuiti.content_agent import TOPIC_PAIRS
            topics = []
            for pair in TOPIC_PAIRS:
                topics.append({
                    "west": pair["west"],
                    "east": pair["east"],
                    "bridge": pair["bridge"],
                    "tags": pair["tags"],
                })
            _json_response(self, {"topics": topics, "count": len(topics)})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_content_get(self, content_id):
        """GET /api/content/:id — single content piece."""
        try:
            from zhihuiti.content_agent import get_piece
            piece = get_piece(content_id)
            if not piece:
                _json_response(self, {"error": "content not found"}, 404)
                return
            _json_response(self, piece)
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_content_generate(self):
        """POST /api/content/generate — trigger new content generation."""
        try:
            from zhihuiti.content_agent import generate_content
            body = _read_body(self)
            topic_hint = body.get("topic", "")

            orch = None
            if _has_llm_key():
                try:
                    orch = _get_orchestrator()
                except Exception:
                    pass

            piece = generate_content(orch=orch, topic_hint=topic_hint)
            _json_response(self, {"status": "generated", "content": piece.to_dict()})
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    # ── Backtest handlers ────────────────────────────────────────

    def _handle_backtest_run(self):
        """GET /api/backtest/run — run backtest on all instruments with history."""
        try:
            from zhihuiti.backtest import run_backtest_all, get_overall_accuracy
            results = run_backtest_all()
            overall = get_overall_accuracy(results)
            _json_response(self, {
                "overall": overall.to_dict(),
                "instruments": [r.to_dict() for r in results],
                "count": len(results),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_backtest_results(self, qs):
        """GET /api/backtest/results?instrument=BTC_USDT — backtest for one instrument."""
        try:
            instrument = qs.get("instrument", [""])[0]
            if not instrument:
                _json_response(self, {"error": "instrument query param required"}, 400)
                return

            from zhihuiti.backtest import (
                build_regime_history_from_candles,
                run_backtest_historical,
            )
            from zhihuiti.scanner import RegimeHistory

            history = RegimeHistory()
            hist = history.get_history(instrument, limit=500)
            source = "forward_snapshots"
            if len(hist) < 10:
                if _guess_domain(instrument) == "crypto":
                    candles = _fetch_crypto_candles(instrument, "4h")
                else:
                    from zhihuiti.market_fetcher import fetch_yahoo_candles
                    candles = fetch_yahoo_candles(instrument, "1d")
                hist = build_regime_history_from_candles(instrument, candles)
                source = "historical_candles"
            if len(hist) < 10:
                _json_response(self, {
                    "error": f"Not enough history for {instrument} ({len(hist)} snapshots, need 10+)",
                }, 400)
                return

            result = run_backtest_historical(instrument, hist)
            _json_response(self, {
                **result.to_dict(),
                "source": source,
                "snapshot_count": len(hist),
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_backtest_accuracy(self):
        """GET /api/backtest/accuracy — overall prediction accuracy stats."""
        try:
            from zhihuiti.backtest import get_forecast_scorecards

            scorecards = get_forecast_scorecards()
            _json_response(self, {
                **scorecards["models"][scorecards["production_model"]],
                "scorecards": scorecards,
            })
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_evolution_status(self):
        """GET /api/evolution — aggregate self-directed evolution status."""
        with _self_loop_lock:
            log_copy = list(_self_loop_log)
        completed = sum(1 for g in log_copy if g.get("status") == "completed")
        failed = sum(1 for g in log_copy if g.get("status") == "failed")
        _json_response(self, {
            "running": _self_loop_running,
            "total_goals_run": len(log_copy),
            "completed": completed,
            "failed": failed,
            "autonomous_evolution": env_enabled("ZHIHUITI_AUTO_EVOLVE"),
            "limits": _evolution_limits(),
            "runtime": dict(_self_loop_meta),
        })

    def _handle_operations_status(self):
        """GET /api/operations/status — compact, alertable production health."""
        import datetime as dt

        with _oracle_scan_meta_lock:
            scan = json.loads(json.dumps(_ORACLE_SCAN_META))
        completed_at = scan.get("last_completed_at")
        scan_age_seconds = None
        if completed_at:
            try:
                completed = dt.datetime.fromisoformat(completed_at)
                scan_age_seconds = max(
                    0, int((dt.datetime.now(dt.timezone.utc) - completed).total_seconds())
                )
            except ValueError:
                pass
        stale_after = max(120, int(scan.get("interval_seconds", 1800)) * 2)

        with _alerts_lock:
            active_alerts = sum(
                1 for alert in _alerts if alert.get("status", "active") == "active"
            )

        try:
            from zhihuiti.backtest import get_forecast_scorecards
            scorecards = get_forecast_scorecards()
            forecast = scorecards["models"][scorecards["production_model"]]
            forecast = {key: value for key, value in forecast.items() if key != "recent"}
        except Exception:
            forecast = {"status": "unavailable"}
            scorecards = {
                "production_model": "incumbent-v1",
                "shadow_model": "transition-calibrated-v1",
                "promotion_ready": False,
                "models": {},
            }

        governance = {
            "autonomous_evolution": env_enabled("ZHIHUITI_AUTO_EVOLVE"),
            "auto_mint_enabled": env_enabled("ZHIHUITI_ALLOW_AUTO_MINT"),
            "max_active_agents": max(
                1, int(os.environ.get("ZHIHUITI_MAX_ACTIVE_AGENTS", "36"))
            ),
            "max_agents_per_role": max(
                1, int(os.environ.get("ZHIHUITI_MAX_AGENTS_PER_ROLE", "12"))
            ),
        }
        warnings = []
        if scan.get("errors"):
            warnings.append("scan_errors")
        if scan_age_seconds is None or scan_age_seconds > stale_after:
            warnings.append("scan_stale")
        if _MACRO_META.get("errors"):
            warnings.append("macro_partial")
        if forecast.get("status") != "validated":
            if forecast.get("status") == "collecting":
                warnings.append("forecast_collecting")
            elif forecast.get("status") == "unavailable":
                warnings.append("forecast_unavailable")
            else:
                warnings.append("forecast_not_better_than_baseline")
        if governance["auto_mint_enabled"]:
            warnings.append("auto_mint_enabled")

        storage = _storage_status()
        if not storage["identity_persisted"]:
            warnings.append("storage_identity_unavailable")
        if storage["database"]["snapshots"] is not None and (
            storage["database"]["snapshots"] > storage["max_snapshots"]
        ):
            warnings.append("snapshot_retention_pending")

        try:
            llm_status = (
                _orchestrator.llm.provider_status()
                if _orchestrator is not None
                else {"configured": False, "message": "Orchestrator is not initialized."}
            )
        except Exception:
            llm_status = {"configured": False, "message": "LLM status is unavailable."}

        external_alert_channel = os.environ.get(
            "ZHIHUITI_EXTERNAL_ALERT_CHANNEL", "",
        ).strip()
        webhook_configured = bool(
            os.environ.get("ZHIHUITI_ALERT_WEBHOOK_URL", "").strip()
        )

        _json_response(self, {
            "status": "degraded" if warnings else "ok",
            "commit": _runtime_commit(),
            "backend_id": _backend_id(),
            "canonical_base_url": _canonical_base_url(),
            "warnings": warnings,
            "scan": {
                **scan,
                "age_seconds": scan_age_seconds,
                "stale_after_seconds": stale_after,
            },
            "macro": {
                "last_attempt_at": _MACRO_META.get("last_attempt_at"),
                "refreshed_at": _MACRO_META.get("refreshed_at"),
                "live_fields": _MACRO_META.get("live_fields", 0),
                "errors": list(_MACRO_META.get("errors", [])),
            },
            "alerts": {
                "active": active_alerts,
                "delivery_configured": bool(
                    webhook_configured or external_alert_channel
                ),
                "webhook_configured": webhook_configured,
                "external_channel": external_alert_channel or None,
                "delivery": dict(_ALERT_DELIVERY_META),
            },
            "llm": llm_status,
            "forecast": forecast,
            "forecast_scorecards": scorecards,
            "governance": governance,
            "storage": storage,
        })

    def _handle_harness_status(self):
        """GET /api/harness — guarded improvement state and audit history."""
        if not _has_llm_key():
            _json_response(self, {"error": "No LLM key configured."}, 503)
            return
        try:
            from zhihuiti.readiness import get_harness_status
            _json_response(self, get_harness_status(_get_orchestrator()))
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _handle_real_dashboard_data(self):
        """GET /api/data — full dashboard data (economy, agents, bloodline, etc.)."""
        if not _has_llm_key():
            _json_response(self, {"error": "No LLM key configured."}, 503)
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
            _json_response(self, {"error": "No LLM key configured."}, 503)
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
            _json_response(self, {"error": "No LLM key configured."}, 503)
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


# ── Scheduled public-data collection ────────────────────────────────────

def _utc_now_iso() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _watchlist_value(name: str, defaults: list[str]) -> list[str]:
    raw = os.environ.get(name, "").strip()
    values = [value.strip() for value in raw.split(",") if value.strip()] if raw else defaults
    return list(dict.fromkeys(values))[:50]


def _scheduled_scan_watchlist() -> dict[str, list[str]]:
    """Return the bounded, operator-configurable public scan universe."""
    return {
        "crypto": _watchlist_value(
            "ZHIHUITI_SCAN_CRYPTO", ["BTC_USDT", "ETH_USDT", "SOL_USDT"],
        ),
        "equities": _watchlist_value(
            "ZHIHUITI_SCAN_EQUITIES", ["AAPL", "MSFT", "NVDA"],
        ),
        "forex": _watchlist_value(
            "ZHIHUITI_SCAN_FOREX", ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
        ),
        "indices": _watchlist_value(
            "ZHIHUITI_SCAN_INDICES", ["^GSPC", "^N225", "^HSI"],
        ),
    }


def _collect_oracle_scan_results() -> tuple[dict[str, list], list[str]]:
    """Collect a small, representative read-only market set."""
    from zhihuiti.market_fetcher import scan_equities, scan_forex, scan_indices
    from zhihuiti.scanner import scan_instruments

    watchlist = _scheduled_scan_watchlist()
    collectors = {
        "crypto": lambda: scan_instruments(
            instruments=watchlist["crypto"],
            fetch_fn=_fetch_crypto_candles,
        ),
        "equities": lambda: scan_equities(symbols=watchlist["equities"]),
        "forex": lambda: scan_forex(symbols=watchlist["forex"]),
        "indices": lambda: scan_indices(symbols=watchlist["indices"]),
    }
    results: dict[str, list] = {}
    errors = []
    for domain, collect in collectors.items():
        try:
            domain_results = collect()
            results[domain] = domain_results
            if not domain_results:
                errors.append(f"{domain}:no_results")
        except Exception as exc:
            results[domain] = []
            errors.append(f"{domain}:{type(exc).__name__}")
    return results, errors


def _run_oracle_scan_cycle() -> dict:
    """Persist one public-data scan and evaluate observation-only agents."""
    with _oracle_scan_meta_lock:
        _ORACLE_SCAN_META["running"] = True
        _ORACLE_SCAN_META["last_attempt_at"] = _utc_now_iso()

    results_by_domain, errors = _collect_oracle_scan_results()
    all_results = [
        result
        for domain_results in results_by_domain.values()
        for result in domain_results
    ]
    history = _get_history()
    previous = history.get_summary()
    previous_regimes = {
        instrument: values["regime"] for instrument, values in previous.items()
    }
    transitions = history.record_scan(all_results) if all_results else []

    backtest_info = {}
    try:
        from zhihuiti.backtest import auto_record_and_verify
        backtest_info = auto_record_and_verify(all_results, history=history)
    except Exception as exc:
        errors.append(f"backtest:{type(exc).__name__}")

    action_count = 0
    try:
        manager = OracleHandler._get_agent_manager()
        serialized = [result.to_dict() for result in all_results]
        actions_by_agent = manager.run_all(serialized, previous_regimes)
        actions = [
            action
            for agent_actions in actions_by_agent.values()
            for action in agent_actions
        ]
        action_count = len(actions)
        domain_by_instrument = {
            result.instrument: domain
            for domain, domain_results in results_by_domain.items()
            for result in domain_results
        }
        public_alerts = [
            {
                **action,
                "domain": domain_by_instrument.get(action["instrument"], "unknown"),
                "source": "oracle_agent",
                "execution": "observation_only",
            }
            for action in actions
            if "alert" in action["action_type"]
        ]
        if public_alerts:
            _record_alerts(public_alerts)
    except Exception as exc:
        errors.append(f"agents:{type(exc).__name__}")

    with _oracle_scan_meta_lock:
        _ORACLE_SCAN_META.update({
            "running": False,
            "last_completed_at": _utc_now_iso(),
            "domains": {
                domain: len(results) for domain, results in results_by_domain.items()
            },
            "instruments": len(all_results),
            "transitions": len(transitions),
            "agent_actions": action_count,
            "errors": errors,
            "backtest": backtest_info,
            "watchlist": _scheduled_scan_watchlist(),
        })
        return json.loads(json.dumps(_ORACLE_SCAN_META))


def _start_oracle_scan_loop(interval: int = 1800):
    """Start one idempotent background collector, running immediately."""
    global _oracle_scan_thread
    with _oracle_scan_start_lock:
        if _oracle_scan_thread is not None and _oracle_scan_thread.is_alive():
            return _oracle_scan_thread

        interval = max(60, interval)
        with _oracle_scan_meta_lock:
            _ORACLE_SCAN_META["interval_seconds"] = interval

        def _loop():
            import time
            while True:
                try:
                    _run_oracle_scan_cycle()
                except Exception as exc:
                    with _oracle_scan_meta_lock:
                        _ORACLE_SCAN_META.update({
                            "running": False,
                            "last_completed_at": _utc_now_iso(),
                            "errors": [f"cycle:{type(exc).__name__}"],
                        })
                time.sleep(interval)

        _oracle_scan_thread = threading.Thread(
            target=_loop,
            daemon=True,
            name="zhihuiti-oracle-scan",
        )
        _oracle_scan_thread.start()
        return _oracle_scan_thread


# ── Self-Directed Evolution Loop ─────────────────────────────────────────

_self_loop_running = False
_self_loop_log: list[dict] = []
_self_loop_lock = threading.Lock()
_self_loop_meta = {"cycles": 0, "goals_started": 0, "stop_reason": "disabled"}

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
    # East × West content generation goals
    "Generate a bilingual content piece about how neuroscience research on mirror neurons validates Buddhist compassion meditation. Include specific studies by Tania Singer and Matthieu Ricard.",
    "Write about the connection between quantum observer effect and Vipassana insight meditation. How does modern physics validate ancient observation practices?",
    "Explore how neuroplasticity research proves what Mahamudra practitioners have known for centuries. Cite specific fMRI studies by Richard Davidson.",
    "Create content about Polyvagal theory and Pranayama breathing. How did ancient yogis discover vagus nerve stimulation thousands of years before Stephen Porges?",
    "Write about flow state psychology (Csikszentmihalyi) and the Taoist concept of Wu Wei (无为). Both describe effortless peak performance.",
    "Explore how epigenetics and karma both describe the same phenomenon: your choices create imprints that ripple across generations.",
    "Write about Default Mode Network research and meditation. What happens in the brain when monks 'stop their thoughts'?",
    "Create content about chaos theory's butterfly effect and Buddhism's Indra's Net — how both describe an interconnected universe where small actions ripple everywhere.",
]


def _evolution_limits() -> dict[str, int]:
    def bounded(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            return max(minimum, min(maximum, int(os.environ.get(name, str(default)))))
        except ValueError:
            return default

    return {
        "max_cycles": bounded("ZHIHUITI_EVOLVE_MAX_CYCLES", 2, 1, 100),
        "max_goals": bounded("ZHIHUITI_EVOLVE_MAX_GOALS", 10, 1, 500),
        "max_tokens": bounded("ZHIHUITI_EVOLVE_MAX_TOKENS", 100000, 1000, 10_000_000),
    }


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
    limits = _evolution_limits()
    _self_loop_meta.update({"cycles": 0, "goals_started": 0, "stop_reason": "running"})

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
        global _self_loop_running

        cycle = 0
        while _self_loop_running:
            if cycle >= limits["max_cycles"]:
                _self_loop_meta["stop_reason"] = "max_cycles_reached"
                _self_loop_running = False
                break
            cycle += 1
            _self_loop_meta["cycles"] = cycle
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
                if _self_loop_meta["goals_started"] >= limits["max_goals"]:
                    _self_loop_meta["stop_reason"] = "max_goals_reached"
                    _self_loop_running = False
                    break
                if getattr(orch.llm, "total_tokens", 0) >= limits["max_tokens"]:
                    _self_loop_meta["stop_reason"] = "max_tokens_reached"
                    _self_loop_running = False
                    break
                try:
                    _self_loop_meta["goals_started"] += 1
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
            if not _self_loop_running:
                break
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
    console.print(f"  GET  /api/oracle/scan/status")
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
        if env_enabled("ZHIHUITI_AUTO_EVOLVE"):
            try:
                orch = _get_orchestrator()
                interval = int(os.environ.get("ZHIHUITI_EVOLVE_INTERVAL", "7200"))
                _start_self_directed_loop(orch, interval)
            except Exception as e:
                console.print(f"  [red]Auto-evolve failed: {e}[/red]")

    # Begin the first keyless macro refresh at process startup. Request traffic
    # may be sparse or routed across instances, so a request-triggered daemon is
    # not sufficient to keep the public feed current.
    _ensure_refresher()

    scan_enabled = os.environ.get("ZHIHUITI_ORACLE_SCAN", "1").strip().lower()
    if scan_enabled not in {"0", "false", "no", "off", "disabled"}:
        scan_interval = int(os.environ.get("ZHIHUITI_ORACLE_SCAN_INTERVAL", "1800"))
        _start_oracle_scan_loop(scan_interval)

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
