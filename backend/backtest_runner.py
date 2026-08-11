"""Point-in-time backtest helpers.

The runner only evaluates predictions that were generated before first pitch.
It intentionally contains no provider/network calls.
"""
from datetime import datetime
from typing import Any, Iterable

from calibration import brier_score, log_loss, roi_units


def eligible_prediction(prediction: dict[str, Any], first_pitch: datetime) -> bool:
    snapshot_at = prediction.get("snapshot_at")
    if not snapshot_at:
        return False
    return snapshot_at < first_pitch


def evaluate_predictions(rows: Iterable[dict[str, Any]], first_pitch: datetime) -> dict[str, Any]:
    eligible = [r for r in rows if eligible_prediction(r, first_pitch)]
    probabilities = [(float(r["probability"]), int(r["won"])) for r in eligible]
    bets = [(bool(r["won"]), float(r["decimal_odds"])) for r in eligible if r.get("bet")]
    return {
        "sample_size": len(eligible),
        "brier_score": brier_score(probabilities),
        "log_loss": log_loss(probabilities),
        "roi_units": roi_units(bets),
    }


def build_calibration_run(model_version: str, cutoff_start: datetime, cutoff_end: datetime,
                          metrics: dict[str, Any], notes: str | None = None) -> dict[str, Any]:
    return {
        "model_version": model_version,
        "cutoff_start": cutoff_start,
        "cutoff_end": cutoff_end,
        "sample_size": metrics["sample_size"],
        "brier_score": metrics["brier_score"],
        "log_loss": metrics["log_loss"],
        "roi_units": metrics["roi_units"],
        "notes": notes,
    }
