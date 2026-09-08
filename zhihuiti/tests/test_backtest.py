"""Tests for candle-derived historical oracle validation."""

from __future__ import annotations

import time

from zhihuiti import backtest
from zhihuiti.backtest import (
    PredictionRecord,
    build_regime_history_from_candles,
    get_forecast_scorecards,
)
from zhihuiti.oracle_intelligence import predict_transition_calibrated


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
        timestamp=time.time() - 16_000,
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
        observation_at=time.time() - 1,
        source_at_prediction=time.time() - 17000,
        outcome_source_at=time.time() - 3600,
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
    assert summary["transition_event_true_positives"] == 1
    assert summary["transition_event_false_positives"] == 0
    assert summary["transition_event_false_negatives"] == 1
    assert summary["transition_event_precision"] == 1.0
    assert summary["transition_event_recall"] == 0.5
    assert summary["transition_event_f1"] == 2 / 3
    assert summary["transition_base_rate"] == 2 / 3
    assert summary["status"] == "benchmarking"


def test_forward_summary_keeps_shadow_model_isolated(monkeypatch):
    incumbent = _prediction("quiet", "quiet", "quiet")
    shadow = _prediction("trending_up", "quiet", "trending_up")
    shadow.model_version = "transition-calibrated-v1"
    monkeypatch.setattr(backtest, "_predictions", [incumbent, shadow])

    incumbent_summary = backtest.get_forward_accuracy_summary(minimum_verified=1)
    shadow_summary = backtest.get_forward_accuracy_summary(
        minimum_verified=1,
        model_version="transition-calibrated-v1",
    )

    assert incumbent_summary["verified"] == 1
    assert incumbent_summary["accuracy"] == 1.0
    assert shadow_summary["verified"] == 1
    assert shadow_summary["transition_recall"] == 1.0


def test_transition_candidate_is_calibrated_and_cannot_self_promote(monkeypatch):
    history = [
        _prediction("quiet", "quiet", "quiet").to_dict()
        for _ in range(24)
    ]
    transition = _prediction("quiet", "quiet", "trending_up").to_dict()
    history.append(transition)

    prediction = predict_transition_calibrated("TEST", "quiet", history)

    assert prediction.predicted_regime == "quiet"
    assert 0 < prediction.probabilities["trending_up"] < 0.5
    assert prediction.probabilities["quiet"] < 1.0

    monkeypatch.setattr(backtest, "_predictions", [])
    scorecards = get_forecast_scorecards()
    assert scorecards["production_model"] == "incumbent-v1"
    assert scorecards["promotion_ready"] is False
    assert scorecards["claim_status"] == "advisory_only"
    assert scorecards["headline_eligible"] is False
    assert "no_skill_over_persistence" in scorecards["promotion_blockers"]


