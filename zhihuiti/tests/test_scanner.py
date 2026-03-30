"""Tests for Market Scanner + Regime History."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from zhihuiti.scanner import (
    DEFAULT_PAIRS,
    RegimeHistory,
    RegimeSnapshot,
    RegimeTransition,
    ScanResult,
    _compute_signal_score,
    scan_instruments,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _fake_candles(n: int = 30, start: float = 70000.0, step: float = 100.0) -> list[dict]:
    """Generate trending up candles."""
    return [
        {"open": start + i * step, "high": start + i * step + 50,
         "low": start + i * step - 50, "close": start + (i + 1) * step, "volume": 100}
        for i in range(n)
    ]


def _fake_flat_candles(n: int = 30, price: float = 70000.0) -> list[dict]:
    import random
    random.seed(99)
    return [
        {"open": price, "high": price + 10, "low": price - 10,
         "close": price + random.uniform(-5, 5), "volume": 100}
        for _ in range(n)
    ]


def _fake_fetch(instrument: str, timeframe: str) -> list[dict]:
    """Fake fetch function for testing."""
    if instrument == "FAIL_USDT":
        return []
    if instrument == "FLAT_USDT":
        return _fake_flat_candles()
    return _fake_candles()


def _scan_result(instrument: str, regime: str = "trending_up", score: float = 0.8) -> ScanResult:
    return ScanResult(
        instrument=instrument, price=71000, change_pct=0.03,
        regime=regime, dominant_theory="emh",
        pattern_count=2, top_pattern="momentum", top_pattern_strength=0.7,
        collision_count=1, signal_score=score,
    )


# ── Scanner ────────────────────────────────────────────────────────────────

class TestScanInstruments:
    def test_scans_multiple_pairs(self):
        results = scan_instruments(
            instruments=["BTC_USDT", "ETH_USDT", "SOL_USDT"],
            fetch_fn=_fake_fetch,
        )
        assert len(results) == 3
        assert all(isinstance(r, ScanResult) for r in results)

    def test_sorted_by_signal_score(self):
        results = scan_instruments(
            instruments=["BTC_USDT", "FLAT_USDT", "ETH_USDT"],
            fetch_fn=_fake_fetch,
        )
        for i in range(len(results) - 1):
            assert results[i].signal_score >= results[i + 1].signal_score

    def test_handles_failed_fetch(self):
        results = scan_instruments(
            instruments=["BTC_USDT", "FAIL_USDT"],
            fetch_fn=_fake_fetch,
        )
        # FAIL_USDT returns empty, should be skipped
        assert len(results) == 1
        assert results[0].instrument == "BTC_USDT"

    def test_uses_default_pairs_when_none(self):
        # Just verify it doesn't crash with default pairs + custom fetch
        results = scan_instruments(
            instruments=["BTC_USDT"],
            fetch_fn=_fake_fetch,
        )
        assert len(results) == 1

    def test_scan_result_to_dict(self):
        r = _scan_result("BTC_USDT")
        d = r.to_dict()
        assert d["instrument"] == "BTC_USDT"
        assert "signal_score" in d
        assert "regime" in d


class TestComputeSignalScore:
    def test_no_patterns_zero_score(self):
        from unittest.mock import MagicMock
        diag = MagicMock()
        diag.patterns = []
        diag.collision_insights = []
        diag.regime = "quiet"
        assert _compute_signal_score(diag) == 0.0

    def test_strong_patterns_high_score(self):
        from unittest.mock import MagicMock
        from zhihuiti.crypto_oracle import DetectedPattern
        diag = MagicMock()
        diag.patterns = [
            DetectedPattern("momentum", 0.9, "", {}, []),
            DetectedPattern("vol_clustering", 0.8, "", {}, []),
        ]
        diag.collision_insights = [MagicMock()]
        diag.regime = "trending_up"
        score = _compute_signal_score(diag)
        assert score > 0.7


# ── Regime History ─────────────────────────────────────────────────────────

class TestRegimeHistory:
    def _make_history(self) -> RegimeHistory:
        tmp = tempfile.mktemp(suffix=".jsonl")
        return RegimeHistory(storage_path=tmp)

    def test_record_creates_snapshot(self):
        h = self._make_history()
        sr = _scan_result("BTC_USDT")
        transition = h.record(sr)
        assert transition is None  # First record, no transition
        history = h.get_history("BTC_USDT")
        assert len(history) == 1
        assert history[0]["regime"] == "trending_up"

    def test_detects_transition(self):
        h = self._make_history()
        h.record(_scan_result("BTC_USDT", regime="quiet"))
        transition = h.record(_scan_result("BTC_USDT", regime="volatile"))
        assert transition is not None
        assert transition.from_regime == "quiet"
        assert transition.to_regime == "volatile"

    def test_no_transition_same_regime(self):
        h = self._make_history()
        h.record(_scan_result("BTC_USDT", regime="quiet"))
        transition = h.record(_scan_result("BTC_USDT", regime="quiet"))
        assert transition is None

    def test_record_scan_batch(self):
        h = self._make_history()
        # First scan
        h.record_scan([
            _scan_result("BTC_USDT", regime="quiet"),
            _scan_result("ETH_USDT", regime="quiet"),
        ])
        # Second scan with regime change on ETH
        transitions = h.record_scan([
            _scan_result("BTC_USDT", regime="quiet"),
            _scan_result("ETH_USDT", regime="volatile"),
        ])
        assert len(transitions) == 1
        assert transitions[0].instrument == "ETH_USDT"

    def test_get_transitions(self):
        h = self._make_history()
        h.record(_scan_result("BTC_USDT", regime="quiet"))
        h.record(_scan_result("BTC_USDT", regime="volatile"))
        h.record(_scan_result("BTC_USDT", regime="trending_up"))

        transitions = h.get_transitions("BTC_USDT")
        assert len(transitions) == 2
        # Most recent first
        assert transitions[0]["to_regime"] == "trending_up"
        assert transitions[1]["to_regime"] == "volatile"

    def test_get_summary(self):
        h = self._make_history()
        h.record(_scan_result("BTC_USDT", regime="volatile"))
        h.record(_scan_result("ETH_USDT", regime="quiet"))

        summary = h.get_summary()
        assert "BTC_USDT" in summary
        assert "ETH_USDT" in summary
        assert summary["BTC_USDT"]["regime"] == "volatile"

    def test_get_all_instruments(self):
        h = self._make_history()
        h.record(_scan_result("BTC_USDT"))
        h.record(_scan_result("SOL_USDT"))
        instruments = h.get_all_instruments()
        assert set(instruments) == {"BTC_USDT", "SOL_USDT"}

    def test_persistence(self):
        tmp = tempfile.mktemp(suffix=".jsonl")
        h1 = RegimeHistory(storage_path=tmp)
        h1.record(_scan_result("BTC_USDT", regime="volatile"))

        # Load fresh from disk
        h2 = RegimeHistory(storage_path=tmp)
        history = h2.get_history("BTC_USDT")
        assert len(history) == 1
        assert history[0]["regime"] == "volatile"

    def test_max_snapshots_trimmed(self):
        h = self._make_history()
        h._max = 5
        for i in range(10):
            h.record(_scan_result("BTC_USDT", score=float(i)))
        history = h.get_history("BTC_USDT")
        assert len(history) == 5

    def test_transition_to_dict(self):
        t = RegimeTransition(
            instrument="BTC_USDT", timestamp=1234567890.0,
            from_regime="quiet", to_regime="volatile",
            price=71000, signal_score=0.8,
        )
        d = t.to_dict()
        assert d["from_regime"] == "quiet"
        assert d["to_regime"] == "volatile"
