"""V3.6 PostgreSQL persistence layer."""
import os
from contextlib import contextmanager
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


def upsert_games(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute('''INSERT INTO games (id,sport,game_date,start_time,away_team_id,home_team_id,venue_id,status)
                               VALUES (%(id)s,%(sport)s,%(game_date)s,%(start_time)s,%(away_team_id)s,%(home_team_id)s,%(venue_id)s,%(status)s)
                               ON CONFLICT (id) DO UPDATE SET start_time=EXCLUDED.start_time,status=EXCLUDED.status''', r)
                count += 1
    return count


def insert_odds(rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with connection() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute('''INSERT INTO odds_snapshots
                    (game_id,snapshot_at,bookmaker,market,outcome,point,decimal_odds,implied_probability)
                    VALUES (%(game_id)s,%(snapshot_at)s,%(bookmaker)s,%(market)s,%(outcome)s,%(point)s,%(decimal_odds)s,%(implied_probability)s)''', r)
                count += 1
    return count
