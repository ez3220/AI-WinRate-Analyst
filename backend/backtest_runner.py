"""Point-in-time backtest evaluation for the V4 prediction ledger."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from calibration import brier_score, log_loss, roi_units


def eligible_prediction(prediction: dict[str, Any], first_pitch: datetime) -> bool:
    snapshot_at = prediction.get("snapshot_at")
    return bool(snapshot_at and snapshot_at < first_pitch)


def _label(prediction: dict[str, Any], result: dict[str, Any], game: dict[str, Any]) -> int | None:
    try:
        away_runs = int(result["away_runs"])
        home_runs = int(result["home_runs"])
    except (KeyError, TypeError, ValueError):
        return None
    market = str(prediction.get("market", "")).lower()
    outcome = str(prediction.get("outcome", "")).lower()
    away = str(game.get("away_team_name") or "").lower()
    home = str(game.get("home_team_name") or "").lower()
    if market == "h2h":
        if away and (outcome == away or outcome in away):
            return int(away_runs > home_runs)
        if home and (outcome == home or outcome in home):
            return int(home_runs > away_runs)
        return None
    if market == "totals" and prediction.get("point") is not None:
        total = away_runs + home_runs
        point = float(prediction["point"])
        if "over" in outcome:
            return int(total > point)
        if "under" in outcome:
            return int(total < point)
    return None


def evaluate_ledger(predictions: list[dict[str, Any]], results: dict[str, dict[str, Any]],
                    games: dict[str, dict[str, Any]]) -> dict[str, Any]:
    eligible: list[tuple[dict[str, Any], int]] = []
    for prediction in predictions:
        game_id = str(prediction.get("game_id"))
        game = games.get(game_id)
        result = results.get(game_id)
        if not game or not result:
            continue
        first_pitch = game.get("start_time")
        if not first_pitch or not eligible_prediction(prediction, first_pitch):
            continue
        if str(result.get("status", "")).lower() not in {"final", "completed"}:
            continue
        label = _label(prediction, result, game)
        if label is not None:
            eligible.append((prediction, label))

    def metrics(rows: list[tuple[dict[str, Any], int]]) -> dict[str, Any]:
        probability_rows = [(float(p["probability"]), y) for p, y in rows]
        bets = [(bool(y), float(p["decimal_odds"])) for p, y in rows
                if str(p.get("recommendation", "")).upper() == "BET"
                and p.get("decimal_odds") is not None and float(p["decimal_odds"]) > 1]
        return {
            "sample_size": len(rows),
            "brier_score": brier_score(probability_rows),
            "log_loss": log_loss(probability_rows),
            "bet_sample_size": len(bets),
            "bet_roi_units": roi_units(bets),
        }

    by_market = {}
    for market in sorted({str(p.get("market")) for p, _ in eligible}):
        by_market[market] = metrics([(p, y) for p, y in eligible if str(p.get("market")) == market])
    overall = metrics(eligible)
    return {**overall, "by_market": by_market}


def build_calibration_run(model_version: str, cutoff_start: datetime, cutoff_end: datetime,
                          metrics: dict[str, Any], notes: str | None = None) -> dict[str, Any]:
    return {
        "model_version": model_version,
        "cutoff_start": cutoff_start,
        "cutoff_end": cutoff_end,
        "sample_size": metrics["sample_size"],
        "brier_score": metrics["brier_score"],
        "log_loss": metrics["log_loss"],
        "roi_units": metrics.get("bet_roi_units"),
        "notes": notes,
    }
