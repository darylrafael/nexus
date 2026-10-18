"""Playwright fixture tests for Phase 7.6: Stale, Fresh-Today, and Missing-Field UI States."""

from __future__ import annotations

import datetime
import json
from typing import Any, Dict

from playwright.sync_api import sync_playwright


def _base_stats_fixture(
    *,
    is_stale: bool,
    latest_date: str,
    trading_days_since: int,
    latest_review_overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    review: Dict[str, Any] = {
        "date": latest_date,
        "ihsg_predicted": "Bearish",
        "ihsg_confidence": 80,
        "calibrated_confidence": 49.7,
        "ihsg_actual": "Bearish",
        "ihsg_actual_pct": -0.45,
        "ihsg_close": 6150.0,
        "ihsg_high": 6190.0,
        "ihsg_low": 6120.0,
        "ihsg_atr14": 70.0,
        "is_true_atr14": True,
        "ihsg_correct": True,
        "isPendingReview": False,
        "isUnscorable": False,
        "isWebFallback": False,
        "foreign_flow_predicted": "Net Sell",
        "foreign_flow_actual": "Net Sell Rp 420B",
        "foreign_flow_correct": True,
        "actual_usdidr": 15650,
        "accuracy_score": 78.5,
        "payoff_bps": 45,
        "summary": "Bearish macro pressure from global yields weighed on IDX financials.",
        "key_risk": "Unexpected BI rate intervention could trigger short covering.",
        "lock_status": "retroactive",
        "locked_at": None,
        "hash_computed_at": "2026-10-15",
        "lock_hash": "9f8e7d6c5b4a3210",
        "sector_accuracy": {"Keuangan": True, "Energi": False},
        "actual_commodities": {
            "Coal": {"name": "Coal", "price": 145.2, "change_pct": -1.2, "signal": "Down"}
        },
        "lessons": [],
        "rca_unanticipated": [],
        "rca_underestimated": [],
        "rca_overestimated": [],
    }
    if latest_review_overrides:
        review.update(latest_review_overrides)

    return {
        "success": True,
        "isDemo": False,
        "holidays": {"2026-12-25": "Christmas Day"},
        "pipelineHealth": {
            "isStale": is_stale,
            "latestDate": latest_date,
            "tradingDaysSinceLatest": trading_days_since,
            "staleMessage": (
                f"Automated pipeline paused since {latest_date} ({trading_days_since} trading days ago)."
                if is_stale
                else "Pipeline is current."
            ),
            "mockDataDetected": False,
            "excludedMockRuns": [],
        },
        "stats": {
            "totalSessions": 12,
            "scorableSessions": 12,
            "avgAccuracy": 46.8,
            "winRate": 41.7,
            "historyRescoredAt": "2026-10-15",
        },
        "nexusStats": {
            "sample_size_n": 12,
            "direction_scorable_sessions": 12,
            "direction_correct_count": 5,
            "direction_accuracy_pct": 41.7,
            "direction_ci_95": {"lower_pct": 19.3, "upper_pct": 68.0},
            "baselines": {
                "always_bearish_pct": 66.7,
                "always_bearish_count": 8,
                "always_bearish_total": 12,
                "persistence_pct": 63.6,
                "persistence_correct_count": 7,
                "persistence_scorable_sessions": 11,
                "always_bullish_pct": 33.3,
                "always_bullish_count": 4,
                "always_bullish_total": 12,
            },
            "payoff": {
                "long_only_total_bps": -176.0,
                "short_only_total_bps": 244.0,
                "long_short_total_bps": 68.0,
            },
            "calibration": {
                "sample_size_n": 12,
                "average_stated_confidence_pct": 79.6,
                "realized_hit_rate_pct": 41.7,
                "calibrated_confidence_pct": 49.7,
                "brier_score": 0.3996,
                "prior_pct": 55.0,
                "prior_strength_n0": 30,
                "status_label": "illustrative shrinkage estimate",
            },
        },
        "reviews": [review],
        "recentLessons": [],
        "telemetry": {"recentSessions": []},
    }


def run_playwright_fixture_state_checks(target_url: str = "http://127.0.0.1:3002") -> Dict[str, Any]:
    """Run Playwright verification against stale, fresh-today, and missing-field fixtures."""
    wib_today = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=7))
    ).strftime("%Y-%m-%d")

    stale_payload = _base_stats_fixture(
        is_stale=True,
        latest_date="2026-10-08",
        trading_days_since=6,
    )
    fresh_payload = _base_stats_fixture(
        is_stale=False,
        latest_date=wib_today,
        trading_days_since=0,
        latest_review_overrides={
            "ihsg_predicted": "Bullish",
            "ihsg_confidence": 75,
            "calibrated_confidence": 51.2,
            "isPendingReview": True,
            "ihsg_actual": None,
            "ihsg_actual_pct": None,
            "ihsg_correct": None,
            "lock_status": "locked_pre_open",
            "created_at": f"{wib_today}T06:55:10+07:00",
            "locked_at": "06:55 WIB",
            "lock_hash": "a1b2c3d4e5f60789",
        },
    )
    missing_field_payload = _base_stats_fixture(
        is_stale=False,
        latest_date=wib_today,
        trading_days_since=0,
        latest_review_overrides={
            "actual_usdidr": None,
            "foreign_flow_actual": None,
            "foreign_flow_predicted": None,
            "ihsg_close": None,
            "previous_close": None,
            "ihsg_high": None,
            "ihsg_low": None,
            "ihsg_atr14": None,
            "accuracy_score": None,
            "isUnscorable": True,
            "actual_commodities": {},
            "recommended_tickers": [],
            "actionable_watchlist": [],
        },
    )

    results: Dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Stale state fixture
        ctx_stale = browser.new_context(viewport={"width": 390, "height": 844})
        page_stale = ctx_stale.new_page()
        page_stale.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(stale_payload),
            ),
        )
        page_stale.goto(target_url, wait_until="networkidle")
        page_stale.wait_for_timeout(400)
        stale_text = page_stale.inner_text("body")
        stale_banner_visible = page_stale.locator(".stale-pipeline-banner").is_visible()
        assert stale_banner_visible, "Expected stale banner to be visible in stale fixture state"
        assert "No new call generated today" in stale_text
        assert "Hash added retroactively; not proof of pre-open lock" in stale_text
        results["stale_fixture"] = {
            "passed": True,
            "staleBannerVisible": stale_banner_visible,
            "hasNoNewCall": "No new call generated today" in stale_text,
            "hasRetroactiveNotice": "Hash added retroactively; not proof of pre-open lock" in stale_text,
        }
        ctx_stale.close()

        # 2. Fresh-today state fixture
        ctx_fresh = browser.new_context(viewport={"width": 390, "height": 844})
        page_fresh = ctx_fresh.new_page()
        page_fresh.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(fresh_payload),
            ),
        )
        page_fresh.goto(target_url, wait_until="networkidle")
        page_fresh.wait_for_timeout(400)
        fresh_text = page_fresh.inner_text("body")
        fresh_stale_count = page_fresh.locator(".stale-pipeline-banner").count()
        assert fresh_stale_count == 0, "Expected no stale banner in fresh-today fixture state"
        assert "TODAY'S PRE-MARKET CALL" in fresh_text
        assert "No new call generated today" not in fresh_text
        assert "Locked at 06:55 WIB" in fresh_text
        results["fresh_today_fixture"] = {
            "passed": True,
            "staleBannerCount": fresh_stale_count,
            "hasTodaysCallHeader": "TODAY'S PRE-MARKET CALL" in fresh_text,
            "hasPreOpenLock": "Locked at 06:55 WIB" in fresh_text,
        }
        ctx_fresh.close()

        # 3. Missing-field state fixture
        ctx_missing = browser.new_context(viewport={"width": 390, "height": 844})
        page_missing = ctx_missing.new_page()
        page_missing.route(
            "**/api/stats",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(missing_field_payload),
            ),
        )
        page_missing.goto(target_url, wait_until="networkidle")
        page_missing.wait_for_timeout(400)
        # Open workbench to inspect missing USD/IDR, foreign flow, and ATR fields
        page_missing.get_by_text("Open Session Workbench").click()
        page_missing.wait_for_timeout(300)
        missing_text = page_missing.inner_text("body")
        assert "Unavailable" in missing_text, "Expected 'Unavailable' for missing USD/IDR"
        assert "Unscorable" in missing_text, "Expected 'Unscorable' for missing accuracy_score"
        assert "NaN" not in missing_text, "Found 'NaN' in missing-field state"
        assert "undefined" not in missing_text, "Found 'undefined' in missing-field state"
        assert "Rp 0" not in missing_text, "Found fabricated 'Rp 0' in missing-field state"
        results["missing_field_fixture"] = {
            "passed": True,
            "hasUnavailable": "Unavailable" in missing_text,
            "hasUnscorable": "Unscorable" in missing_text,
            "zeroNaNOrUndefined": ("NaN" not in missing_text and "undefined" not in missing_text),
        }
        ctx_missing.close()

        browser.close()

    return results


