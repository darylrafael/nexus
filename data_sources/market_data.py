from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo
import requests
import yfinance as yf


JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

INDONESIAN_MONTHS = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

INDONESIAN_DAYS = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu"
}

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


def _format_date_id(d: datetime | date) -> str:
    return f"{d.day} {INDONESIAN_MONTHS[d.month]} {d.year}"


def _format_label_id(d: datetime | date) -> str:
    return f"{INDONESIAN_DAYS[d.weekday()]}, {d.day} {INDONESIAN_MONTHS[d.month]} {d.year}"


def get_market_calendar_info(ref_dt: datetime | None = None) -> dict[str, Any]:
    """
    Determine the last active IDX trading session date and the dynamic date window
    for pre-market morning brief. Handles weekends (e.g. Monday briefs) and public
    holidays (tanggal merah/cuti bersama).

    3-Tier resolution:
    1. Yahoo Finance ^JKSE daily candles (reflects exact IDX trading days).
    2. Local historical artifacts in runs/.
    3. Calendar weekday calculation fallback (Senin -> Jumat).
    """
    if ref_dt is None:
        ref_dt = jakarta_now()
    today_date = ref_dt.date()
    today_key = today_date.strftime("%Y-%m-%d")

    last_trading_key: str | None = None

    # Tier 1: Query Yahoo Finance JKSE chart candles strictly prior to today
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/^JKSE?interval=1d&range=15d"
        res = requests.get(url, headers=_BROWSER_HEADERS, timeout=6)
        if res.status_code == 200:
            result = res.json().get("chart", {}).get("result", [])
            if result:
                timestamps = result[0].get("timestamp", [])
                quotes = result[0].get("indicators", {}).get("quote", [{}])[0]
                closes = quotes.get("close", [])
                past_candles = []
                for i, ts in enumerate(timestamps):
                    c_date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    if c_date < today_key and i < len(closes) and closes[i] is not None:
                        past_candles.append(c_date)
                if past_candles:
                    last_trading_key = past_candles[-1]
    except Exception as e:
        print(f"  [get_market_calendar_info] Yahoo candle query warning: {e}")

    # Tier 2: Check local runs directory for prior sessions
    if not last_trading_key:
        try:
            runs_dir = Path(__file__).resolve().parent.parent / "runs"
            if runs_dir.exists():
                candidate_dirs = sorted(
                    [d.name for d in runs_dir.iterdir() if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name) and d.name < today_key],
                    reverse=True
                )
                if candidate_dirs:
                    last_trading_key = candidate_dirs[0]
        except Exception:
            pass

    # Tier 3: Calendar weekday math fallback
    if not last_trading_key:
        w = ref_dt.weekday()
        if w == 0:  # Monday -> Friday (3 days ago)
            fallback_date = today_date - timedelta(days=3)
        elif w == 6:  # Sunday -> Friday (2 days ago)
            fallback_date = today_date - timedelta(days=2)
        elif w == 5:  # Saturday -> Friday (1 day ago)
            fallback_date = today_date - timedelta(days=1)
        else:  # Tuesday-Friday -> 1 day ago
            fallback_date = today_date - timedelta(days=1)
        last_trading_key = fallback_date.strftime("%Y-%m-%d")

    last_trading_dt = datetime.strptime(last_trading_key, "%Y-%m-%d").date()
    days_gap = (today_date - last_trading_dt).days
    if days_gap <= 0:
        days_gap = 1
    search_days = max(days_gap + 1, 2)
    is_after_gap = days_gap > 1

    last_en = last_trading_dt.strftime("%B %d, %Y")
    today_en = today_date.strftime("%B %d, %Y")

    return {
        "today_key": today_key,
        "today_date_id": _format_date_id(today_date),
        "today_label": _format_label_id(today_date),
        "today_en": today_en,
        "today_day_name_id": INDONESIAN_DAYS[today_date.weekday()],
        "last_trading_key": last_trading_key,
        "last_trading_date_id": _format_date_id(last_trading_dt),
        "last_trading_label": _format_label_id(last_trading_dt),
        "last_trading_en": last_en,
        "last_trading_day_name_id": INDONESIAN_DAYS[last_trading_dt.weekday()],
        "days_gap": days_gap,
        "search_days": search_days,
        "is_after_gap": is_after_gap,
        "period_description_id": (
            f"{_format_label_id(last_trading_dt)} hingga {_format_label_id(today_date)}"
            if is_after_gap
            else _format_label_id(last_trading_dt)
        ),
        "period_description_en": (
            f"{last_en} through {today_en}"
            if is_after_gap
            else last_en
        ),
    }


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
