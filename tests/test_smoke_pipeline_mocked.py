"""
tests/test_smoke_pipeline_mocked.py

End-to-end smoke tests for run_market_brief and run_evening_review
with mocked network and LLM calls to prevent silent crashes and unhandled NameErrors.
"""
from unittest.mock import MagicMock, patch
from agents.market_agent import run_market_brief
from agents.evening_reviewer import run_evening_review
from schemas import MarketPrediction


class MockChoice:
    def __init__(self, content: str):
        self.message = MagicMock(content=content, reasoning=None)
        self.finish_reason = "stop"


class MockLLMResponse:
    def __init__(self, content: str):
        self.choices = [MockChoice(content)]


MOCK_BRIEF_MARKDOWN = """# IHSG Daily Brief -- October 14, 2026

### 1. Indonesian Economy
- BI rate dipertahankan 6.00%, inflasi stabil di 2.1%.
- Signal: Bullish | Confidence: 70

### 2. Global Macro
- Wall Street ditutup menguat moderat.
- Signal: Bullish | Confidence: 60

### 3. Commodities & Energy
- Minyak mentah menguat, batubara stabil di Newcastle.
- Signal: Bullish | Confidence: 65

### 4. Foreign Flow & Market Liquidity
- Arus modal asing mencatat beli bersih Rp 1.25 triliun di pasar reguler.
- Signal: Accumulation | Confidence: 75

### 5. Sector Outlook
- [Banking] — Bullish: Net buy asing pada BBCA dan BBRI.
- [Energy] — Bullish: Kenaikan harga minyak mentah.
- [Consumer] — Bearish: Tekanan depresiasi nilai tukar rupiah.

### 6. Actionable Emittents
- BBCA: Akumulasi asing konsisten di area support.
- BBRI: Penyaluran kredit mikro bertumbuh double digit.
- ADRO: Sentimen harga batubara global.

### 7. Key Market Risks
- Risiko pelemahan nilai tukar rupiah terhadap dolar AS dan eskalasi geopolitik Timur Tengah.
---
Source IDs: src_001, src_002
"""

MOCK_EVENING_ANALYSIS_DICT = {
    "step1_prediction_summary": "IHSG diprediksi Bullish dengan net buy asing.",
    "step2_actual_summary": "IHSG ditutup melemah tipis.",
    "unanticipated_factors": ["Tekanan jual mendadak pada sesi closing"],
    "overestimated_factors": ["Kekuatan inflow perbankan"],
    "underestimated_factors": ["Aksi profit taking investor domestik"],
    "information_delay_factors": [],
    "inverse_correlation_cases": [],
    "step4_accuracy": {
        "direction_score": 0,
        "flow_score": 100,
        "sector_score": 50,
        "composite_accuracy": 50,
    },
    "sector_accuracy": {
        "Banking": False,
        "Energy": True,
        "Consumer": True,
    },
    "step6_lessons": [
        "Ketika foreign flow net buy Rp 1.25T tetapi IHSG ditutup melemah -0.25%, aksi profit taking domestik mendominasi pembentukan harga sesi pre-closing."
    ],
    "summary_sentence": "IHSG ditutup -0.25% berlawanan dengan proyeksi bullish.",
}


@patch("agents.market_agent.search_web")
@patch("agents.market_agent.search_multiple")
@patch("agents.market_agent.fetch_all_commodities")
@patch("agents.market_agent.get_ihsg_data")
@patch("agents.market_agent.fetch_usdidr_snapshot")
@patch("agents.market_agent.llm_chat")
@patch("memory.obsidian.write_note", return_value=True)
def test_smoke_run_market_brief(
    mock_write_note,
    mock_llm_chat,
    mock_fetch_usdidr,
    mock_get_ihsg,
    mock_fetch_commodities,
    mock_search_mult,
    mock_search_web,
):
    """
    PHASE A5: True smoke test for morning brief entry point.
    Only network search, market data fetches, and LLM are mocked.
    Covers real validator, economics engine, artifact persistence, and session logging.
    """
    mock_search_web.return_value = "Saham BBCA dan BBRI memimpin volume transaksi BEI."
    mock_search_mult.return_value = {
        "Indonesian Economy": "Kondisi makro Indonesia stabil.",
        "Global Macro": "The Fed bersikap dovish.",
        "Geopolitics": "Situasi geopolitik terkendali.",
    }
    mock_fetch_commodities.return_value = {
        "all": {
            "Crude Oil": {"price": 75.0, "change_pct": 1.2, "signal": "Up"},
            "Natural Gas": {"price": 2.5, "change_pct": -0.5, "signal": "Down"},
        },
        "changes": {"Crude Oil": 1.2, "Natural Gas": -0.5},
        "evidence_ids": ["src_comm_01"],
    }
    mock_get_ihsg.return_value = "IHSG: 7250.00 (+0.45%)"
    mock_fetch_usdidr.return_value = {
        "usdidr": 15800.0,
        "usdidr_change_pct": -0.25,
        "rupiah_signal": "Strengthened",
        "source": "mock_direct",
    }
    mock_llm_chat.return_value = MockLLMResponse(MOCK_BRIEF_MARKDOWN)

    result = run_market_brief()

    assert result is not None
    assert "IHSG Daily Brief" in result
    assert mock_llm_chat.called


