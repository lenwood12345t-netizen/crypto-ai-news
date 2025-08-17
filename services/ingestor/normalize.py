# services/ingestor/normalize.py
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document
from lxml.html.clean import Cleaner


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HTTP_TIMEOUT = 20


def text_hash(text: str) -> str:
    """
    Stable content hash for deduplication (no 3rd-party 'dedupe' package).
    """
    if not text:
        return ""
    # remove accents, normalize whitespace, lowercase
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = re.sub(r"\W+", " ", norm.lower()).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def slugify(text: str) -> str:
    """
    URL-safe slug (ascii only).
    """
    if not text:
        return "untitled"
    t = unicodedata.normalize("NFKD", text)
    t = t.encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9\- _]+", "", t)
    t = t.replace("_", " ")
    t = re.sub(r"\s+", "-", t.strip().lower())
    return t or "untitled"


def iso_date(dt_str: str | None) -> str | None:
    """
    Returns an ISO-8601 UTC string from a feed date string if possible.
    """
    if not dt_str:
        return None
    try:
        dt = parsedate_to_datetime(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def fetch_rss(url: str, limit: int = 25) -> List[Dict]:
    """
    Pulls items from an RSS/Atom feed and normalizes basic fields.
    """
    feed = feedparser.parse(url)
    items: List[Dict] = []
    for e in feed.entries[:limit]:
        items.append(
            {
                "url": e.get("link"),
                "title": e.get("title", "").strip(),
                "published": iso_date(e.get("published")),
                "source": feed.feed.get("title") or url,
            }
        )
    return items


def _extract_readable_html(html: str) -> str:
    """
    Uses readability to extract the main article HTML and cleans it.
    """
    doc = Document(html)
    cleaned_html = doc.summary(html_partial=True)

    # sanitize
    cleaner = Cleaner(
        scripts=True,
        javascript=True,
        style=True,
        links=False,
        meta=False,
        page_structure=False,
        embedded=False,
        frames=True,
        forms=True,
        annoying_tags=True,
        remove_unknown_tags=False,
        safe_attrs_only=True,
    )
    cleaned = cleaner.clean_html(cleaned_html)
    return cleaned


def fetch_article(url: str) -> Dict[str, str | None]:
    """
    Downloads an article and returns {title, body_text}.
    """
    if not url:
        return {"title": None, "body_text": None}

    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return {"title": None, "body_text": None}

    try:
        doc = Document(resp.text)
        title = (doc.short_title() or "").strip()
        readable_html = _extract_readable_html(resp.text)
        soup = BeautifulSoup(readable_html, "html.parser")
        # get readable text
        body_text = soup.get_text("\n").strip()
        # collapse excessive newlines
        body_text = re.sub(r"\n{3,}", "\n\n", body_text)
        return {"title": title or None, "body_text": body_text or None}
    except Exception:
        return {"title": None, "body_text": None}
