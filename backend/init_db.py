"""Create/upgrade the V4 PostgreSQL schema from schema.sql."""
from pathlib import Path
import psycopg

from db import database_url


def main() -> None:
    sql = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print('V4 schema ready')


if __name__ == '__main__':
    main()
