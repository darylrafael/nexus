from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo
import requests
import yfinance as yf
from utils.direction import classify_direction
from core.time import JAKARTA_TZ, jakarta_now

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
        url = "https://query1.finance.yahoo.com/v8/finance/chart/^JKSE?interval=1d&range=15d"
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
                    if target_date:
                        if target_date in candle_dates:
                            target_idx = candle_dates.index(target_date)
                            assert candle_dates[target_idx] == target_date, f"Index date mismatch: {candle_dates[target_idx]} != {target_date}"
                        else:
                            # CRITICAL: DO NOT fall back to latest candle when target_date is not present
                            raise ValueError(f"no candle for {target_date}")
                    else:
                        # Pick latest candle with non-null close
                        # Exclude today's incomplete candle if current time is before market close (16:00 WIB)
                        now_jkt = jakarta_now()
                        today_key = now_jkt.strftime("%Y-%m-%d")
                        market_closed = now_jkt.hour >= 16

                        for i in range(len(timestamps) - 1, -1, -1):
                            c_date = candle_dates[i]
                            if not market_closed and c_date >= today_key:
                                continue
                            if i < len(closes) and closes[i] is not None:
                                target_idx = i
                                break

                    if target_idx is not None and closes[target_idx] is not None:
                        close = float(closes[target_idx])
                        # Walk backwards to nearest prior non-null close
                        prev_close = None
                        for p in range(target_idx - 1, -1, -1):
                            if p < len(closes) and closes[p] is not None:
                                prev_close = float(closes[p])
                                break

                        if prev_close is not None:
                            pct = _pct_change(close, prev_close)
                            pts = close - prev_close
                            signal = classify_direction(pct)
                        else:
                            pct = None
                            pts = None
                            signal = "Unscorable"

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
                            "ihsg_change_pct": round(pct, 2) if pct is not None else None,
                            "ihsg_change_pts": round(pts, 2) if pts is not None else None,
                            "ihsg_signal": signal,
                            "ihsg_open": round(open_val, 2),
                            "ihsg_high": round(high_val, 2),
                            "ihsg_low": round(low_val, 2),
                            "ihsg_volume": vol_val,
                            "candle_date": candle_dates[target_idx],
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
            hist_dates = [idx.strftime("%Y-%m-%d") for idx in hist.index]
            target_idx = None
            if target_date:
                if target_date in hist_dates:
                    target_idx = hist_dates.index(target_date)
                    assert hist_dates[target_idx] == target_date, f"Index date mismatch: {hist_dates[target_idx]} != {target_date}"
                else:
                    raise ValueError(f"no candle for {target_date} in yfinance")
            else:
                now_jkt = jakarta_now()
                today_key = now_jkt.strftime("%Y-%m-%d")
                market_closed = now_jkt.hour >= 16

                for i in range(len(hist) - 1, -1, -1):
                    if not market_closed and hist_dates[i] >= today_key:
                        continue
                    target_idx = i
                    break

            if target_idx is not None:
                latest = hist.iloc[target_idx]
                close = float(latest["Close"])
                prev_close = None
                for p in range(target_idx - 1, -1, -1):
                    val = hist.iloc[p]["Close"]
                    if val is not None and not (isinstance(val, float) and (val != val)):
                        prev_close = float(val)
                        break

                if prev_close is not None:
                    pct = _pct_change(close, prev_close)
                    pts = close - prev_close
                    signal = classify_direction(pct)
                else:
                    pct = None
                    pts = None
                    signal = "Unscorable"

                return {
                    "ihsg_close": round(close, 2),
                    "ihsg_prev": round(prev_close, 2) if prev_close is not None else None,
                    "ihsg_change_pct": round(pct, 2) if pct is not None else None,
                    "ihsg_change_pts": round(pts, 2) if pts is not None else None,
                    "ihsg_signal": signal,
                    "ihsg_open": round(float(latest["Open"]), 2),
                    "ihsg_high": round(float(latest["High"]), 2),
                    "ihsg_low": round(float(latest["Low"]), 2),
                    "ihsg_volume": int(latest["Volume"]),
                    "candle_date": hist_dates[target_idx],
                    "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                    "source": "yfinance:^JKSE",
                }
    except Exception as e:
        print(f"  [fetch_ihsg_snapshot] yfinance error: {e}")
        if target_date and "no candle for" in str(e):
            raise ValueError(f"market data does not contain requested target date candle {target_date}") from e

    if target_date:
        raise ValueError(f"market data does not contain requested target date candle {target_date}")

    # 3. Web Search Fallback
    try:
        from agents.web_agent import search_web
        import re
        search_date = target_date or jakarta_now().strftime("%d %B %Y")
        text = search_web(f"penutupan IHSG {search_date} level persen", days=3)
        close_match = re.search(r"level\s+([0-9.,]+)", text)
        pct_match = re.search(r"(turun|melemah|menguat|naik)\s+([0-9.,]+)%", text, re.IGNORECASE)
        close = None
        pct = None
        signal = "Unknown"
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
                pct = -val if direction_word in ("turun", "melemah") else val
                signal = classify_direction(pct)
            except Exception:
                pass
        if close:
            return {
                "ihsg_close": round(close, 2),
                "ihsg_prev": None,
                "ihsg_change_pct": round(pct, 2) if pct is not None else None,
                "ihsg_change_pts": None,
                "ihsg_signal": signal,
                "ihsg_open": round(close, 2),
                "ihsg_high": round(close, 2),
                "ihsg_low": round(close, 2),
                "ihsg_volume": 0,
                "candle_date": target_date or jakarta_now().strftime("%Y-%m-%d"),
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                "source": "web_fallback",
                "confidence": "low",
            }
    except Exception as e:
        print(f"  [fetch_ihsg_snapshot] web fallback error: {e}")

    return {
        "ihsg_close": None,
        "ihsg_prev": None,
        "ihsg_change_pct": None,
        "ihsg_change_pts": None,
        "ihsg_signal": "Unknown",
        "candle_date": target_date,
        "error": f"no candle for {target_date}" if target_date else "IHSG data unavailable across all sources.",
        "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
        "source": "unavailable",
    }


