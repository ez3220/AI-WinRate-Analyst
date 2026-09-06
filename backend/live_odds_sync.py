from odds_api_v4 import fetch_mlb_odds, normalize_mlb_odds
from db import insert_odds


def run_odds_sync() -> dict:
    events = fetch_mlb_odds()
    rows = normalize_mlb_odds(events)
    written = insert_odds(rows)
    return {'events': len(events), 'odds_written': written}
