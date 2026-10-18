"""
core/sectors.py

Deterministic evaluation of IDX-IC sectors and subsector mappings for Nexus.
Audience: Buy-side rigorous audit.
Rules:
- 11 IDX-IC parent sectors.
- Strict close data verification: must contain close keywords ('penutupan', 'ditutup', 'close')
  and not be exclusively midday/session-I data.
- Subsector mapping: maps commodities/industries to parent IDX-IC indices.
- Opposite calls on the same parent index mark calls as 'unverifiable' (scored as None).
- Neutral band: +/- 0.20%.
  Change > +0.20% -> Bullish
  Change < -0.20% -> Bearish
  Between -0.20% and +0.20% -> Neutral
- If data missing: None (null), never a guess or fabrication.
"""
from __future__ import annotations
import re

# The 11 official IDX Industrial Classification (IDX-IC) Sectors
IDX_IC_SECTORS = {
    "IDXENERGY": {"name_id": "Energi", "name_en": "Energy"},
    "IDXBASIC": {"name_id": "Barang Baku", "name_en": "Basic Materials"},
    "IDXINDUST": {"name_id": "Perindustrian", "name_en": "Industrials"},
    "IDXNONCYC": {"name_id": "Barang Konsumen Primer", "name_en": "Consumer Non-Cyclicals"},
    "IDXCYCLIC": {"name_id": "Barang Konsumen Non-Primer", "name_en": "Consumer Cyclicals"},
    "IDXHEALTH": {"name_id": "Kesehatan", "name_en": "Healthcare"},
    "IDXFINANCE": {"name_id": "Keuangan", "name_en": "Financials"},
    "IDXPROPERT": {"name_id": "Properti & Real Estat", "name_en": "Properties & Real Estate"},
    "IDXTECH": {"name_id": "Teknologi", "name_en": "Technology"},
    "IDXINFRA": {"name_id": "Infrastruktur", "name_en": "Infrastructures"},
    "IDXTRANS": {"name_id": "Transportasi & Logistik", "name_en": "Transportation & Logistics"},
}

