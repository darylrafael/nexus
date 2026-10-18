import re
import json
from dataclasses import asdict

from schemas import MarketPrediction


from utils.flow import classify_foreign_flow


def _extract_section_text(text: str, section_num: int) -> str:
    """Extract strictly the text of section_num without bleeding into subsequent sections."""
    pattern = rf"###\s*{section_num}\.(.*?)(?=###\s*\d+\.|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else ""


def _extract_signal_confidence(text: str, section_num: int) -> tuple[str | None, int | None, str | None]:
    section = _extract_section_text(text, section_num)
    if not section:
        return None, None, None

    impact_m = re.search(r"(?:Market Impact|Arah|Signal|Sentimen|Proyeksi)\s*[:*]*\s*(Bullish|Bearish|Neutral|Mixed)", section, re.IGNORECASE)
    conf_m = re.search(r"Confidence\s*[:*]*\s*(\d+)", section, re.IGNORECASE)

    raw_signal = impact_m.group(1).capitalize() if impact_m else "Neutral"
    normalized_signal = "Neutral" if raw_signal in ["Mixed", "Neutral"] else raw_signal
    if normalized_signal not in ["Bullish", "Bearish", "Neutral"]:
        normalized_signal = "Neutral"

    raw_conf = int(conf_m.group(1)) if conf_m else 50
    conf = max(0, min(100, raw_conf))

    return normalized_signal, conf, raw_signal


def _extract_overall_ihsg(text: str) -> tuple[str, int, str]:
    signals, confs, raw_signals = [], [], []
    for i in range(1, 5):
        s, c, raw_s = _extract_signal_confidence(text, i)
        if s is not None and c is not None:
            signals.append(s)
            confs.append(c)
            raw_signals.append(raw_s)

    if not signals:
        return "Neutral", 50, "Neutral"

    bullish = signals.count("Bullish")
    bearish = signals.count("Bearish")
    avg_conf = int(round(sum(confs) / len(confs))) if confs else 50
    avg_conf = max(0, min(100, avg_conf))

    if bullish > bearish:
        overall = "Bullish"
        raw_overall = "Bullish"
    elif bearish > bullish:
        overall = "Bearish"
        raw_overall = "Bearish"
    else:
        overall = "Neutral"
        raw_overall = "Mixed" if ("Mixed" in raw_signals or (bullish == bearish and bullish > 0)) else "Neutral"

    return overall, avg_conf, raw_overall


def _extract_foreign_flow(text: str, target_date_str: str | None = None) -> tuple[str, str]:
    section = _extract_section_text(text, 5)
    if not section:
        return "Unknown", ""

    net_match = re.search(r"Net Buy/Sell.*?:(.*?)(?:\n|$)", section, re.IGNORECASE)
    net_raw = net_match.group(1).strip() if net_match else ""

    signal_match = re.search(r"Signal.*?:(.*?)(?:\n|$)", section, re.IGNORECASE)
    signal_stated = signal_match.group(1).strip() if signal_match else ""

    flow_result = classify_foreign_flow(section, target_date_str=target_date_str)
    if flow_result["signal"] != "Unknown":
        signal = flow_result["signal"]
    elif signal_stated:
        st_lower = signal_stated.lower()
        if "accumulation" in st_lower or "net buy" in st_lower:
            signal = "Accumulation"
        elif "distribution" in st_lower or "net sell" in st_lower:
            signal = "Distribution"
        else:
            signal = "Stagnant"
    else:
        signal = "Unknown"

    return signal, net_raw


def _extract_sector_block(text: str) -> tuple:
    match = re.search(r"###\s*6\.(.*?)(?:---|###\s*7\.)", text, re.DOTALL)
    if not match:
        return [], [], []
    section = match.group(1)

    def _clean_sector(s: str) -> str:
        s = s.strip().replace('*', '').replace('[', '').replace(']', '').strip()
        s = re.sub(r'[:\–\—\-]+$', '', s).strip()
        return s

    def _get(label: str) -> list:
        block = re.search(
            rf"\*\*{label}:\*\*(.*?)(?=\*\*(?:Bullish|Bearish|Neutral):|$)",
            section, re.DOTALL | re.IGNORECASE
        )
        if not block:
            return []
        sectors = []
        for line in block.group(1).splitlines():
            line = line.strip()
            if not line.startswith("-"):
                continue
            m = re.match(r"^-\s+(?:\[|\*\*)?([^:\—\–]+?)(?:\]|\*\*)?\s*:\s*(.*)$", line)
            if not m:
                m = re.match(r"^-\s+(?:\[|\*\*)?([^:\—\–]+?)(?:\]|\*\*)?\s+[—–]\s*(.*)$", line)
            if m:
                clean = _clean_sector(m.group(1))
                if clean:
                    sectors.append(clean)
            else:
                raw = line.lstrip("-").strip()
                colon_idx = raw.find(":")
                if colon_idx != -1:
                    clean = _clean_sector(raw[:colon_idx])
                    if clean:
                        sectors.append(clean)
        return sectors

    return _get("Bullish"), _get("Bearish"), _get("Neutral")


from collections import Counter

_IDX_TICKERS_CACHE: set[str] | None = None

