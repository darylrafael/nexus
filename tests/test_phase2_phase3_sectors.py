"""
tests/test_phase2_phase3_sectors.py

Test deterministic sector scoring, subsector mapping, and close-data validation.
"""
from core.sectors import (
    is_close_data,
    map_to_parent_sector,
    parse_sector_percentages_from_text,
    score_sector_predictions,
)


def test_is_close_data_rejects_session_1():
    midday_text = (
        "IHSG +0,48% ke 6.216,27 di akhir sesi I Jumat (31/7/2026). "
        "Indeks sektoral dengan kenaikan terbesar, sektor barang baku +1,93%."
    )
    assert is_close_data(midday_text) is False


def test_is_close_data_accepts_market_close():
    close_text = (
        "IHSG naik 1,36% ke level 6.118,86 pada penutupan perdagangan Senin (5/10/2026). "
        "Berdasarkan Indeks Sektoral IDX-IC, sektor properti naik 2,31%, sektor barang baku naik 2,07%."
    )
    assert is_close_data(close_text) is True


def test_subsector_mapping():
    assert map_to_parent_sector("Coal") == "IDXENERGY"
    assert map_to_parent_sector("Batu Bara") == "IDXENERGY"
    assert map_to_parent_sector("Oil & Gas") == "IDXENERGY"
    assert map_to_parent_sector("CPO") == "IDXBASIC"
    assert map_to_parent_sector("Kelapa Sawit") == "IDXBASIC"
    assert map_to_parent_sector("Nikel") == "IDXBASIC"
    assert map_to_parent_sector("Perbankan") == "IDXFINANCE"
    assert map_to_parent_sector("Bank") == "IDXFINANCE"
    assert map_to_parent_sector("Teknologi") == "IDXTECH"


def test_parse_sector_percentages():
    text = (
        "Indeks ditutup variatif pada penutupan perdagangan. "
        "Sektor properti naik 2,31%, sektor teknologi turun 3,37%, dan sektor energi turun 1,10%."
    )
    parsed = parse_sector_percentages_from_text(text)
    assert parsed.get("IDXPROPERT") == 2.31
    assert parsed.get("IDXTECH") == -3.37
    assert parsed.get("IDXENERGY") == -1.10


def test_score_sector_neutral_band():
    actuals = {
        "IDXENERGY": 0.15,   # within +/- 0.20% -> Neutral
        "IDXFINANCE": -0.80, # < -0.20% -> Bearish
        "IDXBASIC": 1.50,    # > +0.20% -> Bullish
    }
    preds = {
        "Energi": "Neutral",
        "Perbankan": "Bearish",
        "Barang Baku": "Bullish",
        "Teknologi": "Bullish", # missing actual -> None
    }
    scores = score_sector_predictions(preds, actuals)
    assert scores["Energi"] is True
    assert scores["Perbankan"] is True
    assert scores["Barang Baku"] is True
    assert scores["Teknologi"] is None


def test_conflicting_subsector_calls_unverifiable():
    # Coal Bullish, Oil & Gas Bearish -> both map to IDXENERGY
    preds = {
        "Coal": "Bullish",
        "Oil & Gas": "Bearish",
        "Perbankan": "Bullish",
    }
    actuals = {
        "IDXENERGY": 1.50,
        "IDXFINANCE": 0.80,
    }
    scores = score_sector_predictions(preds, actuals)
    assert scores["Coal"] is None        # unverifiable
    assert scores["Oil & Gas"] is None    # unverifiable
    assert scores["Perbankan"] is True


def test_is_close_data_rejects_intraday_and_siang():
    intraday_text = "IHSG bergerak melemah pada perdagangan intraday siang ini. Sektor teknologi tertekan."
    assert is_close_data(intraday_text) is False

