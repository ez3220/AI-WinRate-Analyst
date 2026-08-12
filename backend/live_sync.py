"""V4 live ingestion orchestrator with Taiwan-date handling."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from provider_config import ProviderConfig
from provider_adapters import MLBAdapter, OddsAdapter, WeatherAdapter
from mlb_stats import MLBStatsAdapter
from ingestion import normalize_game, normalize_odds, dedupe_odds
from db import begin_sync, finish_sync, upsert_games, insert_odds, insert_weather, insert_mlb_stats, upsert_game_results

TAIPEI = ZoneInfo('Asia/Taipei')


def _team_key(name: str | None) -> str:
    return ' '.join((name or '').lower().replace('.', '').split())


def taipei_game_date() -> str:
    return datetime.now(TAIPEI).date().isoformat()


def run_live_sync(game_date: str | None = None):
    cfg = ProviderConfig()
    status = cfg.validate()
    if not status['ready']:
        raise RuntimeError('Live provider configuration incomplete: ' + ', '.join(status['missing']))

    game_date = game_date or taipei_game_date()
    sync_id = begin_sync(game_date, 'mlb+mlb-statsapi+odds+weather')
    games_written = odds_written = weather_written = stats_written = results_written = 0

    try:
        games_raw = MLBAdapter(cfg.mlb_base_url, cfg.mlb_api_key).games(game_date)
        odds_raw = OddsAdapter(cfg.odds_base_url, cfg.odds_api_key).odds(game_date)
        games = [normalize_game(x) for x in games_raw]
        game_index = {
            (_team_key(game.get('away_team_name')), _team_key(game.get('home_team_name'))): game['id']
            for game in games
        }
        captured_at = datetime.now(timezone.utc)
        odds = []
        for raw in odds_raw:
            key = (_team_key(raw.get('away_team_name')), _team_key(raw.get('home_team_name')))
            game_id = game_index.get(key)
            if game_id is not None:
                odds.append(normalize_odds(raw, game_id, captured_at=captured_at))
        odds = dedupe_odds(odds)

        games_written = upsert_games(games)
        odds_written = insert_odds(odds)

        stats_rows = []
        stats_adapter = MLBStatsAdapter(cfg.mlb_base_url)
        for game in games:
            stats_rows.extend(stats_adapter.snapshot_game(game, captured_at=captured_at))
        if stats_rows:
            stats_written = insert_mlb_stats(stats_rows)

        result_rows = []
        for game in games:
            status_text = str(game.get('status', '')).lower()
            if game.get('away_score') is not None and game.get('home_score') is not None and status_text in {'final', 'game over', 'completed'}:
                result_rows.append({
                    'game_id': str(game['id']), 'completed_at': captured_at,
                    'away_runs': int(game['away_score']), 'home_runs': int(game['home_score']),
                    'status': 'final', 'source': 'mlb_statsapi',
                })
        if result_rows:
            results_written = upsert_game_results(result_rows)

        if cfg.weather_base_url:
            weather = WeatherAdapter(cfg.weather_base_url, cfg.weather_api_key)
            weather_rows = []
            for game in games:
                lat, lon = game.get('venue_lat'), game.get('venue_lon')
                if lat is not None and lon is not None:
                    weather_rows.extend(weather.forecast_rows(str(game['id']), float(lat), float(lon)))
            weather_written = insert_weather(weather_rows)

        finish_sync(sync_id, 'success', games_written, odds_written, weather_written)
        return {
            'sync_id': sync_id, 'games_written': games_written, 'odds_written': odds_written,
            'weather_written': weather_written, 'stats_written': stats_written,
            'results_written': results_written, 'game_date': game_date, 'status': 'success'
        }
    except Exception as exc:
        finish_sync(sync_id, 'failed', games_written, odds_written, weather_written, str(exc)[:1000])
        raise
