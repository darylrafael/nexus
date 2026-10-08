import pytest
from pathlib import Path
from data_sources.market_data import _parse_commodity_web_summary, fetch_all_commodities


def test_parse_commodity_web_summary_success():
    """Verify numeric price and change_pct are properly parsed from raw web snippets."""
    sample_coal = "Newcastle Coal Dec futures closed at $142.50 (+1.75%) amid strong Asian demand."
    parsed = _parse_commodity_web_summary("Coal (Newcastle)", sample_coal, ["src_coal_01"])

    assert parsed["name"] == "Coal (Newcastle)"
    assert parsed["price"] == 142.50
    assert parsed["change_pct"] == 1.75
    assert parsed["signal"] == "Up"
    assert parsed["source"] == "tavily_web"
    assert "src_coal_01" in parsed["source_ids"]


def test_parse_commodity_web_summary_myr_cpo():
    """Verify alternative currency price and negative percentage are parsed."""
    sample_cpo = "Palm Oil fell -2.1% to 4250 MYR per metric ton on higher Malaysian inventories."
    parsed = _parse_commodity_web_summary("CPO", sample_cpo, ["src_cpo_01"])

    assert parsed["name"] == "CPO"
    assert parsed["price"] == 4250.0
    assert parsed["change_pct"] == -2.1
    assert parsed["signal"] == "Down"


def test_parse_commodity_web_summary_unavailable():
    """Verify unparseable text returns None and Unavailable without throwing errors."""
    unavail_text = "Data unavailable: Rate limit exceeded"
    parsed = _parse_commodity_web_summary("Nickel (LME)", unavail_text, [])

    assert parsed["name"] == "Nickel (LME)"
    assert parsed["price"] is None
    assert parsed["change_pct"] is None
    assert parsed["signal"] == "Unavailable"


def test_no_residual_hardcoded_fallbacks_in_dashboard_source():
    """Verify no residual '15,385' or fake rate fallbacks exist in dashboard code."""
    dashboard_src = Path(__file__).resolve().parent.parent / "dashboard" / "src"
    for file_path in dashboard_src.rglob("*.js"):
        content = file_path.read_text(encoding="utf-8")
        assert "15,385" not in content, f"Found hardcoded 15,385 in {file_path.name}"
        assert "15385" not in content, f"Found hardcoded 15385 in {file_path.name}"
