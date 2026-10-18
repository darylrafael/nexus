"""
tests/test_phase2_provenance_guard.py

Unit tests per layer verifying that test/mock provenance artifacts are detected
and rejected across:
1. core.provenance (is_mock_provenance, check_run_dir_provenance, build_runs_index)
2. memory.learning_store (save_learning, filter_and_quarantine_lessons)
3. utils.stats (compute_canonical_stats + Phase 3.2 null correctness exclusion)
4. scripts.rescore_history (rescore_run)
"""
from __future__ import annotations
import json
from pathlib import Path

from core.paths import get_runs_dir, get_memory_dir
from core.provenance import (
    is_mock_provenance,
    has_mock_provenance,
    check_run_dir_provenance,
    build_runs_index,
)
from memory.learning_store import save_learning, filter_and_quarantine_lessons
from utils.stats import compute_canonical_stats
from scripts.rescore_history import rescore_run


def test_provenance_detects_all_mock_patterns():
    # 1. data_quality.fields.*.source starts with "mock"
    art1 = {
        "data_quality": {
            "fields": {
                "ihsg": {"source": "mock_yfinance", "confidence": "high"},
                "usdidr": {"source": "mock_fx"},
            }
        }
    }
    is_mock, reasons = is_mock_provenance(art1)
    assert is_mock is True
    assert any("mock_yfinance" in r for r in reasons)

    # 2. evidence_ids / sources start with "mock" or "src_mock"
    art2 = {
        "evidence_ids": ["src_mock_1"],
        "sources": {"src_mock_1": {"title": "Mock Title"}},
    }
    assert has_mock_provenance(art2) is True

    # 3. FX/index values flagged synthetic
    art3 = {
        "ihsg": {"close": 7230.0, "synthetic": True},
        "usdidr": {"rate": 15810.0, "source": "synthetic_fx"},
    }
    assert has_mock_provenance(art3) is True

    # 4. Genuine artifact passes
    genuine = {
        "date": "2026-10-07",
        "ihsg_source": "yfinance",
        "data_quality": {"ohlc_valid": True, "flow_verified": True},
        "sources": {"src_abc123": {"url": "https://www.cnbcindonesia.com/market"}},
    }
    assert has_mock_provenance(genuine) is False


def test_learning_store_rejects_mock_provenance():
    runs_dir = get_runs_dir()
    mock_date = "2026-10-16"
    mock_dir = runs_dir / mock_date
    mock_dir.mkdir(parents=True, exist_ok=True)
    (mock_dir / "evening_actuals.json").write_text(
        json.dumps(
            {
                "date": mock_date,
                "ihsg_close": 7230.0,
                "data_quality": {
                    "fields": {"ihsg": {"source": "mock_yfinance"}}
                },
            }
        ),
        encoding="utf-8",
    )

    mock_review = {
        "date": mock_date,
        "ihsg_predicted": "Bullish",
        "ihsg_actual": "Bearish",
        "ihsg_actual_pct": -0.25,
        "ihsg_correct": False,
        "accuracy_score": 0,
        "lessons": [
            "Ketika foreign flow net buy Rp 1.25T terjadi bersamaan dengan penguatan komoditas batu bara, namun IHSG tetap terkoreksi -0.25%, maka tekanan jual domestik mendominasi."
        ],
    }

    # Layer 1: save_learning must reject and return False
    assert save_learning(mock_date, mock_review) is False
    stats_file = get_memory_dir() / "nexus_stats.json"
    if stats_file.exists():
        stored = json.loads(stats_file.read_text(encoding="utf-8"))
        assert mock_review["lessons"][0] not in stored.get("all_lessons", [])

    # Layer 2: filter_and_quarantine_lessons must quarantine with reason mock_provenance_rejected
    valid, rejected = filter_and_quarantine_lessons([mock_review])
    assert len(valid) == 0
    assert len(rejected) == 1
    assert "mock_provenance" in rejected[0]["reason"]


