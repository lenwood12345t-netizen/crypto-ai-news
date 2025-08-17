import os, re, time, hashlib, requests, feedparser, psycopg2
from bs4 import BeautifulSoup
from readability import Document
from dateutil import parser as dt
from openai import OpenAI

# --- config ---
ALLOWLIST = [
  ("CoinDesk",       "https://www.coindesk.com/arc/outboundfeeds/rss/"),
  ("CoinTelegraph",  "https://cointelegraph.com/rss"),
  ("Decrypt",        "https://decrypt.co/feed"),
  ("SEC",            "https://www.sec.gov/news/pressreleases.rss"),
]
MAX_PER_FEED = int(os.getenv("MAX_PER_FEED", "5"))
UA = {'User-Agent': 'CryptoAINewsBot/0.1 (+contact@yourdomain.com)'}
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- pg connection (build from split env or PG_DSN) ---
def build_dsn_from_env():
    host = os.getenv("PGHOST"); port = os.getenv("PGPORT")
    db   = os.getenv("PGDATABASE"); user = os.getenv("PGUSER")
    pw   = os.getenv("PGPASSWORD"); ssl = os.getenv("PGSSLMODE","require")
    if all([host, port, db, user, pw]):
        return f"host={host} port={port} dbname={db} user={user} password={pw} sslmode={ssl}"
    return os.getenv("PG_DSN")

PG_DSN = build_dsn_from_env()
if not PG_DSN:
    raise SystemExit("No PG connection info. Set split vars (PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD) or PG_DSN.")

conn = psycopg2.connect(PG_DSN)
conn.autocommit = True

# --- openai client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def make_slug(title: str) -> str:
    base = re.sub(r"[^a-z0-9\- ]","", title.lower()).strip().replace(" ", "-")
    base = re.sub(r"-+","-", base)[:60].strip("-") or "story"
    stamp = hashlib.sha1(str(time.time()).encode()).hexdigest()[:6]
    return f"{base}-{stamp}"

def fetch_article(url: str):
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    doc = Document(r.text)
    title = (doc.title() or "").strip()
    html = doc.summary()
    soup = BeautifulSoup(html, "lxml")
    text = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
    return title, text

def summarize_md(title: str, text: str, source_name: str, url: str) -> str:
    prompt = f"""
You are a careful news editor. Using ONLY the facts below, write a 120–180 word,
neutral, markdown news brief. End with one line: **Why it matters for crypto:** <short reason>.
No speculation, no price targets.

TITLE: {title}

FACTS/QUOTES:
{text[:2000]}

Include a tiny bullet list of key takeaways at the end.
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.4
    )
    return resp.choices[0].message.content or ""

def insert_article(slug, title, body_md, sources_json):
    with conn.cursor() as cur:
        cur.execute("""
            insert into articles (slug, type, asset, title, body_md, json_payload, confidence)
            values (%s, 'news_brief', NULL, %s, %s, %s::jsonb, 'medium')
            on conflict (slug) do nothing
            returning id
        """, (slug, title, body_md, sources_json))
        row = cur.fetchone()
        return (row[0] if row else None)

def run_once():
    made = 0
    for (name, rss) in ALLOWLIST:
        feed = feedparser.parse(rss)
        for entry in feed.get("entries", [])[:MAX_PER_FEED]:
            url = entry.get("link")
            if not url: continue
            try:
                title, text = fetch_article(url)
                if not (title and text and len(text) > 200):
                    continue
                slug = make_slug(title)
                md = summarize_md(title, text, name, url)
                pub = entry.get("published") or entry.get("updated") or ""
                pub_iso = ""
                try:
                    pub_iso = dt.parse(pub).isoformat()
                except Exception:
                    pass
                payload = {
                    "sources":[{"title": title, "url": url, "publisher": name, "date": pub_iso}],
                    "disclaimer":"AI-generated. Informational only."
                }
                import json
                aid = insert_article(slug, title, md, json.dumps(payload))
                if aid:
                    made += 1
            except Exception as e:
                # Log and continue (keeps action green)
                print("ERROR on", url, "->", repr(e))
                continue
    print(f"Inserted {made} article(s)")

if __name__ == "__main__":
    run_once()


