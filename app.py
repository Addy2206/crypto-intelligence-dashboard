"""
CIPHER — Crypto Intelligence Platform
Python Flask Backend using yfinance

STEP 1 — Install dependencies:
  pip install flask flask-cors yfinance requests

STEP 2 — Run:
  python app.py

Backend: http://localhost:5000
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import yfinance as yf
import math, time, os, requests
from functools import wraps

app = Flask(__name__)
CORS(app)  # allow all origins — fine for a public educational tool

# ── Cache ──────────────────────────────────────────────────────────────────
_cache = {}

def cached(ttl_seconds=60):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            entry = _cache.get(key)
            if entry and (time.time() - entry["ts"] < ttl_seconds):
                return entry["val"]
            result = fn(*args, **kwargs)
            _cache[key] = {"val": result, "ts": time.time()}
            return result
        return wrapper
    return decorator

# ── Coins ──────────────────────────────────────────────────────────────────
COINS = {
    "bitcoin":       {"symbol": "BTC",   "ticker": "BTC-USD",   "name": "Bitcoin",          "logo": "https://cryptologos.cc/logos/bitcoin-btc-logo.png",       "color": "#f0a500"},
    "ethereum":      {"symbol": "ETH",   "ticker": "ETH-USD",   "name": "Ethereum",         "logo": "https://cryptologos.cc/logos/ethereum-eth-logo.png",      "color": "#627eea"},
    "binancecoin":   {"symbol": "BNB",   "ticker": "BNB-USD",   "name": "BNB",              "logo": "https://cryptologos.cc/logos/binancecoin-bnb-logo.png",   "color": "#f3ba2f"},
    "solana":        {"symbol": "SOL",   "ticker": "SOL-USD",   "name": "Solana",           "logo": "https://cryptologos.cc/logos/solana-sol-logo.png",        "color": "#9945ff"},
    "ripple":        {"symbol": "XRP",   "ticker": "XRP-USD",   "name": "XRP",              "logo": "https://cryptologos.cc/logos/xrp-xrp-logo.png",          "color": "#3bcefc"},
    "cardano":       {"symbol": "ADA",   "ticker": "ADA-USD",   "name": "Cardano",          "logo": "https://cryptologos.cc/logos/cardano-ada-logo.png",       "color": "#0052cc"},
    "avalanche":     {"symbol": "AVAX",  "ticker": "AVAX-USD",  "name": "Avalanche",        "logo": "https://cryptologos.cc/logos/avalanche-avax-logo.png",    "color": "#e84142"},
    "dogecoin":      {"symbol": "DOGE",  "ticker": "DOGE-USD",  "name": "Dogecoin",         "logo": "https://cryptologos.cc/logos/dogecoin-doge-logo.png",     "color": "#c2a633"},
    "polkadot":      {"symbol": "DOT",   "ticker": "DOT-USD",   "name": "Polkadot",         "logo": "https://cryptologos.cc/logos/polkadot-new-dot-logo.png",  "color": "#e6007a"},
    "tron":          {"symbol": "TRX",   "ticker": "TRX-USD",   "name": "TRON",             "logo": "https://cryptologos.cc/logos/tron-trx-logo.png",          "color": "#ff0013"},
    "chainlink":     {"symbol": "LINK",  "ticker": "LINK-USD",  "name": "Chainlink",        "logo": "https://cryptologos.cc/logos/chainlink-link-logo.png",    "color": "#2a5ada"},
    "polygon":       {"symbol": "POL",   "ticker": "POL-USD",   "name": "Polygon",          "logo": "https://cryptologos.cc/logos/polygon-matic-logo.png",     "color": "#8247e5"},
    "uniswap":       {"symbol": "UNI",   "ticker": "UNI-USD",   "name": "Uniswap",          "logo": "https://cryptologos.cc/logos/uniswap-uni-logo.png",       "color": "#ff007a"},
    "litecoin":      {"symbol": "LTC",   "ticker": "LTC-USD",   "name": "Litecoin",         "logo": "https://cryptologos.cc/logos/litecoin-ltc-logo.png",      "color": "#bfbbbb"},
    "stellar":       {"symbol": "XLM",   "ticker": "XLM-USD",   "name": "Stellar",          "logo": "https://cryptologos.cc/logos/stellar-xlm-logo.png",       "color": "#7d00ff"},
    "cosmos":        {"symbol": "ATOM",  "ticker": "ATOM-USD",  "name": "Cosmos",           "logo": "https://cryptologos.cc/logos/cosmos-atom-logo.png",       "color": "#2e3148"},
    "monero":        {"symbol": "XMR",   "ticker": "XMR-USD",   "name": "Monero",           "logo": "https://cryptologos.cc/logos/monero-xmr-logo.png",        "color": "#ff6600"},
    "near":          {"symbol": "NEAR",  "ticker": "NEAR-USD",  "name": "NEAR Protocol",    "logo": "https://cryptologos.cc/logos/near-protocol-near-logo.png","color": "#00c08b"},
    "aave":          {"symbol": "AAVE",  "ticker": "AAVE-USD",  "name": "Aave",             "logo": "https://cryptologos.cc/logos/aave-aave-logo.png",         "color": "#b6509e"},
    "algorand":      {"symbol": "ALGO",  "ticker": "ALGO-USD",  "name": "Algorand",         "logo": "https://cryptologos.cc/logos/algorand-algo-logo.png",     "color": "#ffffff"},
    "aptos":         {"symbol": "APT",   "ticker": "APT-USD",   "name": "Aptos",            "logo": "https://cryptologos.cc/logos/aptos-apt-logo.png",         "color": "#00b4d8"},
    "arbitrum":      {"symbol": "ARB",   "ticker": "ARB-USD",   "name": "Arbitrum",         "logo": "https://cryptologos.cc/logos/arbitrum-arb-logo.png",      "color": "#28a0f0"},
    "optimism":      {"symbol": "OP",    "ticker": "OP-USD",    "name": "Optimism",         "logo": "https://cryptologos.cc/logos/optimism-ethereum-op-logo.png","color": "#ff0420"},
    "injective":     {"symbol": "INJ",   "ticker": "INJ-USD",   "name": "Injective",        "logo": "https://cryptologos.cc/logos/injective-inj-logo.png",     "color": "#00b2ff"},
    "sui":           {"symbol": "SUI",   "ticker": "SUI-USD",   "name": "Sui",              "logo": "https://cryptologos.cc/logos/sui-sui-logo.png",           "color": "#4ca3ff"},
    "shiba-inu":     {"symbol": "SHIB",  "ticker": "SHIB-USD",  "name": "Shiba Inu",        "logo": "https://cryptologos.cc/logos/shiba-inu-shib-logo.png",    "color": "#ffa409"},
    "dogecoin":      {"symbol": "DOGE",  "ticker": "DOGE-USD",  "name": "Dogecoin",         "logo": "https://cryptologos.cc/logos/dogecoin-doge-logo.png",     "color": "#c2a633"},
    "the-graph":     {"symbol": "GRT",   "ticker": "GRT-USD",   "name": "The Graph",        "logo": "https://cryptologos.cc/logos/the-graph-grt-logo.png",     "color": "#6f4cff"},
    "sandbox":       {"symbol": "SAND",  "ticker": "SAND-USD",  "name": "The Sandbox",      "logo": "https://cryptologos.cc/logos/the-sandbox-sand-logo.png",  "color": "#04adef"},
    "decentraland":  {"symbol": "MANA",  "ticker": "MANA-USD",  "name": "Decentraland",     "logo": "https://cryptologos.cc/logos/decentraland-mana-logo.png", "color": "#ff2d55"},
    "axie-infinity": {"symbol": "AXS",   "ticker": "AXS-USD",   "name": "Axie Infinity",    "logo": "https://cryptologos.cc/logos/axie-infinity-axs-logo.png", "color": "#0055d5"},
    "filecoin":      {"symbol": "FIL",   "ticker": "FIL-USD",   "name": "Filecoin",         "logo": "https://cryptologos.cc/logos/filecoin-fil-logo.png",      "color": "#0090ff"},
    "internet-computer": {"symbol":"ICP","ticker": "ICP-USD",   "name": "Internet Computer","logo": "https://cryptologos.cc/logos/internet-computer-icp-logo.png","color":"#f15a24"},
    "zcash":         {"symbol": "ZEC",   "ticker": "ZEC-USD",   "name": "Zcash",            "logo": "https://cryptologos.cc/logos/zcash-zec-logo.png",         "color": "#f4b728"},
    "stellar":       {"symbol": "XLM",   "ticker": "XLM-USD",   "name": "Stellar",          "logo": "https://cryptologos.cc/logos/stellar-xlm-logo.png",       "color": "#7d00ff"},
    "flow":          {"symbol": "FLOW",  "ticker": "FLOW-USD",  "name": "Flow",             "logo": "https://cryptologos.cc/logos/flow-flow-logo.png",         "color": "#00ef8b"},
}

# ── Helpers ────────────────────────────────────────────────────────────────
def safe(v):
    if v is None: return None
    try:
        if math.isnan(v) or math.isinf(v): return None
        return round(float(v), 8)
    except Exception: return None

def days_to_period(days):
    d = int(days)
    if d <= 30:  return "1mo",  "1d"
    if d <= 90:  return "3mo",  "1d"
    if d <= 180: return "6mo",  "1d"
    if d <= 365: return "1y",   "1d"
    if d <= 730: return "2y",   "1d"
    return "5y", "1d"

def simple_explanation(coin_name, change_pct):
    """Generate a beginner-friendly explanation of why a coin might be moving."""
    direction = "rising" if change_pct > 0 else "falling"
    magnitude = abs(change_pct)
    if magnitude < 1:
        intensity = "slightly"
    elif magnitude < 3:
        intensity = "moderately"
    elif magnitude < 8:
        intensity = "notably"
    else:
        intensity = "sharply"

    if change_pct > 0:
        reasons = [
            f"More people are buying {coin_name} today than selling.",
            f"Investor confidence in {coin_name} has increased today.",
            f"Demand for {coin_name} is higher than usual right now.",
        ]
    else:
        reasons = [
            f"More people are selling {coin_name} today than buying.",
            f"Some investors are taking profits or reducing risk.",
            f"Broader market uncertainty is affecting {coin_name} today.",
        ]

    import hashlib
    idx = int(hashlib.md5(f"{coin_name}{round(change_pct,1)}".encode()).hexdigest(), 16) % len(reasons)
    return f"{coin_name} is {intensity} {direction}. {reasons[idx]}"


# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/coins")
def list_coins():
    return jsonify(COINS)

@app.route("/api/prices")
@cached(ttl_seconds=60)
def get_prices():
    tickers = [v["ticker"] for v in COINS.values()]
    data = yf.download(tickers, period="2d", interval="1d",
                       auto_adjust=True, progress=False)
    result = {}
    for coin_id, meta in COINS.items():
        t = meta["ticker"]
        try:
            closes = data["Close"][t].dropna()
            if len(closes) < 1: continue
            price = float(closes.iloc[-1])
            prev  = float(closes.iloc[-2]) if len(closes) >= 2 else price
            chg   = ((price - prev) / prev * 100) if prev else 0
            try:
                mc = yf.Ticker(t).fast_info.market_cap
            except Exception:
                mc = None
            result[coin_id] = {
                "id": coin_id, "name": meta["name"], "symbol": meta["symbol"],
                "logo": meta["logo"], "color": meta.get("color", "#ffffff"),
                "price": safe(price), "change_24h": safe(chg), "market_cap": safe(mc),
            }
        except Exception as e:
            print(f"[prices] {coin_id}: {e}")
    return jsonify(result)

@app.route("/api/movers")
@cached(ttl_seconds=120)
def get_movers():
    """Top 3 gainers and top 3 losers with beginner-friendly explanations."""
    tickers = [v["ticker"] for v in COINS.values()]
    try:
        data = yf.download(tickers, period="2d", interval="1d",
                           auto_adjust=True, progress=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    coins_with_change = []
    for coin_id, meta in COINS.items():
        t = meta["ticker"]
        try:
            closes = data["Close"][t].dropna()
            if len(closes) < 2: continue
            price = float(closes.iloc[-1])
            prev  = float(closes.iloc[-2])
            chg   = ((price - prev) / prev * 100) if prev else 0
            coins_with_change.append({
                "id": coin_id, "name": meta["name"], "symbol": meta["symbol"],
                "logo": meta["logo"], "color": meta.get("color", "#ffffff"),
                "price": safe(price), "change_24h": safe(chg),
                "explanation": simple_explanation(meta["name"], chg),
            })
        except Exception:
            continue

    coins_with_change.sort(key=lambda x: x["change_24h"] or 0, reverse=True)
    return jsonify({
        "gainers": coins_with_change[:3],
        "losers":  list(reversed(coins_with_change[-3:])),
        "updated": time.strftime("%H:%M UTC", time.gmtime()),
    })

@app.route("/api/history/<coin_id>")
def get_history(coin_id):
    if coin_id not in COINS:
        return jsonify({"error": "Coin not found"}), 404
    days = request.args.get("days", "1825")
    cache_key = f"history_{coin_id}_{days}"
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"] < 300):
        return entry["val"]
    period, interval = days_to_period(days)
    meta = COINS[coin_id]
    df   = yf.Ticker(meta["ticker"]).history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        return jsonify({"error": "No data returned"}), 500
    dates  = [d.strftime("%Y-%m-%d") for d in df.index]
    prices = [safe(p) for p in df["Close"].tolist()]
    valid  = [p for p in prices if p is not None]
    ath, atl = (max(valid), min(valid)) if valid else (0, 0)
    fp, lp = (prices[0] or 0), (prices[-1] or 0)
    ret = round(((lp - fp) / fp * 100), 2) if fp else 0
    payload = jsonify({
        "coin_id": coin_id, "name": meta["name"], "symbol": meta["symbol"],
        "logo": meta["logo"], "color": meta.get("color","#3bcefc"),
        "dates": dates, "prices": prices,
        "all_time_high": ath, "all_time_low": atl,
        "first_price": fp, "last_price": lp, "total_return_pct": ret,
    })
    _cache[cache_key] = {"val": payload, "ts": time.time()}
    return payload

@app.route("/api/compare")
def compare_coins():
    coins_param = request.args.get("coins", "bitcoin,ethereum,solana")
    days = request.args.get("days", "365")
    coin_list = [c for c in coins_param.split(",") if c in COINS]
    if not coin_list:
        return jsonify({"error": "No valid coins provided"}), 400
    cache_key = f"compare_{'_'.join(sorted(coin_list))}_{days}"
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"] < 300):
        return entry["val"]
    period, interval = days_to_period(days)
    result = {"coins": {}, "dates": None}
    for coin_id in coin_list:
        meta = COINS[coin_id]
        try:
            df = yf.Ticker(meta["ticker"]).history(period=period, interval=interval, auto_adjust=True)
            if df.empty: continue
            dates  = [d.strftime("%Y-%m-%d") for d in df.index]
            prices = [safe(p) for p in df["Close"].tolist()]
            if result["dates"] is None: result["dates"] = dates
            base = prices[0] or 1
            norm = [round((p / base) * 100, 2) if p else None for p in prices]
            fp, lp = (prices[0] or 0), (prices[-1] or 0)
            result["coins"][coin_id] = {
                "name": meta["name"], "symbol": meta["symbol"], "logo": meta["logo"],
                "color": meta.get("color","#ffffff"),
                "normalized": norm,
                "return_pct": round(((lp - fp) / fp * 100), 2) if fp else 0,
            }
        except Exception as e:
            print(f"[compare] {coin_id}: {e}")
    payload = jsonify(result)
    _cache[cache_key] = {"val": payload, "ts": time.time()}
    return payload

@app.route("/api/milestones/<coin_id>")
def get_milestones(coin_id):
    if coin_id not in COINS:
        return jsonify({"error": "Coin not found"}), 404
    cache_key = f"milestones_{coin_id}"
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"] < 600):
        return entry["val"]
    meta = COINS[coin_id]
    df   = yf.Ticker(meta["ticker"]).history(period="5y", interval="1d", auto_adjust=True)
    if df.empty:
        return jsonify({"error": "No data returned"}), 500
    entries = [
        {"date": d.strftime("%Y-%m-%d"), "price": safe(p)}
        for d, p in zip(df.index, df["Close"]) if safe(p) is not None
    ]
    ath = max(entries, key=lambda x: x["price"])
    atl = min(entries, key=lambda x: x["price"])
    changes = []
    for i in range(1, len(entries)):
        prev, curr = entries[i-1]["price"], entries[i]["price"]
        if prev and prev > 0:
            pct = (curr - prev) / prev * 100
            changes.append({"date": entries[i]["date"], "change_pct": round(pct,2), "price": curr})
    best_day  = max(changes, key=lambda x: x["change_pct"]) if changes else {}
    worst_day = min(changes, key=lambda x: x["change_pct"]) if changes else {}
    yearly = {}
    for e in entries:
        yr = e["date"][:4]
        if yr not in yearly:
            yearly[yr] = {"start": e["price"], "end": e["price"]}
        yearly[yr]["end"] = e["price"]
    yearly_returns = [
        {"year": yr, "return_pct": round(((v["end"]-v["start"])/v["start"]*100),2) if v["start"] else 0,
         "start_price": v["start"], "end_price": v["end"]}
        for yr, v in sorted(yearly.items())
    ]
    payload = jsonify({
        "coin_id": coin_id, "name": meta["name"], "symbol": meta["symbol"],
        "ath": ath, "atl": atl, "best_day": best_day, "worst_day": worst_day,
        "yearly_returns": yearly_returns,
    })
    _cache[cache_key] = {"val": payload, "ts": time.time()}
    return payload

@app.route("/api/news")
@cached(ttl_seconds=600)
def get_news():
    import xml.etree.ElementTree as ET
    import re

    RSS_FEEDS = [
        "https://cointelegraph.com/rss",
        "https://coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
    ]

    for url in RSS_FEEDS:
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:12]
            if not items:
                continue
            news = []
            for item in items:
                title = (item.findtext("title") or "").strip()
                link  = (item.findtext("link")  or "").strip()
                desc  = (item.findtext("description") or "").strip()
                date  = (item.findtext("pubDate") or "").strip()
                desc  = re.sub(r"<[^>]+>", "", desc).strip()[:200]
                news.append({"title": title, "link": link, "summary": desc, "date": date})
            print(f"[news] OK — {url} ({len(news)} articles)")
            return jsonify({"articles": news, "source": url})
        except Exception as e:
            print(f"[news] FAILED {url}: {e}")
            continue

    return jsonify({"articles": [
        {"title": "News temporarily unavailable", "link": "#",
         "summary": "Could not reach any news source. Please try again shortly.", "date": ""}
    ], "source": "fallback"})

@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    _cache.clear()
    return jsonify({"status": "cache cleared"})

@app.route("/api/cache/stats")
def cache_stats():
    now = time.time()
    return jsonify({k: round(now - v["ts"], 1) for k, v in _cache.items()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print(f"  CIPHER Backend  —  http://localhost:{port}")
    print(f"  {len(COINS)} coins loaded")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=port)
