# services/ingestor/db.py
import os, psycopg2

def build_dsn_from_env():
    host = os.getenv('PGHOST')
    port = os.getenv('PGPORT')
    db   = os.getenv('PGDATABASE')
    user = os.getenv('PGUSER')
    pw   = os.getenv('PGPASSWORD')
    ssl  = os.getenv('PGSSLMODE', 'require')
    if all([host, port, db, user, pw]):
        # libpq style; psycopg2 understands this perfectly
        return f"host={host} port={port} dbname={db} user={user} password={pw} sslmode={ssl}"
    return None

PG_DSN = os.getenv('PG_DSN') or build_dsn_from_env()
if not PG_DSN:
    raise RuntimeError("No Postgres connection info. Set PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD (and PGSSLMODE) or PG_DSN.")

conn = psycopg2.connect(PG_DSN)
conn.autocommit = True

