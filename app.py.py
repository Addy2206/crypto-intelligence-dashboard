from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading

app = Flask(__name__)

# ── Constants ─────────────────────────────────────────────────────────
COINS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana"
}
COLORS = {
    "BTC-USD": "#F7931A",
    "ETH-USD": "#627EEA",
    "SOL-USD": "#9945FF"
}

# ── Cache ─────────────────────────────────────────────────────────────
_cache = {
    "df":        None,
    "timestamp": 0,
    "lock":      threading.Lock()
}
CACHE_TTL = 300  # 5 minutes


def fetch_data(days=1825):
    """Fetch historical data with 5-minute in-memory cache."""
    with _cache["lock"]:
        now = time.time()
        if _cache["df"] is not None and (now - _cache["timestamp"]) < CACHE_TTL:
            return _cache["df"]

        end   = datetime.today()
        start = end - timedelta(days=days)
        frames = []

        for ticker, name in COINS.items():
            try:
                raw = yf.download(
                    ticker, start=start, end=end,
                    progress=False, auto_adjust=True
                )
                if raw.empty:
                    continue
                df = raw[["Close"]].copy()
                df.columns = ["price"]
                df.index.name = "timestamp"
                df = df.reset_index()
                df["ticker"] = ticker
                df["coin"]   = name
                df["year"]   = df["timestamp"].dt.year
                df["price"]  = pd.to_numeric(df["price"], errors="coerce")
                df = df.dropna(subset=["price"])
                frames.append(df)
            except Exception as e:
                print(f"Error fetching {name}: {e}")

        if not frames:
            return _cache["df"]  # return stale cache if available

        result = pd.concat(frames, ignore_index=True)
        _cache["df"]        = result
        _cache["timestamp"] = now
        return result


# ── Helpers ───────────────────────────────────────────────────────────
def compute_insights(df):
    insights = []
    for ticker, name in COINS.items():
        d = df[df["ticker"] == ticker].sort_values("timestamp")
        if len(d) < 2:
            continue
        prices       = d["price"]
        start_price  = prices.iloc[0]
        end_price    = prices.iloc[-1]
        ath          = prices.max()
        atl          = prices.min()
        total_growth = (end_price - start_price) / start_price * 100
        drawdown     = (ath - end_price) / ath * 100
        volatility   = prices.pct_change().std() * 100

        yearly     = d.groupby("year")["price"].mean()
        best_year  = int(yearly.idxmax())
        worst_year = int(yearly.idxmin())
        avgs       = yearly.values
        yoy        = [(avgs[i] - avgs[i-1]) / avgs[i-1] * 100
                      for i in range(1, len(avgs))]

        if total_growth > 500:
            verdict = "Exceptional Performer"
            risk    = "Very High"
            advice  = "Ideal for aggressive traders. Massive upside but brutal drawdowns."
        elif total_growth > 100:
            verdict = "Strong Performer"
            risk    = "High"
            advice  = "Good for medium-risk traders. Rewarded long-term holders well."
        elif total_growth > 0:
            verdict = "Moderate Performer"
            risk    = "Medium"
            advice  = "Safer relative pick. Lower upside, suits conservative traders."
        else:
            verdict = "Underperformer"
            risk    = "High (downside)"
            advice  = "More loss than gain. Study dip patterns carefully before entering."

        insights.append({
            "ticker":       ticker,
            "name":         name,
            "color":        COLORS[ticker],
            "start_price":  round(float(start_price), 2),
            "end_price":    round(float(end_price), 2),
            "ath":          round(float(ath), 2),
            "atl":          round(float(atl), 2),
            "total_growth": round(float(total_growth), 2),
            "drawdown":     round(float(drawdown), 2),
            "volatility":   round(float(volatility), 4),
            "best_year":    best_year,
            "worst_year":   worst_year,
            "best_yoy":     round(float(max(yoy)), 2) if yoy else 0,
            "worst_yoy":    round(float(min(yoy)), 2) if yoy else 0,
            "verdict":      verdict,
            "risk":         risk,
            "advice":       advice,
        })
    return insights


def compute_rsi(prices, period=14):
    """Compute RSI for a price series."""
    delta  = prices.diff()
    gain   = delta.clip(lower=0)
    loss   = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(round(rsi.iloc[-1], 2)) if not rsi.empty else None


