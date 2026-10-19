"""Unit tests for non-trading skip guards and weekend foreign flow verification (Phase B2 & B3).

Covers:
1. `run_market_brief` skip behavior for weekend, holiday, and normal trading day.
2. `run_evening_review` skip behavior for weekend, holiday, and normal trading day.
3. `utils/flow.py` verification rejecting non-trading target dates, rejecting weekend date strings,
   and reporting matched and target dates.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.evening_reviewer import run_evening_review
from agents.market_agent import run_market_brief
from core.calendar import is_idx_trading_day
from utils.flow import _verify_target_date, classify_foreign_flow


def test_market_brief_skips_on_weekend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """B2: run_market_brief returns structured skip artifact on weekend date without creating brief."""
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("NEXUS_RUNS_DIR", str(runs_dir))

    sunday = "2026-10-18"
    assert not is_idx_trading_day(sunday)

    result = run_market_brief(target_date=sunday, allow_non_trading=False)
    assert isinstance(result, dict)
    assert result["status"] == "skipped"
    assert "Weekend" in result["reason"]
    assert result["date"] == sunday

    session_dir = runs_dir / sunday
    assert session_dir.exists()
    assert (session_dir / "pipeline_status.json").exists()
    assert not (session_dir / "morning_brief.md").exists()
    assert not (session_dir / "morning_prediction.json").exists()

    status_data = json.loads((session_dir / "pipeline_status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "skipped"
    assert status_data["stage"] == "morning_brief"


def test_market_brief_skips_on_holiday(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """B2: run_market_brief returns structured skip artifact on official IDX holiday."""
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("NEXUS_RUNS_DIR", str(runs_dir))

    holiday = "2026-01-01"  # Tahun Baru Masehi
    assert not is_idx_trading_day(holiday)

    result = run_market_brief(target_date=holiday, allow_non_trading=False)
    assert isinstance(result, dict)
    assert result["status"] == "skipped"
    assert "Tahun Baru" in result["reason"]

    session_dir = runs_dir / holiday
    assert (session_dir / "pipeline_status.json").exists()
    assert not (session_dir / "morning_brief.md").exists()


def test_evening_review_skips_on_weekend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """B2: run_evening_review returns structured skip artifact on weekend date without evaluating."""
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("NEXUS_RUNS_DIR", str(runs_dir))

    saturday = "2026-10-17"
    assert not is_idx_trading_day(saturday)

    result = run_evening_review(date_key=saturday, allow_non_trading=False)
    assert isinstance(result, dict)
    assert result["status"] == "skipped"
    assert "Weekend (Saturday)" in result["reason"]

    session_dir = runs_dir / saturday
    assert session_dir.exists()
    assert (session_dir / "pipeline_status.json").exists()
    assert not (session_dir / "evening_review.json").exists()
    assert not (session_dir / "actual_market_data.json").exists()


def test_evening_review_skips_on_holiday(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """B2: run_evening_review returns structured skip artifact on official holiday."""
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("NEXUS_RUNS_DIR", str(runs_dir))

    holiday = "2026-01-01"
    assert not is_idx_trading_day(holiday)

    result = run_evening_review(date_key=holiday, allow_non_trading=False)
    assert isinstance(result, dict)
    assert result["status"] == "skipped"
    assert "Tahun Baru" in result["reason"]


def test_normal_trading_day_does_not_trigger_calendar_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """B2: On a normal trading day, calendar guard passes and proceeds to execution."""
    friday = "2026-10-16"
    assert is_idx_trading_day(friday)

    # For evening review, if morning brief is missing, it returns None (load_morning_brief fails)
    # rather than being skipped by calendar guard.
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("NEXUS_RUNS_DIR", str(runs_dir))
    with patch("agents.evening_reviewer.read_note", return_value=None):
        res = run_evening_review(date_key=friday, allow_non_trading=False)
    # Returns None because morning brief doesn't exist, NOT {"status": "skipped"}
    assert res is None


def test_foreign_flow_rejects_non_trading_target_date():
    """B3: Foreign flow verification rejects non-trading target date as non_trading_target_date."""
    sunday = "2026-10-18"
    sample_text = "Minggu (18/10/2026) investor asing mencatat net sell Rp 1.5 triliun di seluruh pasar."

    is_valid, reason, matched_date = _verify_target_date(sample_text, sunday, strict=True)
    assert is_valid is False
    assert reason == "non_trading_target_date"

    eval_result = classify_foreign_flow(sample_text, target_date_str=sunday, strict=True)
    assert eval_result["signal"] == "Unknown"
    assert eval_result["reason"] == "non_trading_target_date"
    assert eval_result["target_date"] == sunday


def test_foreign_flow_rejects_weekend_date_when_target_is_trading_day():
    """B3: Sunday date string rejected when target date is a trading day (Friday)."""
    friday = "2026-10-16"
    weekend_text = "Minggu (18/10/2026) investor asing mencatat net buy Rp 2.5 triliun."

    is_valid, reason, matched_date = _verify_target_date(weekend_text, friday, strict=True)
    assert is_valid is False
    assert reason == "date_mismatch_rejected"
    assert matched_date == "2026-10-18"

    eval_result = classify_foreign_flow(weekend_text, target_date_str=friday, strict=True)
    assert eval_result["signal"] == "Unknown"
    assert eval_result["reason"] == "date_mismatch_rejected"
    assert eval_result["matched_date"] == "2026-10-18"
    assert eval_result["target_date"] == friday


def test_foreign_flow_accepts_matching_trading_date():
    """B3: Valid trading day matching target date returns verified with matched_date."""
    friday = "2026-10-16"
    valid_text = "Jumat (16/10/2026) investor asing mencatat aksi beli bersih (net buy) sebesar Rp 1.45 triliun di pasar reguler."

    is_valid, reason, matched_date = _verify_target_date(valid_text, friday, strict=True)
    assert is_valid is True
    assert reason == "verified"
    assert matched_date == "2026-10-16"

    eval_result = classify_foreign_flow(valid_text, target_date_str=friday, strict=True)
    assert eval_result["signal"] == "Accumulation"
    assert eval_result["matched_date"] == "2026-10-16"
    assert eval_result["target_date"] == friday
    assert eval_result["net_trillion"] == 1.45
