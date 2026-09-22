from data_sources.market_data import (
    COMMODITY_TICKERS,
    fetch_ihsg_snapshot,
    fetch_yfinance_commodity,
    format_commodity_snapshot,
    format_ihsg_snapshot,
    jakarta_now,
)
from data_sources.news import search_text_with_sources


def get_ihsg_data() -> str:
    try:
        return format_ihsg_snapshot(fetch_ihsg_snapshot())
    except Exception as e:
        return f"IHSG data unavailable: {e}"


def get_commodity_prices() -> str:
    now = jakarta_now().strftime("%B %d, %Y")
    lines = [f"## Real-Time Commodity Prices ({now})\n"]

    lines.append(f"### IHSG Actual Price Data:\n{get_ihsg_data()}\n")

    for name, ticker in COMMODITY_TICKERS.items():
        try:
            snapshot = fetch_yfinance_commodity(name, ticker)
            lines.append(format_commodity_snapshot(snapshot))
        except Exception as e:
            print(f"  [commodity_agent] failed to fetch {name}: {e}")
            lines.append(f"- **{name}**: Price unavailable")

    for name, query in {
        "Coal (Newcastle)": f"Newcastle coal spot price today {now}",
        "CPO (Palm Oil)": f"CPO crude palm oil price Bursa Malaysia today {now}",
        "Nickel (LME)": f"LME nickel spot price today {now}",
    }.items():
        try:
            result, _source_ids = search_text_with_sources(query, category=name, limit_chars=800)
            lines.append(f"\n### {name}:\n{result}")
        except Exception as e:
            print(f"  [commodity_agent] failed to search {name}: {e}")
            lines.append(f"- **{name}**: Price unavailable")

    return "\n".join(lines)