def format_ihsg_snapshot(data: dict[str, Any]) -> str:
    if not data or data.get("error") or data.get("ihsg_close") is None:
        return data.get("error") or "IHSG data unavailable"

    close_val = data["ihsg_close"]
    close_str = f"{close_val:,.2f}" if isinstance(close_val, (int, float)) else str(close_val)

    change = data.get("ihsg_change_pct")
    if change is None:
        change_str = "change unavailable"
    else:
        direction = "UP" if change > 0 else "DOWN"
        change_str = f"{direction} {abs(change):.2f}%"

    open_val = f"{data['ihsg_open']:,.2f}" if isinstance(data.get("ihsg_open"), (int, float)) else "unavailable"
    high_val = f"{data['ihsg_high']:,.2f}" if isinstance(data.get("ihsg_high"), (int, float)) else "unavailable"
    low_val = f"{data['ihsg_low']:,.2f}" if isinstance(data.get("ihsg_low"), (int, float)) else "unavailable"

    source_badge = " [web_fallback - low confidence]" if (data.get("source") == "web_fallback" or data.get("confidence") == "low") else ""

    return (
        f"IHSG Close: {close_str} {change_str}{source_badge}\n"
        f"Open: {open_val} | "
        f"High: {high_val} | "
        f"Low: {low_val}"
    )


