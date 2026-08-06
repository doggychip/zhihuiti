"""Tests for candle-derived historical oracle validation."""

from __future__ import annotations

from zhihuiti.backtest import build_regime_history_from_candles


def _candles(count: int = 80) -> list[dict]:
    return [
        {
            "timestamp": 1_700_000_000 + index * 3600,
            "open": 100 + index,
            "high": 102 + index,
            "low": 99 + index,
            "close": 101 + index,
            "volume": 1_000 + index,
        }
        for index in range(count)
    ]


def test_builds_chronological_regime_snapshots_from_candles():
    snapshots = build_regime_history_from_candles(
        "TEST", _candles(), min_window=30, max_snapshots=20,
    )

    assert len(snapshots) >= 10
    assert snapshots == sorted(snapshots, key=lambda item: item["timestamp"])
    assert all(snapshot["instrument"] == "TEST" for snapshot in snapshots)
    assert all(snapshot["price"] > 0 for snapshot in snapshots)
    assert all(snapshot["regime"] for snapshot in snapshots)


def test_requires_enough_candles_for_honest_validation():
    assert build_regime_history_from_candles(
        "TEST", _candles(35), min_window=30, max_snapshots=20,
    ) == []
