# --- Sources you already like ---
ALLOWLIST = [
  {"name":"CoinDesk","type":"crypto_media","rss":"https://www.coindesk.com/arc/outboundfeeds/rss/"},
  {"name":"CoinTelegraph","type":"crypto_media","rss":"https://cointelegraph.com/rss"},
  {"name":"Decrypt","type":"crypto_media","rss":"https://decrypt.co/feed"},
  {"name":"SEC","type":"regulator","rss":"https://www.sec.gov/news/pressreleases.rss"},
  {"name":"CFTC","type":"regulator","rss":"https://www.cftc.gov/PressRoom/PressReleases/rss"},
]

# --- Display timezone (optional, used in UI/logging) ---
TIMEZONE = 'America/Phoenix'

# --- Hourly topic rotation (for fallback posts) ---
ASSET_ROTATION = [
  'btc','eth','sol','xrp','ada','doge','matic','dot','avax','atom',
  'arb','op','link','near','bch','ltc','uni','apt','ton','trx'
]

# Consider items "fresh" if published within this many minutes
FRESH_WINDOW_MIN = 75

# Don't repeat an asset used in the last N posts (variety)
VARIETY_LOOKBACK = 3
