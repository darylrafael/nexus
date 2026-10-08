"""
tests/test_phase_b2_learning_lifecycle.py

Comprehensive tests verifying Phase B2:
1. detect_market_regime classification logic.
2. evaluate_heuristic_lifecycle empirical states (ACTIVE, HYPOTHESIS, SUPERSEDED, UNTESTED).
3. build_learning_context with exponential time decay, regime prioritization, and lifecycle badging.
4. update_performance_stats canonical heuristics lifecycle tracking.
"""
import pytest
from datetime import datetime, timedelta

from memory.learning_store import (
    detect_market_regime,
    evaluate_heuristic_lifecycle,
    build_learning_context,
    update_performance_stats,
    load_performance_stats,
    MAX_LESSONS_INJECTED,
)
from core.time import jakarta_now


def test_detect_market_regime():
    # Bullish trend
    assert detect_market_regime({"ihsg_actual": "Bullish", "ihsg_actual_pct": 0.65}) == "BULLISH_TREND"
    assert detect_market_regime({"ihsg_actual_pct": 0.55}) == "BULLISH_TREND"

    # Bearish trend
    assert detect_market_regime({"ihsg_actual": "Bearish", "ihsg_actual_pct": -0.75}) == "BEARISH_TREND"
    assert detect_market_regime({"ihsg_actual_pct": -0.60}) == "BEARISH_TREND"

    # Sideways / volatile
    assert detect_market_regime({"ihsg_actual": "Neutral", "ihsg_actual_pct": 0.10}) == "SIDEWAYS_VOLATILE"
    assert detect_market_regime({"ihsg_actual_pct": -0.15}) == "SIDEWAYS_VOLATILE"

    # Edge cases
    assert detect_market_regime({}) == "SIDEWAYS_VOLATILE"
    assert detect_market_regime(None) == "SIDEWAYS_VOLATILE"
    assert detect_market_regime({"ihsg_actual_pct": "invalid"}) == "SIDEWAYS_VOLATILE"


def test_evaluate_heuristic_lifecycle():
    reviews = [
        {
            "date": "2026-10-01",
            "ihsg_correct": True,
            "ihsg_actual": "Bullish",
            "ihsg_actual_pct": 0.8,
            "market_regime": "BULLISH_TREND",
            "lessons": ["Rule Alpha: High foreign inflow confirms bullish breakout."],
            "summary": "Day 1 bull"
        },
        {
            "date": "2026-10-02",
            "ihsg_correct": True,
            "ihsg_actual": "Bullish",
            "ihsg_actual_pct": 0.6,
            "market_regime": "BULLISH_TREND",
            "lessons": [
                "Rule Alpha: High foreign inflow confirms bullish breakout.",
                "Rule Beta: Buy commodities on USD dip."
            ],
            "summary": "Day 2 bull"
        },
        {
            "date": "2026-10-03",
            "ihsg_correct": False,
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.9,
            "market_regime": "BEARISH_TREND",
            "lessons": [
                "Rule Beta: Buy commodities on USD dip.",
                "Rule Gamma: Sideways chop warrants tight trailing stops."
            ],
            "summary": "Day 3 bear"
        },
        {
            "date": "2026-10-04",
            "ihsg_correct": False,
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.7,
            "market_regime": "BEARISH_TREND",
            "lessons": ["Rule Beta: Buy commodities on USD dip."],
            "summary": "Day 4 bear"
        }
    ]

    heuristics = evaluate_heuristic_lifecycle(reviews)
    h_map = {h["rule"]: h for h in heuristics}

    # Rule Alpha: observed 2, validated 2, contradicted 0 -> 100% -> ACTIVE
    assert "Rule Alpha: High foreign inflow confirms bullish breakout." in h_map
    alpha = h_map["Rule Alpha: High foreign inflow confirms bullish breakout."]
    assert alpha["status"] == "ACTIVE"
    assert alpha["observed"] == 2
    assert alpha["validated"] == 2
    assert alpha["validation_rate"] == 100.0
    assert "BULLISH_TREND" in alpha["regimes"]

    # Rule Beta: observed 3, validated 1 (2026-10-02), contradicted 2 (2026-10-03, 2026-10-04) -> 33.3% -> SUPERSEDED
    assert "Rule Beta: Buy commodities on USD dip." in h_map
    beta = h_map["Rule Beta: Buy commodities on USD dip."]
    assert beta["status"] == "SUPERSEDED"
    assert beta["observed"] == 3
    assert beta["validated"] == 1
    assert beta["contradicted"] == 2
    assert beta["validation_rate"] < 50.0

    # Rule Gamma: observed 1, contradicted 1 -> HYPOTHESIS
    assert "Rule Gamma: Sideways chop warrants tight trailing stops." in h_map
    gamma = h_map["Rule Gamma: Sideways chop warrants tight trailing stops."]
    assert gamma["status"] == "HYPOTHESIS"
    assert gamma["observed"] == 1
    assert gamma["validated"] == 0