def test_stats_rejects_mock_provenance_and_excludes_null_correctness():
    runs_dir = get_runs_dir()
    mock_date = "2026-10-16"
    mock_dir = runs_dir / mock_date
    mock_dir.mkdir(parents=True, exist_ok=True)
    (mock_dir / "evening_actuals.json").write_text(
        json.dumps(
            {
                "date": mock_date,
                "data_quality": {"fields": {"ihsg": {"source": "mock_yfinance"}}},
            }
        ),
        encoding="utf-8",
    )

    reviews = [
        # 5 Genuine scorable sessions (4 hits, 1 miss -> 80.0%)
        {
            "date": f"2026-10-0{i}",
            "ihsg_predicted": "Bearish",
            "ihsg_actual": "Bearish" if i <= 4 else "Bullish",
            "ihsg_actual_pct": -0.5 if i <= 4 else 0.5,
            "ihsg_correct": True if i <= 4 else False,
            "ihsg_confidence": 75,
            "accuracy_score": 100 if i <= 4 else 0,
        }
        for i in range(1, 6)
    ] + [
        # Genuine unscorable (ihsg_correct is None) -> Phase 3.2: must NOT be counted in direction_scorable_sessions (n)
        {
            "date": "2026-10-06",
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.4,
            "ihsg_correct": None,
            "ihsg_confidence": 80,
            "accuracy_score": None,
        },
        # Mock session -> Phase 2.2: must be completely rejected
        {
            "date": mock_date,
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.25,
            "ihsg_correct": False,
            "ihsg_confidence": 68,
            "accuracy_score": 0,
        },
    ]

    stats = compute_canonical_stats(reviews)
    assert mock_date in stats["rejected_mock_dates"]
    assert mock_date not in stats["processed_dates"]
    # Only the 5 genuine scorable sessions are counted in n; 2026-10-06 (ihsg_correct=None) and 2026-10-16 (mock) are excluded
    assert stats["direction_scorable_sessions"] == 5
    assert stats["direction_correct_count"] == 4
    assert stats["direction_accuracy_pct"] == 80.0


def test_rescore_history_and_index_reject_mock_runs(tmp_path: Path):
    runs_dir = get_runs_dir()

    # Genuine run
    gen_dir = runs_dir / "2026-10-07"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "morning_prediction.json").write_text(
        json.dumps({"date": "2026-10-07", "ihsg_signal": "Bearish", "ihsg_confidence": 80}),
        encoding="utf-8",
    )
    (gen_dir / "evening_actuals.json").write_text(
        json.dumps({"date": "2026-10-07", "ihsg_close": 6150.0, "ihsg_change_pct": -0.5, "ihsg_signal": "Bearish"}),
        encoding="utf-8",
    )
    (gen_dir / "evening_review.json").write_text(
        json.dumps({"date": "2026-10-07", "ihsg_predicted": "Bearish", "ihsg_actual": "Bearish", "ihsg_correct": True}),
        encoding="utf-8",
    )

    # Mock run
    mock_dir = runs_dir / "2026-10-16"
    mock_dir.mkdir(parents=True, exist_ok=True)
    (mock_dir / "morning_prediction.json").write_text(
        json.dumps({"date": "2026-10-16", "ihsg_signal": "Bullish", "evidence_ids": ["src_mock_1"]}),
        encoding="utf-8",
    )
    (mock_dir / "evening_actuals.json").write_text(
        json.dumps(
            {
                "date": "2026-10-16",
                "ihsg_close": 7230.0,
                "data_quality": {"fields": {"ihsg": {"source": "mock_yfinance"}}},
            }
        ),
        encoding="utf-8",
    )
    (mock_dir / "evening_review.json").write_text(
        json.dumps({"date": "2026-10-16", "ihsg_predicted": "Bullish", "ihsg_actual": "Bearish", "ihsg_correct": False}),
        encoding="utf-8",
    )

    assert check_run_dir_provenance(gen_dir)[0] is False
    assert check_run_dir_provenance(mock_dir)[0] is True

    # rescore_run rejects mock_dir and returns (None, None)
    assert rescore_run(mock_dir, apply=False)[0] is None
    assert rescore_run(gen_dir, apply=False)[0] is not None

    # build_runs_index excludes 2026-10-16 and lists it in rejected_mock_dates / rejected_mock_runs
    idx = build_runs_index(runs_dir)
    assert "2026-10-07" in idx["all_dates"]
    assert "2026-10-16" not in idx["all_dates"]
    assert idx["latest_date"] == "2026-10-07"
    assert "2026-10-16" in idx["rejected_mock_dates"]
    assert any(item["date"] == "2026-10-16" for item in idx["rejected_mock_runs"])
