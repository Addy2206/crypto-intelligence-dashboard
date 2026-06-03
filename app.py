"""
CIPHER — Crypto Intelligence Platform
Python Flask Backend using yfinance

STEP 1 — Install dependencies:
  pip install flask flask-cors yfinance

STEP 2 — Run this file:
  python app.py

Backend will start at: http://localhost:5000
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import yfinance as yf
import math
import time
from functools import wraps

app = Flask(__name__)
CORS(app)

# ── Simple in-memory cache ─────────────────────────────────────────────────
_cache = {}

def cached(ttl_seconds=60):
    """Decorator: cache the return value of a function for ttl_seconds."""
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

# ── 50+ Coins ──────────────────────────────────────────────────────────────
COINS = {
    # ── Top-cap
    "bitcoin":       {"symbol": "BTC",   "ticker": "BTC-USD",   "name": "Bitcoin",        "logo": "https://cryptologos.cc/logos/bitcoin-btc-logo.png"},
    "ethereum":      {"symbol": "ETH",   "ticker": "ETH-USD",   "name": "Ethereum",       "logo": "https://cryptologos.cc/logos/ethereum-eth-logo.png"},
    "binancecoin":   {"symbol": "BNB",   "ticker": "BNB-USD",   "name": "BNB",            "logo": "https://cryptologos.cc/logos/binancecoin-bnb-logo.png"},
    "solana":        {"symbol": "SOL",   "ticker": "SOL-USD",   "name": "Solana",         "logo": "https://cryptologos.cc/logos/solana-sol-logo.png"},
    "ripple":        {"symbol": "XRP",   "ticker": "XRP-USD",   "name": "XRP",            "logo": "https://cryptologos.cc/logos/xrp-xrp-logo.png"},
    "cardano":       {"symbol": "ADA",   "ticker": "ADA-USD",   "name": "Cardano",        "logo": "https://cryptologos.cc/logos/cardano-ada-logo.png"},
    "avalanche":     {"symbol": "AVAX",  "ticker": "AVAX-USD",  "name": "Avalanche",      "logo": "https://cryptologos.cc/logos/avalanche-avax-logo.png"},
    "dogecoin":      {"symbol": "DOGE",  "ticker": "DOGE-USD",  "name": "Dogecoin",       "logo": "https://cryptologos.cc/logos/dogecoin-doge-logo.png"},
    "polkadot":      {"symbol": "DOT",   "ticker": "DOT-USD",   "name": "Polkadot",       "logo": "https://cryptologos.cc/logos/polkadot-new-dot-logo.png"},
    "tron":          {"symbol": "TRX",   "ticker": "TRX-USD",   "name": "TRON",           "logo": "https://cryptologos.cc/logos/tron-trx-logo.png"},
    # ── DeFi / Smart-contract
    "chainlink":     {"symbol": "LINK",  "ticker": "LINK-USD",  "name": "Chainlink",      "logo": "https://cryptologos.cc/logos/chainlink-link-logo.png"},
    "polygon":       {"symbol": "POL",   "ticker": "POL-USD",   "name": "Polygon",        "logo": "https://cryptologos.cc/logos/polygon-matic-logo.png"},
    "uniswap":       {"symbol": "UNI",   "ticker": "UNI-USD",   "name": "Uniswap",        "logo": "https://cryptologos.cc/logos/uniswap-uni-logo.png"},
    "litecoin":      {"symbol": "LTC",   "ticker": "LTC-USD",   "name": "Litecoin",       "logo": "https://cryptologos.cc/logos/litecoin-ltc-logo.png"},
    "stellar":       {"symbol": "XLM",   "ticker": "XLM-USD",   "name": "Stellar",        "logo": "https://cryptologos.cc/logos/stellar-xlm-logo.png"},
    "cosmos":        {"symbol": "ATOM",  "ticker": "ATOM-USD",  "name": "Cosmos",         "logo": "https://cryptologos.cc/logos/cosmos-atom-logo.png"},
    "monero":        {"symbol": "XMR",   "ticker": "XMR-USD",   "name": "Monero",         "logo": "https://cryptologos.cc/logos/monero-xmr-logo.png"},
    "ethereum-classic": {"symbol": "ETC","ticker": "ETC-USD",   "name": "Ethereum Classic","logo": "https://cryptologos.cc/logos/ethereum-classic-etc-logo.png"},
    "vechain":       {"symbol": "VET",   "ticker": "VET-USD",   "name": "VeChain",        "logo": "https://cryptologos.cc/logos/vechain-vet-logo.png"},
    "filecoin":      {"symbol": "FIL",   "ticker": "FIL-USD",   "name": "Filecoin",       "logo": "https://cryptologos.cc/logos/filecoin-fil-logo.png"},
    # ── Layer-2 / Newer
    "near":          {"symbol": "NEAR",  "ticker": "NEAR-USD",  "name": "NEAR Protocol",  "logo": "https://cryptologos.cc/logos/near-protocol-near-logo.png"},
    "aave":          {"symbol": "AAVE",  "ticker": "AAVE-USD",  "name": "Aave",           "logo": "https://cryptologos.cc/logos/aave-aave-logo.png"},
    "algorand":      {"symbol": "ALGO",  "ticker": "ALGO-USD",  "name": "Algorand",       "logo": "https://cryptologos.cc/logos/algorand-algo-logo.png"},
    "aptos":         {"symbol": "APT",   "ticker": "APT-USD",   "name": "Aptos",          "logo": "https://cryptologos.cc/logos/aptos-apt-logo.png"},
    "arbitrum":      {"symbol": "ARB",   "ticker": "ARB-USD",   "name": "Arbitrum",       "logo": "https://cryptologos.cc/logos/arbitrum-arb-logo.png"},
    "optimism":      {"symbol": "OP",    "ticker": "OP-USD",    "name": "Optimism",       "logo": "https://cryptologos.cc/logos/optimism-ethereum-op-logo.png"},
    "injective":     {"symbol": "INJ",   "ticker": "INJ-USD",   "name": "Injective",      "logo": "https://cryptologos.cc/logos/injective-inj-logo.png"},
    "sui":           {"symbol": "SUI",   "ticker": "SUI-USD",   "name": "Sui",            "logo": "https://cryptologos.cc/logos/sui-sui-logo.png"},
    "sei":           {"symbol": "SEI",   "ticker": "SEI-USD",   "name": "Sei",            "logo": "https://cryptologos.cc/logos/sei-sei-logo.png"},
    "celestia":      {"symbol": "TIA",   "ticker": "TIA-USD",   "name": "Celestia",       "logo": "https://cryptologos.cc/logos/celestia-tia-logo.png"},
    # ── Exchange tokens
    "okb":           {"symbol": "OKB",   "ticker": "OKB-USD",   "name": "OKB",            "logo": "https://cryptologos.cc/logos/okb-okb-logo.png"},
    "kucoin-token":  {"symbol": "KCS",   "ticker": "KCS-USD",   "name": "KuCoin Token",   "logo": "https://cryptologos.cc/logos/kucoin-token-kcs-logo.png"},
    # ── Meme coins
    "shiba-inu":     {"symbol": "SHIB",  "ticker": "SHIB-USD",  "name": "Shiba Inu",      "logo": "https://cryptologos.cc/logos/shiba-inu-shib-logo.png"},
    "pepe":          {"symbol": "PEPE",  "ticker": "PEPE-USD",  "name": "Pepe",           "logo": "https://cryptologos.cc/logos/pepe-pepe-logo.png"},
    "bonk":          {"symbol": "BONK",  "ticker": "BONK-USD",  "name": "Bonk",           "logo": "https://cryptologos.cc/logos/bonk1-bonk-logo.png"},
    # ── Infrastructure / Web3
    "the-graph":     {"symbol": "GRT",   "ticker": "GRT-USD",   "name": "The Graph",      "logo": "https://cryptologos.cc/logos/the-graph-grt-logo.png"},
    "render-token":  {"symbol": "RENDER","ticker": "RENDER-USD","name": "Render",         "logo": "https://cryptologos.cc/logos/render-token-rndr-logo.png"},
    "helium":        {"symbol": "HNT",   "ticker": "HNT-USD",   "name": "Helium",         "logo": "https://cryptologos.cc/logos/helium-hnt-logo.png"},
    "arweave":       {"symbol": "AR",    "ticker": "AR-USD",    "name": "Arweave",        "logo": "https://cryptologos.cc/logos/arweave-ar-logo.png"},
    "theta":         {"symbol": "THETA", "ticker": "THETA-USD", "name": "Theta Network",  "logo": "https://cryptologos.cc/logos/theta-token-theta-logo.png"},
    "internet-computer": {"symbol": "ICP","ticker": "ICP-USD",  "name": "Internet Computer","logo": "https://cryptologos.cc/logos/internet-computer-icp-logo.png"},
    # ── Gaming / Metaverse
    "sandbox":       {"symbol": "SAND",  "ticker": "SAND-USD",  "name": "The Sandbox",    "logo": "https://cryptologos.cc/logos/the-sandbox-sand-logo.png"},
    "decentraland":  {"symbol": "MANA",  "ticker": "MANA-USD",  "name": "Decentraland",   "logo": "https://cryptologos.cc/logos/decentraland-mana-logo.png"},
    "axie-infinity": {"symbol": "AXS",   "ticker": "AXS-USD",   "name": "Axie Infinity",  "logo": "https://cryptologos.cc/logos/axie-infinity-axs-logo.png"},
    "gala":          {"symbol": "GALA",  "ticker": "GALA-USD",  "name": "Gala",           "logo": "https://cryptologos.cc/logos/gala-gala-logo.png"},
    # ── Privacy / Misc
    "zcash":         {"symbol": "ZEC",   "ticker": "ZEC-USD",   "name": "Zcash",          "logo": "https://cryptologos.cc/logos/zcash-zec-logo.png"},
    "dash":          {"symbol": "DASH",  "ticker": "DASH-USD",  "name": "Dash",           "logo": "https://cryptologos.cc/logos/dash-dash-logo.png"},
    "iota":          {"symbol": "IOTA",  "ticker": "IOTA-USD",  "name": "IOTA",           "logo": "https://cryptologos.cc/logos/iota-iota-logo.png"},
    "neo":           {"symbol": "NEO",   "ticker": "NEO-USD",   "name": "NEO",            "logo": "https://cryptologos.cc/logos/neo-neo-logo.png"},
    "waves":         {"symbol": "WAVES", "ticker": "WAVES-USD", "name": "Waves",          "logo": "https://cryptologos.cc/logos/waves-waves-logo.png"},
    "zilliqa":       {"symbol": "ZIL",   "ticker": "ZIL-USD",   "name": "Zilliqa",        "logo": "https://cryptologos.cc/logos/zilliqa-zil-logo.png"},
    "qtum":          {"symbol": "QTUM",  "ticker": "QTUM-USD",  "name": "Qtum",           "logo": "https://cryptologos.cc/logos/qtum-qtum-logo.png"},
    "flow":          {"symbol": "FLOW",  "ticker": "FLOW-USD",  "name": "Flow",           "logo": "https://cryptologos.cc/logos/flow-flow-logo.png"},
}

# ── Helpers ────────────────────────────────────────────────────────────────

def safe(v):
    if v is None:
        return None
    try:
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), 8)
    except Exception:
        return None


def days_to_period(days):
    d = int(days)
    if d <= 30:  return "1mo",  "1d"
    if d <= 90:  return "3mo",  "1d"
    if d <= 180: return "6mo",  "1d"
    if d <= 365: return "1y",   "1d"
    if d <= 730: return "2y",   "1d"
    return "5y", "1d"


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/coins")
def list_coins():
    """Return full coin metadata (no prices). Cached 1 hour — list never changes at runtime."""
    return jsonify(COINS)


@app.route("/api/prices")
@cached(ttl_seconds=60)          # refresh every 60 s — matches frontend auto-refresh
def get_prices():
    """Batch-download the latest close + 24-h change for all coins."""
    tickers = [v["ticker"] for v in COINS.values()]
    data = yf.download(tickers, period="2d", interval="1d",
                       auto_adjust=True, progress=False)

    result = {}
    for coin_id, meta in COINS.items():
        t = meta["ticker"]
        try:
            closes = data["Close"][t].dropna()
            if len(closes) < 1:
                continue
            price = float(closes.iloc[-1])
            prev  = float(closes.iloc[-2]) if len(closes) >= 2 else price
            chg   = ((price - prev) / prev * 100) if prev else 0

            # market cap via fast_info (lightweight)
            try:
                mc = yf.Ticker(t).fast_info.market_cap
            except Exception:
                mc = None

            result[coin_id] = {
                "id":         coin_id,
                "name":       meta["name"],
                "symbol":     meta["symbol"],
                "logo":       meta["logo"],
                "price":      safe(price),
                "change_24h": safe(chg),
                "market_cap": safe(mc),
            }
        except Exception as e:
            print(f"[prices] {coin_id}: {e}")

    return jsonify(result)


@app.route("/api/history/<coin_id>")
def get_history(coin_id):
    """Full OHLCV history for one coin. Cached 5 minutes."""
    if coin_id not in COINS:
        return jsonify({"error": "Coin not found"}), 404

    days     = request.args.get("days", "1825")
    cache_key = f"history_{coin_id}_{days}"
    entry     = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"] < 300):
        return entry["val"]

    period, interval = days_to_period(days)
    meta   = COINS[coin_id]
    df     = yf.Ticker(meta["ticker"]).history(period=period, interval=interval, auto_adjust=True)

    if df.empty:
        return jsonify({"error": "No data returned from yfinance"}), 500

    dates  = [d.strftime("%Y-%m-%d") for d in df.index]
    prices = [safe(p) for p in df["Close"].tolist()]

    valid = [p for p in prices if p is not None]
    ath   = max(valid) if valid else 0
    atl   = min(valid) if valid else 0
    fp    = prices[0]  or 0
    lp    = prices[-1] or 0
    ret   = round(((lp - fp) / fp * 100), 2) if fp else 0

    payload = jsonify({
        "coin_id":          coin_id,
        "name":             meta["name"],
        "symbol":           meta["symbol"],
        "logo":             meta["logo"],
        "dates":            dates,
        "prices":           prices,
        "all_time_high":    ath,
        "all_time_low":     atl,
        "first_price":      fp,
        "last_price":       lp,
        "total_return_pct": ret,
    })
    _cache[cache_key] = {"val": payload, "ts": time.time()}
    return payload


@app.route("/api/compare")
def compare_coins():
    """Normalized performance comparison for up to 6 coins. Cached 5 minutes."""
    coins_param = request.args.get("coins", "bitcoin,ethereum,solana")
    days        = request.args.get("days", "365")
    coin_list   = [c for c in coins_param.split(",") if c in COINS]

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
            if df.empty:
                continue

            dates  = [d.strftime("%Y-%m-%d") for d in df.index]
            prices = [safe(p) for p in df["Close"].tolist()]
            if result["dates"] is None:
                result["dates"] = dates

            base = prices[0] or 1
            norm = [round((p / base) * 100, 2) if p is not None else None for p in prices]
            fp, lp = (prices[0] or 0), (prices[-1] or 0)

            result["coins"][coin_id] = {
                "name":       meta["name"],
                "symbol":     meta["symbol"],
                "logo":       meta["logo"],
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
    """ATH, ATL, best/worst day, yearly returns. Cached 10 minutes."""
    if coin_id not in COINS:
        return jsonify({"error": "Coin not found"}), 404

    cache_key = f"milestones_{coin_id}"
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"] < 600):
        return entry["val"]

    meta = COINS[coin_id]
    df   = yf.Ticker(meta["ticker"]).history(period="5y", interval="1d", auto_adjust=True)

    if df.empty:
        return jsonify({"error": "No data returned from yfinance"}), 500

    entries = [
        {"date": d.strftime("%Y-%m-%d"), "price": safe(p)}
        for d, p in zip(df.index, df["Close"])
        if safe(p) is not None
    ]

    ath = max(entries, key=lambda x: x["price"])
    atl = min(entries, key=lambda x: x["price"])

    changes = []
    for i in range(1, len(entries)):
        prev = entries[i - 1]["price"]
        curr = entries[i]["price"]
        if prev and prev > 0:
            pct = (curr - prev) / prev * 100
            changes.append({"date": entries[i]["date"], "change_pct": round(pct, 2), "price": curr})

    best_day  = max(changes, key=lambda x: x["change_pct"]) if changes else {}
    worst_day = min(changes, key=lambda x: x["change_pct"]) if changes else {}

    # Yearly returns — use first and last closing price of each calendar year
    yearly = {}
    for e in entries:
        yr = e["date"][:4]
        if yr not in yearly:
            yearly[yr] = {"start": e["price"], "end": e["price"]}
        yearly[yr]["end"] = e["price"]

    yearly_returns = [
        {
            "year":        yr,
            "return_pct":  round(((v["end"] - v["start"]) / v["start"] * 100), 2) if v["start"] else 0,
            "start_price": v["start"],
            "end_price":   v["end"],
        }
        for yr, v in sorted(yearly.items())
    ]

    payload = jsonify({
        "coin_id":        coin_id,
        "name":           meta["name"],
        "symbol":         meta["symbol"],
        "ath":            ath,
        "atl":            atl,
        "best_day":       best_day,
        "worst_day":      worst_day,
        "yearly_returns": yearly_returns,
    })
    _cache[cache_key] = {"val": payload, "ts": time.time()}
    return payload


# ── Cache management endpoints (optional, handy for debugging) ─────────────

@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    _cache.clear()
    return jsonify({"status": "cache cleared"})


@app.route("/api/cache/stats")
def cache_stats():
    now = time.time()
    return jsonify({k: round(now - v["ts"], 1) for k, v in _cache.items()})


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  CIPHER Backend  —  http://localhost:5000")
    print(f"  {len(COINS)} coins loaded")
    print("  Keep this terminal open, then open index.html")
    print("=" * 55)
    app.run(debug=True, port=5000)