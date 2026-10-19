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


def canonicalize_flow(signal: str | None) -> str:
    """Canonicalize flow signals to standard labels: Accumulation, Distribution, Stagnant, Unknown."""
    if not signal:
        return "Unknown"
    s = str(signal).strip().lower()
    if any(k in s for k in ["sideways", "stagnant", "netral", "flat"]):
        return "Stagnant"
    if any(k in s for k in ["accumulation", "akumulasi", "inflow", "net buy", "beli bersih", "bullish"]):
        return "Accumulation"
    if any(k in s for k in ["distribution", "distribusi", "outflow", "net sell", "jual bersih", "bearish"]):
        return "Distribution"
    return "Unknown"


def _verify_target_date(
    text: str,
    target_date_str: Optional[str],
    strict: bool = False,
) -> tuple[bool, str, Optional[str]]:
    """Verify text refers to the target date. In strict mode, an explicit matching date is required."""
    if not target_date_str or not text:
        return (not strict, "no_target_date" if strict else "ok", None)

    # If target_date is not a valid IDX trading day, refuse flow classification
    from core.calendar import is_idx_trading_day
    try:
        if not is_idx_trading_day(target_date_str):
            return False, "non_trading_target_date", None
    except Exception:
        pass

    text_lower = text.lower()
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
        return (not strict, "unparseable_target_date" if strict else "ok", None)

    explicit_match_found = False
    matched_date_str: Optional[str] = None

    # Indonesian articles write dates as Day/Month/Year (e.g. 10/6/2026 = 10 June).
    date_slash_matches = list(re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text))
    for dm in date_slash_matches:
        d = int(dm.group(1))
        m = int(dm.group(2))
        y = int(dm.group(3))
        found_date = f"{y:04d}-{m:02d}-{d:02d}"
        if y == target_year:
            # Strictly Day/Month/Year for Indonesian financial articles
            if d == target_day and m == target_month:
                explicit_match_found = True
                matched_date_str = found_date
            else:
                return False, "date_mismatch_rejected", found_date
        else:
            return False, "date_mismatch_rejected", found_date

    # Check for textual dates like "6 Oktober 2026" or "Senin (10 Agustus 2026)"
    text_date_pattern = r"\b(\d{1,2})\s+([a-zA-Z]+)(?:\s+(\d{4}))?\b"
    for tdm in re.finditer(text_date_pattern, text):
        d_val = int(tdm.group(1))
        m_word = tdm.group(2).lower()
        y_val = int(tdm.group(3)) if tdm.group(3) else target_year
        if m_word in INDONESIAN_MONTH_MAP:
            m_val = INDONESIAN_MONTH_MAP[m_word]
            found_date = f"{y_val:04d}-{m_val:02d}-{d_val:02d}"
            if y_val == target_year:
                if d_val == target_day and m_val == target_month:
                    explicit_match_found = True
                    matched_date_str = found_date
                elif m_val != target_month or d_val != target_day:
                    target_month_names = [k for k, v in INDONESIAN_MONTH_MAP.items() if v == target_month and len(k) > 3]
                    if not any(tm in text_lower for tm in target_month_names) or d_val != target_day:
                        return False, "date_mismatch_rejected", found_date

    if strict and not explicit_match_found:
        return False, "no_matching_date", matched_date_str

    return True, "verified", (matched_date_str or f"{target_year:04d}-{target_month:02d}-{target_day:02d}")


