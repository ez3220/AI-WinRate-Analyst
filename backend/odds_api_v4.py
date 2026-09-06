"""Production The Odds API V4 adapter for MLB featured markets."""
from datetime import datetime, timezone
import os
import httpx

BASE_URL = 'https://api.the-odds-api.com'
SPORT_KEY = 'baseball_mlb'
MARKETS = 'h2h,spreads,totals'


def fetch_mlb_odds() -> list[dict]:
    key = os.getenv('ODDS_API_KEY')
    if not key:
        raise RuntimeError('ODDS_API_KEY is not configured')
    params = {
        'regions': os.getenv('ODDS_REGIONS', 'us'),
        'markets': MARKETS,
        'oddsFormat': 'decimal',
        'apiKey': key,
    }
    with httpx.Client(timeout=20) as client:
        r = client.get(f'{BASE_URL}/v4/sports/{SPORT_KEY}/odds', params=params)
        r.raise_for_status()
        return r.json()


def normalize_mlb_odds(events: list[dict]) -> list[dict]:
    captured = datetime.now(timezone.utc)
    rows = []
    for event in events:
        game_id = str(event['id'])
        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                for outcome in market.get('outcomes', []):
                    rows.append({
                        'game_id': game_id,
                        'snapshot_at': captured,
                        'source': 'the-odds-api',
                        'bookmaker': bookmaker.get('key') or bookmaker.get('title'),
                        'market': market.get('key'),
                        'outcome': outcome.get('name'),
                        'point': outcome.get('point'),
                        'decimal_odds': float(outcome['price']),
                        'implied_probability': 1 / float(outcome['price']),
                    })
    return rows
