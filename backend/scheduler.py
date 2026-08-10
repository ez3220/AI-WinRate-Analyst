"""V3.6 scheduler entry points. Run with an external scheduler/cron in production."""
from datetime import date
from ingestion_service import ingest_games, ingest_odds
from db import upsert_games, insert_odds


def sync_games(fetch_games):
    rows = ingest_games(fetch_games)
    return upsert_games(rows)


def sync_odds(fetch_odds):
    rows = ingest_odds(fetch_odds)
    return insert_odds(rows)


def daily_sync(fetch_games, fetch_odds):
    return {
        'date': date.today().isoformat(),
        'games_written': sync_games(fetch_games),
        'odds_written': sync_odds(fetch_odds),
    }
