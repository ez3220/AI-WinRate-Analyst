"""Concrete server-side adapters for MLB, The Odds API, and weather."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
import httpx


class MLBAdapter:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip('/')

    def games(self, game_date: str) -> list[dict[str, Any]]:
        params = {'sportId': 1, 'date': game_date, 'hydrate': 'team,probablePitcher,venue'}
        with httpx.Client(timeout=20) as client:
            response = client.get(f'{self.base_url}/schedule', params=params)
            response.raise_for_status()
            payload = response.json()
        rows = []
        for day in payload.get('dates', []):
            for game in day.get('games', []):
                away = game.get('teams', {}).get('away', {})
                home = game.get('teams', {}).get('home', {})
                venue = game.get('venue', {})
                away_pitcher = away.get('probablePitcher') or {}
                home_pitcher = home.get('probablePitcher') or {}
                status = game.get('status', {}).get('detailedState', 'scheduled')
                away_score = away.get('score')
                home_score = home.get('score')
                rows.append({
                    'id': str(game['gamePk']), 'sport': 'mlb', 'game_date': game_date,
                    'start_time': game.get('gameDate'),
                    'away_team_id': str(away.get('team', {}).get('id')),
                    'home_team_id': str(home.get('team', {}).get('id')),
                    'away_team_name': away.get('team', {}).get('name'),
                    'home_team_name': home.get('team', {}).get('name'),
                    'away_pitcher_id': str(away_pitcher.get('id')) if away_pitcher.get('id') else None,
                    'home_pitcher_id': str(home_pitcher.get('id')) if home_pitcher.get('id') else None,
                    'away_pitcher_name': away_pitcher.get('fullName'),
                    'home_pitcher_name': home_pitcher.get('fullName'),
                    'venue_id': str(venue.get('id')) if venue.get('id') else None,
                    'venue_name': venue.get('name'),
                    'venue_lat': venue.get('location', {}).get('latitude'),
                    'venue_lon': venue.get('location', {}).get('longitude'),
                    'status': status,
                    'away_score': away_score,
                    'home_score': home_score,
                })
        return rows


class OddsAdapter:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('ODDS_API_KEY')

    def odds(self, game_date: str) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError('ODDS_API_KEY is not configured')
        params = {'apiKey': self.api_key, 'regions': os.getenv('ODDS_REGIONS', 'us'),
                  'markets': os.getenv('ODDS_MARKETS', 'h2h,totals'), 'oddsFormat': 'decimal'}
        with httpx.Client(timeout=20) as client:
            response = client.get(f'{self.base_url}/sports/baseball_mlb/odds', params=params)
            response.raise_for_status()
            events = response.json()
        rows = []
        for event in events:
            commence = event.get('commence_time')
            if commence and datetime.fromisoformat(commence.replace('Z', '+00:00')).date().isoformat() != game_date:
                continue
            for bookmaker in event.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    for outcome in market.get('outcomes', []):
                        rows.append({'provider_event_id': event.get('id'), 'away_team_name': event.get('away_team'),
                                     'home_team_name': event.get('home_team'), 'bookmaker': bookmaker.get('key'),
                                     'market': market.get('key'), 'outcome': outcome.get('name'),
                                     'point': outcome.get('point'), 'decimal_odds': outcome.get('price')})
        return rows


class WeatherAdapter:
    def __init__(self, base_url: str | None, api_key: str | None = None):
        self.base_url = (base_url or '').rstrip('/')
        self.api_key = api_key

    def forecast_rows(self, game_id: str, lat: float, lon: float) -> list[dict[str, Any]]:
        if not self.base_url:
            return []
        params = {'latitude': lat, 'longitude': lon,
                  'hourly': 'temperature_2m,precipitation_probability,wind_speed_10m,wind_direction_10m,weather_code',
                  'forecast_days': 2}
        if self.api_key:
            params['apikey'] = self.api_key
        captured_at = datetime.now(timezone.utc)
        with httpx.Client(timeout=20) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        hourly = payload.get('hourly', {})
        rows = []
        for i, timestamp in enumerate(hourly.get('time', [])):
            rows.append({'game_id': game_id, 'snapshot_at': captured_at,
                         'forecast_at': datetime.fromisoformat(timestamp).astimezone(timezone.utc),
                         'source': 'weather_provider',
                         'temperature_c': (hourly.get('temperature_2m') or [None])[i],
                         'wind_mph': ((hourly.get('wind_speed_10m') or [None])[i] or 0) * 0.621371,
                         'wind_direction_deg': (hourly.get('wind_direction_10m') or [None])[i],
                         'precipitation_probability': (hourly.get('precipitation_probability') or [None])[i],
                         'condition': str((hourly.get('weather_code') or [None])[i])})
        return rows