# Subsector / Keyword mapping to Parent IDX-IC Sector
SUBSECTOR_TO_PARENT = {
    # Energy
    "energi": "IDXENERGY",
    "energy": "IDXENERGY",
    "batu bara": "IDXENERGY",
    "batubara": "IDXENERGY",
    "coal": "IDXENERGY",
    "minyak": "IDXENERGY",
    "gas": "IDXENERGY",
    "oil": "IDXENERGY",
    "oil & gas": "IDXENERGY",
    "migas": "IDXENERGY",

    # Basic Materials
    "barang baku": "IDXBASIC",
    "basic materials": "IDXBASIC",
    "basic material": "IDXBASIC",
    "logam": "IDXBASIC",
    "mineral": "IDXBASIC",
    "nikel": "IDXBASIC",
    "nickel": "IDXBASIC",
    "cpo": "IDXBASIC",
    "kelapa sawit": "IDXBASIC",
    "sawit": "IDXBASIC",
    "palm oil": "IDXBASIC",
    "emas": "IDXBASIC",
    "gold": "IDXBASIC",
    "timah": "IDXBASIC",
    "tembaga": "IDXBASIC",
    "copper": "IDXBASIC",
    "tin": "IDXBASIC",
    "semen": "IDXBASIC",
    "cement": "IDXBASIC",
    "kimia": "IDXBASIC",
    "chemicals": "IDXBASIC",

    # Industrials
    "perindustrian": "IDXINDUST",
    "industri": "IDXINDUST",
    "industrials": "IDXINDUST",
    "alat berat": "IDXINDUST",
    "heavy equipment": "IDXINDUST",
    "mesin": "IDXINDUST",

    # Consumer Non-Cyclicals
    "barang konsumen primer": "IDXNONCYC",
    "consumer non-cyclicals": "IDXNONCYC",
    "consumer staples": "IDXNONCYC",
    "makanan": "IDXNONCYC",
    "minuman": "IDXNONCYC",
    "f&b": "IDXNONCYC",
    "food": "IDXNONCYC",
    "beverage": "IDXNONCYC",
    "rokok": "IDXNONCYC",
    "tobacco": "IDXNONCYC",
    "poultry": "IDXNONCYC",
    "unggas": "IDXNONCYC",
    "peternakan": "IDXNONCYC",

    # Consumer Cyclicals
    "barang konsumen non-primer": "IDXCYCLIC",
    "consumer cyclicals": "IDXCYCLIC",
    "siklikal": "IDXCYCLIC",
    "konsumen siklikal": "IDXCYCLIC",
    "ritel": "IDXCYCLIC",
    "retail": "IDXCYCLIC",
    "otomotif": "IDXCYCLIC",
    "automotive": "IDXCYCLIC",
    "media": "IDXCYCLIC",

    # Healthcare
    "kesehatan": "IDXHEALTH",
    "healthcare": "IDXHEALTH",
    "farmasi": "IDXHEALTH",
    "pharmaceuticals": "IDXHEALTH",
    "rumah sakit": "IDXHEALTH",
    "hospitals": "IDXHEALTH",

    # Financials
    "keuangan": "IDXFINANCE",
    "financials": "IDXFINANCE",
    "perbankan": "IDXFINANCE",
    "bank": "IDXFINANCE",
    "multifinance": "IDXFINANCE",
    "asuransi": "IDXFINANCE",

    # Property
    "properti": "IDXPROPERT",
    "property": "IDXPROPERT",
    "real estat": "IDXPROPERT",
    "real estate": "IDXPROPERT",

    # Technology
    "teknologi": "IDXTECH",
    "technology": "IDXTECH",
    "tech": "IDXTECH",
    "digital": "IDXTECH",

    # Infrastructure
    "infrastruktur": "IDXINFRA",
    "infrastructures": "IDXINFRA",
    "infrastructure": "IDXINFRA",
    "telekomunikasi": "IDXINFRA",
    "telco": "IDXINFRA",
    "telecom": "IDXINFRA",
    "jalan tol": "IDXINFRA",
    "toll roads": "IDXINFRA",
    "utilitas": "IDXINFRA",
    "utilities": "IDXINFRA",
    "tower": "IDXINFRA",

    # Transportation
    "transportasi": "IDXTRANS",
    "transportation": "IDXTRANS",
    "logistik": "IDXTRANS",
    "logistics": "IDXTRANS",
    "pelayaran": "IDXTRANS",
    "shipping": "IDXTRANS",
    "penerbangan": "IDXTRANS",
    "aviation": "IDXTRANS",
}

NEUTRAL_BAND = 0.20  # +/- 0.20%


def map_to_parent_sector(sector_str: str) -> str | None:
    """Resolve subsector or colloquial name to IDX-IC code."""
    if not sector_str:
        return None
    s = sector_str.strip().lower()
    # Check direct code
    s_upper = s.upper()
    if s_upper in IDX_IC_SECTORS:
        return s_upper
    # Check exact keyword mapping
    if s in SUBSECTOR_TO_PARENT:
        return SUBSECTOR_TO_PARENT[s]
    # Check partial match
    for kw, parent in SUBSECTOR_TO_PARENT.items():
        if kw in s or s in kw:
            return parent
    return None


def is_close_data(text: str) -> bool:
    """Verify that sector text is explicit market-close data, not session-I midday."""
    if not text or len(text) < 20:
        return False
    t_lower = text.lower()

    # Reject if explicitly marked as session 1 or intraday without explicit market close
    is_sesi_1 = bool(re.search(r"\b(?:sesi\s+i\b|sesi\s+1\b|tengah\s+hari|jeda\s+siang|intraday|siang)\b", t_lower))
    has_close = bool(re.search(r"\b(?:penutupan|ditutup|akhir\s+perdagangan|close|closing|sesi\s+ii|sesi\s+2)\b", t_lower))

    if is_sesi_1 and not has_close:
        return False
    return has_close


