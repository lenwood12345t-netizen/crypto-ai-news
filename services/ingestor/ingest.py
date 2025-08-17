import os, time, hashlib
from datetime import datetime, timezone, timedelta
from dateutil import tz
from config import ALLOWLIST, TIMEZONE, ASSET_ROTATION, FRESH_WINDOW_MIN, VARIETY_LOOKBACK
from normalize import fetch_rss, fetch_article, iso_date
from dedupe import text_hash
from db import upsert_source, insert_raw, insert_document, conn
from generate import create_spec_outlook, create_news_brief

def make_slug(prefix:str)->str:
    return prefix + '-' + hashlib.sha1(str(time.time()).encode()).hexdigest()[:8]

local_tz = tz.gettz(TIMEZONE)

# ---------- helpers -----------------------------------------------------------

def posted_this_hour() -> bool:
    """Prevent more than one post per hour (UTC hour bucket)."""
    with conn.cursor() as cur:
        cur.execute("""
          select 1
          from articles
          where date_trunc('hour', created_at) = date_trunc('hour', now())
          limit 1
        """)
        return cur.fetchone() is not None

def recent_assets(n:int=VARIETY_LOOKBACK) -> set:
    """Return set of assets used in the last N posts."""
    with conn.cursor() as cur:
        cur.execute("""
          select asset
          from articles
          where asset is not null
          order by created_at desc
          limit %s
        """, (n,))
        return {r[0] for r in cur.fetchall() if r[0]}

def pick_next_asset() -> str:
    """Deterministic hourly choice; avoid recently used asset when possible."""
    hour = int(datetime.now(timezone.utc).strftime('%Y%m%d%H'))
    recent = recent_assets()
    for offset in range(len(ASSET_ROTATION)):
        cand = ASSET_ROTATION[(hour + offset) % len(ASSET_ROTATION)]
        if cand not in recent:
            return cand
    return ASSET_ROTATION[hour % len(ASSET_ROTATION)]  # fallback

def fresh_feed_candidates():
    """Collect feed entries fresher than FRESH_WINDOW_MIN minutes (newest first)."""
    items = []
    now = datetime.now(timezone.utc)
    for s in ALLOWLIST:
        sid = upsert_source(s['name'], s['type'], s.get('rss'))
        feed = fetch_rss(s['rss']) if s.get('rss') else {'entries': []}
        for e in feed.get('entries', []):
            published = iso_date(e.get('published') or e.get('updated'))
            if not published:
                continue
            if (now - published) > timedelta(minutes=FRESH_WINDOW_MIN):
                continue
            items.append((published, s, e))
    items.sort(key=lambda x: x[0], reverse=True)
    return items

# ---------- hourly policy -----------------------------------------------------

def run_hourly():
    # 1) one post per hour, max
    if posted_this_hour():
        print("Already posted this hour; exiting.")
        return

    # 2) Try fresh news first
    for published, s, e in fresh_feed_candidates():
        url = e.get('link')
        try:
            title, text = fetch_article(url)
        except Exception as ex:
            print("fetch_article failed:", ex)
            continue

        h = text_hash(text)
        raw_id = insert_raw(upsert_source(s['name'], s['type'], s.get('rss')),
                            url, 'en', text, title, published, h)
        if not raw_id:
            # duplicate URL
            continue

        insert_document(raw_id, url, title, text, published)

        slug = make_slug('news')
        src = [{
            "title": title,
            "url": url,
            "publisher": s['name'],
            "date": (published.isoformat() if published else '')
        }]
        ctx = f"Title: {title}\n\nQuotes/Facts:\n{text[:2000]}"
        create_news_brief(slug, title, ctx, src)
        print("Posted news:", slug)
        return  # one-and-done this hour

    # 3) If no fresh news, publish rotating spec_outlook
    asset = pick_next_asset()
    slug = make_slug(asset)
    ctx = f"Create bull/base/bear scenarios for {asset.upper()} over 7d/30d based on current crypto context."
    create_spec_outlook(slug, asset, ctx, [])
    print("Posted spec_outlook:", slug, "asset:", asset)

if __name__ == '__main__':
    run_hourly()
