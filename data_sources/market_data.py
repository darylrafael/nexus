from datetime import date, datetime, timedelta, timezone
import re
from typing import Any
import requests
import yfinance as yf
from utils.direction import classify_direction
from core.time import jakarta_now

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
            from core.paths import get_runs_dir
            runs_dir = get_runs_dir()
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


def calculate_atr(
    highs: list[Any],
    lows: list[Any],
    closes: list[Any],
    target_idx: int | None = None,
    period: int = 14,
) -> float | None:
    """Calculate Average True Range (ATR) over up to 14 periods for dynamic volatility bands."""
    if not closes or not highs or not lows:
        return None
    end_idx = (target_idx + 1) if (target_idx is not None and target_idx >= 0) else len(closes)
    tr_list = []
    for i in range(1, end_idx):
        if i >= len(highs) or i >= len(lows) or i >= len(closes):
            break
        h = highs[i]
        l = lows[i]
        c_prev = closes[i - 1]
        if h is None or l is None or c_prev is None:
            continue
        try:
            h_f = float(h)
            l_f = float(l)
            cp_f = float(c_prev)
            if h_f != h_f or l_f != l_f or cp_f != cp_f:  # NaN check
                continue
            tr = max(h_f - l_f, abs(h_f - cp_f), abs(l_f - cp_f))
            tr_list.append(tr)
        except (ValueError, TypeError):
            continue

    if not tr_list:
        return None
    sample = tr_list[-period:] if len(tr_list) >= period else tr_list
    return round(sum(sample) / len(sample), 2)


