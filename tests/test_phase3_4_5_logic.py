"""
Unit and regression tests for Phases 3, 4, and 5:
- Phase 3.2: null ihsg_correct excluded from direction n
- Phase 3.4: scripts/evaluate.py metric block sync & absence of contaminated n=13 figures
- Phase 4.1: USD/IDR vs Rupiah FX convention detection and unreliable_source_data vs sign_confusion
- Phase 4.2: Hand-computed calibrated confidence shrinkage and n < 30 label
- Phase 4.3: Lessons from failed data_quality or mock provenance sessions are not injected
- Phase 5.1 & 5.2: Retroactive lock status on historical runs, lock_ledger.jsonl hash chain, and tamper detection
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from core.locking import (
    get_lock_ledger_path,
    lock_morning_prediction,
    verify_prediction_lock,
)
from memory.learning_store import (
    build_learning_context,
    filter_and_quarantine_lessons,
    validate_lesson,
)
from scripts.evaluate import (
    METRICS_END,
    METRICS_START,
    TARGET_DOCS,
    build_metrics_markdown,
    sync_doc_metric_blocks,
)
from utils.stats import (
    compute_canonical_stats,
    compute_empirical_calibrated_confidence,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_phase3_2_null_ihsg_correct_excluded_from_direction_n():
    """A session with ihsg_correct = None must never be counted as a miss in direction n."""
    reviews = [
        {
            "date": "2026-09-22",
            "ihsg_predicted": "Bearish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.45,
            "ihsg_correct": True,
            "ihsg_confidence": 75,
        },
        {
            "date": "2026-09-23",
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.60,
            "ihsg_correct": False,
            "ihsg_confidence": 80,
        },
        {
            "date": "2026-09-24",
            "ihsg_predicted": "Bearish",
            "ihsg_actual": "Pending",
            "ihsg_actual_pct": None,
            "ihsg_correct": None,
            "ihsg_confidence": 75,
        },
    ]
    stats = compute_canonical_stats(reviews)
    assert stats["direction_scorable_sessions"] == 2
    assert stats["direction_correct_count"] == 1
    assert stats["sample_size_n"] == 2
    assert stats["baselines"]["always_bearish_total"] == 2


def test_phase3_4_docs_metric_blocks_synced_and_free_of_contaminated_numbers():
    """All target docs must have synced METRICS blocks and zero contaminated n=13 figures."""
    real_stats_path = REPO_ROOT / "runs" / "global" / "nexus_stats.json"
    real_index_path = REPO_ROOT / "runs" / "index.json"
    assert real_stats_path.exists()
    stats = json.loads(real_stats_path.read_text(encoding="utf-8"))
    raw_index = json.loads(real_index_path.read_text(encoding="utf-8")) if real_index_path.exists() else None

    expected_md = build_metrics_markdown(stats, raw_index)
    mismatched = sync_doc_metric_blocks(expected_md, check_only=True)
    assert mismatched == [], f"Out-of-sync metric blocks in: {mismatched}"

    forbidden_contaminated = [
        "38.5%",
        "-204.0 bps",
        "-204 bps",
        "+40.0 bps",
        "+40 bps",
        "0.4044",
        "47.8%",
        "69.2%",
        "30.8%",
    ]
    for doc_path in TARGET_DOCS:
        text = doc_path.read_text(encoding="utf-8")
        assert METRICS_START in text and METRICS_END in text, f"Missing markers in {doc_path.name}"
        for bad in forbidden_contaminated:
            assert bad not in text, f"Contaminated metric {bad!r} found in {doc_path.name}"


def test_phase4_1_rupiah_vs_usdidr_convention_and_historical_rejections():
    """
    Verify USD/IDR vs Rupiah convention detection and accurate rejection reasons
    for 2026-09-28, 2026-10-01, and 2026-10-07.
    """
    # 1. "Rupiah menguat -0.318%" is valid under USD/IDR convention
    ok, reason = validate_lesson(
        "Ketika sentimen global membaik, tetapi Rupiah dapat menguat (-0.318%) meskipun dolar indeks stabil, maka tekanan jual mereda.",
        session_actuals={
            "date": "2026-10-02",
            "usdidr_change_pct": -0.318,
            "rupiah_signal": "Strengthened",
            "data_quality": {"spot_usdidr_change_pct": -0.318, "fx_reliable": True},
        },
    )
    assert ok is True
    assert reason == "valid"

    # 2. Explicit USD/IDR convention: "USD/IDR naik +0.48%" is valid when actual is +0.476%
    ok_pair, reason_pair = validate_lesson(
        "Ketika pasar dibuka, tetapi USD/IDR naik +0.48% akibat arus keluar obligasi, maka sektor perbankan terkoreksi.",
        session_actuals={
            "date": "2026-10-01",
            "usdidr_change_pct": 0.476,
            "rupiah_signal": "Weakened",
            "data_quality": {"spot_usdidr_change_pct": 0.476, "fx_reliable": True},
        },
    )
    assert ok_pair is True
    assert reason_pair == "valid"

    # 3. Explicit USD/IDR sign contradiction: "USD/IDR naik -0.48%" -> sign_confusion
    ok_bad_pair, reason_bad_pair = validate_lesson(
        "Ketika pasar dibuka, tetapi USD/IDR naik -0.48% pada perdagangan sore, maka IHSG tertekan.",
        session_actuals={
            "date": "2026-10-01",
            "usdidr_change_pct": -0.48,
            "data_quality": {"spot_usdidr_change_pct": -0.48, "fx_reliable": True},
        },
    )
    assert ok_bad_pair is False
    assert "sign_confusion" in reason_bad_pair

    # 4. Direction contradicts stored actuals: "Rupiah menguat -0.318%" when actual was +0.534% -> sign_confusion
    ok_dir_mismatch, reason_dir_mismatch = validate_lesson(
        "Ketika pasar dibuka, tetapi Rupiah menguat -0.318% pada sesi penutupan, maka IHSG menguat.",
        session_actuals={
            "date": "2026-10-07",
            "usdidr_change_pct": 0.534,
            "rupiah_signal": "Weakened",
            "data_quality": {"spot_usdidr_change_pct": 0.534, "fx_reliable": True},
        },
    )
    assert ok_dir_mismatch is False
    assert "sign_confusion" in reason_dir_mismatch

    # 5. Check real rescored nexus_stats.json for 2026-09-28, 2026-10-01, 2026-10-07 rejected reasons
    real_stats = json.loads((REPO_ROOT / "runs" / "global" / "nexus_stats.json").read_text(encoding="utf-8"))
    rejected_by_date = {}
    for item in real_stats.get("rejected_lessons", []):
        rejected_by_date.setdefault(item["date"], []).append(item["reason"])

    assert any("unreliable_source_data" in r for r in rejected_by_date.get("2026-09-28", []))
    assert any("unreliable_source_data" in r for r in rejected_by_date.get("2026-10-01", []))
    assert any("unreliable_source_data" in r for r in rejected_by_date.get("2026-10-07", []))
    for d in ("2026-09-28", "2026-10-01", "2026-10-07"):
        assert not any("sign_confusion" in r for r in rejected_by_date.get(d, []))


def test_phase4_2_hand_computed_calibrated_confidence():
    """
    Hand-computed verification of compute_empirical_calibrated_confidence:
    Example A (canonical corpus): k=5, n=12, stated=79.6%, N0=30, prior_cap=55.0%
      w = min(12 / 30, 1.0) = 0.4
      p_realized = (5 / 12) * 100 = 41.6666667%
      p_prior = min(79.6, 55.0) = 55.0%
      calibrated = round(0.4 * 41.6666667 + 0.6 * 55.0, 1) = round(49.6666667, 1) = 49.7%
      status_label = "illustrative shrinkage estimate" (since n=12 < 30)
    """
    res_a = compute_empirical_calibrated_confidence(
        direction_correct=5,
        direction_scorable=12,
        stated_confidence_pct=79.6,
    )
    assert res_a["calibrated_confidence_pct"] == 49.7
    assert res_a["sample_size_n"] == 12
    assert res_a["empirical_weight"] == 0.4
    assert res_a["prior_pct"] == 55.0
    assert res_a["prior_strength_n0"] == 30
    assert res_a["status_label"] == "illustrative shrinkage estimate"

    res_b = compute_empirical_calibrated_confidence(
        direction_correct=6,
        direction_scorable=15,
        stated_confidence_pct=50.0,
    )
    assert res_b["calibrated_confidence_pct"] == 45.0
    assert res_b["status_label"] == "illustrative shrinkage estimate"

    res_c = compute_empirical_calibrated_confidence(
        direction_correct=18,
        direction_scorable=30,
        stated_confidence_pct=80.0,
    )
    assert res_c["calibrated_confidence_pct"] == 60.0
    assert res_c["status_label"] == "calibrated"


def test_phase4_3_lessons_from_failed_data_quality_or_mock_not_injected():
    """Lessons from sessions with failed data_quality or mock provenance must not be injected."""
    reviews = [
        # 1. Valid genuine session (session 1)
        {
            "date": "2026-10-01",
            "ihsg_predicted": "Bearish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.45,
            "ihsg_correct": True,
            "accuracy_score": 80,
            "data_quality": {"overall_valid": True, "ohlc_valid": True, "fx_consistent": True},
            "lessons": [
                "Ketika sektor teknologi diprediksi Bullish, tetapi imbal hasil obligasi naik, maka sektor teknologi terkoreksi."
            ],
        },
        # 2. Failed data_quality session (session 2)
        {
            "date": "2026-10-02",
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.70,
            "ihsg_correct": False,
            "accuracy_score": 20,
            "data_quality": {"overall_valid": False, "ohlc_valid": False},
            "lessons": [
                "Ketika data OHLC tidak valid pada sesi penutupan, tetapi indeks terlihat turun, maka sinyal menjadi bias."
            ],
        },
        # 3. Mock provenance session (session 3)
        {
            "date": "2026-10-05",
            "ihsg_predicted": "Bullish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.25,
            "ihsg_correct": False,
            "accuracy_score": 20,
            "data_quality": {
                "overall_valid": True,
                "fields": {"ihsg": {"source": "mock_yfinance"}},
            },
            "lessons": [
                "Ketika foreign flow net buy Rp 1.25T terjadi, tetapi IHSG tetap turun -0.25%, maka tekanan domestik mendominasi."
            ],
        },
        # 4. Subsequent genuine session validating session 1
        {
            "date": "2026-10-06",
            "ihsg_predicted": "Bearish",
            "ihsg_actual": "Bearish",
            "ihsg_actual_pct": -0.50,
            "ihsg_correct": True,
            "accuracy_score": 85,
            "sector_accuracy": {"Technology": False},
            "data_quality": {"overall_valid": True, "ohlc_valid": True, "fx_consistent": True},
            "lessons": [],
        },
    ]

    valid_lessons, rejected = filter_and_quarantine_lessons(reviews)
    assert any("sektor teknologi terkoreksi" in l for l in valid_lessons)
    assert not any("sinyal menjadi bias" in l for l in valid_lessons)
    assert not any("foreign flow net buy Rp 1.25T" in l for l in valid_lessons)
    assert any("data_quality_failed" in r["reason"] for r in rejected)
    assert any("mock_provenance" in r["reason"] for r in rejected)

    context_str = build_learning_context(reviews)
    assert "sinyal menjadi bias" not in context_str
    assert "foreign flow net buy Rp 1.25T" not in context_str
    assert "2026-10-02" not in context_str
    assert "2026-10-05" not in context_str


def test_phase5_lock_ledger_and_post_lock_tamper_detection():
    """
    Verify that locking a prediction writes to runs/global/lock_ledger.jsonl,
    and editing a prediction after locking is detected by verify_prediction_lock.
    """
    # 1. Verify historical predictions in real repo are marked retroactive
    hist_pred_path = REPO_ROOT / "runs" / "2026-10-08" / "morning_prediction.json"
    hist_pred = json.loads(hist_pred_path.read_text(encoding="utf-8"))
    assert hist_pred["lock_status"] == "retroactive"
    assert hist_pred["out_of_sample_verified"] is False
    assert hist_pred["locked_at"] is None
    assert "retroactively" in hist_pred["lock_note"]

    # 2. Lock a new prediction created at 06:55 WIB (pre-open)
    wib_tz = timezone(timedelta(hours=7))
    created_pre_open = datetime(2026, 10, 19, 6, 55, 0, tzinfo=wib_tz).isoformat(timespec="seconds")
    pred = {
        "date": "2026-10-19",
        "ihsg_direction": "Bearish",
        "ihsg_confidence": 75,
        "foreign_flow_outlook": "Selling/Distribution",
        "key_risk": "Global bond yield spike",
        "summary": "Bearish bias on rising yields.",
        "sectors": {"Financials": "Bearish"},
    }
    locked = lock_morning_prediction(pred, created_at_iso=created_pre_open)
    assert locked["lock_status"] == "locked_pre_open"
    assert locked["out_of_sample_verified"] is True
    assert locked["locked_at"] == "06:55 WIB"
    assert get_lock_ledger_path().exists()

    # Verify untampered prediction passes verification
    verify_ok = verify_prediction_lock("2026-10-19", locked)
    assert verify_ok["valid"] is True
    assert verify_ok["tampered"] is False

    # 3. Tamper with the prediction after locking and verify detection
    tampered = dict(locked)
    tampered["ihsg_direction"] = "Bullish"
    verify_bad = verify_prediction_lock("2026-10-19", tampered)
    assert verify_bad["valid"] is False
    assert verify_bad["tampered"] is True
    assert "prediction_content_modified" in verify_bad["reason"]


def test_lock_ledger_chain_and_entry_tamper_detection(tmp_path, monkeypatch):
    """Phase D4: End-to-end verification detects tampered entry_hash and broken prev_hash chains in lock ledger."""
    import core.locking as lock_mod

    # Run strictly in isolated tmp_path
    monkeypatch.setattr(lock_mod, "RUNS_DIR", tmp_path / "runs")

    wib_tz = timezone(timedelta(hours=7))
    t1 = datetime(2026, 10, 19, 6, 50, 0, tzinfo=wib_tz).isoformat(timespec="seconds")
    t2 = datetime(2026, 10, 20, 6, 50, 0, tzinfo=wib_tz).isoformat(timespec="seconds")

    pred1 = {"date": "2026-10-19", "ihsg_direction": "Bearish", "ihsg_confidence": 70}
    locked1 = lock_morning_prediction(pred1, created_at_iso=t1)

    pred2 = {"date": "2026-10-20", "ihsg_direction": "Bullish", "ihsg_confidence": 65}
    locked2 = lock_morning_prediction(pred2, created_at_iso=t2)

    # Both initial predictions verify cleanly
    assert verify_prediction_lock("2026-10-19", locked1)["valid"] is True
    assert verify_prediction_lock("2026-10-20", locked2)["valid"] is True

    ledger_file = get_lock_ledger_path()
    lines = [json.loads(line) for line in ledger_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2

    # 1. Tamper with prev_hash in line 2 of the ledger
    lines_corrupted_chain = [dict(lines[0]), dict(lines[1])]
    lines_corrupted_chain[1]["prev_hash"] = "TAMPERED_PREV_HASH"
    ledger_file.write_text("\n".join(json.dumps(ln) for ln in lines_corrupted_chain) + "\n", encoding="utf-8")
    verify_chain_tamper = verify_prediction_lock("2026-10-20", locked2)
    assert verify_chain_tamper["valid"] is False
    assert verify_chain_tamper["tampered"] is True
    assert "ledger_chain_broken" in verify_chain_tamper["reason"]

    # 2. Tamper with entry_hash in line 1 of the ledger
    lines_corrupted_entry = [dict(lines[0]), dict(lines[1])]
    lines_corrupted_entry[0]["entry_hash"] = "tampered_entry_hash"
    ledger_file.write_text("\n".join(json.dumps(ln) for ln in lines_corrupted_entry) + "\n", encoding="utf-8")
    verify_entry_tamper = verify_prediction_lock("2026-10-19", locked1)
    assert verify_entry_tamper["valid"] is False
    assert verify_entry_tamper["tampered"] is True
    assert "ledger_entry_hash_mismatch" in verify_entry_tamper["reason"]

