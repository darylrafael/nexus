from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf


JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

COMMODITY_TICKERS = {
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
}


def jakarta_now() -> datetime:
    return datetime.now(JAKARTA_TZ)


def _pct_change(latest: float, previous: float | None) -> float:
    return ((latest - previous) / previous * 100) if previous else 0.0


def fetch_ihsg_snapshot(period: str = "2d") -> dict[str, Any]:
    ihsg = yf.Ticker("^JKSE")
    hist = ihsg.history(period=period)
    if len(hist) < 1:
        return {"ihsg_signal": "Unknown", "error": "IHSG data unavailable."}

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


def fetch_yfinance_commodity(name: str, ticker: str) -> dict[str, Any]:
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
