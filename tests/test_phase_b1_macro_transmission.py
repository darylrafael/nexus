import pytest
from utils.flow import classify_foreign_flow
from agents.economics_engine import build_economics_context, SECTOR_LOGIC, RUPIAH_LOGIC


def test_classify_foreign_flow_regular_market():
    """Verify regular market flow is properly detected and categorized."""
    text = "Investor asing mencatatkan net buy sebesar Rp 1.5 Triliun di pasar reguler pada sesi perdagangan hari ini."
    res = classify_foreign_flow(text, target_date_str=None)

    assert res["signal"] == "Accumulation"
    assert res["net_trillion"] == 1.5
    assert res["market_scope"] == "regular"
    assert res["is_all_market"] is False


def test_classify_foreign_flow_all_market_negotiated():
    """Verify negotiated crossing / all market flow is detected and flagged."""
    text = "Di seluruh pasar, aksi beli bersih asing tercatat Rp 3.2 Triliun terbantu crossing di pasar negosiasi."
    res = classify_foreign_flow(text, target_date_str=None)

    assert res["signal"] == "Accumulation"
    assert res["net_trillion"] == 3.2
    assert res["market_scope"] == "all_market"
    assert res["is_all_market"] is True


def test_macro_net_importer_warning_on_crude_spike(monkeypatch):
    """Verify build_economics_context includes net importer macro warning when crude spikes >= 2%."""
    # Mock search so network is not called
    monkeypatch.setattr("agents.economics_engine.get_affected_stocks", lambda c, d, cd, **k: "Mocked stock results")

    ctx = build_economics_context(
        commodity_changes={"Crude Oil": 2.50, "Coal": 1.0},
        rupiah_change=-0.25,
        rate_direction="hike",
        current_date="2026-10-08"
    )

    assert "Macro Net Importer Warning" in ctx
    assert "Banking & Consumer sectors face indirect margin caution" in ctx
    assert "Pharmaceuticals (90%+ API imported in USD): BEARISH" in ctx
    assert "consumer_goods" in SECTOR_LOGIC
    assert "pharmaceutical" in SECTOR_LOGIC
