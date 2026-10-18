from pathlib import Path
from data_sources.market_data import _parse_commodity_web_summary


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

    # Test comma-formatted thousands
    sample_cpo_comma = "CPO gained +1.8% to 4,280 MYR amid tightening supplies."
    parsed_comma = _parse_commodity_web_summary("CPO", sample_cpo_comma, ["src_cpo_02"])
    assert parsed_comma["price"] == 4280.0
    assert parsed_comma["change_pct"] == 1.8

    sample_nickel_comma = "LME Nickel closed higher at $16,450.50 (+2.35%) in London."
    parsed_nickel = _parse_commodity_web_summary("Nickel (LME)", sample_nickel_comma, ["src_ni_01"])
    assert parsed_nickel["price"] == 16450.50
    assert parsed_nickel["change_pct"] == 2.35


def test_parse_commodity_web_summary_unavailable():
    """Verify unparseable text returns None and Unavailable without throwing errors."""
    unavail_text = "Data unavailable: Rate limit exceeded"
    parsed = _parse_commodity_web_summary("Nickel (LME)", unavail_text, [])

    assert parsed["name"] == "Nickel (LME)"
    assert parsed["price"] is None
    assert parsed["change_pct"] is None
    assert parsed["signal"] == "Unavailable"


def test_no_residual_hardcoded_fallbacks_in_dashboard_source():
    """Verify no residual '15,385', '17,893', or fake rate fallbacks exist in dashboard code."""
    dashboard_src = Path(__file__).resolve().parent.parent / "dashboard" / "src"
    for file_path in dashboard_src.rglob("*.js"):
        content = file_path.read_text(encoding="utf-8")
        assert "15,385" not in content, f"Found hardcoded 15,385 in {file_path.name}"
        assert "15385" not in content, f"Found hardcoded 15385 in {file_path.name}"
        assert "17,893" not in content, f"Found hardcoded 17,893 in {file_path.name}"
        assert "17893" not in content, f"Found hardcoded 17893 in {file_path.name}"


def test_collect_actual_data_foreign_flow_classification_real_call(monkeypatch):
    """
    PHASE A1 Regression Test:
    Verify collect_actual_data calls the REAL classify_foreign_flow without NameError.
    Only network functions are patched.
    """
    from agents.evening_reviewer import collect_actual_data

    # Patch ONLY the 4 external network functions
    monkeypatch.setattr(
        "agents.evening_reviewer.fetch_ihsg_snapshot",
        lambda **kwargs: {
            "ihsg_close": 7600.0,
            "ihsg_prev": 7550.0,
            "ihsg_change_pct": 0.66,
            "ihsg_change_pts": 50.0,
            "ihsg_signal": "Bullish",
            "source": "mock_yfinance",
            "confidence": "high",
        },
    )
    monkeypatch.setattr(
        "agents.evening_reviewer.fetch_usdidr_snapshot",
        lambda **kwargs: {
            "usdidr": 15500.0,
            "usdidr_change_pct": -0.2,
            "rupiah_signal": "Strengthening",
            "source": "mock_fx",
            "confidence": "high",
        },
    )
    monkeypatch.setattr(
        "agents.evening_reviewer.fetch_all_commodities",
        lambda **kwargs: {
            "all": {},
            "evidence_ids": ["src_comm_01"],
        },
    )

    def mock_search_text(query, **kwargs):
        if "asing net buy sell" in query:
            return "Asing net buy Rp 2,5 triliun pasar reguler Senin (5/10/2026)", ["src_ff_01"]
        return "mock news text", ["src_news_01"]

    monkeypatch.setattr("agents.evening_reviewer.search_text_with_sources", mock_search_text)

    # Call the REAL collect_actual_data
    actuals = collect_actual_data("5 Oktober 2026", target_date="2026-10-05")

    # Assert signal is Accumulation and no "error" key exists in foreign_flow
    assert actuals["foreign_flow_signal"] == "Accumulation"
    assert "error" not in actuals["foreign_flow"]
    assert actuals["foreign_flow"]["net_trillion"] == 2.5


def test_collect_actual_data_foreign_flow_date_mismatch_rejected(monkeypatch):
    """
    PHASE A1 Case 2:
    An article dated 10/6/2026 with target 2026-10-05 must return Unknown
    with reason 'no_matching_date' or 'date_mismatch_rejected'.
    """
    from agents.evening_reviewer import collect_actual_data

    monkeypatch.setattr(
        "agents.evening_reviewer.fetch_ihsg_snapshot",
        lambda **kwargs: {"ihsg_close": 7600.0, "ihsg_signal": "Bullish"},
    )
    monkeypatch.setattr(
        "agents.evening_reviewer.fetch_usdidr_snapshot",
        lambda **kwargs: {"usdidr": 15500.0, "rupiah_signal": "Strengthening"},
    )
    monkeypatch.setattr(
        "agents.evening_reviewer.fetch_all_commodities",
        lambda **kwargs: {"all": {}, "evidence_ids": []},
    )

    def mock_search_text(query, **kwargs):
        if "asing net buy sell" in query:
            return "Asing net buy Rp 2,5 triliun pasar reguler Rabu (10/6/2026)", ["src_ff_02"]
        return "mock news text", []

    monkeypatch.setattr("agents.evening_reviewer.search_text_with_sources", mock_search_text)

    actuals = collect_actual_data("5 Oktober 2026", target_date="2026-10-05")

    assert actuals["foreign_flow_signal"] == "Unknown"
    assert actuals["foreign_flow"].get("reason") in ("no_matching_date", "date_mismatch_rejected")