TICKER_STOPLIST = {
    "IHSG", "FROM", "DATA", "WITH", "THIS", "THAT", "EACH", "ONLY",
    "THAN", "WHEN", "THEN", "OPEN", "HIGH", "WILL", "ALSO", "INTO",
    "MORE", "MOST", "NEXT", "BEEN", "HAVE", "WERE", "BULL", "BEAR",
    "BANK", "FLOW", "DROP", "RATE", "REAL", "NETT", "SELL", "NEWS",
    "ASIA", "IDXR", "USDA", "DATE", "XRPL", "HTTP", "JSON", "POST",
    "RISK", "COST", "PEAK", "SLOW", "FAST", "SPOT", "NONE", "NULL",
    "INFO", "VIEW", "LINK", "TRUE", "CODE", "PAGE", "LQ45", "BEII",
    "IDRR", "USDD", "CPOO", "WIBB", "WALL", "DOWW", "TECH", "GOOD",
    "FOOD", "HOME", "CARE", "BEST", "EAST", "LIFE", "SAFE", "STAR",
    "GOLD", "COAL", "TIME", "YEAR", "WEEK", "DAYS", "PORT", "SAAT",
    "PADA", "DARI", "OLEH", "AKAN", "YANG", "JIKA", "AGAR", "BISA",
    "KINI", "LALU", "KITA", "KAMI", "MERE", "SEGI", "LUAR", "TREN",
    "SENT", "RUPS", "EMIT", "INDO", "NOTE"
}


def get_idx_universe() -> set[str]:
    global _IDX_TICKERS_CACHE
    if _IDX_TICKERS_CACHE is None:
        from core.paths import get_data_dir
        p = get_data_dir() / "idx_tickers.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                _IDX_TICKERS_CACHE = set(data.get("tickers", []))
            except Exception:
                _IDX_TICKERS_CACHE = set()
        else:
            _IDX_TICKERS_CACHE = set()
    return _IDX_TICKERS_CACHE


def _extract_tickers(text: str, max_tickers: int = 10) -> list[str]:
    """Extract valid IDX tickers from text.

    - Validates against official IDX universe in data/idx_tickers.json.
    - Filters out stoplist words (e.g. DATE, XRPL, IHSG, etc.).
    - Ranks deterministically by mention frequency (most frequent first, alphabetical tie-break).
    - Caps at max_tickers (default 10).
    """
    universe = get_idx_universe()
    raw_tokens = re.findall(r'\b([A-Z]{4})\b', text)
    valid_candidates = []

    for t in raw_tokens:
        if t in TICKER_STOPLIST:
            continue
        if universe and t not in universe:
            continue
        valid_candidates.append(t)

    if not valid_candidates:
        return []

    counts = Counter(valid_candidates)
    ranked = sorted(counts.keys(), key=lambda t: (-counts[t], t))
    return ranked[:max_tickers]


def extract_ticker_reasons(text: str, tickers: list[str]) -> dict[str, str]:
    """Extract a one-line clean context reason for each ticker from the brief."""
    reasons = {}
    lines = text.splitlines()
    for t in tickers:
        found_reason = ""
        for line in lines:
            line_clean = line.strip().replace("*", "").replace("#", "")
            if t in line_clean:
                cleaned = re.sub(r'\[.*?\]', '', line_clean).strip()
                cleaned = re.sub(r'\s+', ' ', cleaned)
                if len(cleaned) > 10:
                    found_reason = cleaned[:120]
                    break
        reasons[t] = found_reason or "Catalyst identified in market brief."
    return reasons


def _extract_key_risk(text: str) -> str:
    match = re.search(r"###\s*7\..*?-\s+(.*?)(?:---|$)", text, re.DOTALL)
    return match.group(1).strip()[:300] if match else ""


def _extract_commodity_signals(text: str) -> dict:
    match = re.search(r"###\s*3\.(.*?)(?:---|###\s*4\.)", text, re.DOTALL)
    if not match:
        return {}
    section = match.group(1)
    commodities = {}
    for name in ["Oil", "Coal", "CPO", "Nickel", "Natural Gas"]:
        m = re.search(rf"{name}.*?(Bullish|Bearish|Neutral)", section, re.IGNORECASE)
        if m:
            commodities[name] = m.group(1)
    return commodities


def _extract_source_ids(text: str) -> list:
    return sorted(set(re.findall(r"\bsrc_[a-f0-9]{10}\b", text)))


def extract_predictions(brief_text: str, date: str) -> "MarketPrediction":
    ihsg_signal, ihsg_conf, raw_ihsg = _extract_overall_ihsg(brief_text)
    ff_signal, ff_net                 = _extract_foreign_flow(brief_text, target_date_str=date)
    bull, bear, neutral               = _extract_sector_block(brief_text)

    from utils.stats import compute_empirical_calibrated_confidence
    from core.paths import get_memory_dir

    dir_correct = 0
    dir_scorable = 0
    stats_file = get_memory_dir() / "nexus_stats.json"
    if stats_file.exists():
        try:
            st = json.loads(stats_file.read_text(encoding="utf-8"))
            dir_correct = int(st.get("direction_correct_count") or 0)
            dir_scorable = int(st.get("direction_scorable_sessions") or 0)
        except Exception:
            pass

    cal_info = compute_empirical_calibrated_confidence(
        direction_correct=dir_correct,
        direction_scorable=dir_scorable,
        stated_confidence_pct=ihsg_conf,
    )
    calibrated_conf = cal_info["calibrated_confidence_pct"]

    return MarketPrediction(
        date=date,
        ihsg_signal=ihsg_signal,
        ihsg_confidence=ihsg_conf,
        foreign_flow_signal=ff_signal,
        foreign_flow_net=ff_net,
        sector_bullish=[s.strip() for s in bull],
        sector_bearish=[s.strip() for s in bear],
        sector_neutral=[s.strip() for s in neutral],
        recommended_tickers=_extract_tickers(brief_text),
        key_risk=_extract_key_risk(brief_text),
        commodities_predicted=_extract_commodity_signals(brief_text),
        evidence_ids=_extract_source_ids(brief_text),
        raw_ihsg_signal=raw_ihsg,
        calibrated_confidence=calibrated_conf,
    )


def prediction_to_json(pred: "MarketPrediction") -> str:
    return json.dumps(asdict(pred), ensure_ascii=False, indent=2)