def test_auto_record_reports_warmup_instead_of_silently_skipping(monkeypatch):
    class EmptyHistory:
        def get_history(self, instrument, limit=100):
            return []

    monkeypatch.setattr(backtest, "verify_predictions", lambda *args: 0)
    monkeypatch.setattr(backtest, "_predictions", [])

    result = backtest.auto_record_and_verify([
        {"instrument": "TEST", "regime": "quiet", "price": 100,
         "observed_at": time.time(), "source_at": time.time() - 3600},
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
    assert backtest.verify_predictions("TEST", "quiet", 100.0, source_at=time.time()-3600) == 1


def test_outage_does_not_score_month_old_predictions(monkeypatch):
    pred = _prediction("quiet", "quiet", "")
    pred.timestamp = time.time() - 30 * 86400
    pred.verified_at = 0
    monkeypatch.setattr(backtest, "_predictions", [pred])
    assert backtest.verify_predictions("TEST", "quiet", 100) == 0
    summary = backtest.get_forward_accuracy_summary()
    assert summary["expired"] == 1
    assert summary["pending"] == summary["verified"] == 0
    assert pred.actual_regime == ""


def test_uses_observation_time_and_persisted_horizon(monkeypatch):
    monkeypatch.setattr(backtest.time, "time", lambda: 100000)
    pred = _prediction("quiet", "quiet", "")
    pred.timestamp = 80000
    pred.verified_at = 0
    pred.source_at_prediction = 79000
    monkeypatch.setattr(backtest, "_predictions", [pred])
    monkeypatch.setattr(backtest, "_rewrite_store", lambda: None)
    monkeypatch.setenv("ZHIHUITI_PREDICTION_HORIZON_SECONDS", "3600")
    assert backtest.verify_predictions("TEST", "quiet", 100, 94000, 93000) == 0
    assert backtest.verify_predictions("TEST", "quiet", 100, 95000, 79000) == 0
    assert backtest.verify_predictions("TEST", "quiet", 100, 100001, 99000) == 0
    assert backtest.verify_predictions("TEST", "quiet", float("nan"), 95000, 93000) == 0
    assert backtest.verify_predictions("TEST", "quiet", 100, 95000, 93000) == 1
    assert pred.observation_at == 95000
    assert pred.outcome_source_at == 93000


def test_missing_source_observation_is_not_recorded(monkeypatch):
    monkeypatch.setattr(backtest, "_predictions", [])
    result = backtest.auto_record_and_verify([
        {"instrument": "TEST", "regime": "quiet", "price": 100},
    ])
    assert result["verified"] == 0
    assert result["prediction_errors"][0]["error"] == "missing_or_stale_observation"
    assert backtest._predictions == []


def test_record_and_reload_preserves_verification_contract(monkeypatch, tmp_path):
    monkeypatch.setattr(backtest, "_predictions", [])
    monkeypatch.setattr(backtest, "_store_path", tmp_path / "predictions.jsonl")
    monkeypatch.setenv("ZHIHUITI_PREDICTION_HORIZON_SECONDS", "7200")
    pred = backtest.record_prediction("TEST", "quiet", "quiet", .5, {"quiet": 1}, [], 100, source_at=1000)
    monkeypatch.setattr(backtest, "_predictions", [])
    backtest._load_predictions()
    assert backtest._predictions[0].to_dict() == pred.to_dict()
    assert pred.horizon_seconds == 7200


def test_failed_rewrite_preserves_original_ledger(monkeypatch, tmp_path):
    import pytest
    ledger = tmp_path / "predictions.jsonl"
    ledger.write_text("original\n")
    monkeypatch.setattr(backtest, "_store_path", ledger)
    monkeypatch.setattr(backtest, "_predictions", [_prediction("quiet", "quiet", "quiet")])
    def fail_replace(*args):
        raise OSError("simulated disk error")
    monkeypatch.setattr(backtest.os, "replace", fail_replace)
    with pytest.raises(OSError):
        backtest._rewrite_store()
    assert ledger.read_text() == "original\n"
    assert list(tmp_path.glob(".predictions-*")) == []


def test_legacy_late_labels_are_preserved_but_excluded(monkeypatch):
    pred = _prediction("quiet", "quiet", "quiet")
    pred.timestamp = time.time() - 30*86400
    pred.observation_at = 0
    pred.source_at_prediction = 0
    monkeypatch.setattr(backtest, "_predictions", [pred])
    summary = backtest.get_forward_accuracy_summary()
    assert summary["verified"] == summary["correct"] == summary["pending"] == 0
    assert summary["expired"] == summary["excluded_outcomes"] == 1
    assert pred.verified_at > 0  # original evidence is retained, not erased


def test_recent_legacy_forecast_without_source_is_unscorable(monkeypatch):
    pred = _prediction("quiet", "quiet", "")
    pred.timestamp = time.time()
    pred.verified_at = 0
    pred.source_at_prediction = 0
    monkeypatch.setattr(backtest, "_predictions", [pred])
    summary = backtest.get_forward_accuracy_summary()
    assert summary["unscorable"] == 1
    assert summary["pending"] == summary["verified"] == summary["expired"] == 0
