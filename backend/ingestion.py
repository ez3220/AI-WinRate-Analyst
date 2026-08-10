"""V3.5 ingestion contracts and normalization helpers.
Provider adapters intentionally accept provider-neutral payloads; network credentials stay server-side.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_game(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(raw.get('id')),
        'sport': str(raw.get('sport', 'mlb')).lower(),
        'game_date': raw.get('game_date'),
        'start_time': raw.get('start_time'),
        'away_team_id': raw.get('away_team_id'),
        'home_team_id': raw.get('home_team_id'),
        'venue_id': raw.get('venue_id'),
        'status': raw.get('status', 'scheduled'),
    }


def normalize_odds(raw: Dict[str, Any], captured_at: datetime | None = None) -> Dict[str, Any]:
    price = raw.get('decimal_odds')
    implied = None if price is None or price <= 1 else 1 / price
    return {
        'game_id': str(raw.get('game_id')),
        'snapshot_at': captured_at or utc_now(),
        'bookmaker': raw.get('bookmaker'),
        'market': raw.get('market'),
        'outcome': raw.get('outcome'),
        'point': raw.get('point'),
        'decimal_odds': price,
        'implied_probability': implied,
    }


def dedupe_odds(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for row in rows:
        key = (row['game_id'], row['bookmaker'], row['market'], row['outcome'], row['point'], row['decimal_odds'])
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result
