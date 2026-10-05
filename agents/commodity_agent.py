from data_sources.market_data import (
    COMMODITY_TICKERS,
    fetch_ihsg_snapshot,
    fetch_yfinance_commodity,
    format_commodity_snapshot,
    format_ihsg_snapshot,
    jakarta_now,
)
from data_sources.news import search_text_with_sources


def get_ihsg_data(target_date: str | None = None) -> str:
    try:
        return format_ihsg_snapshot(fetch_ihsg_snapshot(target_date=target_date))
    except Exception as e:
        return f"IHSG data unavailable: {e}"


def get_commodity_prices(
    search_days: int = 2,
    target_date: str | None = None,
    target_label: str | None = None,
) -> str:
    now_str = jakarta_now().strftime("%B %d, %Y")
    label = target_label or now_str
    lines = [f"## Real-Time Commodity Prices ({label})\n"]

    lines.append(f"### IHSG Actual Price Data:\n{get_ihsg_data(target_date=target_date)}\n")

    for name, ticker in COMMODITY_TICKERS.items():
        try:
            snapshot = fetch_yfinance_commodity(name, ticker)
            lines.append(format_commodity_snapshot(snapshot))
        except Exception as e:
            print(f"  [commodity_agent] failed to fetch {name}: {e}")
            lines.append(f"- **{name}**: Price unavailable")

    for name, query in {
        "Coal (Newcastle)": f"Newcastle coal spot price {label}",
        "CPO (Palm Oil)": f"CPO crude palm oil price Bursa Malaysia {label}",
        "Nickel (LME)": f"LME nickel spot price {label}",
    }.items():
        try:
            result, _source_ids = search_text_with_sources(
                query, days=search_days, category=name, limit_chars=800
            )
            lines.append(f"\n### {name}:\n{result}")
        except Exception as e:
            print(f"  [commodity_agent] failed to search {name}: {e}")
            lines.append(f"- **{name}**: Price unavailable")

    return "\n".join(lines)