def compute_max_drawdown(prices):
    """Compute maximum drawdown percentage."""
    roll_max   = prices.cummax()
    drawdown   = (prices - roll_max) / roll_max * 100
    return float(round(drawdown.min(), 2))


# ── Existing routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception:
        return jsonify({"message": "Flask is running. Add templates/index.html for the UI."}), 200


@app.route("/api/prices")
def api_prices():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch price data"}), 500
        result = {}
        for ticker in COINS:
            d = df[df["ticker"] == ticker].sort_values("timestamp")
            result[ticker] = {
                "dates":  d["timestamp"].dt.strftime("%Y-%m-%d").tolist(),
                "prices": [round(float(p), 2) for p in d["price"].tolist()],
                "name":   COINS[ticker],
                "color":  COLORS[ticker],
            }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/yearly")
def api_yearly():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch yearly data"}), 500
        result = {}
        for ticker in COINS:
            d      = df[df["ticker"] == ticker]
            yearly = d.groupby("year")["price"].agg(
                avg="mean", high="max", low="min"
            ).reset_index()
            result[ticker] = {
                "name":  COINS[ticker],
                "color": COLORS[ticker],
                "years": yearly["year"].tolist(),
                "avg":   [round(float(v), 2) for v in yearly["avg"].tolist()],
                "high":  [round(float(v), 2) for v in yearly["high"].tolist()],
                "low":   [round(float(v), 2) for v in yearly["low"].tolist()],
            }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/insights")
def api_insights():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch insight data"}), 500
        return jsonify(compute_insights(df))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/live")
def api_live():
    result = []
    for ticker, name in COINS.items():
        try:
            t    = yf.Ticker(ticker)
            info = t.fast_info
            result.append({
                "ticker": ticker,
                "name":   name,
                "color":  COLORS[ticker],
                "price":  round(float(info.last_price), 2),
                "high24": round(float(info.day_high), 2),
                "low24":  round(float(info.day_low), 2),
                "change": round(float(
                    (info.last_price - info.previous_close)
                    / info.previous_close * 100
                ), 2),
            })
        except Exception as e:
            result.append({
                "ticker": ticker,
                "name":   name,
                "color":  COLORS[ticker],
                "error":  str(e)
            })
    return jsonify(result)


# ── New routes ────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({
        "status":    "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_age": round(time.time() - _cache["timestamp"], 1)
                     if _cache["timestamp"] else None
    })


