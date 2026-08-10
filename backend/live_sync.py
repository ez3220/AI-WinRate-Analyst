from datetime import date
from provider_config import ProviderConfig
from provider_adapters import MLBAdapter, OddsAdapter
from ingestion import normalize_game, normalize_odds, dedupe_odds
from db import upsert_games, insert_odds


def run_live_sync(game_date: str | None = None):
    cfg = ProviderConfig()
    status = cfg.validate()
    if not status['ready']:
        raise RuntimeError('Live provider configuration incomplete: ' + ', '.join(status['missing']))
    game_date = game_date or date.today().isoformat()
    games_raw = MLBAdapter(cfg.mlb_base_url).games(game_date)
    odds_raw = OddsAdapter(cfg.odds_base_url).odds(game_date)
    games = [normalize_game(x) for x in games_raw]
    odds = dedupe_odds(normalize_odds(x) for x in odds_raw)
    return {'games_written': upsert_games(games), 'odds_written': insert_odds(odds), 'game_date': game_date}