def parse_sector_percentages_from_text(text: str) -> dict[str, float]:
    """Parse actual percentage changes for IDX-IC sectors from close text.

    Returns dict mapping IDX-IC sector codes (e.g. 'IDXENERGY') to float
    percentages.
    """
    if not is_close_data(text):
        return {}

    parsed: dict[str, float] = {}

    # Pattern: sektor X (turun/naik) Y% or sektor X (+/-)Y%
    pattern = re.compile(
        r"(?:sektor|indeks\s+sektoral|indeks)\s+([A-Za-z\s&/-]+?)\s+"
        r"(?:yang\s+)?(?:sebesar\s+)?(naik|menguat|melonjak|turun|melemah|terkoreksi|jatuh|merosot|\+|-)?\s*"
        r"([0-9]+(?:[.,][0-9]+)?)\s*(?:%|persen)",
        re.IGNORECASE,
    )

    for m in pattern.finditer(text):
        sector_name = m.group(1).strip()
        dir_word = (m.group(2) or "").strip().lower()
        val_str = m.group(3).replace(",", ".")
        try:
            val = float(val_str)
        except ValueError:
            continue

        if dir_word in ["turun", "melemah", "terkoreksi", "jatuh", "merosot", "-"]:
            signed_val = -abs(val)
        elif dir_word in ["naik", "menguat", "melonjak", "+"]:
            signed_val = abs(val)
        else:
            # Check context right before/after
            continue

        parent = map_to_parent_sector(sector_name)
        if parent and parent not in parsed:
            parsed[parent] = round(signed_val, 2)

    return parsed


def score_sector_predictions(
    predicted_sectors: dict[str, str],
    actual_sector_changes: dict[str, float],
) -> dict[str, bool | None]:
    """Score predicted sector calls against actual percentages deterministically.

    predicted_sectors: e.g. {"Coal": "Bullish", "Oil & Gas": "Bearish", "Banking": "Bullish"}
    actual_sector_changes: e.g. {"IDXENERGY": 1.25, "IDXFINANCE": -0.40}

    Opposite calls on the same parent index mark both calls as 'unverifiable' (None).
    Missing actual data returns None.
    """
    if not predicted_sectors:
        return {}

    # 1. Map all predicted items to their parent index and collect directions
    parent_map: dict[str, str] = {}
    parent_calls: dict[str, set[str]] = {}

    for item_name, call in predicted_sectors.items():
        if not call:
            continue
        c_norm = call.strip().capitalize()
        parent = map_to_parent_sector(item_name)
        if not parent:
            continue
        parent_map[item_name] = parent
        if parent not in parent_calls:
            parent_calls[parent] = set()
        parent_calls[parent].add(c_norm)

    results: dict[str, bool | None] = {}

    for item_name, call in predicted_sectors.items():
        parent = parent_map.get(item_name)
        if not parent:
            results[item_name] = None
            continue

        # Check for conflicting calls on same parent index
        calls = parent_calls.get(parent, set())
        has_bullish = any(c in ["Bullish", "Overweight", "Up"] for c in calls)
        has_bearish = any(c in ["Bearish", "Underweight", "Down"] for c in calls)

        if has_bullish and has_bearish:
            # Conflicting calls on the same parent index -> unverifiable
            results[item_name] = None
            continue

        # Check if actual data exists for this parent sector
        if parent not in actual_sector_changes:
            results[item_name] = None
            continue

        act_pct = actual_sector_changes[parent]
        # Neutral band rule
        if act_pct > NEUTRAL_BAND:
            act_direction = "Bullish"
        elif act_pct < -NEUTRAL_BAND:
            act_direction = "Bearish"
        else:
            act_direction = "Neutral"

        c_norm = call.strip().capitalize()
        if c_norm in ["Bullish", "Overweight", "Up"]:
            pred_direction = "Bullish"
        elif c_norm in ["Bearish", "Underweight", "Down"]:
            pred_direction = "Bearish"
        elif c_norm in ["Neutral", "Flat"]:
            pred_direction = "Neutral"
        else:
            results[item_name] = None
            continue

        results[item_name] = (pred_direction == act_direction)

    return results
