"""Normalization helpers. Preserve source and capture time for auditability."""
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_game(raw: Dict[str, Any]) -> Dict[str, Any]:
    game_id = raw.get('id') or raw.get('game_id')
    if game_id is None:
        raise ValueError('game payload missing id')
    return {
        'id': str(game_id),
        'sport': str(raw.get('sport', 'mlb')).lower(),
        'game_date': raw.get('game_date'),
        'start_time': raw.get('start_time'),
        'away_team_id': raw.get('away_team_id'),
        'away_team_name': raw.get('away_team_name'),
        'home_team_id': raw.get('home_team_id'),
        'home_team_name': raw.get('home_team_name'),
        'venue_id': raw.get('venue_id'),
        'venue_name': raw.get('venue_name'),
        'venue_lat': raw.get('venue_lat'),
        'venue_lon': raw.get('venue_lon'),
        'status': raw.get('status', 'scheduled'),
    }


def normalize_odds(raw: Dict[str, Any], game_id: str, captured_at: datetime | None = None, source: str = 'the-odds-api') -> Dict[str, Any]:
    price = raw.get('decimal_odds')
    if price is None or float(price) <= 1:
        raise ValueError('odds payload has invalid decimal_odds')
    return {
        'game_id': str(game_id),
        'snapshot_at': captured_at or utc_now(),
        'source': source,
        'bookmaker': raw.get('bookmaker'),
        'market': raw.get('market'),
        'outcome': raw.get('outcome'),
        'point': raw.get('point'),
        'decimal_odds': float(price),
        'implied_probability': 1 / float(price),
    }


def dedupe_odds(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dedupe one ingestion batch while preserving distinct snapshots over time."""
    seen = set()
    result = []
    for row in rows:
        key = (row['game_id'], row['source'], row['bookmaker'], row['market'], row['outcome'], row['point'])
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result
