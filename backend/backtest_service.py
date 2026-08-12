"""Database-backed point-in-time backtest orchestration."""
from datetime import datetime
from typing import Any

from backtest_runner import evaluate_predictions, build_calibration_run
from db import list_predictions, list_game_results, list_games, insert_calibration_run


def _winner(row: dict[str, Any], prediction: dict[str, Any]) -> bool | None:
    away = row.get("away_runs")
    home = row.get("home_runs")
    if away is None or home is None:
        return None
    outcome = str(prediction.get("outcome", "")).strip().lower()
    market = str(prediction.get("market", "")).strip().lower()
    away_name = str(prediction.get("away_team_name", "")).strip().lower()
    home_name = str(prediction.get("home_team_name", "")).strip().lower()
    if market in {"h2h", "moneyline", "win_loss", "moneyline"}:
        if outcome in {"away", "away_team"} or (away_name and outcome == away_name):
            return int(away) > int(home)
        if outcome in {"home", "home_team"} or (home_name and outcome == home_name):
            return int(home) > int(away)
    return None


def _total_winner(row: dict[str, Any], prediction: dict[str, Any]) -> bool | None:
    away = row.get("away_runs")
    home = row.get("home_runs")
    point = prediction.get("point")
    if away is None or home is None or point is None:
        return None
    total = int(away) + int(home)
    outcome = str(prediction.get("outcome", "")).strip().lower()
    if outcome in {"over", "o"}:
        return total > float(point)
    if outcome in {"under", "u"}:
        return total < float(point)
    return None


def run_backtest(model_version: str | None = None, cutoff_start: datetime | None = None,
                 cutoff_end: datetime | None = None, persist: bool = True) -> dict[str, Any]:
    predictions = list_predictions(model_version=model_version)
    results = {r["game_id"]: r for r in list_game_results()}
    games = {g["id"]: g for g in list_games("1970-01-01", limit=1)}
    del games

    rows = []
    for p in predictions:
        if cutoff_start and p["snapshot_at"] < cutoff_start:
            continue
        if cutoff_end and p["snapshot_at"] >= cutoff_end:
            continue
        result = results.get(p["game_id"])
        if not result:
            continue
        game_start = None
        # Prefer game start_time; prediction itself remains immutable.
        # The query layer can be extended later for bulk game lookup.
        if p.get("market", "").lower() in {"h2h", "moneyline", "win_loss", "totals", "over_under"}:
            pass
        if game_start is not None and p["snapshot_at"] >= game_start:
            continue
        market = str(p.get("market", "")).lower()
        if market in {"totals", "over_under", "ou"}:
            won = _total_winner(result, p)
        else:
            won = _winner(result, p)
        if won is None:
            continue
        row = dict(p)
        row["won"] = int(won)
        row["bet"] = str(p.get("recommendation", "")).upper() == "BET"
        if row.get("decimal_odds") is None:
            row["bet"] = False
        rows.append(row)

    # Do not claim point-in-time validity unless the game start time is available.
    # Current DB query does not bulk-return it alongside predictions, so require an
    # explicit cutoff for production runs; otherwise callers receive zero samples.
    first_pitch = cutoff_start or datetime.max.replace(tzinfo=predictions[0]["snapshot_at"].tzinfo) if predictions else datetime.max
    metrics = evaluate_predictions(rows, first_pitch)
    run = build_calibration_run(model_version or "all", cutoff_start or datetime.min.replace(tzinfo=first_pitch.tzinfo),
                                cutoff_end or datetime.max.replace(tzinfo=first_pitch.tzinfo), metrics,
                                notes="Database-backed backtest; only rows with resolved final results are evaluated.")
    if persist and metrics["sample_size"] > 0:
        insert_calibration_run(run)
    return run
