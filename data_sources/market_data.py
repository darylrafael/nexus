from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo
import requests
import yfinance as yf


JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

COMMODITY_TICKERS = {
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
}

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def jakarta_now() -> datetime:
    return datetime.now(JAKARTA_TZ)


def _pct_change(latest: float, previous: float | None) -> float:
    return ((latest - previous) / previous * 100) if previous else 0.0


def fetch_ihsg_snapshot(period: str = "5d", target_date: str = None) -> dict[str, Any]:
    """
    Fetch IHSG snapshot.
    Supports targeting a specific historical session date (YYYY-MM-DD).
    1. Tries Yahoo Finance direct chart API with browser user-agent (avoids yfinance 429).
    2. Falls back to yfinance library.
    3. Falls back to Tavily web search.
    """
    # 1. Direct Yahoo Finance Chart API
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/^JKSE?interval=1d&range=10d"
        res = requests.get(url, headers=_BROWSER_HEADERS, timeout=8)
        if res.status_code == 200:
            result = res.json().get("chart", {}).get("result", [])
            if result:
                d = result[0]
                timestamps = d.get("timestamp", [])
                quotes = d.get("indicators", {}).get("quote", [{}])[0]
                closes = quotes.get("close", [])
                
                if timestamps and closes:
                    candle_dates = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") for ts in timestamps]
                    
                    target_idx = None
                    if target_date and target_date in candle_dates:
                        target_idx = candle_dates.index(target_date)
                    else:
                        # Pick latest candle with non-null close
                        for i in range(len(timestamps) - 1, -1, -1):
                            if i < len(closes) and closes[i] is not None:
                                target_idx = i
                                break

                    if target_idx is not None and closes[target_idx] is not None:
                        close = float(closes[target_idx])
                        prev_idx = target_idx - 1 if target_idx > 0 else None
                        prev_close = float(closes[prev_idx]) if prev_idx is not None and closes[prev_idx] is not None else None
                        pct = _pct_change(close, prev_close)
                        pts = (close - prev_close) if prev_close is not None else 0.0
                        
                        open_vals = quotes.get("open", [])
                        high_vals = quotes.get("high", [])
                        low_vals = quotes.get("low", [])
                        vol_vals = quotes.get("volume", [])
                        
                        open_val = float(open_vals[target_idx] if target_idx < len(open_vals) and open_vals[target_idx] is not None else close)
                        high_val = float(high_vals[target_idx] if target_idx < len(high_vals) and high_vals[target_idx] is not None else close)
                        low_val = float(low_vals[target_idx] if target_idx < len(low_vals) and low_vals[target_idx] is not None else close)
                        vol_val = int(vol_vals[target_idx] if target_idx < len(vol_vals) and vol_vals[target_idx] is not None else 0)

                        return {
                            "ihsg_close": round(close, 2),
                            "ihsg_prev": round(prev_close, 2) if prev_close is not None else None,
                            "ihsg_change_pct": round(pct, 2),
                            "ihsg_change_pts": round(pts, 2),
                            "ihsg_signal": "Bullish" if pct > 0.2 else ("Bearish" if pct < -0.2 else "Neutral"),
                            "ihsg_open": round(open_val, 2),
                            "ihsg_high": round(high_val, 2),
                            "ihsg_low": round(low_val, 2),
                            "ihsg_volume": vol_val,
                            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                            "source": "yahoo_direct:^JKSE",
                        }
    except Exception as e:
        print(f"  [fetch_ihsg_snapshot] Direct Yahoo query error: {e}")

    # 2. yfinance library
    try:
        ihsg = yf.Ticker("^JKSE")
        hist = ihsg.history(period=period)
        if len(hist) >= 1:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else None
            close = float(latest["Close"])
            prev_close = float(prev["Close"]) if prev is not None else None
            pct = _pct_change(close, prev_close)
            pts = close - prev_close if prev_close is not None else 0.0

            return {
                "ihsg_close": round(close, 2),
                "ihsg_prev": round(prev_close, 2) if prev_close is not None else None,
                "ihsg_change_pct": round(pct, 2),
                "ihsg_change_pts": round(pts, 2),
                "ihsg_signal": "Bullish" if pct > 0.2 else ("Bearish" if pct < -0.2 else "Neutral"),
                "ihsg_open": round(float(latest["Open"]), 2),
                "ihsg_high": round(float(latest["High"]), 2),
                "ihsg_low": round(float(latest["Low"]), 2),
                "ihsg_volume": int(latest["Volume"]),
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                "source": "yfinance:^JKSE",
            }
    except Exception as e:
        print(f"  [fetch_ihsg_snapshot] yfinance error: {e}")

    # 3. Web Search Fallback
    try:
        from agents.web_agent import search_web
        import re
        search_date = target_date or jakarta_now().strftime("%d %B %Y")
        text = search_web(f"penutupan IHSG {search_date} level persen", days=3)
        close_match = re.search(r"level\s+([0-9.,]+)", text)
        pct_match = re.search(r"(turun|melemah|menguat|naik)\s+([0-9.,]+)%", text, re.IGNORECASE)
        close = None
        pct = 0.0
        signal = "Neutral"
        if close_match:
            try:
                raw_close = close_match.group(1).replace(".", "").replace(",", ".")
                close = float(raw_close)
            except Exception:
                pass
        if pct_match:
            try:
                direction_word = pct_match.group(1).lower()
                val = float(pct_match.group(2).replace(",", "."))
                if direction_word in ("turun", "melemah"):
                    pct = -val
                    signal = "Bearish"
                else:
                    pct = val
                    signal = "Bullish"
            except Exception:
                pass
        if close:
            return {
                "ihsg_close": round(close, 2),
                "ihsg_prev": None,
                "ihsg_change_pct": round(pct, 2),
                "ihsg_change_pts": 0.0,
                "ihsg_signal": signal,
                "ihsg_open": round(close, 2),
                "ihsg_high": round(close, 2),
                "ihsg_low": round(close, 2),
                "ihsg_volume": 0,
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                "source": "web_fallback:tavily",
            }
    except Exception as e:
        print(f"  [fetch_ihsg_snapshot] web fallback error: {e}")

    return {"ihsg_signal": "Unknown", "error": "IHSG data unavailable across all sources."}


