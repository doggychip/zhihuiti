"""Tests for candle-derived historical oracle validation."""

from __future__ import annotations

import time

from zhihuiti import backtest
from zhihuiti.backtest import PredictionRecord, build_regime_history_from_candles


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


def _prediction(predicted: str, current: str, actual: str) -> PredictionRecord:
    return PredictionRecord(
        instrument="TEST",
        timestamp=time.time() - 20_000,
        predicted_regime=predicted,
        current_regime=current,
        confidence=0.8,
        probabilities={
            "trending_up": 0.8 if predicted == "trending_up" else 0.05,
            "trending_down": 0.8 if predicted == "trending_down" else 0.05,
            "mean_reverting": 0.8 if predicted == "mean_reverting" else 0.05,
            "volatile": 0.8 if predicted == "volatile" else 0.05,
            "quiet": 0.8 if predicted == "quiet" else 0.05,
        },
        patterns_at_prediction=[],
        price_at_prediction=100.0,
        baseline_regime=current,
        actual_regime=actual,
        actual_price=101.0,
        verified_at=time.time(),
        correct=predicted == actual,
        baseline_correct=current == actual,
    )


def test_forward_summary_compares_against_persistence(monkeypatch):
    predictions = [
        _prediction("quiet", "quiet", "quiet"),
        _prediction("trending_up", "quiet", "trending_up"),
        _prediction("quiet", "quiet", "trending_down"),
    ]
    monkeypatch.setattr(backtest, "_predictions", predictions)

    summary = backtest.get_forward_accuracy_summary(minimum_verified=1)

    assert summary["accuracy"] == 2 / 3
    assert summary["persistence_baseline_accuracy"] == 1 / 3
    assert summary["skill_over_persistence"] == 1 / 3
    assert summary["transition_predictions"] == 2
    assert summary["transition_accuracy"] == 0.5
    assert summary["predicted_transitions"] == 1
    assert summary["transition_precision"] == 1.0
    assert summary["transition_recall"] == 0.5
    assert summary["transition_false_alarms"] == 0
    assert summary["status"] == "benchmarking"


def test_auto_record_reports_warmup_instead_of_silently_skipping(monkeypatch):
    class EmptyHistory:
        def get_history(self, instrument, limit=100):
            return []

    monkeypatch.setattr(backtest, "verify_predictions", lambda *args: 0)
    monkeypatch.setattr(backtest, "_predictions", [])

    result = backtest.auto_record_and_verify([
        {"instrument": "TEST", "regime": "quiet", "price": 100},
    ], history=EmptyHistory())

    assert result["status"] == "collecting"
    assert result["warming_instruments"] == 1
    assert result["eligible_instruments"] == 0
    assert result["prediction_errors"] == []


def test_prediction_verification_respects_configured_horizon(monkeypatch):
    monkeypatch.setenv("ZHIHUITI_PREDICTION_HORIZON_SECONDS", "14400")
    prediction = _prediction("quiet", "quiet", "")
    prediction.timestamp = time.time() - 3601
    prediction.verified_at = 0.0
    monkeypatch.setattr(backtest, "_predictions", [prediction])
    monkeypatch.setattr(backtest, "_rewrite_store", lambda: None)

    assert backtest.verify_predictions("TEST", "quiet", 100.0) == 0
    prediction.timestamp = time.time() - 14401
    assert backtest.verify_predictions("TEST", "quiet", 100.0) == 1