def test_fixture_state_payloads_schema():
    """Verify fixture payloads for stale, fresh-today, and missing-field UI states."""
    stale = _base_stats_fixture(is_stale=True, latest_date="2026-10-08", trading_days_since=6)
    assert stale["pipelineHealth"]["isStale"] is True
    assert stale["reviews"][0]["lock_status"] == "retroactive"

    fresh = _base_stats_fixture(
        is_stale=False,
        latest_date="2026-10-18",
        trading_days_since=0,
        latest_review_overrides={"lock_status": "locked_pre_open", "locked_at": "06:55 WIB"},
    )
    assert fresh["pipelineHealth"]["isStale"] is False
    assert fresh["reviews"][0]["lock_status"] == "locked_pre_open"

    missing = _base_stats_fixture(
        is_stale=False,
        latest_date="2026-10-18",
        trading_days_since=0,
        latest_review_overrides={"actual_usdidr": None, "accuracy_score": None, "isUnscorable": True},
    )
    assert missing["reviews"][0]["actual_usdidr"] is None
    assert missing["reviews"][0]["accuracy_score"] is None
    assert missing["reviews"][0]["isUnscorable"] is True


if __name__ == "__main__":
    res = run_playwright_fixture_state_checks()
    print(json.dumps(res, indent=2))

