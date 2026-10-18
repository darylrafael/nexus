"""
tests/test_phase2_scoring_fixes.py

Comprehensive tests verifying Phase 2 fixes:
1. classify_direction canonical threshold logic.
2. classify_foreign_flow IDR parsing (Triliun, Miliar), Rp1T threshold, and date mismatch rejection.
3. fetch_ihsg_snapshot target date assertion and backwards walk on null prev close.
4. prediction_extractor section scoping, Mixed -> Neutral mapping, and confidence bounds [0, 100].
5. validator.check_numeric_consistency non-destructive checking.
6. Canonical stats & accuracy calculations (scorable denominators, separated metrics).
"""
import pytest
import pandas as pd

from utils.direction import classify_direction
from utils.flow import classify_foreign_flow
from utils.stats import compute_session_accuracy, compute_canonical_stats
from agents.validator import check_numeric_consistency, validate_predictions_post_hoc
from agents.prediction_extractor import extract_predictions
import data_sources.market_data as md


# ── 1. Canonical Direction Classification ────────────────────────────────────

def test_classify_direction_thresholds():
    assert classify_direction(0.21) == "Bullish"
    assert classify_direction(1.50) == "Bullish"
    assert classify_direction(-0.21) == "Bearish"
    assert classify_direction(-1.50) == "Bearish"

    # Within [-0.20%, +0.20%] is Neutral
    assert classify_direction(0.20) == "Neutral"
    assert classify_direction(-0.20) == "Neutral"
    assert classify_direction(0.0) == "Neutral"
    assert classify_direction(0.05) == "Neutral"
    assert classify_direction(-0.15) == "Neutral"

    # None / non-numeric
    assert classify_direction(None) == "Unknown"
    assert classify_direction("invalid") == "Unknown"


# ── 2. Foreign Flow Classification & Date Rejection ──────────────────────────

def test_classify_foreign_flow_parsing():
    # >= Rp1T Net Buy -> Accumulation
    text1 = "Investor asing mencatatkan aksi net buy sebesar Rp 1,50 triliun pada perdagangan hari ini (2026-10-07)."
    res1 = classify_foreign_flow(text1, target_date_str="2026-10-07")
    assert res1["signal"] == "Accumulation"
    assert pytest.approx(res1["net_trillion"], 0.01) == 1.50

    # <= -Rp1T Net Sell -> Distribution
    text2 = "Asing membukukan net sell sebesar Rp 2,75 triliun di seluruh pasar modal pada 2026-10-07."
    res2 = classify_foreign_flow(text2, target_date_str="2026-10-07")
    assert res2["signal"] == "Distribution"
    assert pytest.approx(res2["net_trillion"], 0.01) == -2.75

    # Sub-1T (e.g. Rp500 Miliar) -> Stagnant
    text3 = "Investor asing membukukan aksi beli bersih tipis net buy Rp 500 miliar pada 2026-10-07."
    res3 = classify_foreign_flow(text3, target_date_str="2026-10-07")
    assert res3["signal"] == "Stagnant"
    assert pytest.approx(res3["net_trillion"], 0.01) == 0.50

    text4 = "Asing mencatatkan net sell Rp 850 miliar pada 2026-10-07."
    res4 = classify_foreign_flow(text4, target_date_str="2026-10-07")
    assert res4["signal"] == "Stagnant"
    assert pytest.approx(res4["net_trillion"], 0.01) == -0.85


def test_classify_foreign_flow_date_mismatch_rejection():
    # Article contains outdated month (e.g. August article scraped for an October run)
    text_stale = "Asing Net Buy atau Net Sell IHSG Agustus 2026: tercatat net buy tipis Rp942,0 miliar sepanjang 10/8/2026."
    res = classify_foreign_flow(text_stale, target_date_str="2026-10-07")
    assert res["signal"] == "Unknown"
    assert res.get("reason") == "date_mismatch_rejected"


# ── 3. Market Data Target Date Assertion & Backwards Walk ────────────────────

def test_fetch_ihsg_snapshot_missing_target_date_raises(monkeypatch):
    # Mock direct yahoo to fail so it falls back to yfinance mock
    def mock_requests_get(*args, **kwargs):
        raise Exception("direct yahoo offline")

    monkeypatch.setattr(md.requests, "get", mock_requests_get)

    # Mock yf.download / yf.Ticker returning candles without target date
    dates = pd.date_range("2026-09-01", "2026-09-05", freq="D")
    df = pd.DataFrame({
        "Close": [6000.0, 6010.0, 6020.0, 6030.0, 6040.0],
        "Open": [5990.0] * 5,
        "High": [6050.0] * 5,
        "Low": [5980.0] * 5,
        "Volume": [1000] * 5,
    }, index=dates)

    class MockTicker:
        def history(self, *args, **kwargs):
            return df

    monkeypatch.setattr(md.yf, "Ticker", lambda ticker: MockTicker())
    monkeypatch.setattr(md.yf, "download", lambda *args, **kwargs: df)

    with pytest.raises(ValueError, match="does not contain requested target date candle"):
        md.fetch_ihsg_snapshot(target_date="2026-09-20")


