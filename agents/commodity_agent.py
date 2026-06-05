import yfinance as yf
from agents.web_agent import search_web
from datetime import datetime

COMMODITIES = {
    "Crude Oil (WTI)": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
}

def get_ihsg_data() -> str:
    try:
        ihsg = yf.Ticker("^JKSE")
        hist = ihsg.history(period="2d")
        if len(hist) < 1:
            return "IHSG data unavailable."
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else None
        close = latest["Close"]
        open_ = latest["Open"]
        high = latest["High"]
        low = latest["Low"]
        change = ((close - prev["Close"]) / prev["Close"] * 100) if prev is not None else 0
        direction = "▲" if change > 0 else "▼"
        return (
            f"IHSG Close: {close:,.2f} {direction} {abs(change):.2f}%\n"
            f"Open: {open_:,.2f} | High: {high:,.2f} | Low: {low:,.2f}"
        )
    except Exception as e:
        return f"IHSG data unavailable: {e}"

def get_commodity_prices() -> str:
    now = datetime.now().strftime("%B %d, %Y")
    lines = [f"## Real-Time Commodity Prices ({now})\n"]

    # IHSG actual data first
    lines.append(f"### IHSG Actual Price Data:\n{get_ihsg_data()}\n")

    for name, ticker in COMMODITIES.items():
        try:
            data = yf.Ticker(ticker)
            price = data.fast_info.last_price
            prev = data.fast_info.previous_close
            change = ((price - prev) / prev) * 100 if prev else 0
            direction = "▲" if change > 0 else "▼"
            lines.append(f"- **{name}**: \ {direction} {abs(change):.2f}%")
        except:
            lines.append(f"- **{name}**: Price unavailable")

    for name, query in {
        "Coal (Newcastle)": f"Newcastle coal spot price today {now}",
        "CPO (Palm Oil)": f"CPO crude palm oil price Bursa Malaysia today {now}",
        "Nickel (LME)": f"LME nickel spot price today {now}"
    }.items():
        try:
            result = search_web(query)
            lines.append(f"\n### {name}:\n{result[:300]}")
        except:
            lines.append(f"- **{name}**: Price unavailable")

    return "\n".join(lines)
