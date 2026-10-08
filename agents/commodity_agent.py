from data_sources.market_data import (
    fetch_all_commodities,
    fetch_ihsg_snapshot,
    format_all_commodities_markdown,
    format_ihsg_snapshot,
    jakarta_now,
)


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

    ihsg_section = f"### IHSG Actual Price Data:\n{get_ihsg_data(target_date=target_date)}\n"
    comm_data = fetch_all_commodities(target_label=label, search_days=search_days)
    comm_markdown = format_all_commodities_markdown(comm_data, target_label=label)

    return f"{ihsg_section}\n{comm_markdown}"
