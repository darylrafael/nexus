import pytest
from datetime import datetime, date
from unittest.mock import MagicMock

from core.calendar import (
    load_idx_holidays,
    is_idx_trading_day,
    get_holiday_reason,
    get_last_trading_day,
    get_trading_day_or_previous,
)
from data_sources.provider import (
    MarketDataProvider,
    YahooMarketDataProvider,
    LicensedMarketDataProvider,
    get_market_data_provider,
)
import agents.web_agent as wa
from schemas import SourceRecord


# ── 1. IDX Trading Holiday Calendar ──────────────────────────────────────────

def test_idx_holiday_calendar_detection():
    holidays = load_idx_holidays()
    assert len(holidays) > 0
    assert "2026-01-01" in holidays
    assert "2026-08-17" in holidays

    # New Year 2026 (Thursday) is a holiday
    assert is_idx_trading_day("2026-01-01") is False
    assert get_holiday_reason("2026-01-01") is not None

    # Weekend (Saturday: 2026-10-10) is not a trading day
    assert is_idx_trading_day("2026-10-10") is False
    assert "Saturday" in get_holiday_reason("2026-10-10")

    # Regular trading day: Thursday 2026-10-08
    assert is_idx_trading_day("2026-10-08") is True
    assert get_holiday_reason("2026-10-08") is None


def test_idx_last_trading_day_resolution():
    # If reference is Monday 2026-01-05, last trading day should be Friday 2026-01-02
    last_trading = get_last_trading_day("2026-01-05")
    assert last_trading == "2026-01-02"

    # Friday 2026-01-02: 2026-01-01 is holiday, so last trading day before Friday 2026-01-02 is Wednesday 2025-12-31
    last_before_jan2 = get_last_trading_day("2026-01-02")
    assert last_before_jan2 == "2025-12-31"


# ── 2. MarketDataProvider Licensing Boundaries ───────────────────────────────

def test_market_data_provider_licensing_and_public_mode_guard(monkeypatch):
    provider = YahooMarketDataProvider()
    assert provider.personal_use_only is True
    assert provider.provider_name == "YahooFinance"

    # Default / personal mode -> no error checking guard
    monkeypatch.setenv("NEXUS_PUBLIC_MODE", "false")
    provider._check_public_mode_guard()

    # Public mode enabled -> must raise RuntimeError refusing unlicensed scraping
    monkeypatch.setenv("NEXUS_PUBLIC_MODE", "true")
    with pytest.raises(RuntimeError) as exc_info:
        provider._check_public_mode_guard()
    assert "restricted to personal/research use only" in str(exc_info.value)

    # Licensed provider
    licensed = LicensedMarketDataProvider()
    assert licensed.personal_use_only is False
    assert licensed.provider_name == "LicensedEnterpriseFeed"


# ── 3. Web Agent Domain Filtering & Freshness ────────────────────────────────

def test_web_agent_domain_filtering(monkeypatch):
    wa.clear_search_cache()

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Legitimate News Article",
                "url": "https://market.bisnis.com/read/20261008/ihsg-menguat",
                "content": "IHSG ditutup menguat",
                "published_date": "2026-10-08T10:00:00",
            },
            {
                "title": "Unverified Social Rumor",
                "url": "https://www.tiktok.com/@trader_xyz/video/12345",
                "content": "Saham ini bakal terbang",
                "published_date": "2026-10-08T10:00:00",
            },
            {
                "title": "Twitter Thread",
                "url": "https://x.com/analyst/status/67890",
                "content": "Rumor IHSG",
                "published_date": "2026-10-08T10:00:00",
            },
            {
                "title": "Report Without Date",
                "url": "https://idx.co.id/press/123",
                "content": "Pengumuman bursa",
                "published_date": "",
            }
        ]
    }
    monkeypatch.setattr(wa, "_get_client", lambda: mock_client)

    records = wa.search_web_records("IHSG", days=1, category="macro")

    # TikTok and X.com must be filtered out
    urls = [r.url for r in records]
    assert "https://market.bisnis.com/read/20261008/ihsg-menguat" in urls
    assert "https://idx.co.id/press/123" in urls
    assert not any("tiktok.com" in u for u in urls)
    assert not any("x.com" in u for u in urls)

    # Missing date must be flagged as freshness_status="unknown"
    idx_rec = next(r for r in records if "idx.co.id" in r.url)
    assert idx_rec.freshness_status == "unknown"

    formatted = wa.format_source_records(records)
    assert "date unknown" in formatted