def fetch_usdidr_snapshot() -> dict[str, Any]:
    """Fetch USD/IDR exchange rate.

    Tries direct Yahoo endpoint first, falls back to yfinance, then web
    search.
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
        if match:
            try:
                rate = float(match.group(1).replace(".", "").replace(",", "."))
                return {
                    "usdidr": round(rate, 0),
                    "usdidr_change_pct": None,
                    "rupiah_signal": "Unknown",
                    "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                    "source": "web_fallback",
                    "confidence": "low",
                }
            except Exception:
                pass
    except Exception as e:
        print(f"  [fetch_usdidr_snapshot] web fallback error: {e}")

    return {
        "usdidr": None,
        "usdidr_change_pct": None,
        "rupiah_signal": "Unavailable",
        "error": "USD/IDR data unavailable across all sources.",
        "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
        "source": "unavailable",
    }


def fetch_yfinance_commodity(name: str, ticker: str) -> dict[str, Any]:
    """Fetch commodity price via direct Yahoo chart API first, falling back to

    yfinance.
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
    except Exception as e:
        return {
            "name": name,
            "ticker": ticker,
            "price": None,
            "previous_close": None,
            "change_pct": None,
            "signal": "Unavailable",
            "error": f"Price unavailable for {ticker}: {e}",
            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            "source": f"error:{ticker}",
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
    name = data.get("name", "Commodity")
    price = data.get("price")
    if price is None:
        return f"- **{name}**: unavailable"

    price_str = f"{price:,.2f}" if isinstance(price, (int, float)) else str(price)
    change = data.get("change_pct")
    if change is None:
        return f"- **{name}**: {price_str} (change unavailable)"

    direction = "UP" if change > 0 else "DOWN"
    return f"- **{name}**: {price_str} {direction} {abs(change):.2f}%"


def _parse_commodity_web_summary(name: str, raw_text: str, source_ids: list[str]) -> dict[str, Any]:
    """Parse numeric price and change percentage from web search snippets if available."""
    price = None
    change_pct = None
    signal = "Unavailable"

    if raw_text and not raw_text.startswith("Data unavailable:"):
        # Match percentage: e.g. +2.5%, -1.2%, 0.8%
        pct_match = re.search(r"([+-]?[0-9]+(?:\.[0-9]+)?)\s*%", raw_text)
        if pct_match:
            try:
                change_pct = float(pct_match.group(1))
                signal = "Up" if change_pct > 0 else ("Down" if change_pct < 0 else "Flat")
            except ValueError:
                pass

        # Match dollar or local currency price: e.g. $142.50 or 4,250 MYR
        price_match = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", raw_text)
        if price_match:
            try:
                price = float(price_match.group(1))
            except ValueError:
                pass
        else:
            alt_price = re.search(r"([0-9]{2,5}(?:\.[0-9]+)?)\s*(?:USD|MYR|USD/t)", raw_text, re.IGNORECASE)
            if alt_price:
                try:
                    price = float(alt_price.group(1).replace(",", ""))
                except ValueError:
                    pass

    return {
        "name": name,
        "ticker": "WEB_SEARCH",
        "price": price,
        "change_pct": change_pct,
        "signal": signal,
        "source": "tavily_web",
        "raw": raw_text,
        "source_ids": source_ids,
        "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
    }


def fetch_all_commodities(
    target_label: str | None = None,
    search_days: int = 1,
) -> dict[str, Any]:
    """
    Centralized commodity fetching across both yfinance (tickers) and web search (Coal/CPO/Nickel).
    Used by both morning brief (market_agent / commodity_agent) and evening review.
    Eliminates redundant dual queries and ensures uniform economic indicators.
    """
    from data_sources.news import search_text_with_sources

    now_str = jakarta_now().strftime("%B %d, %Y")
    label = target_label or now_str

    yfinance_data: dict[str, dict[str, Any]] = {}
    web_data: dict[str, dict[str, Any]] = {}
    all_data: dict[str, dict[str, Any]] = {}
    evidence_ids: list[str] = []

    # 1. Fetch yfinance tickers
    for name, ticker in COMMODITY_TICKERS.items():
        try:
            snap = fetch_yfinance_commodity(name, ticker)
            yfinance_data[name] = snap
            all_data[name] = snap
        except Exception as e:
            err_snap = {
                "name": name,
                "ticker": ticker,
                "price": None,
                "change_pct": None,
                "signal": "Unavailable",
                "error": str(e),
            }
            yfinance_data[name] = err_snap
            all_data[name] = err_snap

    # 2. Fetch web commodities (Coal, CPO, Nickel)
    web_queries = {
        "Coal (Newcastle)": f"harga batu bara Newcastle spot price {label}",
        "CPO": f"harga CPO crude palm oil price {label}",
        "Nickel (LME)": f"harga nikel LME nickel spot price {label}",
    }

    for name, query in web_queries.items():
        try:
            result, source_ids = search_text_with_sources(
                query, days=search_days, category=name, limit_chars=600
            )
            item = _parse_commodity_web_summary(name, result, source_ids)
            web_data[name] = item
            all_data[name] = item
            evidence_ids.extend(source_ids)
        except Exception as e:
            err_item = {
                "name": name,
                "ticker": "WEB_SEARCH",
                "price": None,
                "change_pct": None,
                "signal": "Unavailable",
                "raw": f"Data unavailable: {e}",
                "source_ids": [],
                "error": str(e),
                "source": "error",
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            }
            web_data[name] = err_item
            all_data[name] = err_item

    # 3. Map clean changes for economics engine
    changes = {
        "Crude Oil": yfinance_data.get("Crude Oil (WTI)", {}).get("change_pct"),
        "Brent Crude": yfinance_data.get("Brent Crude", {}).get("change_pct"),
        "Natural Gas": yfinance_data.get("Natural Gas", {}).get("change_pct"),
        "Coal": web_data.get("Coal (Newcastle)", {}).get("change_pct"),
        "CPO": web_data.get("CPO", {}).get("change_pct"),
        "Nickel": web_data.get("Nickel (LME)", {}).get("change_pct"),
    }

    return {
        "yfinance": yfinance_data,
        "web": web_data,
        "all": all_data,
        "changes": changes,
        "evidence_ids": evidence_ids,
        "label": label,
    }



def format_all_commodities_markdown(comm_data: dict[str, Any], target_label: str | None = None) -> str:
    """Format commodities into clean markdown for LLM brief/review prompts."""
    label = target_label or comm_data.get("label", "Current")
    lines = [f"## Real-Time Commodity Prices ({label})\n"]

    for name, snap in comm_data.get("yfinance", {}).items():
        lines.append(format_commodity_snapshot(snap))

    for name, item in comm_data.get("web", {}).items():
        raw_text = item.get("raw", "unavailable")
        lines.append(f"\n### {name}:\n{raw_text}")

    return "\n".join(lines)
