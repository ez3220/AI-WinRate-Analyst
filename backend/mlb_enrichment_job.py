"""Run point-in-time MLB stat enrichment against games already persisted by Live Sync."""
from datetime import datetime, timezone
from provider_config import ProviderConfig
from db import connection, insert_mlb_stats
from stats_enrichment import MLBStatsEnricher


def _games(game_date: str) -> list[dict]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT id,start_time,away_team_id,home_team_id,away_pitcher_id,home_pitcher_id
                       FROM games WHERE game_date=%s ORDER BY start_time''', (game_date,))
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def enrich_game_date(game_date: str) -> dict:
    cfg = ProviderConfig()
    enricher = MLBStatsEnricher(cfg.mlb_base_url)
    rows = []
    for game in _games(game_date):
        enriched = enricher.enrich_game(game)
        if enriched.get('complete') is False:
            continue
        for side in ('away', 'home'):
            pitcher = enriched.get(f'{side}_pitcher') or {}
            hitting = enriched.get(f'{side}_hitting') or {}
            rows.append({
                'game_id': enriched['game_id'],
                'snapshot_at': enriched['snapshot_at'],
                'source': enriched['source'],
                'side': side,
                'pitcher_era': pitcher.get('pitcher_era'),
                'pitcher_whip': pitcher.get('pitcher_whip'),
                'last5_era': None,
                'last5_whip': None,
                'ops': hitting.get('ops'),
                'runs_per_game': hitting.get('runs_per_game'),
                'bullpen_score': None,
                'lineup_strength': None,
                'strikeouts': pitcher.get('strikeouts'),
                'walks': pitcher.get('walks'),
                'innings_pitched': pitcher.get('innings_pitched'),
            })
    return {'game_date': game_date, 'stats_written': insert_mlb_stats(rows),
            'synced_at': datetime.now(timezone.utc).isoformat(), 'status': 'success'}
