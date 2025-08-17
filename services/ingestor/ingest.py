# services/ingestor/ingest.py
from __future__ import annotations

import json
import os
import time
from typing import Iterable

import psycopg2
import psycopg2.extras

from normalize import (
    fetch_rss,
    fetch_article,
    text_hash,
    slugify,
)

# A few crypto feeds to start. You can add/remove as you like.
FEEDS: list[str] = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
]

TYPE = "news_brief"  # articles.type


def _connect() -> psycopg2.extensions.connection:
    """
    Connect using PG_DSN if present; else fall back to individual envs.
    """
    dsn = os.getenv("PG_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "6543")
    db = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD")
    sslmode = os.getenv("PGSSLMODE", "require")
    if not (host and db and password):
        raise RuntimeError("Missing PG connection envs or PG_DSN")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
        sslmode=sslmode,
    )


def _row_exists(cur: psycopg2.extensions.cursor, slug: str) -> bool:
    cur.execute("SELECT 1 FROM public.articles WHERE slug = %s LIMIT 1", (slug,))
    return cur.fetchone() is not None


def _insert_article(
    cur: psycopg2.extensions.cursor,
    *,
    slug: str,
    title: str,
    body_md: str,
    json_payload: dict,
) -> None:
    cur.execute(
        """
        INSERT INTO public.articles (slug, type, title, body_md, json_payload)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (slug, TYPE, title, body_md, json.dumps(json_payload)),
    )


def iter_feed_items(feeds: Iterable[str]):
    for url in feeds:
        for item in fetch_rss(url, limit=25):
            yield item


def main() -> None:
    print("INGESTOR: starting…")

    conn = _connect()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    inserted = 0
    checked = 0

    for item in iter_feed_items(FEEDS):
        checked += 1
        url = item.get("url")
        title = (item.get("title") or "").strip()
        if not url or not title:
            continue

        # Build a stable slug/hash
        title_hash = text_hash(title)
        slug = f"{slugify(title)}-{title_hash[:6]}"

        if _row_exists(cur, slug):
            continue

        art = fetch_article(url)
        body_text = art.get("body_text") or ""
        if not body_text:
            # skip if no body
            continue

        json_payload = {
            "sources": [url],
            "disclaimer": "Auto-ingested via GitHub Actions",
            "ingested_ts": int(time.time()),
        }

        _insert_article(cur, slug=slug, title=title, body_md=body_text, json_payload=json_payload)
        inserted += 1
        print(f"+ inserted: {slug}")

    cur.close()
    conn.close()
    print(f"INGESTOR: done. inserted={inserted}, seen={checked}")


if __name__ == "__main__":
    main()

