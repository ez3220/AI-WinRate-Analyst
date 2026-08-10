"""V4 live ingestion orchestrator.

A successful sync writes provider data plus an immutable sync_run audit record.
No recommendation is generated from an incomplete provider snapshot.
"""
from datetime import date
from provider_config import ProviderConfig
from provider_adapters import MLBAdapter, OddsAdapter, WeatherAdapter
from ingestion import normalize_game, normalize_odds, dedupe_odds
from db import begin_sync, finish_sync, upsert_games, insert_odds, insert_weather


def _team_key(name: str | None) -> str:
    return ' '.join((name or '').lower().replace('.', '').split())


def run_live_sync(game_date: str | None = None):
    cfg = ProviderConfig()
    status = cfg.validate()
    if not status['ready']:
        raise RuntimeError('Live provider configuration incomplete: ' + ', '.join(status['missing']))

    game_date = game_date or date.today().isoformat()
    sync_id = begin_sync(game_date, 'mlb+odds+weather')
    games_written = odds_written = weather_written = 0

    try:
        games_raw = MLBAdapter(cfg.mlb_base_url, cfg.mlb_api_key).games(game_date)
        odds_raw = OddsAdapter(cfg.odds_base_url, cfg.odds_api_key).odds(game_date)
        games = [normalize_game(x) for x in games_raw]

        game_index = {}
        for game in games:
            game_index[(_team_key(game.get('away_team_name')), _team_key(game.get('home_team_name')))] = game['id']

        captured_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        odds = []
        for raw in odds_raw:
            key = (_team_key(raw.get('away_team_name')), _team_key(raw.get('home_team_name')))
            game_id = game_index.get(key)
            if game_id is None:
                continue
            odds.append(normalize_odds(raw, game_id, captured_at=captured_at))
        odds = dedupe_odds(odds)

        games_written = upsert_games(games)
        odds_written = insert_odds(odds)

        if cfg.weather_base_url:
            weather = WeatherAdapter(cfg.weather_base_url, cfg.weather_api_key)
            weather_rows = []
            for game in games:
                lat = game.get('venue_lat')
                lon = game.get('venue_lon')
                if lat is not None and lon is not None:
                    weather_rows.extend(weather.forecast_rows(str(game['id']), float(lat), float(lon)))
            weather_written = insert_weather(weather_rows)

        finish_sync(sync_id, 'success', games_written, odds_written, weather_written)
        return {
            'sync_id': sync_id,
            'games_written': games_written,
            'odds_written': odds_written,
            'weather_written': weather_written,
            'game_date': game_date,
            'status': 'success',
        }
    except Exception as exc:
        finish_sync(sync_id, 'failed', games_written, odds_written, weather_written, str(exc)[:1000])
        raise
