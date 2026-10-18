"""
tests/test_phase3_stats.py

Tests for scorable blend, Wilson confidence intervals, baselines, and payoff metrics.
"""
from utils.stats import (
    compute_session_accuracy,
    compute_wilson_ci,
    compute_canonical_stats,
)


def test_session_accuracy_dynamic_blend():
    # 1. All 3 scorable: 50% index (1) + 30% sector (0.5) + 20% flow (0)
    # Expected: 50*1 + 30*0.5 + 20*0 = 50 + 15 + 0 = 65%
    sec_acc = {"s1": True, "s2": False}
    score = compute_session_accuracy(
        ihsg_correct=True,
        foreign_flow_correct=False,
        sector_accuracy=sec_acc,
    )
    assert score == 65

    # 2. Flow unscorable (None):
    # Normalized weights: Index (50/80 = 62.5%), Sector (30/80 = 37.5%)
    # Index True (1), Sector all True (1) -> 100%
    score_no_flow = compute_session_accuracy(
        ihsg_correct=True,
        foreign_flow_correct=None,
        sector_accuracy={"s1": True},
    )
    assert score_no_flow == 100

    # 3. All unscorable -> None, never 0
    score_none = compute_session_accuracy(
        ihsg_correct=None,
        foreign_flow_correct=None,
        sector_accuracy={"s1": None},
    )
    assert score_none is None


def test_wilson_confidence_interval():
    lower, upper = compute_wilson_ci(k=6, n=10)
    assert lower is not None and upper is not None
    # For 6/10 (60%), 95% Wilson CI is roughly [31.3%, 83.2%]
    assert 25.0 <= lower <= 35.0
    assert 75.0 <= upper <= 90.0

    # Edge cases
    assert compute_wilson_ci(0, 0) == (None, None)


def test_canonical_stats_baselines_and_payoffs():
    reviews = [
        {
            "date": "2026-10-01",
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -1.02,
            "ihsg_correct": False,
            "ihsg_confidence": 80,
            "foreign_flow_correct": True,
            "sector_accuracy": {"s1": False},
            "accuracy_score": 20,
        },
        {
            "date": "2026-10-02",
            "ihsg_predicted": "Bearish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.50,
            "ihsg_correct": True,
            "ihsg_confidence": 75,
            "foreign_flow_correct": True,
            "sector_accuracy": {"s1": True},
            "accuracy_score": 100,
        },
    ]

    stats = compute_canonical_stats(reviews)
    assert stats["total_sessions"] == 2
    assert stats["is_sample_sufficient"] is False
    assert "Insufficient sample" in stats["sample_warning"]
    # Per Phase C1: When scorable n < 5, accuracy percentage is suppressed (None)
    assert stats["direction_accuracy_pct"] is None
    assert stats["direction_info"]["label"] == "Insufficient data"

    # Baselines: 2 actual Bearish sessions -> always_bearish = 100.0%
    assert stats["baselines"]["always_bearish_pct"] == 100.0
    assert stats["baselines"]["always_bullish_pct"] == 0.0

    # Payoffs:
    # Day 1: Bullish pred, actual -1.02% -> Long payoff = -102.0 bps
    # Day 2: Bearish pred, actual -0.50% -> Short payoff = +50.0 bps
    assert stats["payoff"]["long_only_total_bps"] == -102.0
    assert stats["payoff"]["short_only_total_bps"] == 50.0
    assert stats["payoff"]["long_short_total_bps"] == -52.0