def test_build_learning_context_decay_and_regime():
    now_str = jakarta_now().strftime("%Y-%m-%d")
    recent_date = (jakarta_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    stale_date = (jakarta_now() - timedelta(days=20)).strftime("%Y-%m-%d")

    learnings = [
        {
            "date": stale_date,
            "ihsg_correct": True,
            "ihsg_actual": "Bullish",
            "ihsg_actual_pct": 0.7,
            "market_regime": "BULLISH_TREND",
            "lessons": ["Old Bull Rule: Stale wisdom from weeks ago."],
            "accuracy_score": 85
        },
        {
            "date": recent_date,
            "ihsg_correct": True,
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.8,
            "market_regime": "BEARISH_TREND",
            "lessons": ["Recent Bear Rule: Focus on liquidity drain."],
            "accuracy_score": 90
        }
    ]

    # Test with BEARISH_TREND current regime
    ctx_bearish = build_learning_context(learnings, current_regime="BEARISH_TREND")
    assert "Past Performance Calibration" in ctx_bearish
    assert "Recent Bear Rule: Focus on liquidity drain." in ctx_bearish
    assert "[ACTIVE]" in ctx_bearish or "[HYPOTHESIS]" in ctx_bearish
    assert "BEARISH_TREND" in ctx_bearish

    # Bearish rule should appear first because of recentness + regime boost
    bear_idx = ctx_bearish.find("Recent Bear Rule")
    bull_idx = ctx_bearish.find("Old Bull Rule")
    assert bear_idx < bull_idx


def test_update_performance_stats_lifecycle_integration(tmp_path, monkeypatch):
    import memory.learning_store as ls

    # Redirect ARTIFACT_ROOT to temporary path
    monkeypatch.setattr(ls, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(ls, "write_note", lambda note, content: True)

    fake_artifacts = {}

    def mock_save(date, name, data):
        fake_artifacts[f"{date}/{name}"] = data
        return True

    def mock_load(date, name):
        return fake_artifacts.get(f"{date}/{name}")

    monkeypatch.setattr(ls, "save_json_artifact", mock_save)
    monkeypatch.setattr(ls, "load_json_artifact", mock_load)

    review_day = {
        "date": "2026-10-08",
        "ihsg_correct": True,
        "ihsg_actual": "Bullish",
        "ihsg_actual_pct": 0.45,
        "market_regime": "BULLISH_TREND",
        "lessons": [
            "Test Heuristic 1: Keep cash reserves during macro rate shifts.",
            "Test Heuristic 2: Rebalance defensive stocks."
        ],
        "accuracy_score": 92
    }

    res = update_performance_stats(review_day)
    assert res is True

    saved = fake_artifacts.get("global/nexus_stats.json")
    assert saved is not None
    assert "heuristics" in saved
    assert saved["active_heuristics_count"] == 2
    assert saved["superseded_heuristics_count"] == 0
    assert saved["hypothesis_heuristics_count"] == 0
    assert saved["total_sessions"] >= 1

