"""V3.5 ingestion service skeleton.

Actual provider HTTP adapters are injected so secrets and provider-specific details remain outside the core pipeline.
"""
from typing import Callable, Dict, Iterable, List
from ingestion import normalize_game, normalize_odds, dedupe_odds


def ingest_games(fetcher: Callable[[], Iterable[Dict]]) -> List[Dict]:
    return [normalize_game(x) for x in fetcher()]


def ingest_odds(fetcher: Callable[[], Iterable[Dict]]) -> List[Dict]:
    return dedupe_odds(normalize_odds(x) for x in fetcher())
