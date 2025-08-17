# services/ingestor/ingest.py
import os, time, json
import psycopg2

PG_DSN = os.getenv("PG_DSN")
if not PG_DSN:
    raise SystemExit("Missing PG_DSN env var")

# Connect
conn = psycopg2.connect(PG_DSN)
conn.autocommit = True

slug = f"hello-from-ci-{int(time.time())}"
title = "Hello from GitHub Actions"
body_md = "This is a test article inserted by the CI job."
payload = {"sources": [], "disclaimer": "AI-generated. Not investment advice."}

with conn.cursor() as cur:
    cur.execute("""
        insert into articles (slug, type, asset, title, body_md, json_payload, confidence)
        values (%s, %s, %s, %s, %s, %s::jsonb, %s)
        returning id
    """, (slug, 'news_brief', None, title, body_md, json.dumps(payload), 'medium'))
    row = cur.fetchone()
    print("Inserted article id:", row[0], "slug:", slug)

print("Done.")