def format_ihsg_snapshot(data: dict[str, Any]) -> str:
    if data.get("error"):
        return data["error"]

    change = data.get("ihsg_change_pct", 0)
    direction = "UP" if change > 0 else "DOWN"
    return (
        f"IHSG Close: {data['ihsg_close']:,.2f} {direction} {abs(change):.2f}%\n"
        f"Open: {data['ihsg_open']:,.2f} | "
        f"High: {data['ihsg_high']:,.2f} | "
        f"Low: {data['ihsg_low']:,.2f}"
    )


def fetch_usdidr_snapshot() -> dict[str, Any]:
    """
    Fetch USD/IDR exchange rate.
    Tries direct Yahoo endpoint first, falls back to yfinance, then web search.
    """
    # 1. Direct Yahoo endpoint
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/USDIDR=X?interval=1d&range=5d"
        res = requests.get(url, headers=_BROWSER_HEADERS, timeout=8)
        if res.status_code == 200:
            result = res.json().get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                rate = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
                prev_rate = meta.get("chartPreviousClose") or meta.get("previousClose")
                if rate:
                    rate = float(rate)
                    prev_rate = float(prev_rate) if prev_rate else None
                    pct = _pct_change(rate, prev_rate)
                    return {
                        "usdidr": round(rate, 0),
                        "usdidr_change_pct": round(pct, 3),
                        "rupiah_signal": "Weakened" if pct > 0 else "Strengthened",
                        "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                        "source": "yahoo_direct:USDIDR=X",
                    }
    except Exception as e:
        print(f"  [fetch_usdidr_snapshot] Direct Yahoo query error: {e}")

    # 2. yfinance library
    try:
        idr = yf.Ticker("USDIDR=X")
        fast_info = idr.fast_info
        rate = float(fast_info.last_price)
        prev_rate = float(fast_info.previous_close) if fast_info.previous_close else None
        pct = _pct_change(rate, prev_rate)
        return {
            "usdidr": round(rate, 0),
            "usdidr_change_pct": round(pct, 3),
            "rupiah_signal": "Weakened" if pct > 0 else "Strengthened",
            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            "source": "yfinance:USDIDR=X",
        }
    except Exception as e:
        print(f"  [fetch_usdidr_snapshot] yfinance error: {e}")

    # 3. Web search fallback
    try:
        from agents.web_agent import search_web
        import re
        today_id = jakarta_now().strftime("%d %B %Y")
        text = search_web(f"kurs rupiah dolar AS hari ini {today_id}", days=2)
        match = re.search(r"Rp\s*([0-9.,]+)", text)
        rate = 17950.0
        if match:
            try:
                rate = float(match.group(1).replace(".", "").replace(",", "."))
            except Exception:
                pass
        return {
            "usdidr": round(rate, 0),
            "usdidr_change_pct": 0.0,
            "rupiah_signal": "Weakened" if rate > 17500 else "Strengthened",
            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            "source": "web_fallback:USDIDR",
        }
    except Exception:
        return {
            "usdidr": 17950.0,
            "usdidr_change_pct": 0.0,
            "rupiah_signal": "Neutral",
            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            "source": "fallback:default",
        }


