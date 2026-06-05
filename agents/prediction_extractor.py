import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class MarketPrediction:
    date: str
    ihsg_signal: str                    # "Bullish" / "Bearish" / "Neutral"
    ihsg_confidence: int                # 0-100
    foreign_flow_signal: str            # "Accumulation" / "Distribution" / "Stagnant/Sideways"
    foreign_flow_net: str               # e.g. "Net Buy Rp1.2T"
    sector_bullish: list = field(default_factory=list)
    sector_bearish: list = field(default_factory=list)
    sector_neutral: list = field(default_factory=list)
    recommended_tickers: list = field(default_factory=list)
    key_risk: str = ""
    commodities_predicted: dict = field(default_factory=dict)


def _extract_signal_confidence(text: str, section_num: int) -> tuple:
    pattern = rf"###\s*{section_num}\..*?Market Impact.*?\*\*(Bullish|Bearish|Neutral)\*\*.*?Confidence.*?(\d+)%"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1), int(match.group(2))
    return "Neutral", 50


def _extract_overall_ihsg(text: str) -> tuple:
    signals, confs = [], []
    for i in range(1, 5):
        s, c = _extract_signal_confidence(text, i)
        signals.append(s)
        confs.append(c)
    bullish = signals.count("Bullish")
    bearish = signals.count("Bearish")
    avg_conf = int(sum(confs) / len(confs)) if confs else 50
    if bullish > bearish:
        return "Bullish", avg_conf
    elif bearish > bullish:
        return "Bearish", avg_conf
    return "Neutral", avg_conf


def _extract_foreign_flow(text: str) -> tuple:
    match = re.search(r"###\s*5\.(.*?)(?:---|###\s*6\.)", text, re.DOTALL)
    if not match:
        return "Unknown", ""
    section = match.group(1)

    signal_match = re.search(r"Signal.*?:(.*?)(?:\n|$)", section, re.IGNORECASE)
    signal_text = signal_match.group(1).lower() if signal_match else ""
    if "accumulation" in signal_text or "net buy" in signal_text:
        signal = "Accumulation"
    elif "distribution" in signal_text or "net sell" in signal_text:
        signal = "Distribution"
    else:
        signal = "Stagnant/Sideways"

    net_match = re.search(r"Net Buy/Sell.*?:(.*?)(?:\n|$)", section, re.IGNORECASE)
    net_raw = net_match.group(1).strip() if net_match else ""
    return signal, net_raw


def _extract_sector_block(text: str) -> tuple:
    match = re.search(r"###\s*6\.(.*?)(?:---|###\s*7\.)", text, re.DOTALL)
    if not match:
        return [], [], []
    section = match.group(1)

    def _get(label: str) -> list:
        block = re.search(
            rf"\*\*{label}:\*\*(.*?)(?=\*\*(?:Bullish|Bearish|Neutral):|$)",
            section, re.DOTALL | re.IGNORECASE
        )
        if not block:
            return []
        return [m.strip() for m in re.findall(r"-\s+([^:\n]+):", block.group(1))]

    return _get("Bullish"), _get("Bearish"), _get("Neutral")


def _extract_tickers(text: str) -> list:
    tickers = set(re.findall(r'\b([A-Z]{4})\b', text))
    noise = {"IHSG", "FROM", "DATA", "WITH", "THIS", "THAT", "EACH", "ONLY",
             "THAN", "WHEN", "THEN", "OPEN", "HIGH", "WILL", "ALSO", "INTO",
             "MORE", "MOST", "NEXT", "BEEN", "HAVE", "WERE", "BULL", "BEAR"}
    return list(tickers - noise)


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


def extract_predictions(brief_text: str, date: str) -> "MarketPrediction":
    ihsg_signal, ihsg_conf = _extract_overall_ihsg(brief_text)
    ff_signal, ff_net      = _extract_foreign_flow(brief_text)
    bull, bear, neutral    = _extract_sector_block(brief_text)

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
    )


def prediction_to_json(pred: "MarketPrediction") -> str:
    return json.dumps(asdict(pred), ensure_ascii=False, indent=2)
