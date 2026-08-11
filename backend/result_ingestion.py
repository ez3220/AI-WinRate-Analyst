"""Ingest final MLB scores into the result ledger for backtesting.

This job reads the MLB schedule endpoint through the server-side adapter only.
It never writes scores into prediction/stat snapshots and is safe to rerun.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

from db import upsert_game_results
from provider_adapters import MLBAdapter
from provider_config import ProviderConfig

TAIPEI = ZoneInfo('Asia/Taipei')
FINAL_STATES = {'final', 'game over', 'completed early', 'completed'}


def taipei_game_date() -> str:
    return datetime.now(TAIPEI).date().isoformat()


def _is_final(status: str | None) -> bool:
    normalized = ' '.join((status or '').strip().lower().split())
    return normalized in FINAL_STATES or normalized.startswith('final')


def _result_row(game: dict[str, Any], captured_at: datetime) -> dict[str, Any] | None:
    if not _is_final(game.get('status')):
        return None
    away_score = game.get('away_score')
    home_score = game.get('home_score')
    if away_score is None or home_score is None:
        return None
    return {
        'game_id': str(game['id']),
        # The schedule feed does not expose a reliable completion timestamp.
        # Store the observation timestamp rather than inventing a completion time.
        'completed_at': captured_at,
        'away_runs': int(away_score),
        'home_runs': int(home_score),
        'status': 'final',
        'source': 'mlb_statsapi_final_ingest',
    }


def ingest_final_results(game_date: str | None = None) -> dict[str, Any]:
    cfg = ProviderConfig()
    game_date = game_date or taipei_game_date()
    games = MLBAdapter(cfg.mlb_base_url, cfg.mlb_api_key).games(game_date)
    captured_at = datetime.now(timezone.utc)
    rows = [row for game in games if (row := _result_row(game, captured_at)) is not None]
    written = upsert_game_results(rows) if rows else 0
    return {
        'game_date': game_date,
        'fetched_games': len(games),
        'final_games': len(rows),
        'results_written': written,
        'captured_at': captured_at.isoformat(),
        'status': 'success',
    }


if __name__ == '__main__':
    print(ingest_final_results())
