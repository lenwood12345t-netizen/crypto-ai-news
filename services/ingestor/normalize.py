# services/ingestor/normalize.py

import datetime as dt
import time
import requests
import feedparser
from readability import Document
from bs4 import BeautifulSoup


def iso_date(value):
    """
    Convert common feedparser date types to ISO-8601.
    Accepts: time.struct_time, datetime, epoch (int/float), or ISO str passthrough.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        d = dt.datetime.utcfromtimestamp(value).replace(tzinfo=dt.timezone.utc)
        return d.isoformat()

    if hasattr(value, "tm_year"):  # time.struct_time
        d = dt.datetime.fromtimestamp(time.mktime(value), tz=dt.timezone.utc)
        return d.isoformat()

    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return value.isoformat()

    if isinstance(value, str):
        return value  # assume it's already ISO

    return None


def fetch_rss(url, limit=20):
    """
    Return a list of {url, title, published} items from an RSS/Atom feed.
    """
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:limit]:
        link = e.get("link") or ""
        title = e.get("title") or ""
        published = e.get("published_parsed") or e.get("updated_parsed")
        items.append(
            {
                "url": link,
                "title": title,
                "published": iso_date(published),
            }
        )
    return items


def fetch_article(url, timeout=20):
    """
    Download a URL and extract main article text & title.
    Returns a dict with keys: title, text, asset (optional).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()

    html = r.text
    doc = Document(html)
    title = (doc.short_title() or "").strip()
    content_html = doc.summary()

    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text("\n").strip()

    # You can try to pull a lead image if you want. Keep None if you don’t care.
    asset = None

    return {
        "title": title,
        "text": text,
        "asset": asset,
    }
