import unittest
from unittest.mock import MagicMock, patch

from agents.economics_engine import build_economics_context
from data_sources.market_data import (
    fetch_ihsg_snapshot,
    fetch_usdidr_snapshot,
    fetch_yfinance_commodity,
    format_commodity_snapshot,
    format_ihsg_snapshot,
)


class Phase1NoFabricatedDataTests(unittest.TestCase):
    @patch("data_sources.market_data.requests.get", side_effect=Exception("Network error"))
    @patch("data_sources.market_data.yf.Ticker", side_effect=Exception("yfinance down"))
    @patch("agents.web_agent.search_web", side_effect=Exception("Search down"))
    def test_fetch_usdidr_snapshot_all_fail_returns_none(self, mock_web, mock_yf, mock_req):
        res = fetch_usdidr_snapshot()
        self.assertIsNone(res.get("usdidr"))
        self.assertIsNone(res.get("usdidr_change_pct"))
        self.assertEqual(res.get("rupiah_signal"), "Unavailable")
        self.assertIn("error", res)

    @patch("data_sources.market_data.requests.get", side_effect=Exception("Network error"))
    @patch("data_sources.market_data.yf.Ticker", side_effect=Exception("yfinance down"))
    def test_fetch_yfinance_commodity_failure_returns_none(self, mock_yf, mock_req):
        res = fetch_yfinance_commodity("Crude Oil", "CL=F")
        self.assertIsNone(res.get("price"))
        self.assertIsNone(res.get("change_pct"))
        self.assertIsNone(res.get("previous_close"))
        self.assertEqual(res.get("signal"), "Unavailable")
        self.assertIn("error", res)

    def test_format_commodity_snapshot_with_none_values(self):
        # price is None
        formatted_none = format_commodity_snapshot({"name": "Crude Oil", "price": None})
        self.assertEqual(formatted_none, "- **Crude Oil**: unavailable")

        # change_pct is None
        formatted_no_change = format_commodity_snapshot({"name": "Brent Crude", "price": 85.5, "change_pct": None})
        self.assertIn("change unavailable", formatted_no_change)
        self.assertNotIn("0.00%", formatted_no_change)

    def test_format_ihsg_snapshot_with_none_values(self):
        # error / missing close
        formatted_err = format_ihsg_snapshot({"error": "IHSG data unavailable", "ihsg_close": None})
        self.assertIn("IHSG data unavailable", formatted_err)

        # change_pct is None
        formatted_no_change = format_ihsg_snapshot({
            "ihsg_close": 7500.0,
            "ihsg_change_pct": None,
            "ihsg_open": 7480.0,
            "ihsg_high": 7510.0,
            "ihsg_low": 7470.0,
        })
        self.assertIn("change unavailable", formatted_no_change)
        self.assertNotIn("0.00%", formatted_no_change)

        # web fallback confidence flag
        formatted_fallback = format_ihsg_snapshot({
            "ihsg_close": 7500.0,
            "ihsg_change_pct": 0.5,
            "source": "web_fallback",
            "confidence": "low",
        })
        self.assertIn("web_fallback - low confidence", formatted_fallback)

    @patch("data_sources.market_data.requests.get", side_effect=Exception("Yahoo down"))
    @patch("data_sources.market_data.yf.Ticker", side_effect=Exception("yfinance down"))
    @patch("agents.web_agent.search_web", return_value="IHSG hari ini ditutup di level 7.350 menguat 0.45%")
    def test_fetch_ihsg_snapshot_web_fallback_flagged(self, mock_web, mock_yf, mock_req):
        res = fetch_ihsg_snapshot()
        self.assertEqual(res.get("source"), "web_fallback")
        self.assertEqual(res.get("confidence"), "low")
        self.assertEqual(res.get("ihsg_close"), 7350.0)
        self.assertEqual(res.get("ihsg_signal"), "Bullish")

    def test_build_economics_context_handles_none_change(self):
        context = build_economics_context(
            commodity_changes={"Crude Oil": None, "Natural Gas": 2.5},
            current_date="8 Oktober 2026",
            search_days=1,
        )
        self.assertIn("Crude Oil: commodity Crude Oil data unavailable", context)
        self.assertNotIn("Crude Oil +0.00%", context)


if __name__ == "__main__":
    unittest.main()
