"""PostgreSQL persistence and read layer for immutable live snapshots."""
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable, Dict, Any
import psycopg


def database_url() -> str:
    value = os.getenv('DATABASE_URL')
    if not value:
        raise RuntimeError('DATABASE_URL is not configured')
    return value


@contextmanager
def connection():
    with psycopg.connect(database_url()) as conn:
        yield conn
        conn.commit()


def begin_sync(game_date: str, source: str) -> int:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''INSERT INTO sync_runs (started_at, game_date, source, status)
                       VALUES (%s,%s,%s,'running') RETURNING sync_id''',
                    (datetime.now(timezone.utc), game_date, source))
        return cur.fetchone()[0]


def finish_sync(sync_id: int, status: str, games: int, odds: int, weather: int, error: str | None = None) -> None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''UPDATE sync_runs SET finished_at=%s,status=%s,games_fetched=%s,
                       odds_fetched=%s,weather_fetched=%s,error=%s WHERE sync_id=%s''',
                    (datetime.now(timezone.utc), status, games, odds, weather, error, sync_id))


def upsert_games(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute('''INSERT INTO games
                (id,sport,game_date,start_time,away_team_id,away_team_name,home_team_id,home_team_name,
                 away_pitcher_id,home_pitcher_id,away_pitcher_name,home_pitcher_name,
                 venue_id,venue_name,venue_lat,venue_lon,status,updated_at)
                VALUES (%(id)s,%(sport)s,%(game_date)s,%(start_time)s,%(away_team_id)s,%(away_team_name)s,
                        %(home_team_id)s,%(home_team_name)s,%(away_pitcher_id)s,%(home_pitcher_id)s,
                        %(away_pitcher_name)s,%(home_pitcher_name)s,%(venue_id)s,%(venue_name)s,%(venue_lat)s,
                        %(venue_lon)s,%(status)s,NOW())
                ON CONFLICT (id) DO UPDATE SET start_time=EXCLUDED.start_time,
                    away_team_id=EXCLUDED.away_team_id,away_team_name=EXCLUDED.away_team_name,
                    home_team_id=EXCLUDED.home_team_id,home_team_name=EXCLUDED.home_team_name,
                    away_pitcher_id=EXCLUDED.away_pitcher_id,home_pitcher_id=EXCLUDED.home_pitcher_id,
                    away_pitcher_name=EXCLUDED.away_pitcher_name,home_pitcher_name=EXCLUDED.home_pitcher_name,
                    venue_id=EXCLUDED.venue_id,venue_name=EXCLUDED.venue_name,venue_lat=EXCLUDED.venue_lat,
                    venue_lon=EXCLUDED.venue_lon,status=EXCLUDED.status,updated_at=NOW()''', r)
            count += 1
    return count


def insert_odds(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute('''INSERT INTO odds_snapshots
                (game_id,snapshot_at,source,bookmaker,market,outcome,point,decimal_odds,implied_probability)
                VALUES (%(game_id)s,%(snapshot_at)s,%(source)s,%(bookmaker)s,%(market)s,%(outcome)s,
                        %(point)s,%(decimal_odds)s,%(implied_probability)s) ON CONFLICT DO NOTHING''', r)
            count += cur.rowcount
    return count


def insert_weather(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute('''INSERT INTO weather_snapshots
                (game_id,snapshot_at,forecast_at,source,temperature_c,wind_mph,wind_direction_deg,
                 precipitation_probability,condition)
                VALUES (%(game_id)s,%(snapshot_at)s,%(forecast_at)s,%(source)s,%(temperature_c)s,%(wind_mph)s,
                        %(wind_direction_deg)s,%(precipitation_probability)s,%(condition)s) ON CONFLICT DO NOTHING''', r)
            count += cur.rowcount
    return count


def insert_mlb_stats(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute('''INSERT INTO mlb_stat_snapshots
                (game_id,snapshot_at,source,side,pitcher_era,pitcher_whip,last5_era,last5_whip,
                 ops,runs_per_game,bullpen_score,lineup_strength,strikeouts,walks,innings_pitched)
                VALUES (%(game_id)s,%(snapshot_at)s,%(source)s,%(side)s,%(pitcher_era)s,%(pitcher_whip)s,
                        %(last5_era)s,%(last5_whip)s,%(ops)s,%(runs_per_game)s,%(bullpen_score)s,
                        %(lineup_strength)s,%(strikeouts)s,%(walks)s,%(innings_pitched)s)
                ON CONFLICT DO NOTHING''', r)
            count += cur.rowcount
    return count


def upsert_game_results(rows: Iterable[Dict[str, Any]]) -> int:
    """Persist only completed game results for point-in-time backtesting."""
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            if r.get('status') not in (None, 'final', 'completed'):
                raise ValueError('game result must be final/completed')
            away_runs = int(r['away_runs'])
            home_runs = int(r['home_runs'])
            if away_runs < 0 or home_runs < 0:
                raise ValueError('runs must be non-negative')
            cur.execute('''INSERT INTO game_results
                (game_id,completed_at,away_runs,home_runs,status,source)
                VALUES (%(game_id)s,%(completed_at)s,%(away_runs)s,%(home_runs)s,'final',%(source)s)
                ON CONFLICT (game_id) DO UPDATE SET completed_at=EXCLUDED.completed_at,
                    away_runs=EXCLUDED.away_runs,home_runs=EXCLUDED.home_runs,
                    status='final',source=EXCLUDED.source''', r)
            count += 1
    return count


def list_game_results(game_ids: Iterable[str] | None = None) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        if game_ids:
            ids = list(game_ids)
            cur.execute('''SELECT game_id,completed_at,away_runs,home_runs,status,source
                           FROM game_results WHERE game_id = ANY(%s)
                           ORDER BY completed_at DESC''', (ids,))
        else:
            cur.execute('''SELECT game_id,completed_at,away_runs,home_runs,status,source
                           FROM game_results ORDER BY completed_at DESC''')
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def insert_predictions(rows: Iterable[Dict[str, Any]]) -> int:
    """Persist immutable model outputs for later point-in-time evaluation."""
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            probability = float(r['probability'])
            if not 0.0 <= probability <= 1.0:
                raise ValueError('prediction probability must be between 0 and 1')
            odds = r.get('decimal_odds')
            if odds is not None and float(odds) <= 1.0:
                raise ValueError('decimal odds must be greater than 1')
            cur.execute('''INSERT INTO prediction_ledger
                (game_id,snapshot_at,model_version,market,outcome,point,probability,decimal_odds,
                 implied_probability,edge,ev,recommendation,source)
                VALUES (%(game_id)s,%(snapshot_at)s,%(model_version)s,%(market)s,%(outcome)s,%(point)s,
                        %(probability)s,%(decimal_odds)s,%(implied_probability)s,%(edge)s,%(ev)s,
                        %(recommendation)s,%(source)s)
                ON CONFLICT (game_id,snapshot_at,model_version,market,outcome,point) DO NOTHING''', r)
            count += cur.rowcount
    return count


def list_predictions(game_ids: Iterable[str] | None = None, model_version: str | None = None) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        clauses = []
        params: list[Any] = []
        if game_ids:
            clauses.append('game_id = ANY(%s)')
            params.append(list(game_ids))
        if model_version:
            clauses.append('model_version=%s')
            params.append(model_version)
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        cur.execute(f'''SELECT prediction_id,game_id,snapshot_at,model_version,market,outcome,point,
                               probability,decimal_odds,implied_probability,edge,ev,recommendation,source,created_at
                        FROM prediction_ledger{where} ORDER BY snapshot_at ASC''', params)
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def list_games(game_date: str, limit: int = 100) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT id,sport,game_date,start_time,away_team_id,away_team_name,home_team_id,
                              home_team_name,away_pitcher_id,home_pitcher_id,away_pitcher_name,home_pitcher_name,
                              venue_id,venue_name,venue_lat,venue_lon,status,updated_at
                       FROM games WHERE game_date=%s ORDER BY start_time NULLS LAST LIMIT %s''', (game_date, limit))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def latest_odds(game_id: str, limit: int = 200) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT game_id,snapshot_at,source,bookmaker,market,outcome,point,decimal_odds,implied_probability
                       FROM odds_snapshots WHERE game_id=%s ORDER BY snapshot_at DESC LIMIT %s''', (game_id, limit))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def latest_weather(game_id: str) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT game_id,snapshot_at,forecast_at,source,temperature_c,wind_mph,wind_direction_deg,
                              precipitation_probability,condition FROM weather_snapshots WHERE game_id=%s
                       ORDER BY forecast_at DESC,snapshot_at DESC''', (game_id,))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def latest_mlb_stats(game_id: str) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT game_id,snapshot_at,source,side,pitcher_era,pitcher_whip,last5_era,last5_whip,
                              ops,runs_per_game,bullpen_score,lineup_strength,strikeouts,walks,innings_pitched
                       FROM mlb_stat_snapshots WHERE game_id=%s ORDER BY snapshot_at DESC''', (game_id,))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def matchup_snapshot(game_id: str) -> dict[str, Any] | None:
    """Return the latest point-in-time inputs for one game without provider calls."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT id,game_date,start_time,away_team_id,away_team_name,home_team_id,home_team_name,
                              away_pitcher_id,home_pitcher_id,away_pitcher_name,home_pitcher_name,venue_id,venue_name,
                              venue_lat,venue_lon,status FROM games WHERE id=%s''', (game_id,))
        game_row = cur.fetchone()
        if not game_row:
            return None
        columns = [d.name for d in cur.description]
        game = dict(zip(columns, game_row))
        return {'game': game, 'stats': latest_mlb_stats(game_id), 'odds': latest_odds(game_id), 'weather': latest_weather(game_id)}