@app.route("/api/sentiment")
def api_sentiment():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        sentiments = []
        for ticker, name in COINS.items():
            d      = df[df["ticker"] == ticker].sort_values("timestamp")
            prices = d["price"]

            if len(prices) < 30:
                continue

            total_growth = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] * 100
            volatility   = float(prices.pct_change().std() * 100)
            ath          = prices.max()
            drawdown     = float((ath - prices.iloc[-1]) / ath * 100)

            yearly     = d.groupby("year")["price"].mean()
            avgs       = yearly.values
            yoy_list   = [(avgs[i] - avgs[i-1]) / avgs[i-1] * 100
                          for i in range(1, len(avgs))]
            recent_yoy = yoy_list[-1] if yoy_list else 0

            # Score 0–100
            growth_score     = min(max(total_growth / 10, 0), 40)
            volatility_score = max(20 - volatility * 2, 0)
            drawdown_score   = max(20 - drawdown / 2, 0)
            yoy_score        = min(max(recent_yoy / 5, 0), 20)
            confidence       = round(growth_score + volatility_score +
                                     drawdown_score + yoy_score, 1)

            if confidence >= 70:
                sentiment    = "Bullish"
                risk_level   = "Medium"
                explanation  = (f"{name} shows strong growth of {total_growth:.1f}% "
                                f"with manageable volatility. Positive momentum detected.")
            elif confidence >= 45:
                sentiment    = "Neutral"
                risk_level   = "Medium-High"
                explanation  = (f"{name} shows mixed signals. Growth is present but "
                                f"volatility of {volatility:.2f}% suggests caution.")
            elif confidence >= 25:
                sentiment    = "Bearish"
                risk_level   = "High"
                explanation  = (f"{name} is under pressure with {drawdown:.1f}% drawdown "
                                f"from peak. Risk-averse traders should wait.")
            else:
                sentiment    = "Very Bearish"
                risk_level   = "Very High"
                explanation  = (f"{name} is showing severe weakness. High volatility "
                                f"and large drawdown suggest significant risk.")

            sentiments.append({
                "ticker":           ticker,
                "name":             name,
                "color":            COLORS[ticker],
                "sentiment":        sentiment,
                "risk_level":       risk_level,
                "confidence_score": confidence,
                "total_growth_pct": round(float(total_growth), 2),
                "volatility_pct":   round(volatility, 4),
                "drawdown_pct":     round(drawdown, 2),
                "recent_yoy_pct":   round(float(recent_yoy), 2),
                "explanation":      explanation,
            })

        return jsonify(sentiments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/risk")
def api_risk():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        result = []
        for ticker, name in COINS.items():
            d      = df[df["ticker"] == ticker].sort_values("timestamp")
            prices = d["price"]

            if len(prices) < 2:
                continue

            volatility   = float(prices.pct_change().std() * 100)
            max_dd       = compute_max_drawdown(prices)
            total_growth = float((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] * 100)

            # Risk score 0–100 (higher = riskier)
            vol_score = min(volatility * 5, 50)
            dd_score  = min(abs(max_dd) / 2, 40)
            gr_score  = max(10 - total_growth / 100, 0)
            risk_score = round(vol_score + dd_score + gr_score, 1)

            if risk_score >= 75:
                category = "Extreme"
            elif risk_score >= 55:
                category = "High"
            elif risk_score >= 35:
                category = "Medium"
            else:
                category = "Low"

            result.append({
                "ticker":       ticker,
                "name":         name,
                "color":        COLORS[ticker],
                "volatility":   round(volatility, 4),
                "max_drawdown": round(max_dd, 2),
                "risk_score":   risk_score,
                "risk_category": category,
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/indicators/<ticker>")
def api_indicators(ticker):
    try:
        ticker = ticker.upper()
        if ticker not in COINS:
            return jsonify({"error": f"Unknown ticker {ticker}. Use BTC-USD, ETH-USD or SOL-USD"}), 400

        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        d      = df[df["ticker"] == ticker].sort_values("timestamp")
        prices = d["price"].reset_index(drop=True)

        if len(prices) < 200:
            return jsonify({"error": "Not enough data for indicators"}), 400

        rsi    = compute_rsi(prices)
        ma50   = float(round(prices.rolling(50).mean().iloc[-1], 2))
        ma200  = float(round(prices.rolling(200).mean().iloc[-1], 2))
        current = float(round(prices.iloc[-1], 2))

        # Signal
        if current > ma50 > ma200:
            signal = "Strong Uptrend — price above both MAs"
        elif current > ma200:
            signal = "Moderate Uptrend — price above 200-day MA"
        elif current < ma50 < ma200:
            signal = "Strong Downtrend — price below both MAs"
        else:
            signal = "Mixed — watch for crossover"

        rsi_signal = (
            "Overbought — consider taking profit" if rsi and rsi > 70
            else "Oversold — potential buy opportunity" if rsi and rsi < 30
            else "Neutral RSI"
        )

        return jsonify({
            "ticker":       ticker,
            "name":         COINS[ticker],
            "current_price": current,
            "rsi":          rsi,
            "rsi_signal":   rsi_signal,
            "ma_50":        ma50,
            "ma_200":       ma200,
            "ma_signal":    signal,
            "above_ma50":   current > ma50,
            "above_ma200":  current > ma200,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio", methods=["POST"])
def api_portfolio():
    try:
        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "Send JSON body e.g. {\"BTC-USD\": 0.5}"}), 400

        # Validate tickers
        invalid = [t for t in body if t not in COINS]
        if invalid:
            return jsonify({"error": f"Unknown tickers: {invalid}"}), 400

        live_prices = {}
        changes     = {}
        for ticker in body:
            try:
                info = yf.Ticker(ticker).fast_info
                live_prices[ticker] = float(info.last_price)
                changes[ticker]     = float(
                    (info.last_price - info.previous_close)
                    / info.previous_close * 100
                )
            except Exception as e:
                return jsonify({"error": f"Could not fetch price for {ticker}: {e}"}), 500

        allocation   = {}
        total_value  = 0.0
        for ticker, qty in body.items():
            val = float(qty) * live_prices[ticker]
            allocation[ticker] = {
                "name":       COINS[ticker],
                "quantity":   float(qty),
                "price":      round(live_prices[ticker], 2),
                "value":      round(val, 2),
                "change_pct": round(changes[ticker], 2),
            }
            total_value += val

        for ticker in allocation:
            allocation[ticker]["weight_pct"] = round(
                allocation[ticker]["value"] / total_value * 100, 2
            )

        best_asset  = max(allocation, key=lambda t: changes[t])
        worst_asset = min(allocation, key=lambda t: changes[t])

        weighted_change = sum(
            changes[t] * allocation[t]["value"] / total_value
            for t in allocation
        )

        return jsonify({
            "total_value":       round(total_value, 2),
            "portfolio_change_pct": round(weighted_change, 2),
            "best_asset":        {"ticker": best_asset,  "name": COINS[best_asset],  "change_pct": round(changes[best_asset], 2)},
            "worst_asset":       {"ticker": worst_asset, "name": COINS[worst_asset], "change_pct": round(changes[worst_asset], 2)},
            "allocation":        allocation,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/correlation")
def api_correlation():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        pivot = df.pivot_table(index="timestamp", columns="ticker", values="price")
        pivot = pivot.dropna()

        if pivot.empty:
            return jsonify({"error": "Not enough overlapping data"}), 500

        corr   = pivot.pct_change().dropna().corr().round(4)
        tickers = list(corr.columns)

        matrix = []
        for t1 in tickers:
            row = {}
            for t2 in tickers:
                row[t2] = float(corr.loc[t1, t2])
            matrix.append({"ticker": t1, "name": COINS.get(t1, t1), "correlations": row})

        interpretation = []
        pairs = [(tickers[i], tickers[j])
                 for i in range(len(tickers))
                 for j in range(i+1, len(tickers))]
        for t1, t2 in pairs:
            val = float(corr.loc[t1, t2])
            if val > 0.8:
                label = "Very High — move almost in lockstep"
            elif val > 0.6:
                label = "High — strong co-movement"
            elif val > 0.4:
                label = "Moderate — partial co-movement"
            else:
                label = "Low — relatively independent"
            interpretation.append({
                "pair":  f"{t1} / {t2}",
                "value": round(val, 4),
                "label": label
            })

        return jsonify({
            "matrix":         matrix,
            "interpretation": interpretation
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/market-summary")
def api_market_summary():
    try:
        df = fetch_data()
        if df is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        stats = {}
        for ticker, name in COINS.items():
            d      = df[df["ticker"] == ticker].sort_values("timestamp")
            prices = d["price"]
            if len(prices) < 2:
                continue
            stats[ticker] = {
                "name":         name,
                "total_growth": float((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] * 100),
                "volatility":   float(prices.pct_change().std() * 100),
                "current":      float(prices.iloc[-1]),
            }

        if not stats:
            return jsonify({"error": "No stats available"}), 500

        best_performer  = max(stats, key=lambda t: stats[t]["total_growth"])
        worst_performer = min(stats, key=lambda t: stats[t]["total_growth"])
        most_volatile   = max(stats, key=lambda t: stats[t]["volatility"])

        avg_growth = sum(s["total_growth"] for s in stats.values()) / len(stats)
        avg_vol    = sum(s["volatility"]   for s in stats.values()) / len(stats)

        if avg_growth > 100 and avg_vol < 5:
            condition = "Bull Market — strong growth, controlled risk"
        elif avg_growth > 50:
            condition = "Cautious Bull — growth present but volatile"
        elif avg_growth > 0:
            condition = "Sideways — low momentum, wait for breakout"
        else:
            condition = "Bear Market — negative trend across assets"

        return jsonify({
            "best_performer": {
                "ticker":     best_performer,
                "name":       stats[best_performer]["name"],
                "growth_pct": round(stats[best_performer]["total_growth"], 2),
            },
            "worst_performer": {
                "ticker":     worst_performer,
                "name":       stats[worst_performer]["name"],
                "growth_pct": round(stats[worst_performer]["total_growth"], 2),
            },
            "most_volatile": {
                "ticker":         most_volatile,
                "name":           stats[most_volatile]["name"],
                "volatility_pct": round(stats[most_volatile]["volatility"], 4),
            },
            "market_condition":  condition,
            "avg_growth_pct":    round(avg_growth, 2),
            "avg_volatility_pct": round(avg_vol, 4),
            "generated_at":      datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)