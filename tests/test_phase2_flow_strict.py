"""
tests/test_phase2_flow_strict.py

Tests for Phase 2 data integrity in foreign flow:
- Indonesian date parsing as D/M (10/6/2026 is June 10, not October 6).
- Strict mode requiring explicit matching date.
- Rp1T threshold (252.65B = Stagnant).
"""
import pytest
from utils.flow import classify_foreign_flow, canonicalize_flow


def test_indonesian_dm_date_rejection():
    # An article from 10 June 2026 must be REJECTED when target is 6 October 2026 (2026-10-06)
    text_june = "Pada perdagangan Rabu (10/6/2026), investor asing mencatatkan net buy Rp 1.5 triliun di pasar reguler."
    result = classify_foreign_flow(text_june, target_date_str="2026-10-06", strict=True)
    assert result["signal"] == "Unknown"
    assert result["reason"] in ("date_mismatch_rejected", "no_matching_date")


def test_strict_mode_requires_matching_date():
    # Text without any explicit date must be rejected under strict=True
    text_no_date = "Investor asing mencatatkan net buy Rp 2.5 triliun di seluruh pasar."
    result = classify_foreign_flow(text_no_date, target_date_str="2026-10-06", strict=True)
    assert result["signal"] == "Unknown"
    assert result["reason"] == "no_matching_date"


def test_rp1t_threshold_stagnant():
    # Rp 252.65 miliar net buy (< Rp1 Triliun) must be Stagnant, NOT Accumulation
    text = "Asing mencatatkan beli bersih Rp 252,65 miliar pada perdagangan Selasa (6/10/2026)."
    result = classify_foreign_flow(text, target_date_str="2026-10-06", strict=True)
    assert result["signal"] == "Stagnant"
    assert result["net_trillion"] == pytest.approx(0.25265, rel=1e-3)


def test_rp1t_threshold_accumulation():
    # Rp 1.45 triliun net buy (>= Rp1 Triliun) is Accumulation
    text = "Asing membukukan beli bersih Rp 1,45 triliun pada perdagangan Selasa (6/10/2026)."
    result = classify_foreign_flow(text, target_date_str="2026-10-06", strict=True)
    assert result["signal"] == "Accumulation"
    assert result["net_trillion"] == pytest.approx(1.45, rel=1e-3)


def test_canonicalize_flow():
    assert canonicalize_flow("Stagnant/Sideways") == "Stagnant"
    assert canonicalize_flow("Stagnant") == "Stagnant"
    assert canonicalize_flow("Net Buy / Inflow") == "Accumulation"
    assert canonicalize_flow("Net Sell / Outflow") == "Distribution"
    assert canonicalize_flow(None) == "Unknown"
