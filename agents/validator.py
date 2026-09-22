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

        # Skip lines that have both to avoid corrupting mixed-direction sentences
        if has_negative and not has_positive:
            for term in BULLISH_TERMS:
                pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                line = pattern.sub("declined", line)

        elif has_positive and not has_negative:
            for term in BEARISH_TERMS:
                pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                line = pattern.sub("gained", line)

        fixed.append(line)
    return "\n".join(fixed)


def validate(text: str) -> str:
    """Run all validation passes."""
    text = fix_direction_language(text)
    # Ticker consistency validator removed due to flawed assumptions about market mechanics
    # (Top gainers CAN experience foreign net sell simultaneously).
    return text
