from dataclasses import dataclass, field
from typing import Any, Optional

"""
Nexus data schemas / contracts.

Actively used:
  - SourceRecord       — web_agent.py: each Tavily search result
  - MarketPrediction   — prediction_extractor.py → evening_reviewer.py

Reserved for future typed wiring (currently replaced by plain dicts):
  - SectorCall         — intended for structured sector signals in market_agent
  - ActualMarketData   — intended to type the 'actual' dict in evening_reviewer
  - ReviewResult       — intended to type the 'learning' dict returned by run_evening_review
"""



@dataclass
class SourceRecord:
    id: str
    category: str
    title: str
    url: str
    retrieved_at: str
    published_at: Optional[str] = None
    summary: str = ""
    freshness_days: Optional[int] = None
    freshness_status: str = "fresh"


@dataclass
class SectorCall:
    sector: str
    direction: str
    confidence: int
    rationale: str = ""
    related_tickers: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class MarketPrediction:
    date: str
    ihsg_signal: str
    ihsg_confidence: int
    foreign_flow_signal: str
    foreign_flow_net: str
    sector_bullish: list[str] = field(default_factory=list)
    sector_bearish: list[str] = field(default_factory=list)
    sector_neutral: list[str] = field(default_factory=list)
    recommended_tickers: list[str] = field(default_factory=list)
    key_risk: str = ""
    commodities_predicted: dict[str, str] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    raw_ihsg_signal: Optional[str] = None
    calibrated_confidence: Optional[float] = None
    lock_hash: Optional[str] = None
    locked_at: Optional[str] = None
    lock_status: Optional[str] = None
    hash_computed_at: Optional[str] = None
    created_at: Optional[str] = None
    out_of_sample_verified: Optional[bool] = None
    lock_note: Optional[str] = None


@dataclass
class ActualMarketData:
    date: str
    ihsg_signal: str = "Unknown"
    ihsg_close: Optional[float] = None
    ihsg_change_pct: Optional[float] = None
    ihsg_change_pts: Optional[float] = None
    foreign_flow_signal: str = "Unknown"
    usdidr: Optional[float] = None
    usdidr_change_pct: Optional[float] = None
    commodities: dict[str, Any] = field(default_factory=dict)
    sector_performance: str = ""
    top_movers: str = ""
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    date: str
    accuracy_score: int
    ihsg_correct: bool
    foreign_flow_correct: bool
    ihsg_predicted: str
    ihsg_actual: str
    foreign_flow_predicted: str
    foreign_flow_actual: str
    sector_accuracy: dict[str, Optional[bool]] = field(default_factory=dict)
    lessons: list[str] = field(default_factory=list)
    summary: str = ""
    rca_unanticipated: list[str] = field(default_factory=list)
    rca_overestimated: list[str] = field(default_factory=list)
    rca_underestimated: list[str] = field(default_factory=list)


def validate_artifact_data(filename: str, data: Any) -> tuple[bool, str]:
    """
    Validate an artifact payload against its structural contract.
    Returns (True, '') if valid, or (False, reason) if malformed.
    """
    if not isinstance(data, dict):
        return False, f"Artifact payload must be a dict, got {type(data).__name__}"

    if filename == "morning_prediction.json":
        for req in ["date", "ihsg_signal", "foreign_flow_signal"]:
            if req not in data:
                return False, f"Missing required field '{req}' in morning_prediction.json"
        return True, ""

    elif filename in ("evening_actuals.json", "actual_market_data.json"):
        if "date" not in data:
            return False, f"Missing required field 'date' in {filename}"
        return True, ""

    elif filename == "evening_review.json":
        for req in ["date", "accuracy_score"]:
            if req not in data:
                return False, f"Missing required field '{req}' in evening_review.json"
        return True, ""

    elif filename == "nexus_stats.json":
        if "total_sessions" not in data:
            return False, "Missing 'total_sessions' in nexus_stats.json"
        return True, ""

    elif filename == "telemetry.json":
        if "stats" not in data or "sessions" not in data:
            return False, "Missing 'stats' or 'sessions' in telemetry.json"
        return True, ""

    # Unknown artifact types pass by default
    return True, ""