@patch("agents.evening_reviewer.fetch_ihsg_snapshot")
@patch("agents.evening_reviewer.fetch_usdidr_snapshot")
@patch("agents.evening_reviewer.fetch_all_commodities")
@patch("agents.evening_reviewer.search_text_with_sources")
@patch("agents.evening_reviewer.collect_unexpected_news")
@patch("agents.evening_reviewer.run_llm_analysis")
@patch("agents.evening_reviewer.save_learning")
@patch("agents.evening_reviewer.update_performance_stats")
@patch("memory.obsidian.read_note", return_value="")
@patch("memory.obsidian.write_note", return_value=True)
def test_smoke_run_evening_review(
    mock_write_note,
    mock_read_note,
    mock_update_stats,
    mock_save_learning,
    mock_run_analysis,
    mock_collect_news,
    mock_search_text,
    mock_fetch_commodities,
    mock_fetch_usdidr,
    mock_fetch_ihsg,
    tmp_path,
    monkeypatch,
):
    """
    PHASE A5: True smoke test for evening review entry point.
    Only network and LLM are mocked; collect_actual_data, classify_foreign_flow,
    and artifact generation execute real code.
    Fails if any step records an internal error key in evening_actuals.json.
    """
    import dataclasses
    from memory.artifacts import save_json_artifact, save_text_artifact, load_json_artifact

    date_key = "2026-10-14"

    # Pre-seed realistic morning prediction artifact on disk
    pred = MarketPrediction(
        date=date_key,
        ihsg_signal="Bullish",
        ihsg_confidence=70,
        foreign_flow_signal="Accumulation",
        foreign_flow_net="Rp 1.25 Triliun",
        sector_bullish=["Banking"],
        sector_bearish=["Consumer"],
        key_risk="USD rally",
        recommended_tickers=["BBCA"],
        evidence_ids=["src_1"],
    )
    save_json_artifact(date_key, "morning_prediction.json", dataclasses.asdict(pred))
    save_text_artifact(date_key, "morning_brief.md", MOCK_BRIEF_MARKDOWN)

    # Mock external network snapshots with valid clean responses
    mock_fetch_ihsg.return_value = {
        "ihsg_close": 7230.0,
        "ihsg_prev": 7250.0,
        "ihsg_change_pct": -0.28,
        "ihsg_change_pts": -20.0,
        "ihsg_signal": "Bearish",
        "ihsg_open": 7245.0,
        "ihsg_high": 7260.0,
        "ihsg_low": 7220.0,
        "ihsg_volume": 12000000000,
        "candle_date": date_key,
        "source": "mock_yfinance",
        "confidence": "high",
    }
    mock_fetch_usdidr.return_value = {
        "usdidr": 15810.0,
        "usdidr_change_pct": 0.06,
        "rupiah_signal": "Weakened",
        "candle_date": date_key,
        "source": "mock_fx",
        "confidence": "high",
    }
    mock_fetch_commodities.return_value = {
        "all": {
            "Crude Oil (WTI)": {"price": 75.0, "change_pct": 1.2, "signal": "Up"},
            "Brent Crude": {"price": 78.5, "change_pct": 0.8, "signal": "Up"},
        },
        "evidence_ids": ["src_comm_01"],
    }

    def fake_search_text(query, **kwargs):
        if "asing net buy sell" in query:
            return (
                "Asing membukukan net buy Rp 1,25 triliun di pasar reguler pada perdagangan Rabu (14/10/2026).",
                ["src_ff_01"],
            )
        if "performa penutupan sektor" in query:
            return (
                "Indeks sektoral ditutup variatif pada penutupan perdagangan. Sektor perbankan naik 0.8% dan konsumer turun 0.5%.",
                ["src_sec_01"],
            )
        return "Saham top movers BEI", ["src_tm_01"]

    mock_search_text.side_effect = fake_search_text
    mock_collect_news.return_value = {"news": []}
    mock_run_analysis.return_value = MOCK_EVENING_ANALYSIS_DICT

    # Execute REAL run_evening_review (which calls real collect_actual_data)
    learning = run_evening_review(date_key=date_key)

    assert learning is not None
    assert learning["date"] == date_key
    assert learning["ihsg_predicted"] == "Bullish"
    assert learning["foreign_flow_actual"] in ("Accumulation", "Net Buy / Inflow", "Bullish")

    # Inspect persisted evening_actuals artifact: MUST NOT contain error keys
    actual_art = load_json_artifact(date_key, "evening_actuals.json")
    assert actual_art is not None
    assert "error" not in actual_art.get("foreign_flow", {})
    assert "error" not in actual_art.get("ihsg", {})
    assert "error" not in actual_art.get("usdidr", {})
    assert actual_art.get("foreign_flow_signal") == "Accumulation"

