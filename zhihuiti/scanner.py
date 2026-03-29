"""Market Scanner + Regime History — multi-instrument scanning and temporal tracking.

Scanner: runs the crypto oracle across multiple instruments in parallel,
ranks by strongest signal, and returns a market-wide view.

History: persists diagnosis snapshots over time so regime transitions
(quiet -> volatile -> trending) can be detected.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Multi-pair scanner ─────────────────────────────────────────────────────

DEFAULT_PAIRS = [
    "BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "DOGE_USDT",
    "ADA_USDT", "AVAX_USDT", "DOT_USDT", "LINK_USDT", "BNB_USDT",
]


@dataclass
class ScanResult:
    """Diagnosis summary for one instrument."""
    instrument: str
    price: float
    change_pct: float
    regime: str
    dominant_theory: str
    pattern_count: int
    top_pattern: str
    top_pattern_strength: float
    collision_count: int
    signal_score: float  # composite score for ranking

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "price": self.price,
            "change_pct": round(self.change_pct, 4),
            "regime": self.regime,
            "dominant_theory": self.dominant_theory,
            "pattern_count": self.pattern_count,
            "top_pattern": self.top_pattern,
            "top_pattern_strength": round(self.top_pattern_strength, 3),
            "collision_count": self.collision_count,
            "signal_score": round(self.signal_score, 3),
        }


def _compute_signal_score(diagnosis) -> float:
    """Compute a composite signal score from a diagnosis.

    Higher score = stronger/more actionable signal.
    Combines pattern strengths, collision count, and regime clarity.
    """
    patterns = diagnosis.patterns
    if not patterns:
        return 0.0

    # Average pattern strength
    avg_strength = sum(p.strength for p in patterns) / len(patterns)

    # Bonus for multiple strong patterns (more context = better signal)
    multi_bonus = min(0.3, len(patterns) * 0.1)

    # Bonus for collision insights (cross-domain bridges add confidence)
    collision_bonus = min(0.2, len(diagnosis.collision_insights) * 0.1)

    # Regime clarity: non-quiet regimes are more actionable
    regime_bonus = 0.1 if diagnosis.regime != "quiet" else 0.0

    return min(1.0, avg_strength + multi_bonus + collision_bonus + regime_bonus)


def scan_instruments(
    instruments: list[str] | None = None,
    timeframe: str = "4h",
    fetch_fn=None,
) -> list[ScanResult]:
    """Scan multiple instruments and rank by signal strength.

    Args:
        instruments: List of instrument names (defaults to DEFAULT_PAIRS).
        timeframe: Candle timeframe.
        fetch_fn: Optional function(instrument, timeframe) -> list[dict].
                  Defaults to Crypto.com API fetch.

    Returns:
        List of ScanResult sorted by signal_score descending.
    """
    from zhihuiti.crypto_oracle import diagnose_market

    if instruments is None:
        instruments = DEFAULT_PAIRS

    if fetch_fn is None:
        from zhihuiti.api import _fetch_crypto_candles
        fetch_fn = _fetch_crypto_candles

    results: list[ScanResult] = []
    errors: list[str] = []

    for inst in instruments:
        try:
            candles = fetch_fn(inst, timeframe)
            if not candles:
                errors.append(f"{inst}: no data")
                continue

            diag = diagnose_market(candles, instrument=inst)
            signal_score = _compute_signal_score(diag)

            top_pattern = diag.patterns[0] if diag.patterns else None

            results.append(ScanResult(
                instrument=inst,
                price=diag.price,
                change_pct=diag.change_pct,
                regime=diag.regime,
                dominant_theory=diag.dominant_theory,
                pattern_count=len(diag.patterns),
                top_pattern=top_pattern.name if top_pattern else "",
                top_pattern_strength=top_pattern.strength if top_pattern else 0.0,
                collision_count=len(diag.collision_insights),
                signal_score=signal_score,
            ))
        except Exception as e:
            errors.append(f"{inst}: {e}")

    results.sort(key=lambda r: -r.signal_score)
    return results


# ── Regime history tracker ─────────────────────────────────────────────────

@dataclass
class RegimeSnapshot:
    """A point-in-time regime observation."""
    instrument: str
    timestamp: float  # unix timestamp
    regime: str
    price: float
    change_pct: float
    pattern_count: int
    top_pattern: str
    signal_score: float

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "timestamp": self.timestamp,
            "regime": self.regime,
            "price": self.price,
            "change_pct": round(self.change_pct, 4),
            "pattern_count": self.pattern_count,
            "top_pattern": self.top_pattern,
            "signal_score": round(self.signal_score, 3),
        }


@dataclass
class RegimeTransition:
    """A detected regime change."""
    instrument: str
    timestamp: float
    from_regime: str
    to_regime: str
    price: float
    signal_score: float

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "timestamp": self.timestamp,
            "from_regime": self.from_regime,
            "to_regime": self.to_regime,
            "price": self.price,
            "signal_score": round(self.signal_score, 3),
        }


class RegimeHistory:
    """Persists regime snapshots and detects transitions.

    Stores data in a JSON file (one per instrument line).
    Thread-safe for concurrent writes.
    """

    def __init__(self, storage_path: str | Path | None = None, max_snapshots: int = 500):
        if storage_path is None:
            self._path = Path.home() / ".zhihuiti" / "regime_history.jsonl"
        else:
            self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._max = max_snapshots

        # In-memory cache: instrument -> list of snapshots (most recent last)
        self._cache: dict[str, list[RegimeSnapshot]] = {}
        self._load()

    def _load(self):
        """Load history from disk."""
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    snap = RegimeSnapshot(**d)
                    self._cache.setdefault(snap.instrument, []).append(snap)
        except Exception:
            pass

    def _save(self):
        """Write all snapshots to disk."""
        try:
            with open(self._path, "w") as f:
                for snapshots in self._cache.values():
                    for snap in snapshots[-self._max:]:
                        f.write(json.dumps(snap.to_dict()) + "\n")
        except Exception:
            pass

    def record(self, scan_result: ScanResult) -> RegimeTransition | None:
        """Record a scan result and return a transition if regime changed."""
        snap = RegimeSnapshot(
            instrument=scan_result.instrument,
            timestamp=time.time(),
            regime=scan_result.regime,
            price=scan_result.price,
            change_pct=scan_result.change_pct,
            pattern_count=scan_result.pattern_count,
            top_pattern=scan_result.top_pattern,
            signal_score=scan_result.signal_score,
        )

        with self._lock:
            history = self._cache.setdefault(scan_result.instrument, [])
            prev = history[-1] if history else None

            history.append(snap)
            # Trim to max
            if len(history) > self._max:
                self._cache[scan_result.instrument] = history[-self._max:]

            self._save()

        # Detect transition
        if prev and prev.regime != snap.regime:
            return RegimeTransition(
                instrument=snap.instrument,
                timestamp=snap.timestamp,
                from_regime=prev.regime,
                to_regime=snap.regime,
                price=snap.price,
                signal_score=snap.signal_score,
            )
        return None

    def record_scan(self, scan_results: list[ScanResult]) -> list[RegimeTransition]:
        """Record a full scan and return any transitions detected."""
        transitions = []
        for sr in scan_results:
            t = self.record(sr)
            if t:
                transitions.append(t)
        return transitions

    def get_history(self, instrument: str, limit: int = 50) -> list[dict]:
        """Get recent regime history for an instrument."""
        with self._lock:
            snapshots = self._cache.get(instrument, [])
        return [s.to_dict() for s in snapshots[-limit:]]

    def get_transitions(self, instrument: str | None = None, limit: int = 20) -> list[dict]:
        """Get recent regime transitions, optionally filtered by instrument."""
        with self._lock:
            all_snaps: list[tuple[str, list[RegimeSnapshot]]] = []
            if instrument:
                snaps = self._cache.get(instrument, [])
                all_snaps = [(instrument, snaps)]
            else:
                all_snaps = list(self._cache.items())

        transitions = []
        for inst, snaps in all_snaps:
            for i in range(1, len(snaps)):
                if snaps[i].regime != snaps[i - 1].regime:
                    transitions.append(RegimeTransition(
                        instrument=inst,
                        timestamp=snaps[i].timestamp,
                        from_regime=snaps[i - 1].regime,
                        to_regime=snaps[i].regime,
                        price=snaps[i].price,
                        signal_score=snaps[i].signal_score,
                    ).to_dict())

        transitions.sort(key=lambda t: -t["timestamp"])
        return transitions[:limit]

    def get_all_instruments(self) -> list[str]:
        """List all instruments with history."""
        with self._lock:
            return list(self._cache.keys())

    def get_summary(self) -> dict:
        """Get a summary of current regimes across all instruments."""
        with self._lock:
            summary = {}
            for inst, snaps in self._cache.items():
                if snaps:
                    latest = snaps[-1]
                    summary[inst] = {
                        "regime": latest.regime,
                        "price": latest.price,
                        "signal_score": round(latest.signal_score, 3),
                        "snapshots": len(snaps),
                    }
        return summary
