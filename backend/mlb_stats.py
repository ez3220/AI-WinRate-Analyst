"""Server-side MLB StatsAPI snapshot adapter.

Only publishes values returned by MLB StatsAPI; missing metrics remain null.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import httpx


class MLBStatsAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self._team_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._pitcher_cache: dict[tuple[str, str], dict[str, Any]] = {}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=20) as client:
            response = client.get(f'{self.base_url}/{path.lstrip("/")}', params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _first_split(payload: dict[str, Any]) -> dict[str, Any]:
        stats = payload.get('stats') or []
        splits = stats[0].get('splits') if stats else []
        return (splits or [{}])[0].get('stat') or {}

    def team(self, team_id: str, season: str) -> dict[str, Any]:
        key = (team_id, season)
        if key not in self._team_cache:
            payload = self._get(f'teams/{team_id}/stats', {'stats': 'season', 'group': 'hitting', 'season': season})
            self._team_cache[key] = self._first_split(payload)
        stat = self._team_cache[key]
        games = float(stat.get('gamesPlayed') or 0)
        runs = float(stat.get('runs') or 0)
        ops = stat.get('ops')
        return {
            'ops': float(ops) if ops is not None else None,
            'runs_per_game': runs / games if games > 0 else None,
            # OPS is an observed lineup-strength proxy; no synthetic bullpen value is created.
            'lineup_strength': max(0.0, min(100.0, float(ops) * 100.0)) if ops is not None else None,
        }

    def pitcher(self, pitcher_id: str | None, season: str) -> dict[str, Any]:
        if not pitcher_id:
            return {'pitcher_era': None, 'pitcher_whip': None, 'last5_era': None, 'last5_whip': None}
        key = (pitcher_id, season)
        if key not in self._pitcher_cache:
            season_payload = self._get(f'people/{pitcher_id}/stats', {'stats': 'season', 'group': 'pitching', 'season': season})
            log_payload = self._get(f'people/{pitcher_id}/stats', {'stats': 'gameLog', 'group': 'pitching', 'season': season})
            self._pitcher_cache[key] = {
                'season': self._first_split(season_payload),
                'logs': ((log_payload.get('stats') or [{}])[0].get('splits') or []),
            }
        cached = self._pitcher_cache[key]
        season_stat = cached['season']
        logs = sorted(cached['logs'], key=lambda x: str(x.get('date') or ''), reverse=True)[:5]
        ip = er = hits = walks = 0.0
        for split in logs:
            stat = split.get('stat') or {}
            # Game-log rows can include relief appearances; use the five latest pitching games
            # because the provider does not guarantee a starter-only filter.
            try:
                innings = float(str(stat.get('inningsPitched', '0')).replace('.1', '.333333').replace('.2', '.666667'))
            except ValueError:
                innings = 0.0
            ip += innings
            er += float(stat.get('earnedRuns') or 0)
            hits += float(stat.get('hits') or 0)
            walks += float(stat.get('baseOnBalls') or 0)
        last5_era = (er * 9.0 / ip) if ip > 0 else None
        last5_whip = ((hits + walks) / ip) if ip > 0 else None
        return {
            'pitcher_era': float(season_stat['era']) if season_stat.get('era') is not None else None,
            'pitcher_whip': float(season_stat['whip']) if season_stat.get('whip') is not None else None,
            'last5_era': last5_era,
            'last5_whip': last5_whip,
        }

    def snapshot_game(self, game: dict[str, Any], captured_at: datetime | None = None) -> list[dict[str, Any]]:
        captured_at = captured_at or datetime.now(timezone.utc)
        season = str((game.get('game_date') or captured_at.date()).year)
        rows = []
        for side in ('away', 'home'):
            team_id = game.get(f'{side}_team_id')
            team = self.team(str(team_id), season) if team_id else {}
            pitcher = self.pitcher(game.get(f'{side}_pitcher_id'), season)
            rows.append({
                'game_id': str(game['id']), 'snapshot_at': captured_at, 'source': 'mlb_statsapi', 'side': side,
                **pitcher, **team, 'bullpen_score': None, 'strikeouts': None, 'walks': None, 'innings_pitched': None,
            })
        return rows
