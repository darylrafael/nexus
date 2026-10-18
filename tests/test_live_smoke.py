"""Unit tests for scripts/live_smoke.py (Phase C1 & C2).

Proves:
1. `scripts/live_smoke.py` refuses to run against the repository's real `runs/`
   directory or any subdirectory inside it.
2. `validate_smoke_session` passes on a valid isolated fixture session directory
   covering all 7 checks (artifacts exist, no error keys & data_quality passing,
   foreign_flow valid or Unknown with reason, OHLC valid, USD/IDR change consistent
   within 0.05%, tickers in `data/idx_tickers.json`, no mock provenance).
3. `validate_smoke_session` catches violations of each check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.paths import get_real_repo_runs_dir
from scripts.live_smoke import (
    assert_safe_runs_dir,
    main as live_smoke_main,
    validate_smoke_session,
)


def _write_valid_fixture_session(session_dir: Path) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "morning_brief.md").write_text(
        "# IHSG Daily Brief — October 16, 2026\n\nBanking and Energy outlook.\nSource IDs: src_a1b2c3d4e5\n",
        encoding="utf-8",
    )
    (session_dir / "morning_prediction.json").write_text(
        json.dumps(
            {
                "date": "2026-10-16",
                "ihsg_signal": "Bullish",
                "ihsg_confidence": 75,
                "calibrated_confidence": 49.7,
                "foreign_flow_signal": "Accumulation",
                "foreign_flow_net": "Net Buy Rp 540 miliar",
                "sector_bullish": ["Financials"],
                "sector_bearish": ["Technology"],
                "sector_neutral": [],
                "recommended_tickers": ["BBCA", "BBRI", "BMRI"],
                "key_risk": "Nilai tukar rupiah",
                "commodities_predicted": {"Oil": "bullish"},
                "evidence_ids": ["src_a1b2c3d4e5"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # USD/IDR: prev=17900, close=17885 -> (17885 - 17900) / 17900 * 100 = -0.08379888% -> stored -0.084%
    (session_dir / "actual_market_data.json").write_text(
        json.dumps(
            {
                "date": "2026-10-16",
                "schema_version": 2,
                "ihsg": {
                    "status": "ok",
                    "open": 6150.0,
                    "high": 6195.0,
                    "low": 6140.0,
                    "close": 6180.0,
                    "prev": 6146.72,
                    "change_pct": 0.54,
                    "signal": "Bullish",
                    "source": "yahoo_direct:^JKSE",
                },
                "usdidr": {
                    "status": "ok",
                    "rate": 17885.0,
                    "prev": 17900.0,
                    "change_pct": -0.084,
                    "signal": "Strengthened",
                    "source": "yahoo_direct:USDIDR=X",
                },
                "foreign_flow": {
                    "status": "ok",
                    "signal": "Unknown",
                    "reason": "date_mismatch_rejected",
                },
                "foreign_flow_signal": "Unknown",
                "data_quality": {
                    "overall_valid": True,
                    "checks": {
                        "ohlc_valid": True,
                        "fx_consistent": True,
                        "flow_date_matched": False,
                        "sector_data_is_close": True,
                    },
                    "fields": {
                        "ihsg": {"source": "yahoo_direct:^JKSE", "valid": True},
                        "usdidr": {"source": "yahoo_direct:USDIDR=X", "valid": True},
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (session_dir / "evening_review.json").write_text(
        json.dumps(
            {
                "date": "2026-10-16",
                "ihsg_predicted": "Bullish",
                "ihsg_actual": "Bullish",
                "ihsg_actual_pct": 0.54,
                "ihsg_correct": True,
                "foreign_flow_predicted": "Accumulation",
                "foreign_flow_actual": "Unknown",
                "foreign_flow_correct": None,
                "accuracy_score": 100,
                "error_rate_pct": 0,
                "data_quality": {
                    "overall_valid": True,
                    "fields": {
                        "ihsg": {"source": "yahoo_direct:^JKSE", "valid": True},
                        "usdidr": {"source": "yahoo_direct:USDIDR=X", "valid": True},
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_live_smoke_refuses_real_runs_dir():
    """Phase C1 & C2: Script must refuse to run if NEXUS_RUNS_DIR resolves inside the repo's real runs/."""
    real_runs = get_real_repo_runs_dir()
    with pytest.raises(RuntimeError, match="REFUSED"):
        assert_safe_runs_dir(real_runs)

    with pytest.raises(RuntimeError, match="REFUSED"):
        assert_safe_runs_dir(real_runs / "2026-10-08")

    with pytest.raises(RuntimeError, match="REFUSED"):
        validate_smoke_session(real_runs / "2026-10-08")


def test_live_smoke_validator_passes_on_valid_fixture_directory(tmp_path: Path):
    """Phase C2: Prove scripts/live_smoke.py validator passes on a valid isolated fixture directory."""
    session_dir = tmp_path / "isolated_runs" / "2026-10-16"
    _write_valid_fixture_session(session_dir)

    report = validate_smoke_session(session_dir)
    assert report["passed"] is True, f"Expected all checks to pass, got: {report}"
    for name, check in report["checks"].items():
        assert check["passed"] is True, f"Check {name} failed: {check}"

    exit_code = live_smoke_main(["--validate-dir", str(session_dir)])
    assert exit_code == 0


def test_live_smoke_validator_catches_invalid_artifacts(tmp_path: Path):
    """Verify validator rejects error keys, invalid OHLC, inconsistent FX, bad tickers, and mock provenance."""
    session_dir = tmp_path / "isolated_runs" / "2026-10-16_bad"
    _write_valid_fixture_session(session_dir)

    # Corrupt OHLC, FX consistency, tickers, error keys, and provenance
    pred = json.loads((session_dir / "morning_prediction.json").read_text(encoding="utf-8"))
    pred["recommended_tickers"] = ["BBCA", "NOT_AN_IDX_TICKER"]
    (session_dir / "morning_prediction.json").write_text(json.dumps(pred), encoding="utf-8")

    actual = json.loads((session_dir / "actual_market_data.json").read_text(encoding="utf-8"))
    actual["ihsg"]["high"] = 6100.0  # Invalid: high < open (6150)
    actual["usdidr"]["change_pct"] = 2.50  # Inconsistent with (17885 - 17900)/17900
    actual["error"] = "upstream failure"
    actual["data_quality"]["fields"]["ihsg"]["source"] = "mock_yfinance"
    (session_dir / "actual_market_data.json").write_text(json.dumps(actual), encoding="utf-8")

    report = validate_smoke_session(session_dir)
    assert report["passed"] is False
    assert report["checks"]["no_error_keys_and_dq_passing"]["passed"] is False
    assert report["checks"]["ohlc_valid"]["passed"] is False
    assert report["checks"]["usdidr_change_consistent"]["passed"] is False
    assert report["checks"]["tickers_in_idx_whitelist"]["passed"] is False
    assert report["checks"]["no_mock_provenance"]["passed"] is False
