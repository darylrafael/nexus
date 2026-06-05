from agents.web_agent import search_web

# Economic logic only — NO hardcoded tickers
# Tickers are discovered dynamically via search

COMMODITY_LOGIC = {
    "Crude Oil":  {"producers": "oil and gas upstream companies",  "consumers": "airlines, shipping, petrochemical companies"},
    "Coal":       {"producers": "coal mining companies",           "consumers": "electricity-intensive manufacturers"},
    "CPO":        {"producers": "palm oil plantation companies",   "consumers": "consumer goods and food manufacturers who use palm oil as raw material"},
    "Nickel":     {"producers": "nickel mining companies",        "consumers": "EV battery and stainless steel manufacturers"},
    "Natural Gas": {"producers": "gas upstream companies",        "consumers": "fertilizer and utility companies"},
}

SECTOR_LOGIC = {
    "toll_road": "Toll road operators earn from toll fees only — NOT affected by fuel costs. Higher commodity logistics traffic is bullish.",
    "aviation":  "Airlines are directly fuel-sensitive — rising oil = rising avtur costs = margin compression = bearish.",
    "banking":   "Rate hike = short-term bullish for banks (wider NIM). Long-term risk if loan growth slows.",
    "property":  "Rate hike = bearish. Higher mortgage rates reduce demand.",
}

RUPIAH_LOGIC = {
    "weaken": [
        "Exporters (earn USD, convert to more IDR): BULLISH",
        "Importers (pay USD, cost increases in IDR): BEARISH",
        "Companies with USD-denominated debt: BEARISH (debt burden rises in IDR)",
        "Domestic purchasing power for imported goods: DECREASES — NOT increases",
    ],
    "strengthen": [
        "Exporters (earn USD, convert to less IDR): BEARISH",
        "Importers: BULLISH (imported goods cheaper in IDR)",
        "Companies with USD debt: BULLISH (debt burden decreases)",
    ]
}


def get_affected_stocks(commodity: str, direction: str, current_date: str) -> str:
    """Dynamically search for IDX stocks affected by this commodity move."""
    dir_word_id = "naik" if direction == "up" else "turun"
    dir_word_en = "rise" if direction == "up" else "fall"

    print(f"  [economics] searching affected stocks: {commodity} {dir_word_en}")

    result_id = search_web(
        f"saham IDX BEI terdampak harga {commodity} {dir_word_id} {current_date}", days=2
    )
    result_en = search_web(
        f"IDX Indonesia stocks affected {commodity} price {dir_word_en} {current_date}", days=2
    )
    return f"{result_id}\n{result_en}"


def build_economics_context(
    commodity_changes: dict,
    rupiah_change: float = None,
    rate_direction: str = None,
    current_date: str = ""
) -> str:
    """
    Build pre-computed economic impact context with dynamic stock discovery.
    LLM receives: correct economic direction + search-discovered affected stocks.
    """
    lines = ["\n## Pre-Computed Economic Impacts\n"]
    lines.append("INSTRUCTION: Use the economic logic below as ground truth.")
    lines.append("Use the search results to identify WHICH specific IDX stocks are affected.")
    lines.append("Do NOT override the economic direction stated here.\n")

    for commodity, pct_change in commodity_changes.items():
        if commodity not in COMMODITY_LOGIC or abs(pct_change) < 0.1:
            continue

        logic = COMMODITY_LOGIC[commodity]
        direction = "up" if pct_change > 0 else "down"
        sign = "+" if pct_change > 0 else ""

        lines.append(f"### {commodity} {sign}{pct_change:.2f}%:")

        if pct_change > 0:
            lines.append(f"  → {logic['producers']}: BULLISH (revenue increases)")
            lines.append(f"  → {logic['consumers']}: BEARISH (input costs rise, margins compress)")
        else:
            lines.append(f"  → {logic['producers']}: BEARISH (revenue decreases)")
            lines.append(f"  → {logic['consumers']}: BULLISH (input costs fall, margins improve)")

        affected = get_affected_stocks(commodity, direction, current_date)
        lines.append(f"  Search results for affected IDX stocks:\n{affected[:500]}\n")

    if rupiah_change is not None and abs(rupiah_change) > 0.05:
        direction = "weaken" if rupiah_change < 0 else "strengthen"
        lines.append(f"\n### Rupiah {'weakened' if rupiah_change < 0 else 'strengthened'} {abs(rupiah_change):.2f}%:")
        for point in RUPIAH_LOGIC[direction]:
            lines.append(f"  → {point}")

    if rate_direction:
        lines.append(f"\n### Interest Rate {rate_direction.title()}:")
        if rate_direction == "hike":
            lines.append("  → Banks: BULLISH short-term (wider NIM)")
            lines.append("  → Property: BEARISH (higher mortgage costs)")
            lines.append("  → Infrastructure: BEARISH (higher project financing costs)")
            lines.append("  → Rupiah: BULLISH (rate hike attracts foreign inflows)")
        else:
            lines.append("  → Banks: BEARISH short-term (NIM compression)")
            lines.append("  → Property: BULLISH (cheaper mortgages)")

    lines.append(f"\n### Sector Behavior Rules:")
    for sector, rule in SECTOR_LOGIC.items():
        lines.append(f"  → {sector}: {rule}")

    return "\n".join(lines)