def validate_ohlc(
    open_v: float | None,
    high_v: float | None,
    low_v: float | None,
    close_v: float | None,
    prev_open: float | None = None,
    prev_high: float | None = None,
    prev_low: float | None = None,
    prev_close: float | None = None,
) -> bool:
    """Validate that OHLC bars adhere to geometric invariants:

    - low <= min(open, close)
    - high >= max(open, close)
    - high >= low
    - not identical to previous candle if close differs
    """
    if open_v is None or high_v is None or low_v is None or close_v is None:
        return False
    try:
        o = float(open_v)
        h = float(high_v)
        l = float(low_v)
        c = float(close_v)
    except (ValueError, TypeError):
        return False

    if (h < l) or (h < max(o, c)) or (l > min(o, c)):
        return False

    if (
        prev_open is not None
        and prev_high is not None
        and prev_low is not None
        and prev_close is not None
    ):
        try:
            po = float(prev_open)
            ph = float(prev_high)
            pl = float(prev_low)
            pc = float(prev_close)
            if o == po and h == ph and l == pl and c == pc:
                # Stale copied candle from previous session
                return False
            if (o == po and h == ph and l == pl) and (c != pc):
                return False
        except (ValueError, TypeError):
            pass

    return True


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

                        raw_open = open_vals[target_idx] if target_idx < len(open_vals) and open_vals[target_idx] is not None else None
                        raw_high = high_vals[target_idx] if target_idx < len(high_vals) and high_vals[target_idx] is not None else None
                        raw_low = low_vals[target_idx] if target_idx < len(low_vals) and low_vals[target_idx] is not None else None
                        raw_vol = vol_vals[target_idx] if target_idx < len(vol_vals) and vol_vals[target_idx] is not None else None

                        prev_o = None
                        prev_h = None
                        prev_l = None
                        if target_idx > 0:
                            prev_o = open_vals[target_idx - 1] if (target_idx - 1) < len(open_vals) else None
                            prev_h = high_vals[target_idx - 1] if (target_idx - 1) < len(high_vals) else None
                            prev_l = low_vals[target_idx - 1] if (target_idx - 1) < len(low_vals) else None

                        is_ohlc_valid = validate_ohlc(raw_open, raw_high, raw_low, close, prev_o, prev_h, prev_l, prev_close)

                        open_val = round(float(raw_open), 2) if is_ohlc_valid and raw_open is not None else None
                        high_val = round(float(raw_high), 2) if is_ohlc_valid and raw_high is not None else None
                        low_val = round(float(raw_low), 2) if is_ohlc_valid and raw_low is not None else None
                        vol_val = int(raw_vol) if raw_vol is not None else None

                        atr_val = calculate_atr(high_vals, low_vals, closes, target_idx=target_idx, period=14)
                        s1 = round(close - atr_val, 2) if atr_val else None
                        r1 = round(close + atr_val, 2) if atr_val else None
                        s2 = round(close - 2 * atr_val, 2) if atr_val else None
                        r2 = round(close + 2 * atr_val, 2) if atr_val else None

                        return {
                            "ihsg_close": round(close, 2),
                            "ihsg_prev": round(prev_close, 2) if prev_close is not None else None,
                            "ihsg_change_pct": round(pct, 2) if pct is not None else None,
                            "ihsg_change_pts": round(pts, 2) if pts is not None else None,
                            "ihsg_signal": signal,
                            "ihsg_open": open_val,
                            "ihsg_high": high_val,
                            "ihsg_low": low_val,
                            "ihsg_volume": vol_val,
                            "ihsg_atr14": atr_val,
                            "dynamic_s1": s1,
                            "dynamic_r1": r1,
                            "dynamic_s2": s2,
                            "dynamic_r2": r2,
                            "candle_date": candle_dates[target_idx],
                            "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                            "source": "yahoo_direct:^JKSE",
                            "ohlc_valid": is_ohlc_valid,
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

                raw_open = latest.get("Open") if "Open" in latest and latest["Open"] is not None and not (isinstance(latest["Open"], float) and latest["Open"] != latest["Open"]) else None
                raw_high = latest.get("High") if "High" in latest and latest["High"] is not None and not (isinstance(latest["High"], float) and latest["High"] != latest["High"]) else None
                raw_low = latest.get("Low") if "Low" in latest and latest["Low"] is not None and not (isinstance(latest["Low"], float) and latest["Low"] != latest["Low"]) else None
                raw_vol = latest.get("Volume") if "Volume" in latest and latest["Volume"] is not None and not (isinstance(latest["Volume"], float) and latest["Volume"] != latest["Volume"]) else None

                prev_o, prev_h, prev_l = None, None, None
                if target_idx > 0:
                    prev_row = hist.iloc[target_idx - 1]
                    prev_o = prev_row.get("Open")
                    prev_h = prev_row.get("High")
                    prev_l = prev_row.get("Low")

                is_ohlc_valid = validate_ohlc(raw_open, raw_high, raw_low, close, prev_o, prev_h, prev_l, prev_close)

                open_val = round(float(raw_open), 2) if is_ohlc_valid and raw_open is not None else None
                high_val = round(float(raw_high), 2) if is_ohlc_valid and raw_high is not None else None
                low_val = round(float(raw_low), 2) if is_ohlc_valid and raw_low is not None else None
                vol_val = int(raw_vol) if raw_vol is not None else None

                highs_list = hist["High"].tolist() if "High" in hist else []
                lows_list = hist["Low"].tolist() if "Low" in hist else []
                closes_list = hist["Close"].tolist() if "Close" in hist else []
                atr_val = calculate_atr(highs_list, lows_list, closes_list, target_idx=target_idx, period=14)
                s1 = round(close - atr_val, 2) if atr_val else None
                r1 = round(close + atr_val, 2) if atr_val else None
                s2 = round(close - 2 * atr_val, 2) if atr_val else None
                r2 = round(close + 2 * atr_val, 2) if atr_val else None

                return {
                    "ihsg_close": round(close, 2),
                    "ihsg_prev": round(prev_close, 2) if prev_close is not None else None,
                    "ihsg_change_pct": round(pct, 2) if pct is not None else None,
                    "ihsg_change_pts": round(pts, 2) if pts is not None else None,
                    "ihsg_signal": signal,
                    "ihsg_open": open_val,
                    "ihsg_high": high_val,
                    "ihsg_low": low_val,
                    "ihsg_volume": vol_val,
                    "ihsg_atr14": atr_val,
                    "dynamic_s1": s1,
                    "dynamic_r1": r1,
                    "dynamic_s2": s2,
                    "dynamic_r2": r2,
                    "candle_date": hist_dates[target_idx],
                    "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                    "source": "yfinance:^JKSE",
                    "ohlc_valid": is_ohlc_valid,
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
                "ihsg_open": None,
                "ihsg_high": None,
                "ihsg_low": None,
                "ihsg_volume": None,
                "ihsg_atr14": None,
                "dynamic_s1": None,
                "dynamic_r1": None,
                "dynamic_s2": None,
                "dynamic_r2": None,
                "candle_date": target_date or jakarta_now().strftime("%Y-%m-%d"),
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                "source": "web_fallback",
                "confidence": "low",
                "ohlc_valid": False,
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
    atr_val = data.get("ihsg_atr14")
    atr_str = f"\nDynamic Volatility ATR(14): {atr_val:.2f} pts | S1: {data.get('dynamic_s1'):,.2f} | R1: {data.get('dynamic_r1'):,.2f}" if (atr_val and data.get("dynamic_s1") and data.get("dynamic_r1")) else ""

    return (
        f"IHSG Close: {close_str} {change_str}{source_badge}\n"
        f"Open: {open_val} | "
        f"High: {high_val} | "
        f"Low: {low_val}{atr_str}"
    )


def fetch_usdidr_snapshot() -> dict[str, Any]:
    """Fetch USD/IDR exchange rate.

    Tries direct Yahoo endpoint first, falls back to yfinance, then web
    search. Computes percentage change strictly from consecutive daily closes.
    """
    # 1. Direct Yahoo endpoint
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/USDIDR=X?interval=1d&range=5d"
        res = requests.get(url, headers=_BROWSER_HEADERS, timeout=8)
        if res.status_code == 200:
            result = res.json().get("chart", {}).get("result", [])
            if result:
                d = result[0]
                quotes = d.get("indicators", {}).get("quote", [{}])[0]
                raw_closes = quotes.get("close", [])
                valid_closes = [float(c) for c in raw_closes if c is not None and not (isinstance(c, float) and c != c)]

                rate = None
                prev_rate = None
                pct = None

                if len(valid_closes) >= 2:
                    rate = valid_closes[-1]
                    prev_rate = valid_closes[-2]
                    pct = ((rate - prev_rate) / prev_rate) * 100
                elif len(valid_closes) == 1:
                    rate = valid_closes[0]
                    meta = d.get("meta", {})
                    prev_close_meta = meta.get("previousClose")
                    if prev_close_meta:
                        prev_rate = float(prev_close_meta)
                        pct = ((rate - prev_rate) / prev_rate) * 100

                if rate is not None:
                    signal = "Weakened" if (pct is not None and pct > 0) else ("Strengthened" if (pct is not None and pct < 0) else "Unknown")
                    return {
                        "usdidr": round(rate, 0),
                        "usdidr_change_pct": round(pct, 3) if pct is not None else None,
                        "rupiah_signal": signal,
                        "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                        "source": "yahoo_direct:USDIDR=X",
                    }
    except Exception as e:
        print(f"  [fetch_usdidr_snapshot] Direct Yahoo query error: {e}")

    # 2. yfinance library
    try:
        idr = yf.Ticker("USDIDR=X")
        hist = idr.history(period="5d")
        if len(hist) >= 2:
            rate = float(hist["Close"].iloc[-1])
            prev_rate = float(hist["Close"].iloc[-2])
            pct = ((rate - prev_rate) / prev_rate) * 100
            signal = "Weakened" if pct > 0 else ("Strengthened" if pct < 0 else "Unknown")
            return {
                "usdidr": round(rate, 0),
                "usdidr_change_pct": round(pct, 3),
                "rupiah_signal": signal,
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
                "source": "yfinance:USDIDR=X",
            }
        elif len(hist) == 1:
            rate = float(hist["Close"].iloc[0])
            return {
                "usdidr": round(rate, 0),
                "usdidr_change_pct": None,
                "rupiah_signal": "Unknown",
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


_COMMODITY_KEYWORDS = {
    "Coal (Newcastle)": ["batu bara", "coal", "newcastle", "thermal coal"],
    "CPO": ["cpo", "crude palm oil", "kelapa sawit", "sawit", "palm oil", "minyak sawit"],
    "Nickel (LME)": ["nikel", "nickel", "lme", "lme nickel"],
}

_DOWN_INDICATORS = [
    "turun", "melemah", "terkoreksi", "merosot", "anjlok", "terpukul", "jatuh", "anjloknya",
    "drop", "dropped", "fell", "falls", "falling", "down", "decline", "declined", "declining",
    "slump", "slumped", "plunge", "plunged", "minus", "loss", "losses", "decrease", "decreased"
]

_UP_INDICATORS = [
    "naik", "menguat", "melonjak", "terangkat", "rebound", "melenting", "positif",
    "rose", "rises", "rising", "jump", "jumped", "surge", "surged", "up", "gain", "gained",
    "rally", "rallied", "increase", "increased", "advancing", "advance"
]


def _parse_commodity_web_summary(name: str, raw_text: str, source_ids: list[str]) -> dict[str, Any]:
    """Parse numeric price and change percentage from web search snippets if available.

    Requires % to be near a commodity keyword in the same sentence and sign-resolved.
    Assigns parse_confidence: 'high' only when keyword and clear signed direction match.
    """
    price = None
    change_pct = None
    signal = "Unavailable"
    parse_confidence = "none"

    if raw_text and not raw_text.startswith("Data unavailable:"):
        keywords = _COMMODITY_KEYWORDS.get(name, [name.lower()])
        sentences = re.split(r"(?<=[.!?\n])\s+", raw_text)

        best_change = None
        best_price = None

        for sentence in sentences:
            s_lower = sentence.lower()
            # Must contain at least one commodity keyword
            if not any(kw in s_lower for kw in keywords):
                continue

            # Look for price in sentence
            if best_price is None:
                p_match = re.search(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)", sentence)
                if p_match:
                    try:
                        best_price = float(p_match.group(1).replace(",", ""))
                    except ValueError:
                        pass
                else:
                    alt_price = re.search(r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:USD|MYR|USD/t)", sentence, re.IGNORECASE)
                    if alt_price:
                        try:
                            best_price = float(alt_price.group(1).replace(",", ""))
                        except ValueError:
                            pass

            # Look for percentage in sentence
            pct_matches = list(re.finditer(r"([+-]?[0-9]+(?:[.,][0-9]+)?)\s*%", sentence))
            for m in pct_matches:
                raw_pct_str = m.group(1).replace(",", ".")
                try:
                    num_val = float(raw_pct_str)
                except ValueError:
                    continue

                # Determine sign
                has_explicit_sign = raw_pct_str.startswith("+") or raw_pct_str.startswith("-")
                has_down_word = any(w in s_lower for w in _DOWN_INDICATORS)
                has_up_word = any(w in s_lower for w in _UP_INDICATORS)

                if has_explicit_sign:
                    signed_val = num_val
                elif has_down_word and not has_up_word:
                    signed_val = -abs(num_val)
                elif has_up_word and not has_down_word:
                    signed_val = abs(num_val)
                else:
                    # Ambiguous sign or unsigned without clear directional term
                    signed_val = None

                if signed_val is not None:
                    best_change = signed_val
                    parse_confidence = "high"
                    break

            if parse_confidence == "high":
                break

        if best_change is not None:
            change_pct = round(best_change, 2)
            signal = "Up" if change_pct > 0 else ("Down" if change_pct < 0 else "Flat")
        elif best_price is not None:
            parse_confidence = "low"
        else:
            parse_confidence = "none"

        price = best_price

    return {
        "name": name,
        "ticker": "WEB_SEARCH",
        "price": price,
        "change_pct": change_pct,
        "signal": signal,
        "source": "tavily_web",
        "raw": raw_text,
        "source_ids": source_ids,
        "parse_confidence": parse_confidence,
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
                "parse_confidence": "none",
                "retrieved_at": jakarta_now().isoformat(timespec="seconds"),
            }
            web_data[name] = err_item
            all_data[name] = err_item

    # 3. Map clean changes for economics engine (high confidence only for web parsed)
    changes = {
        "Crude Oil": yfinance_data.get("Crude Oil (WTI)", {}).get("change_pct"),
        "Brent Crude": yfinance_data.get("Brent Crude", {}).get("change_pct"),
        "Natural Gas": yfinance_data.get("Natural Gas", {}).get("change_pct"),
        "Coal": web_data.get("Coal (Newcastle)", {}).get("change_pct") if web_data.get("Coal (Newcastle)", {}).get("parse_confidence") == "high" else None,
        "CPO": web_data.get("CPO", {}).get("change_pct") if web_data.get("CPO", {}).get("parse_confidence") == "high" else None,
        "Nickel": web_data.get("Nickel (LME)", {}).get("change_pct") if web_data.get("Nickel (LME)", {}).get("parse_confidence") == "high" else None,
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