def fetch_yfinance_commodity(name: str, ticker: str) -> dict[str, Any]:
    """
    Fetch commodity price via direct Yahoo chart API first, falling back to yfinance.
    """
    # 1. Direct Yahoo endpoint
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        res = requests.get(url, headers=_BROWSER_HEADERS, timeout=8)
        if res.status_code == 200:
            result = res.json().get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                price = meta.get("regularMarketPrice")
                prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                if price is not None:
                    price = float(price)
                    prev = float(prev) if prev is not None else None
                    pct = _pct_change(price, prev)
                    return {
                        "name": name,
                        "ticker": ticker,
                        "price": round(price, 2),
                        "previous_close": round(prev, 2) if prev is not None else None,
                        "change_pct": round(pct, 2),
                        "signal": "Up" if pct > 0 else "Down",
                        "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                        "source": f"yahoo_direct:{ticker}",
                    }
    except Exception:
        pass

    # 2. yfinance library
    try:
        data = yf.Ticker(ticker)
        fast_info = data.fast_info
        price = float(fast_info.last_price)
        previous = float(fast_info.previous_close) if fast_info.previous_close else None
        pct = _pct_change(price, previous)
        return {
            "name": name,
            "ticker": ticker,
            "price": round(price, 2),
            "previous_close": round(previous, 2) if previous is not None else None,
            "change_pct": round(pct, 2),
            "signal": "Up" if pct > 0 else "Down",
            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            "source": f"yfinance:{ticker}",
        }
    except Exception:
        return {
            "name": name,
            "ticker": ticker,
            "price": 0.0,
            "previous_close": 0.0,
            "change_pct": 0.0,
            "signal": "Neutral",
            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            "source": f"fallback:{ticker}",
        }


def fetch_yfinance_commodities(
    tickers: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    tickers = tickers or COMMODITY_TICKERS
    snapshots = {}
    for name, ticker in tickers.items():
        snapshots[name] = fetch_yfinance_commodity(name, ticker)
    return snapshots


def format_commodity_snapshot(data: dict[str, Any]) -> str:
    change = data.get("change_pct", 0)
    direction = "UP" if change > 0 else "DOWN"
    price = data.get("price", "N/A")
    if isinstance(price, float):
        price = f"{price:,.2f}"
    return f"- **{data.get('name', 'Commodity')}**: {price} {direction} {abs(change):.2f}%"
