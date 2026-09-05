"""Database-backed point-in-time backtest orchestration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from backtest_runner import build_calibration_run, evaluate_ledger
from db import insert_calibration_run, list_game_results, list_predictions


def run_backtest(
    model_version: str | None = None,
    cutoff_start: datetime | None = None,
    cutoff_end: datetime | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Evaluate immutable prediction snapshots against final game results.

    ``list_predictions`` already joins each prediction to its game's start time
    and team names. Build the game lookup from that result so the point-in-time
    eligibility check in ``evaluate_ledger`` is actually enforced.
    """
    predictions = list_predictions(model_version=model_version)

    if cutoff_start is not None:
        predictions = [p for p in predictions if p["snapshot_at"] >= cutoff_start]
    if cutoff_end is not None:
        predictions = [p for p in predictions if p["snapshot_at"] < cutoff_end]

    game_ids = {str(p["game_id"]) for p in predictions}
    results = {
        str(r["game_id"]): r
        for r in list_game_results(game_ids=game_ids)
    }

    games: dict[str, dict[str, Any]] = {}
    for p in predictions:
        game_id = str(p["game_id"])
        games.setdefault(
            game_id,
            {
                "id": game_id,
                "start_time": p.get("start_time"),
                "away_team_name": p.get("away_team_name"),
                "home_team_name": p.get("home_team_name"),
            },
        )

    metrics = evaluate_ledger(predictions, results, games)

    tz = None
    for p in predictions:
        snapshot_at = p.get("snapshot_at")
        if snapshot_at is not None and getattr(snapshot_at, "tzinfo", None) is not None:
            tz = snapshot_at.tzinfo
            break

    if cutoff_start is not None:
        run_start = cutoff_start
    elif tz is not None:
        run_start = datetime.min.replace(tzinfo=tz)
    else:
        run_start = datetime.min

    if cutoff_end is not None:
        run_end = cutoff_end
    elif tz is not None:
        run_end = datetime.max.replace(tzinfo=tz)
    else:
        run_end = datetime.max

    run = build_calibration_run(
        model_version or "all",
        run_start,
        run_end,
        metrics,
        notes="Database-backed point-in-time backtest; only eligible predictions with final results are evaluated.",
    )

    if persist and metrics["sample_size"] > 0:
        insert_calibration_run(run)

    return run
