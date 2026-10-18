from memory.learning_store import filter_and_quarantine_lessons, validate_lesson
from utils.stats import (
    SCORING_WEIGHTS,
    compute_session_accuracy,
    format_accuracy_metric,
)


def test_validate_lesson_rejections():
    # 1. Reject +17K invalid unit notation
    l1 = "Ketika sektor Kesehatan diprediksi Bearish, tetapi sektor tersebut mengalami kenaikan terbesar (+17K), maka analisis sektor perlu..."
    valid1, reason1 = validate_lesson(l1)
    assert not valid1
    assert "invalid_unit" in reason1

    # 2. Reject unreliable FX source data when numeric pct disagrees with session actuals (2026-09-28 & 2026-10-01)
    l2 = "Ketika IHSG diprediksi Bearish dengan risiko pelemahan Rupiah, tetapi Rupiah melemah sebesar +0.871%, maka IHSG ditutup Bearish."
    valid2, reason2 = validate_lesson(
        l2,
        session_actuals={
            "date": "2026-09-28",
            "usdidr_change_pct": 0.871,
            "data_quality": {"spot_usdidr_change_pct": 0.268, "fx_reliable": False},
        },
    )
    assert not valid2
    assert "unreliable_source_data" in reason2

    l3 = "Ketika IHSG diprediksi Bullish, tetapi terjadi pelemahan Rupiah sebesar +2.195% dan sentimen global resesi, maka IHSG ditutup Bearish."
    valid3, reason3 = validate_lesson(
        l3,
        session_actuals={
            "date": "2026-10-01",
            "usdidr_change_pct": 2.195,
            "data_quality": {"spot_usdidr_change_pct": 0.476, "fx_reliable": False},
        },
    )
    assert not valid3
    assert "unreliable_source_data" in reason3

    # 3. Reject genuine sign confusion (explicit USD/IDR contradiction or spot-level contradiction)
    l_sign = "Ketika pasar dibuka, tetapi USD/IDR naik sebesar -0.50%, maka IHSG ditutup Bearish."
    valid_s, reason_s = validate_lesson(l_sign)
    assert not valid_s
    assert "sign_confusion" in reason_s

    # 4. Reject boilerplate
    l4 = "Ketika volatilitas pasar meningkat drastis, analis perlu memperketat stop-loss sektoral agar risiko modal terkendali."
    valid4, reason4 = validate_lesson(l4)
    assert not valid4
    assert "boilerplate" in reason4


def test_validate_lesson_accepts_clean_lessons():
    l_clean = "Ketika harga Brent Crude anjlok -3.42% dan Rupiah terdepresiasi ke level 17.900, maka sektor Energi tertekan turun -1.10%."
    valid, reason = validate_lesson(l_clean)
    assert valid
    assert reason == "valid"

    # Phase 4.1: "rupiah menguat -0.318%" is valid under USD/IDR convention when actuals match
    l_rupiah_strengthened = "Ketika sentimen global membaik, tetapi Rupiah dapat menguat -0.318%, maka tekanan jual mereda."
    valid_fx, reason_fx = validate_lesson(
        l_rupiah_strengthened,
        session_actuals={
            "date": "2026-10-02",
            "usdidr_change_pct": -0.318,
            "rupiah_signal": "Strengthened",
            "data_quality": {"spot_usdidr_change_pct": -0.318, "fx_reliable": True},
        },
    )
    assert valid_fx
    assert reason_fx == "valid"


def test_tail_deduplication_and_cap_per_session():
    # Session with 4 lessons sharing identical tail
    mock_review = {
        "date": "2026-09-30",
        "ihsg_correct": False,
        "ihsg_actual_pct": -0.83,
        "lessons": [
            "Ketika IHSG diprediksi Bearish, tetapi ketegangan geopolitik menyebabkan bursa saham Asia melemah, maka IHSG ditutup Bearish (-0.83%).",
            "Ketika foreign flow diprediksi Stagnant/Sideways, tetapi terjadi akumulasi asing, maka IHSG tetap ditutup Bearish (-0.83%).",
            "Ketika sektor Properti diprediksi Bearish, tetapi sektor properti justru naik +1.25%, maka IHSG tetap ditutup Bearish (-0.83%).",
            "Ketika sektor Banking diprediksi Neutral, tetapi sektor keuangan turun -0.38%, maka IHSG tetap ditutup Bearish (-0.83%).",
        ]
    }
    valid_lessons, rejected = filter_and_quarantine_lessons([mock_review])
    # The duplicate tails must be rejected or deduplicated, and maximum 2 per session
    assert len(valid_lessons) <= 2
    assert len(rejected) >= 2
    assert any("duplicate_tail" in r["reason"] for r in rejected)


def test_small_sample_stats_rules():
    # If scorable n < 5: pct is None, label is 'Insufficient data'
    flow_res = format_accuracy_metric(correct=0, scorable=1)
    assert flow_res["pct"] is None
    assert flow_res["label"] == "Insufficient data"
    assert flow_res["is_sufficient"] is False

    # If 5 <= scorable < 30: pct is calculated, label indicates sample too small
    dir_res = format_accuracy_metric(correct=5, scorable=12)
    assert dir_res["pct"] == 41.7
    assert "sample too small" in dir_res["label"]
    assert dir_res["is_sufficient"] is False

    # If scorable >= 30: is_sufficient is True
    large_res = format_accuracy_metric(correct=20, scorable=35)
    assert large_res["pct"] == 57.1
    assert large_res["is_sufficient"] is True


def test_scoring_weights_constant():
    assert SCORING_WEIGHTS["direction"] == 0.50
    assert SCORING_WEIGHTS["sector"] == 0.30
    assert SCORING_WEIGHTS["flow"] == 0.20
    # Blend calculation test
    acc = compute_session_accuracy(ihsg_correct=True, foreign_flow_correct=True, sector_accuracy={"Technology": True})
    assert acc == 100
