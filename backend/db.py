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
        cur.execute(
            '''INSERT INTO sync_runs (started_at, game_date, source, status)
               VALUES (%s,%s,%s,'running') RETURNING sync_id''',
            (datetime.now(timezone.utc), game_date, source),
        )
        return cur.fetchone()[0]


def finish_sync(sync_id: int, status: str, games: int, odds: int, weather: int, error: str | None = None) -> None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            '''UPDATE sync_runs SET finished_at=%s,status=%s,games_fetched=%s,
               odds_fetched=%s,weather_fetched=%s,error=%s WHERE sync_id=%s''',
            (datetime.now(timezone.utc), status, games, odds, weather, error, sync_id),
        )


def upsert_games(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute('''INSERT INTO games (id,sport,game_date,start_time,away_team_id,home_team_id,venue_id,status)
                           VALUES (%(id)s,%(sport)s,%(game_date)s,%(start_time)s,%(away_team_id)s,%(home_team_id)s,%(venue_id)s,%(status)s)
                           ON CONFLICT (id) DO UPDATE SET start_time=EXCLUDED.start_time,
                           away_team_id=EXCLUDED.away_team_id,home_team_id=EXCLUDED.home_team_id,
                           venue_id=EXCLUDED.venue_id,status=EXCLUDED.status''', r)
            count += 1
    return count


def insert_odds(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute('''INSERT INTO odds_snapshots
                (game_id,snapshot_at,source,bookmaker,market,outcome,point,decimal_odds,implied_probability)
                VALUES (%(game_id)s,%(snapshot_at)s,%(source)s,%(bookmaker)s,%(market)s,%(outcome)s,
                        %(point)s,%(decimal_odds)s,%(implied_probability)s)
                ON CONFLICT DO NOTHING''', r)
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
                        %(wind_direction_deg)s,%(precipitation_probability)s,%(condition)s)
                ON CONFLICT DO NOTHING''', r)
            count += cur.rowcount
    return count


def list_games(game_date: str, limit: int = 100) -> list[dict[str, Any]]:
    """Read games exclusively from PostgreSQL; no provider/network calls."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT id,sport,game_date,start_time,away_team_id,home_team_id,venue_id,status
                       FROM games WHERE game_date=%s ORDER BY start_time NULLS LAST LIMIT %s''',
                    (game_date, limit))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def latest_odds(game_id: str, limit: int = 200) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT game_id,snapshot_at,source,bookmaker,market,outcome,point,
                              decimal_odds,implied_probability
                       FROM odds_snapshots WHERE game_id=%s
                       ORDER BY snapshot_at DESC LIMIT %s''', (game_id, limit))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def latest_weather(game_id: str) -> list[dict[str, Any]]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute('''SELECT game_id,snapshot_at,forecast_at,source,temperature_c,wind_mph,
                              wind_direction_deg,precipitation_probability,condition
                       FROM weather_snapshots WHERE game_id=%s
                       ORDER BY forecast_at DESC,snapshot_at DESC''', (game_id,))
        columns = [d.name for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
