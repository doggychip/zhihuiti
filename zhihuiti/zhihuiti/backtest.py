"""Backtesting engine — verify oracle predictions against actual outcomes.

Records predictions made by predict_regime(), then checks what actually
happened when new scan data comes in. Tracks accuracy, calibration, and
pattern reliability over time.

Usage:
  GET /api/backtest/run          — run backtest on all instruments with history
  GET /api/backtest/results      — get latest backtest results
  GET /api/backtest/accuracy     — overall prediction accuracy stats
  POST /api/backtest/predict     — record a prediction for future verification
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ── Data structures ──────────────────────────────────────────────────────

@dataclass
class PredictionRecord:
    """A recorded prediction to be verified later."""
    instrument: str
    timestamp: float
    predicted_regime: str
    current_regime: str
    confidence: float
    probabilities: dict[str, float]
    patterns_at_prediction: list[str]  # pattern names active at prediction time
    price_at_prediction: float
    baseline_regime: str = ""
    model_version: str = "incumbent-v1"
    # Filled in after verification
    actual_regime: str = ""
    actual_price: float = 0.0
    verified_at: float = 0.0
    correct: bool = False
    baseline_correct: bool = False
    price_change_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BacktestResult:
    """Results from running a backtest on historical data."""
    instrument: str
    total_predictions: int
    correct_predictions: int
    accuracy: float
    avg_confidence: float
    avg_confidence_when_correct: float
    avg_confidence_when_wrong: float
    regime_accuracy: dict[str, dict]  # regime → {total, correct, accuracy}
    pattern_reliability: dict[str, dict]  # pattern → {present_count, correct_when_present}
    recent_predictions: list[dict]  # last 20 prediction records

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OverallAccuracy:
    """Aggregate accuracy across all instruments."""
    total_predictions: int
    correct_predictions: int
    accuracy: float
    calibration: list[dict]  # confidence bucket → actual accuracy
    best_instrument: str
    worst_instrument: str
    best_regime: str
    worst_regime: str
    instruments: dict[str, float]  # instrument → accuracy

    def to_dict(self) -> dict:
        return asdict(self)


# ── Prediction Store ─────────────────────────────────────────────────────

_predictions: list[PredictionRecord] = []
_predictions_lock = threading.Lock()
_store_path = Path(os.environ.get("ZHIHUITI_DATA", "/app/data")) / "predictions.jsonl"


def prediction_horizon_seconds() -> int:
    """Return the minimum forward-verification horizon (default: four hours)."""
    try:
        return max(3600, int(os.environ.get(
            "ZHIHUITI_PREDICTION_HORIZON_SECONDS", "14400",
        )))
    except ValueError:
        return 14400


def _load_predictions():
    """Load saved predictions from disk."""
    global _predictions
    if _store_path.exists():
        with _predictions_lock:
            try:
                with open(_store_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            d = json.loads(line)
                            _predictions.append(PredictionRecord(**d))
            except Exception:
                pass


def _save_prediction(pred: PredictionRecord):
    """Append a prediction to disk."""
    _store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_store_path, "a") as f:
        f.write(json.dumps(pred.to_dict()) + "\n")


def record_prediction(
    instrument: str,
    predicted_regime: str,
    current_regime: str,
    confidence: float,
    probabilities: dict[str, float],
    patterns: list[str],
    price: float,
    model_version: str = "incumbent-v1",
) -> PredictionRecord:
    """Record a prediction for future verification."""
    pred = PredictionRecord(
        instrument=instrument,
        timestamp=time.time(),
        predicted_regime=predicted_regime,
        current_regime=current_regime,
        confidence=confidence,
        probabilities=probabilities,
        patterns_at_prediction=patterns,
        price_at_prediction=price,
        baseline_regime=current_regime,
        model_version=model_version,
    )
    with _predictions_lock:
        _predictions.append(pred)
    _save_prediction(pred)
    return pred


def verify_predictions(instrument: str, actual_regime: str, actual_price: float) -> int:
    """Verify unverified predictions for an instrument against actual outcome.

    Returns number of predictions verified.
    """
    verified = 0
    now = time.time()
    with _predictions_lock:
        for pred in _predictions:
            if pred.instrument == instrument and not pred.verified_at:
                # Verify only after the configured forward horizon has elapsed.
                if now - pred.timestamp < prediction_horizon_seconds():
                    continue
                pred.actual_regime = actual_regime
                pred.actual_price = actual_price
                pred.verified_at = now
                pred.correct = pred.predicted_regime == actual_regime
                baseline = pred.baseline_regime or pred.current_regime
                pred.baseline_correct = baseline == actual_regime
                if pred.price_at_prediction > 0:
                    pred.price_change_pct = (
                        (actual_price - pred.price_at_prediction)
                        / pred.price_at_prediction * 100
                    )
                verified += 1
    # Rewrite store with updated predictions
    if verified > 0:
        _rewrite_store()
    return verified


def get_forward_accuracy_summary(
    minimum_verified: int = 30,
    model_version: str = "incumbent-v1",
) -> dict:
    """Measure forecast value relative to a naive regime-persistence baseline."""
    from zhihuiti.oracle_intelligence import REGIMES

    with _predictions_lock:
        predictions = list(_predictions)
    predictions = [
        prediction for prediction in predictions
        if prediction.model_version == model_version
    ]
    verified = [prediction for prediction in predictions if prediction.verified_at > 0]
    total = len(verified)
    correct = sum(1 for prediction in verified if prediction.correct)
    baseline_correct = sum(
        1 for prediction in verified
        if (prediction.baseline_regime or prediction.current_regime)
        == prediction.actual_regime
    )

    regime_stats: dict[str, dict] = {}
    for prediction in verified:
        actual = prediction.actual_regime or "unknown"
        stats = regime_stats.setdefault(actual, {"total": 0, "correct": 0})
        stats["total"] += 1
        if prediction.correct:
            stats["correct"] += 1
    for stats in regime_stats.values():
        stats["accuracy"] = stats["correct"] / stats["total"]

    transition_predictions = [
        prediction for prediction in verified
        if prediction.actual_regime
        != (prediction.baseline_regime or prediction.current_regime)
    ]
    transition_correct = sum(
        1 for prediction in transition_predictions if prediction.correct
    )
    predicted_transitions = [
        prediction for prediction in verified
        if prediction.predicted_regime
        != (prediction.baseline_regime or prediction.current_regime)
    ]
    transition_false_alarms = sum(
        1 for prediction in predicted_transitions
        if prediction.actual_regime
        == (prediction.baseline_regime or prediction.current_regime)
    )

    brier_values = []
    for prediction in verified:
        if prediction.actual_regime not in REGIMES:
            continue
        brier_values.append(sum(
            (
                float(prediction.probabilities.get(regime, 0.0))
                - (1.0 if regime == prediction.actual_regime else 0.0)
            ) ** 2
            for regime in REGIMES
        ))

    accuracy = correct / total if total else 0.0
    baseline_accuracy = baseline_correct / total if total else 0.0
    balanced_accuracy = (
        sum(stats["accuracy"] for stats in regime_stats.values()) / len(regime_stats)
        if regime_stats else 0.0
    )
    skill = accuracy - baseline_accuracy
    enough_transitions = len(transition_predictions) >= 10
    if total < minimum_verified:
        status = "collecting"
    elif skill <= 0 or not enough_transitions:
        status = "benchmarking"
    else:
        status = "validated"

    recent = [
        prediction.to_dict()
        for prediction in sorted(predictions, key=lambda item: item.timestamp, reverse=True)[:20]
    ]
    return {
        "model_version": model_version,
        "status": status,
        "minimum_verified_predictions": minimum_verified,
        "minimum_transition_predictions": 10,
        "horizon_seconds": prediction_horizon_seconds(),
        "total_predictions": len(predictions),
        "verified": total,
        "correct": correct,
        "accuracy": accuracy,
        "persistence_baseline_accuracy": baseline_accuracy,
        "skill_over_persistence": skill,
        "balanced_accuracy": balanced_accuracy,
        "brier_score": sum(brier_values) / len(brier_values) if brier_values else None,
        "transition_predictions": len(transition_predictions),
        "transition_correct": transition_correct,
        "transition_accuracy": (
            transition_correct / len(transition_predictions)
            if transition_predictions else None
        ),
        "predicted_transitions": len(predicted_transitions),
        "transition_precision": (
            transition_correct / len(predicted_transitions)
            if predicted_transitions else None
        ),
        "transition_recall": (
            transition_correct / len(transition_predictions)
            if transition_predictions else None
        ),
        "transition_false_alarms": transition_false_alarms,
        "unverified": len(predictions) - total,
        "regime_accuracy": regime_stats,
        "recent": recent,
    }


def get_forecast_scorecards() -> dict:
    """Return isolated incumbent and shadow scorecards with a strict promotion gate."""
    with _predictions_lock:
        versions = sorted({prediction.model_version for prediction in _predictions})

    incumbent = get_forward_accuracy_summary(model_version="incumbent-v1")
    models = {"incumbent-v1": incumbent}
    for version in versions:
        if version != "incumbent-v1":
            models[version] = get_forward_accuracy_summary(model_version=version)

    candidate = models.get("transition-calibrated-v1")
    promotion_ready = bool(
        candidate
        and candidate["verified"] >= candidate["minimum_verified_predictions"]
        and candidate["transition_predictions"]
        >= candidate["minimum_transition_predictions"]
        and candidate["skill_over_persistence"] > 0
        and candidate["brier_score"] is not None
        and incumbent["brier_score"] is not None
        and candidate["brier_score"] < incumbent["brier_score"]
        and (candidate["transition_precision"] or 0) > 0
        and (candidate["transition_recall"] or 0) > 0
    )
    return {
        "production_model": "incumbent-v1",
        "shadow_model": "transition-calibrated-v1",
        "promotion_ready": promotion_ready,
        "models": models,
    }


def _rewrite_store():
    """Rewrite the full prediction store (after verification updates)."""
    _store_path.parent.mkdir(parents=True, exist_ok=True)
    with _predictions_lock:
        with open(_store_path, "w") as f:
            for pred in _predictions:
                f.write(json.dumps(pred.to_dict()) + "\n")


# ── Backtesting Engine ───────────────────────────────────────────────────

def build_regime_history_from_candles(
    instrument: str,
    candles: list[dict],
    min_window: int = 30,
    max_snapshots: int = 60,
) -> list[dict]:
    """Build a chronological, no-lookahead regime series from OHLCV candles.

    Each snapshot diagnoses only candles available at that point. This provides
    immediate historical validation without pretending repeated current scans
    are independent observations.
    """
    if len(candles) < min_window + 10:
        return []

    from zhihuiti.crypto_oracle import diagnose_market

    available = len(candles) - min_window + 1
    step = max(1, available // max(1, max_snapshots))
    endpoints = list(range(min_window, len(candles) + 1, step))
    if endpoints[-1] != len(candles):
        endpoints.append(len(candles))
    endpoints = endpoints[-max_snapshots:]

    snapshots = []
    for end in endpoints:
        visible = candles[:end]
        diagnosis = diagnose_market(visible, instrument=instrument)
        top_pattern = diagnosis.patterns[0] if diagnosis.patterns else None
        candle_timestamp = visible[-1].get("timestamp", end)
        if isinstance(candle_timestamp, (int, float)) and candle_timestamp > 10_000_000_000:
            candle_timestamp /= 1000
        snapshots.append({
            "instrument": instrument,
            "timestamp": float(candle_timestamp),
            "regime": diagnosis.regime,
            "price": diagnosis.price,
            "change_pct": diagnosis.change_pct,
            "pattern_count": len(diagnosis.patterns),
            "top_pattern": top_pattern.name if top_pattern else "",
            "top_pattern_strength": top_pattern.strength if top_pattern else 0.0,
            "signal_score": 0.0,
        })
    return snapshots

def run_backtest_historical(instrument: str, history: list[dict]) -> BacktestResult:
    """Run a backtest using historical regime data.

    Simulates making predictions at each point in history using the
    transition matrix built from prior data, then checks accuracy.
    """
    from zhihuiti.oracle_intelligence import build_transition_matrix, predict_regime

    if len(history) < 10:
        return BacktestResult(
            instrument=instrument,
            total_predictions=0,
            correct_predictions=0,
            accuracy=0.0,
            avg_confidence=0.0,
            avg_confidence_when_correct=0.0,
            avg_confidence_when_wrong=0.0,
            regime_accuracy={},
            pattern_reliability={},
            recent_predictions=[],
        )

    predictions = []
    regime_stats: dict[str, dict] = {}
    pattern_stats: dict[str, dict] = {}

    # Use a sliding window: predict from history[:i], verify with history[i]
    min_window = 5  # need at least 5 points to build transition matrix
    for i in range(min_window, len(history) - 1):
        past = history[:i]
        current = history[i]
        actual_next = history[i + 1]

        current_regime = current.get("regime", "quiet")
        patterns = []
        if current.get("top_pattern"):
            patterns.append({"name": current["top_pattern"],
                             "strength": current.get("top_pattern_strength", 0.5)})

        try:
            prediction = predict_regime(
                instrument=instrument,
                history=past,
                current_regime=current_regime,
                patterns=patterns,
            )
        except Exception:
            continue

        actual_regime = actual_next.get("regime", "quiet")
        correct = prediction.predicted_regime == actual_regime

        rec = {
            "predicted": prediction.predicted_regime,
            "actual": actual_regime,
            "confidence": prediction.confidence,
            "correct": correct,
            "current_regime": current_regime,
            "patterns": [p["name"] for p in patterns],
            "price": current.get("price", 0),
            "actual_price": actual_next.get("price", 0),
        }
        predictions.append(rec)

        # Track per-regime accuracy
        if current_regime not in regime_stats:
            regime_stats[current_regime] = {"total": 0, "correct": 0}
        regime_stats[current_regime]["total"] += 1
        if correct:
            regime_stats[current_regime]["correct"] += 1

        # Track pattern reliability
        for p in patterns:
            pname = p["name"]
            if pname not in pattern_stats:
                pattern_stats[pname] = {"present_count": 0, "correct_when_present": 0}
            pattern_stats[pname]["present_count"] += 1
            if correct:
                pattern_stats[pname]["correct_when_present"] += 1

    # Calculate results
    total = len(predictions)
    correct_count = sum(1 for p in predictions if p["correct"])
    accuracy = correct_count / total if total > 0 else 0.0

    confidences = [p["confidence"] for p in predictions]
    correct_confs = [p["confidence"] for p in predictions if p["correct"]]
    wrong_confs = [p["confidence"] for p in predictions if not p["correct"]]

    # Add accuracy to regime stats
    for regime, stats in regime_stats.items():
        stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0

    # Add accuracy to pattern stats
    for pattern, stats in pattern_stats.items():
        stats["accuracy"] = (
            stats["correct_when_present"] / stats["present_count"]
            if stats["present_count"] > 0 else 0.0
        )

    return BacktestResult(
        instrument=instrument,
        total_predictions=total,
        correct_predictions=correct_count,
        accuracy=accuracy,
        avg_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        avg_confidence_when_correct=sum(correct_confs) / len(correct_confs) if correct_confs else 0.0,
        avg_confidence_when_wrong=sum(wrong_confs) / len(wrong_confs) if wrong_confs else 0.0,
        regime_accuracy=regime_stats,
        pattern_reliability=pattern_stats,
        recent_predictions=predictions[-20:],
    )


def run_backtest_all() -> list[BacktestResult]:
    """Run backtest on all instruments with enough history."""
    from zhihuiti.scanner import RegimeHistory

    history = RegimeHistory()
    instruments = history.get_all_instruments()
    results = []

    for instrument in instruments:
        hist = history.get_history(instrument, limit=500)
        if len(hist) >= 10:
            result = run_backtest_historical(instrument, hist)
            results.append(result)

    return results


def get_overall_accuracy(results: list[BacktestResult]) -> OverallAccuracy:
    """Calculate aggregate accuracy from backtest results."""
    total = sum(r.total_predictions for r in results)
    correct = sum(r.correct_predictions for r in results)
    accuracy = correct / total if total > 0 else 0.0

    # Per-instrument accuracy
    instruments = {r.instrument: r.accuracy for r in results if r.total_predictions > 0}

    best_inst = max(instruments, key=instruments.get) if instruments else ""
    worst_inst = min(instruments, key=instruments.get) if instruments else ""

    # Per-regime accuracy (merged across instruments)
    regime_totals: dict[str, dict] = {}
    for r in results:
        for regime, stats in r.regime_accuracy.items():
            if regime not in regime_totals:
                regime_totals[regime] = {"total": 0, "correct": 0}
            regime_totals[regime]["total"] += stats["total"]
            regime_totals[regime]["correct"] += stats["correct"]

    regime_acc = {
        r: s["correct"] / s["total"] if s["total"] > 0 else 0.0
        for r, s in regime_totals.items()
    }
    best_regime = max(regime_acc, key=regime_acc.get) if regime_acc else ""
    worst_regime = min(regime_acc, key=regime_acc.get) if regime_acc else ""

    # Confidence calibration buckets
    all_preds = []
    for r in results:
        all_preds.extend(r.recent_predictions)

    buckets = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    calibration = []
    for low, high in buckets:
        bucket_preds = [p for p in all_preds if low <= p["confidence"] < high]
        bucket_correct = sum(1 for p in bucket_preds if p["correct"])
        calibration.append({
            "bucket": f"{low:.1f}-{high:.1f}",
            "count": len(bucket_preds),
            "correct": bucket_correct,
            "actual_accuracy": bucket_correct / len(bucket_preds) if bucket_preds else 0.0,
        })

    return OverallAccuracy(
        total_predictions=total,
        correct_predictions=correct,
        accuracy=accuracy,
        calibration=calibration,
        best_instrument=best_inst,
        worst_instrument=worst_inst,
        best_regime=best_regime,
        worst_regime=worst_regime,
        instruments=instruments,
    )


# ── Auto-verify on scan ─────────────────────────────────────────────────

def auto_record_and_verify(scan_results: list, history=None) -> dict:
    """Called after each scan to:
    1. Verify old predictions against new data
    2. Record new predictions for future verification

    Returns summary of verifications and new predictions.
    """
    from zhihuiti.oracle_intelligence import (
        predict_regime,
        predict_transition_calibrated,
    )
    from zhihuiti.scanner import RegimeHistory

    history = history or RegimeHistory()
    verified_count = 0
    new_predictions = 0
    eligible_instruments = 0
    warming_instruments = 0
    prediction_errors: list[dict[str, str]] = []
    shadow_predictions = 0

    for result in scan_results:
        instrument = result.instrument if hasattr(result, 'instrument') else result.get("instrument", "")
        regime = result.regime if hasattr(result, 'regime') else result.get("regime", "quiet")
        price = result.price if hasattr(result, 'price') else result.get("price", 0)

        # Verify old predictions
        verified_count += verify_predictions(instrument, regime, price)

        # Make and record new prediction
        try:
            hist = history.get_history(instrument, limit=100)
            if len(hist) >= 5:
                eligible_instruments += 1
                patterns = []
                top_pattern = result.top_pattern if hasattr(result, 'top_pattern') else result.get("top_pattern", "")
                top_strength = result.top_pattern_strength if hasattr(result, 'top_pattern_strength') else result.get("top_pattern_strength", 0.5)
                if top_pattern:
                    patterns.append({"name": top_pattern, "strength": top_strength})

                prediction = predict_regime(
                    instrument=instrument,
                    history=hist,
                    current_regime=regime,
                    patterns=patterns,
                )
                record_prediction(
                    instrument=instrument,
                    predicted_regime=prediction.predicted_regime,
                    current_regime=regime,
                    confidence=prediction.confidence,
                    probabilities=prediction.probabilities,
                    patterns=[p["name"] for p in patterns],
                    price=price,
                )
                new_predictions += 1

                with _predictions_lock:
                    verified_history = [
                        item.to_dict()
                        for item in _predictions
                        if item.verified_at > 0
                        and item.model_version == "incumbent-v1"
                    ]
                shadow = predict_transition_calibrated(
                    instrument=instrument,
                    current_regime=regime,
                    verified_history=verified_history,
                )
                record_prediction(
                    instrument=instrument,
                    predicted_regime=shadow.predicted_regime,
                    current_regime=regime,
                    confidence=shadow.confidence,
                    probabilities=shadow.probabilities,
                    patterns=[p["name"] for p in patterns],
                    price=price,
                    model_version="transition-calibrated-v1",
                )
                shadow_predictions += 1
            else:
                warming_instruments += 1
        except Exception as exc:
            prediction_errors.append({
                "instrument": instrument,
                "error": type(exc).__name__,
            })

    return {
        "status": "active" if eligible_instruments else "collecting",
        "verified": verified_count,
        "new_predictions": new_predictions,
        "shadow_predictions": shadow_predictions,
        "total_stored": len(_predictions),
        "eligible_instruments": eligible_instruments,
        "warming_instruments": warming_instruments,
        "prediction_errors": prediction_errors,
    }


# Load on import
_load_predictions()
