"""Point-in-time MLB stat enrichment using MLB Stats API date-range endpoints.

The cutoff is the scheduled first-pitch time. Stats after the cutoff are never
included, which prevents look-ahead leakage in live scoring and backtests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import httpx


class MLBStatsEnricher:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=20) as client:
            response = client.get(f'{self.base_url}/{path.lstrip("/")}', params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _date(value: datetime) -> str:
        return value.astimezone(timezone.utc).date().isoformat()

    def pitcher(self, pitcher_id: str | None, cutoff: datetime) -> dict[str, Any]:
        if not pitcher_id:
            return {}
        end = self._date(cutoff - timedelta(seconds=1))
        start = (cutoff - timedelta(days=45)).date().isoformat()
        payload = self._get(f'people/{pitcher_id}/stats', {
            'stats': 'byDateRange', 'group': 'pitching', 'startDate': start, 'endDate': end,
        })
        stats = (payload.get('stats') or [{}])[0].get('splits') or []
        if not stats:
            return {}
        s = stats[0].get('stat') or {}
        return {
            'pitcher_id': str(pitcher_id),
            'pitcher_era': _num(s.get('era')),
            'pitcher_whip': _num(s.get('whip')),
            'innings_pitched': _num(s.get('inningsPitched')),
            'strikeouts': _num(s.get('strikeOuts')),
            'walks': _num(s.get('baseOnBalls')),
        }

    def team_hitting(self, team_id: str | None, cutoff: datetime) -> dict[str, Any]:
        if not team_id:
            return {}
        end = self._date(cutoff - timedelta(seconds=1))
        start = (cutoff - timedelta(days=45)).date().isoformat()
        payload = self._get(f'teams/{team_id}/stats', {
            'stats': 'byDateRange', 'group': 'hitting', 'startDate': start, 'endDate': end,
        })
        stats = (payload.get('stats') or [{}])[0].get('splits') or []
        if not stats:
            return {}
        s = stats[0].get('stat') or {}
        return {
            'team_id': str(team_id),
            'ops': _num(s.get('ops')),
            'runs': _num(s.get('runs')),
            'games_played': _num(s.get('gamesPlayed')),
            'runs_per_game': _safe_ratio(s.get('runs'), s.get('gamesPlayed')),
        }

    def enrich_game(self, game: dict[str, Any]) -> dict[str, Any]:
        start = game.get('start_time')
        if not start:
            return {'game_id': str(game['id']), 'complete': False}
        cutoff = datetime.fromisoformat(str(start).replace('Z', '+00:00'))
        away_pitcher = game.get('away_pitcher_id')
        home_pitcher = game.get('home_pitcher_id')
        return {
            'game_id': str(game['id']),
            'snapshot_at': cutoff,
            'source': 'mlb_stats_api',
            'away_pitcher': self.pitcher(away_pitcher, cutoff),
            'home_pitcher': self.pitcher(home_pitcher, cutoff),
            'away_hitting': self.team_hitting(game.get('away_team_id'), cutoff),
            'home_hitting': self.team_hitting(game.get('home_team_id'), cutoff),
        }


def _num(value: Any) -> float | None:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_ratio(a: Any, b: Any) -> float | None:
    x, y = _num(a), _num(b)
    return None if x is None or y is None or y <= 0 else x / y
