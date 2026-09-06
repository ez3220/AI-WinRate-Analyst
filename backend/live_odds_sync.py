"""Production MLB odds ingestion for V4."""
from datetime import datetime, timezone

from odds_api_v4 import fetch_mlb_odds, normalize_mlb_odds
from db import insert_odds, upsert_games


def _game_rows(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        event_id = str(event['id'])
        start = event.get('commence_time')
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00')) if start else None
        rows.append({
            'id': event_id,
            'sport': event.get('sport_key', 'baseball_mlb'),
            'game_date': start_dt.date() if start_dt else None,
            'start_time': start_dt,
            'away_team_id': None,
            'away_team_name': event.get('away_team'),
            'home_team_id': None,
            'home_team_name': event.get('home_team'),
            'away_pitcher_id': None,
            'home_pitcher_id': None,
            'away_pitcher_name': None,
            'home_pitcher_name': None,
            'venue_id': None,
            'venue_name': None,
            'venue_lat': None,
            'venue_lon': None,
            'status': 'scheduled',
        })
    return rows


def run_odds_sync() -> dict:
    events = fetch_mlb_odds()
    games_written = upsert_games(_game_rows(events))
    rows = normalize_mlb_odds(events)
    written = insert_odds(rows)
    return {
        'events': len(events),
        'games_upserted': games_written,
        'odds_written': written,
        'captured_at': datetime.now(timezone.utc).isoformat(),
    }
