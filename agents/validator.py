import re

# --- 1. Commodity Economics ---
# Hardcoded producer/consumer relationships
COMMODITY_ECONOMICS = {
    "CPO": {
        "producers": ["AALI", "LSIP", "SIMP", "TBLA"],
        "consumers": ["UNVR", "ICBP", "INDF", "MYOR"],
        "note": "Rising CPO price = margin expansion for planters, margin compression for consumer goods manufacturers."
    },
    "Coal": {
        "producers": ["ADRO", "PTBA", "ITMG", "HRUM", "BYAN", "BUMI"],
        "consumers": ["electricity-intensive manufacturers, cement"],
        "note": "Rising coal = revenue uplift for miners, higher input cost for power-intensive industries."
    },
    "Nickel": {
        "producers": ["INCO", "ANTM", "MBMA", "NCKL"],
        "consumers": ["EV battery supply chain"],
        "note": "Rising nickel = good for miners, raises battery production costs."
    },
    "Crude Oil": {
        "producers": ["MEDC", "ENRG", "RUIS"],
        "consumers": ["transport, petrochemical, aviation"],
        "note": "Rising oil = revenue boost for oil firms, cost pressure for transport and industrial sectors."
    }
}

def build_commodity_context(commodity_text: str) -> str:
    """Inject correct producer/consumer logic into commodity data."""
    context = commodity_text + "\n\n## Commodity Economics Rules (DO NOT REVERSE):\n"
    for commodity, data in COMMODITY_ECONOMICS.items():
        producers = ", ".join(data["producers"]) if isinstance(data["producers"], list) else data["producers"]
        consumers = ", ".join(data["consumers"]) if isinstance(data["consumers"], list) else data["consumers"]
        context += f"- {commodity}: Producers (benefit from price rise) = {producers}. Consumers (hurt by price rise) = {consumers}. {data['note']}\n"
    return context


# --- 2. Direction Language Fixer ---
BULLISH_TERMS = ["rose", "rise", "gained", "gain", "climbed", "rallied", "uptick",
                 "increased", "modest rise", "slight rise", "small gain", "jumped"]
BEARISH_TERMS = ["fell", "dropped", "declined", "slid", "slipped", "weakened",
                 "lost", "fell back", "retreated", "dipped"]

def fix_direction_language(text: str) -> str:
    """Fix contradictory directional language near percentages."""
    lines = text.split("\n")
    fixed = []
    for line in lines:
        has_negative = bool(re.search(r'[‑\-]\d+\.?\d*\s*%', line))
        has_positive = bool(re.search(r'\+\d+\.?\d*\s*%', line))

        if has_negative:
            for term in BULLISH_TERMS:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                if pattern.search(line):
                    line = pattern.sub("declined", line)

        if has_positive:
            for term in BEARISH_TERMS:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                if pattern.search(line):
                    line = pattern.sub("gained", line)

        fixed.append(line)
    return "\n".join(fixed)


# --- 3. Ticker Cross-Validator ---
def extract_tickers(text: str) -> set:
    """Extract IDX-style tickers (3-4 uppercase letters) from text."""
    return set(re.findall(r'\b[A-Z]{3,4}\b', text))

def validate_ticker_consistency(text: str) -> str:
    """
    Find tickers listed as top gainers in commodity/macro sections
    but also listed as distributed in foreign flow section.
    Flag contradictions.
    """
    sections = text.split("### ")
    gainer_tickers = set()
    flow_section = ""

    for section in sections:
        if section.startswith("3.") or section.startswith("1.") or section.startswith("2."):
            # Extract tickers next to positive percentages
            for match in re.finditer(r'\*\*([A-Z]{3,4})\*\*[^‑\-]*?\+\d+', section):
                gainer_tickers.add(match.group(1))
        if section.startswith("5."):
            flow_section = section

    if not flow_section or not gainer_tickers:
        return text

    lines = text.split("\n")
    result = []
    in_flow = False

    for line in lines:
        if "### 5." in line:
            in_flow = True
        elif line.startswith("### 6."):
            in_flow = False

        if in_flow and ("Distributed" in line or "distributed" in line or "sell" in line.lower()):
            tickers_in_line = extract_tickers(line)
            contradictions = tickers_in_line & gainer_tickers
            if contradictions:
                line += f"  ⚠️ [No data confirms {', '.join(contradictions)} as distributed — these were top gainers. Remove unless explicit sell data exists.]"

        result.append(line)

    return "\n".join(result)


def validate(text: str) -> str:
    """Run all validation passes."""
    text = fix_direction_language(text)
    text = validate_ticker_consistency(text)
    return text