def classify_foreign_flow(
    text: str,
    target_date_str: Optional[str] = None,
    threshold_trillion: float = 1.0,
    strict: bool = False,
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
            "matched_date": None,
            "target_date": target_date_str,
        }

    # Date recency check
    is_valid_date, date_reason, matched_date = _verify_target_date(text, target_date_str, strict=strict)
    if not is_valid_date:
        return {
            "signal": "Unknown",
            "net_trillion": None,
            "raw_figure": None,
            "reason": date_reason,
            "matched_date": matched_date,
            "target_date": target_date_str,
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

    # Helper to parse a match into net signed trillion
    def _parse_match_to_trillion(m_obj: Any) -> tuple[float, str, str, str]:
        d_str = m_obj.group("direction") or ""
        amt_str = m_obj.group("amount").replace(".", "").replace(",", ".") if "." in m_obj.group("amount") and "," in m_obj.group("amount") else m_obj.group("amount").replace(",", ".")
        u_str = m_obj.group("unit").lower()
        if not d_str:
            span_s = max(0, m_obj.start() - 50)
            span_e = min(len(text), m_obj.end() + 50)
            surr = text[span_s:span_e].lower()
            if any(w in surr for w in ["net sell", "jual bersih", "outflow", "distribusi"]):
                d_str = "net sell"
            elif any(w in surr for w in ["net buy", "beli bersih", "inflow", "akumulasi"]):
                d_str = "net buy"

        try:
            r_num = float(amt_str)
        except ValueError:
            return 0.0, "Unknown", amt_str, u_str

        if u_str in ["triliun", "trillion", "t"]:
            amt_t = r_num
        elif u_str in ["miliar", "milyar", "billion", "m", "b"]:
            amt_t = r_num / 1000.0
        else:
            amt_t = r_num

        is_s = any(w in d_str.lower() for w in ["sell", "jual", "outflow", "distribusi"])
        signed_t = -amt_t if is_s else amt_t
        dir_label = "Sell" if is_s else "Buy"
        return round(signed_t, 4), dir_label, amt_str, u_str

    # Multi-match analysis for scope isolation & crossing divergence
    parsed_matches = []
    text_lower = text.lower()
    for m in matches:
        signed_val, dir_lbl, amt_str, u_str = _parse_match_to_trillion(m)
        surround = text_lower[max(0, m.start() - 60):min(len(text_lower), m.end() + 60)]
        is_reg = any(k in surround for k in ["pasar reguler", "regular market", "papan reguler"])
        is_nego = any(k in surround for k in ["pasar negosiasi", "seluruh pasar", "all market", "total pasar", "pasar tunai", "crossing"])
        parsed_matches.append({
            "match": m,
            "net_trillion": signed_val,
            "direction": dir_lbl,
            "raw_figure": f"{amt_str} {u_str}",
            "is_regular": is_reg,
            "is_nego": is_nego,
        })

    reg_entries = [p for p in parsed_matches if p["is_regular"]]
    nego_entries = [p for p in parsed_matches if p["is_nego"] and not p["is_regular"]]

    divergence_alert = None
    if reg_entries and nego_entries:
        reg_net = reg_entries[0]["net_trillion"]
        nego_net = nego_entries[0]["net_trillion"]
        if nego_net > 0 and reg_net < 0:
            divergence_alert = f"DIVERGENCE: Net buy didorong crossing pasar negosiasi ({nego_entries[0]['raw_figure']}), namun pasar reguler net sell ({reg_entries[0]['raw_figure']})."
        elif reg_net > 0 and nego_net < 0:
            divergence_alert = f"DIVERGENCE: Pasar reguler net buy ({reg_entries[0]['raw_figure']}), namun seluruh pasar net sell akibat negosiasi."

    # Priority selection: prioritize explicit regular flow for trading decisions if both exist
    selected = reg_entries[0] if reg_entries else parsed_matches[0]

    net_signed_trillion = selected["net_trillion"]
    dir_str = selected["direction"]
    amount_str = selected["raw_figure"].split()[0]
    unit_str = selected["raw_figure"].split()[1] if len(selected["raw_figure"].split()) > 1 else ""

    # Apply Rp1 Trillion threshold
    if abs(net_signed_trillion) < threshold_trillion:
        signal = "Stagnant"
    elif net_signed_trillion >= threshold_trillion:
        signal = "Accumulation"
    else:
        signal = "Distribution"

    # Detect overall market scope
    is_negotiated = any(k in text_lower for k in ["pasar negosiasi", "seluruh pasar", "all market", "total pasar", "pasar tunai"])
    is_regular_explicit = any(k in text_lower for k in ["pasar reguler", "regular market", "papan reguler"])

    if is_negotiated and not is_regular_explicit:
        market_scope = "all_market"
    else:
        market_scope = "regular"

    return {
        "signal": signal,
        "net_trillion": round(net_signed_trillion, 4),
        "raw_figure": f"{amount_str} {unit_str}".strip(),
        "direction": dir_str,
        "market_scope": market_scope,
        "is_all_market": (market_scope == "all_market"),
        "regular_net_trillion": reg_entries[0]["net_trillion"] if reg_entries else (net_signed_trillion if market_scope == "regular" else None),
        "all_market_net_trillion": nego_entries[0]["net_trillion"] if nego_entries else (net_signed_trillion if market_scope == "all_market" else None),
        "divergence_alert": divergence_alert,
        "reason": "classified_successfully",
        "matched_date": matched_date,
        "target_date": target_date_str,
    }
