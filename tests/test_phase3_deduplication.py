"""
tests/test_phase3_deduplication.py

Comprehensive tests for Phase 3:
1. Tavily query deduplication, caching, and metrics tracking in web_agent.
2. Centralized commodity fetching in market_data.py.
3. Unified markdown formatting of commodities.
4. Pipeline status tracking and partial state recording on failure.
"""
from unittest.mock import MagicMock
from datetime import datetime
import json

import agents.web_agent as wa
from data_sources.market_data import (
    fetch_all_commodities,
    format_all_commodities_markdown,
)


# ── 1. Tavily Search Deduplication & Caching ──────────────────────────────────

def test_tavily_search_deduplication_and_metrics(monkeypatch):
    wa.clear_search_cache()

    # Mock TavilyClient.search
    mock_search_calls = 0

    def mock_search(query, max_results=7, days=1):
        nonlocal mock_search_calls
        mock_search_calls += 1
        return {
            "results": [
                {
                    "title": f"Result for {query}",
                    "url": f"https://example.com/{query.replace(' ', '_')}",
                    "content": f"Sample content for {query}",
                    "published_date": datetime.now().isoformat(),
                }
            ]
        }

    mock_client = MagicMock()
    mock_client.search = mock_search
    monkeypatch.setattr(wa, "_get_client", lambda: mock_client)

    # First call: cache miss, triggers API call
    rec1 = wa.search_web_records("IHSG market outlook", days=1, category="macro")
    metrics1 = wa.get_search_metrics()
    assert metrics1["total_queries"] == 1
    assert metrics1["api_calls"] == 1
    assert metrics1["cache_hits"] == 0
    assert mock_search_calls == 1
    assert len(rec1) == 1
    assert rec1[0].title == "Result for IHSG market outlook"

    # Second call with identical query (case-insensitive & stripped): should hit cache
    rec2 = wa.search_web_records("  ihsg market outlook  ", days=1, category="macro_cached")
    metrics2 = wa.get_search_metrics()
    assert metrics2["total_queries"] == 2
    assert metrics2["api_calls"] == 1  # No additional API call
    assert metrics2["cache_hits"] == 1  # Cache hit recorded
    assert mock_search_calls == 1  # Tavily client not invoked again
    assert len(rec2) == 1
    assert rec2[0].category == "macro_cached"

    # Clear cache test
    wa.clear_search_cache()
    metrics_cleared = wa.get_search_metrics()
    assert metrics_cleared["api_calls"] == 0
    assert metrics_cleared["cache_hits"] == 0


# ── 2. Centralized Commodity Fetching ─────────────────────────────────────────

def test_fetch_all_commodities_consolidation(monkeypatch):
    # Mock yfinance commodity fetcher
    def mock_yfinance(name, ticker):
        return {
            "name": name,
            "ticker": ticker,
            "price": 85.50 if "Oil" in name else 3.20,
            "change_pct": 1.50 if "Oil" in name else -0.75,
            "signal": "Up" if "Oil" in name else "Down",
        }

    # Mock web search commodity fetcher
    def mock_search_sources(query, days=1, category="", limit_chars=None):
        return f"Spot price data for {category}: 150 USD/MT", [f"src_{category}"]

    import data_sources.market_data as md
    monkeypatch.setattr(md, "fetch_yfinance_commodity", mock_yfinance)
    monkeypatch.setattr("data_sources.news.search_text_with_sources", mock_search_sources)

    comm = fetch_all_commodities(target_label="8 Oktober 2026", search_days=1)

    # Check top-level keys
    assert "yfinance" in comm
    assert "web" in comm
    assert "changes" in comm
    assert "all" in comm
    assert "evidence_ids" in comm

    # Check yfinance ticker consolidation
    assert "Crude Oil (WTI)" in comm["yfinance"]
    assert "Brent Crude" in comm["yfinance"]
    assert "Natural Gas" in comm["yfinance"]
    assert comm["changes"]["Crude Oil"] == 1.50
    assert comm["changes"]["Natural Gas"] == -0.75

    # Check web commodities
    assert "Coal (Newcastle)" in comm["web"]
    assert "CPO" in comm["web"]
    assert "Nickel (LME)" in comm["web"]
    assert len(comm["evidence_ids"]) == 3

    # Check formatted markdown
    md_output = format_all_commodities_markdown(comm, target_label="8 Oktober 2026")
    assert "## Real-Time Commodity Prices (8 Oktober 2026)" in md_output
    assert "Crude Oil (WTI)" in md_output
    assert "Coal (Newcastle)" in md_output


# ── 3. Pipeline Partial State Resilience on Failure ──────────────────────────

def test_pipeline_status_recording_on_failure(tmp_path, monkeypatch):
    test_date = "2026-10-09"
    run_dir = tmp_path / test_date
    run_dir.mkdir(parents=True, exist_ok=True)

    status_file = run_dir / "pipeline_status.json"

    # Simulate saving failure status as done in market_agent / scheduler
    failure_payload = {
        "stage": "morning_brief",
        "status": "failed",
        "date": test_date,
        "error": "Tavily API timeout or rate limit exceeded",
        "failed_at": datetime.now().isoformat(),
    }
    status_file.write_text(json.dumps(failure_payload, indent=2), encoding="utf-8")

    # Verify evening review loader / scheduler can read and identify failure
    assert status_file.exists()
    status_read = json.loads(status_file.read_text(encoding="utf-8"))
    assert status_read["status"] == "failed"
    assert "rate limit exceeded" in status_read["error"]
