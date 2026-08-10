"""V3.7 provider-to-database orchestration."""
from ingestion_service import ingest_games, ingest_odds
from db import upsert_games, insert_odds


def sync_provider(fetch_games, fetch_odds):
    games = ingest_games(fetch_games)
    odds = ingest_odds(fetch_odds)
    return {
        'games_written': upsert_games(games),
        'odds_written': insert_odds(odds),
    }
