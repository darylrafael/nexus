import re
from typing import Any, Optional


INDONESIAN_MONTH_MAP = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agt": 8, "aug": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12, "dec": 12,
}


def _verify_target_date(text: str, target_date_str: Optional[str]) -> bool:
    """Return False if text explicitly refers to a different date than target_date_str."""
    if not target_date_str or not text:
        return True

    text_lower = text.lower()

    # Parse target_date_str (YYYY-MM-DD or 'D MMMM YYYY')
    target_year = None
    target_month = None
    target_day = None

    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", target_date_str)
    if iso_match:
        target_year = int(iso_match.group(1))
        target_month = int(iso_match.group(2))
        target_day = int(iso_match.group(3))
    else:
        text_date_m = re.search(r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})", target_date_str)
        if text_date_m:
            target_day = int(text_date_m.group(1))
            m_name = text_date_m.group(2).lower()
            target_month = INDONESIAN_MONTH_MAP.get(m_name)
            target_year = int(text_date_m.group(3))

    if not target_month or not target_day:
        return True

    # Check for date patterns in snippet like "(10/8/2026)" or "10/08/2026"
    date_slash_m = re.search(r"\(?\b(\d{1,2})/(\d{1,2})/(\d{4})\b\)?", text)
    if date_slash_m:
        d1 = int(date_slash_m.group(1))
        d2 = int(date_slash_m.group(2))
        y = int(date_slash_m.group(3))
        # If year matches or is present, verify day and month
        if y == target_year:
            # Could be D/M/Y or M/D/Y
            matches_target = (d1 == target_day and d2 == target_month) or (d2 == target_day and d1 == target_month)
            if not matches_target:
                return False

    # Check for textual month mentions in snippet like "Senin (10 Agustus 2026)"
    for m_name, m_num in INDONESIAN_MONTH_MAP.items():
        if len(m_name) > 3 and m_name in text_lower:
            if m_num != target_month:
                # Text mentions a completely different month!
                # If target month is also mentioned, it might be comparative, otherwise reject
                target_month_names = [k for k, v in INDONESIAN_MONTH_MAP.items() if v == target_month and len(k) > 3]
                if not any(tm in text_lower for tm in target_month_names):
                    return False

    return True


def classify_foreign_flow(
    text: str,
    target_date_str: Optional[str] = None,
    threshold_trillion: float = 1.0,
) -> dict[str, Any]:
    """Parse a Rupiah foreign flow figure and sign, applying the Rp1T threshold.

    - Threshold: |net| < Rp1 Trillion -> 'Stagnant'
    - net >= +1.0T -> 'Accumulation'
    - net <= -1.0T -> 'Distribution'
    - No figure found or date rejected -> 'Unknown'
    """
    if not text or not isinstance(text, str):
        return {
            "signal": "Unknown",
            "net_trillion": None,
            "raw_figure": None,
            "reason": "empty_input",
        }

    # Date recency check
    if not _verify_target_date(text, target_date_str):
        return {
            "signal": "Unknown",
            "net_trillion": None,
            "raw_figure": None,
            "reason": "date_mismatch_rejected",
        }

    # Regex to capture: (net buy|beli bersih|net sell|jual bersih) ... Rp X (triliun|miliar|t|m)
    # or Rp X (triliun|miliar) ... (net buy|net sell)
    pattern = (
        r"(?P<direction>net\s+buy|beli\s+bersih|inflow|akumulasi|net\s+sell|jual\s+bersih|outflow|distribusi)?"
        r"[^\d\n\r]{0,30}?"
        r"(?:rp\.?|idr)\s*(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>triliun|trillion|miliar|milyar|billion|[tmb])\b"
    )

    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    if not matches:
        # Try reverse order: Rp X (triliun|miliar) ... (net buy|net sell)
        pattern_rev = (
            r"(?:rp\.?|idr)\s*(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>triliun|trillion|miliar|milyar|billion|[tmb])\b"
            r"[^\n\r]{0,30}?"
            r"(?P<direction>net\s+buy|beli\s+bersih|inflow|akumulasi|net\s+sell|jual\s+bersih|outflow|distribusi)"
        )
        matches = list(re.finditer(pattern_rev, text, re.IGNORECASE))

    if not matches:
        return {
            "signal": "Unknown",
            "net_trillion": None,
            "raw_figure": None,
            "reason": "no_flow_figure_found",
        }

    # Use first valid match
    m = matches[0]
    dir_str = m.group("direction") or ""
    amount_str = m.group("amount").replace(".", "").replace(",", ".") if "." in m.group("amount") and "," in m.group("amount") else m.group("amount").replace(",", ".")
    unit_str = m.group("unit").lower()

    # If direction was not in the immediate regex group, search within surrounding text (50 chars)
    if not dir_str:
        span_start = max(0, m.start() - 50)
        span_end = min(len(text), m.end() + 50)
        surrounding = text[span_start:span_end].lower()
        if any(w in surrounding for w in ["net sell", "jual bersih", "outflow", "distribusi"]):
            dir_str = "net sell"
        elif any(w in surrounding for w in ["net buy", "beli bersih", "inflow", "akumulasi"]):
            dir_str = "net buy"

    try:
        raw_num = float(amount_str)
    except ValueError:
        return {
            "signal": "Unknown",
            "net_trillion": None,
            "raw_figure": None,
            "reason": "unparseable_number",
        }

    # Convert to Trillion IDR
    if unit_str in ["triliun", "trillion", "t"]:
        amount_trillion = raw_num
    elif unit_str in ["miliar", "milyar", "billion", "m", "b"]:
        amount_trillion = raw_num / 1000.0
    else:
        amount_trillion = raw_num

    # Determine sign
    is_sell = any(w in dir_str.lower() for w in ["sell", "jual", "outflow", "distribusi"])
    net_signed_trillion = -amount_trillion if is_sell else amount_trillion

    # Apply Rp1 Trillion threshold
    if abs(net_signed_trillion) < threshold_trillion:
        signal = "Stagnant"
    elif net_signed_trillion >= threshold_trillion:
        signal = "Accumulation"
    else:
        signal = "Distribution"

    # Detect market scope: Pasar Reguler vs All Market / Pasar Negosiasi
    text_lower = text.lower()
    is_negotiated = any(k in text_lower for k in ["pasar negosiasi", "seluruh pasar", "all market", "total pasar", "pasar tunai"])
    is_regular_explicit = any(k in text_lower for k in ["pasar reguler", "regular market", "papan reguler"])

    if is_negotiated and not is_regular_explicit:
        market_scope = "all_market"
    else:
        market_scope = "regular"

    return {
        "signal": signal,
        "net_trillion": round(net_signed_trillion, 4),
        "raw_figure": f"{amount_str} {unit_str}",
        "direction": "Sell" if is_sell else "Buy",
        "market_scope": market_scope,
        "is_all_market": (market_scope == "all_market"),
        "reason": "classified_successfully",
    }