def test_fetch_ihsg_snapshot_backward_walk_on_null_prev(monkeypatch):
    def mock_requests_get(*args, **kwargs):
        raise Exception("direct yahoo offline")

    monkeypatch.setattr(md.requests, "get", mock_requests_get)

    # Target date candle exists, but previous candle is NaN and no prior valid candles exist
    dates = pd.date_range("2026-09-20", "2026-09-21", freq="D")
    df = pd.DataFrame({
        "Close": [float("nan"), 6374.91],
        "Open": [float("nan"), 6300.0],
        "High": [float("nan"), 6400.0],
        "Low": [float("nan"), 6250.0],
        "Volume": [0, 0],
    }, index=dates)

    class MockTicker:
        def history(self, *args, **kwargs):
            return df

    monkeypatch.setattr(md.yf, "Ticker", lambda ticker: MockTicker())
    monkeypatch.setattr(md.yf, "download", lambda *args, **kwargs: df)

    snap = md.fetch_ihsg_snapshot(target_date="2026-09-21")
    assert snap["ihsg_close"] == 6374.91
    assert snap["ihsg_prev"] is None
    assert snap["ihsg_change_pct"] is None
    assert snap["ihsg_signal"] == "Unscorable"


# ── 4. Prediction Extractor: Scoping, Mixed Mapping & Bounds ─────────────────

def test_extract_predictions_scoping_and_mapping():
    # Brief with Mixed signal and missing middle sections (to ensure no DOTALL bleed)
    sample_brief = """
### 1. Proyeksi IHSG Hari Ini
- **Arah**: Mixed
- **Rentang**: 6800 - 6850
- **Confidence**: 150% (should be clamped to 100)
- **Key Risk**: Volatilitas global

### 5. Arus Dana Asing (Foreign Flow)
- **Arah**: Akumulasi (Net buy Rp 1,8 Triliun)

### 7. Ticker Watchlist
- BBCA, BBRI, BMRI
"""
    pred = extract_predictions(sample_brief, date="2026-10-07")
    # Raw signal preserved
    assert pred.raw_ihsg_signal == "Mixed"
    # Canonical mapped to Neutral
    assert pred.ihsg_signal == "Neutral"
    # Clamped to 100%
    assert pred.ihsg_confidence == 100
    # Foreign flow mapped
    assert pred.foreign_flow_signal == "Accumulation"
    # Middle missing sections did not bleed
    assert pred.sector_bullish == []
    assert pred.sector_bearish == []


# ── 5. Validator: Non-destructive Numeric Consistency Check ──────────────────

def test_check_numeric_consistency_flags_contradiction_without_mutation():
    text = "IHSG hari ini diproyeksikan menguat pesat sebesar -1.85% ke level 6.200."
    contradictions = check_numeric_consistency(text)
    assert len(contradictions) > 0
    assert "positive direction term used with negative percentage" in contradictions[0]["issue"].lower()

    # validate_predictions_post_hoc does not mutate the text
    validated = validate_predictions_post_hoc(text)
    assert validated == text  # Text preserved verbatim


# ── 6. Canonical Stats & Scoring Computations ────────────────────────────────

def test_compute_session_accuracy():
    # Both correct, 1 sector scorable (correct) -> 3 / 3 = 100%
    assert compute_session_accuracy(True, True, {"Energy": True}) == 100

    # 50% Index (True) + 20% Flow (False) + 0 scorable sectors -> 0.50 / 0.70 = 71%
    assert compute_session_accuracy(True, False, {"Energy": None}) == 71

    # 50% Index (False) + 20% Flow (True) + 30% Sector (True) -> 0.50*0 + 0.20*1 + 0.30*1 = 50%
    assert compute_session_accuracy(False, True, {"Energy": True}) == 50

    # Unscorable day (all None) -> returns None
    assert compute_session_accuracy(None, None, {"Energy": None}) is None


def test_compute_canonical_stats_scorable_denominators():
    reviews = [
        {
            "date": "2026-09-22",
            "ihsg_correct": True,
            "foreign_flow_correct": False,
            "sector_accuracy": {"Energy": True, "Tech": False},
            "accuracy_score": 67,
            "lessons": ["Lesson 1"],
            "rca_unanticipated": ["Surprise rate hike"],
        },
        {
            "date": "2026-09-23",
            "ihsg_correct": None,  # Unscorable direction day
            "foreign_flow_correct": True,
            "sector_accuracy": {"Energy": True},
            "accuracy_score": 100,
            "lessons": ["Lesson 2"],
            "rca_unanticipated": [],
        },
        {
            "date": "2026-09-24",
            "ihsg_correct": False,
            "foreign_flow_correct": None,  # Unscorable flow day
            "sector_accuracy": {},
            "accuracy_score": 0,
            "lessons": ["Lesson 1"],  # Duplicate lesson
            "rca_unanticipated": ["Surprise rate hike"],
        },
    ]

    # Create 9 reviews (3 cycles) so direction and flow have n=6 scorable (>=5 threshold)
    extended_reviews = []
    for cycle in range(3):
        for idx, base in enumerate(reviews):
            item = dict(base)
            day = 20 + cycle * 3 + idx
            item["date"] = f"2026-09-{day:02d}"
            extended_reviews.append(item)

    stats = compute_canonical_stats(extended_reviews)
    assert stats["total_sessions"] == 9

    # Direction: 6 scorable sessions, 3 correct -> 50.0%
    assert stats["direction_scorable_sessions"] == 6
    assert stats["direction_correct_count"] == 3
    assert stats["direction_accuracy_pct"] == 50.0

    # Flow: 6 scorable sessions, 3 correct -> 50.0%
    assert stats["flow_scorable_sessions"] == 6
    assert stats["flow_correct_count"] == 3
    assert stats["flow_accuracy_pct"] == 50.0

    # Sector: 9 scorable items, 6 correct -> 66.7%
    assert stats["sector_verifiable_count"] == 9
    assert stats["sector_correct_count"] == 6
    assert stats["sector_accuracy_pct"] == 66.7

    # Rolling avg: (67 + 100 + 0) / 3 = 55.7%
    assert stats["rolling_avg_accuracy"] == 55.7

    # Deduplicated lessons
    assert len(stats["all_lessons"]) == 2
    assert stats["missed_factor_counts"]["Surprise rate hike"] == 6
