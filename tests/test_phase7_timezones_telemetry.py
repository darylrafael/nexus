from datetime import timedelta
from unittest.mock import patch

from core.time import jakarta_now
from memory.session import init_db, log_session, export_telemetry_json
from memory.artifacts import save_json_artifact, load_json_artifact
from memory.obsidian import write_note, reset_obsidian_status
from delivery.telegram import markdown_to_safe_html
from utils.text import split_text
from schemas import validate_artifact_data


# ── 1. Timezone Integrity ────────────────────────────────────────────────────

def test_jakarta_now_timezone_awareness():
    now_jkt = jakarta_now()
    assert now_jkt.tzinfo is not None
    # Offset for Asia/Jakarta must be +07:00 (25200 seconds)
    assert now_jkt.utcoffset() == timedelta(hours=7)


# ── 2. Telemetry Failure Logging & Sanitization ──────────────────────────────

def test_telemetry_failure_logging_and_privacy_scrubbing(tmp_path, monkeypatch):
    db_file = tmp_path / "test_telemetry.db"
    monkeypatch.setattr("memory.session.DB_PATH", db_file)
    monkeypatch.setattr("memory.session._DB_INITIALIZED", False)

    init_db()

    # 1. Log a failed run
    fail_id = log_session(
        query="SELECT * FROM confidential_internal_query",
        agent="market_agent",
        model="gpt-oss-120b",
        result="Secret API result output",
        success=False,
        error_msg="Connection timeout connecting to upstream provider",
        duration_ms=4500
    )
    assert fail_id is not None

    # 2. Log a successful run
    ok_id = log_session(
        query="public_query",
        agent="market_agent",
        model="gpt-oss-120b",
        result="Public summary output",
        success=True,
        duration_ms=1200
    )
    assert ok_id is not None

    # 3. Export telemetry artifact and verify privacy scrubbing
    telemetry_path = tmp_path / "telemetry.json"
    exported = export_telemetry_json(output_path=telemetry_path)

    assert exported["stats"]["totalRuns"] == 2
    assert exported["stats"]["successfulRuns"] == 1
    assert exported["stats"]["failedRuns"] == 1

    # Verify query and result text are removed from public API payload
    for sess in exported["sessions"]:
        assert "query" not in sess
        assert "result" not in sess
        assert "error_msg" in sess


# ── 3. Telegram Formatting & Splitting ───────────────────────────────────────

def test_markdown_to_safe_html_conversion():
    raw = "*IHSG* menguat +0.5% & <saham> `BBRI` naik! _BULLISH_ signal."
    html_out = markdown_to_safe_html(raw)

    # Must convert bold to <b>
    assert "<b>IHSG</b>" in html_out
    # Must convert inline code to <code>
    assert "<code>BBRI</code>" in html_out
    # Must convert italic to <i>
    assert "<i>BULLISH</i>" in html_out
    # Must escape raw HTML tags and ampersands
    assert "&amp;" in html_out
    assert "&lt;saham&gt;" in html_out
    assert "<saham>" not in html_out


def test_telegram_snake_case_not_broken_by_italic():
    raw = "Variabel morning_prediction dan market_agent_run tidak boleh italic."
    html_out = markdown_to_safe_html(raw)
    assert "morning_prediction" in html_out
    assert "market_agent_run" in html_out
    assert "<i>prediction" not in html_out


def test_telegram_text_splitting_on_paragraph_boundaries():
    para1 = "A" * 1500
    para2 = "B" * 1500
    para3 = "C" * 1500
    full_text = f"{para1}\n\n{para2}\n\n{para3}"

    chunks = split_text(full_text, max_length=2000)
    assert len(chunks) == 3
    assert chunks[0] == para1
    assert chunks[1] == para2
    assert chunks[2] == para3


# ── 4. Artifact Schema Validation & Versioning ───────────────────────────────

def test_artifact_schema_validation(tmp_path, monkeypatch):
    monkeypatch.setattr("memory.artifacts.ARTIFACT_ROOT", tmp_path)

    # Valid morning prediction
    valid_pred = {
        "date": "2026-10-08",
        "ihsg_signal": "BULLISH",
        "ihsg_confidence": 75,
        "foreign_flow_signal": "NET_BUY",
    }
    is_valid, _ = validate_artifact_data("morning_prediction.json", valid_pred)
    assert is_valid is True

    # Invalid morning prediction missing required field
    invalid_pred = {"date": "2026-10-08", "ihsg_signal": "BULLISH"}
    is_valid, reason = validate_artifact_data("morning_prediction.json", invalid_pred)
    assert is_valid is False
    assert "foreign_flow_signal" in reason

    # Automatic schema_version attachment on save
    saved_path = save_json_artifact("2026-10-08", "morning_prediction.json", valid_pred)
    assert saved_path.exists()
    loaded = load_json_artifact("2026-10-08", "morning_prediction.json")
    assert loaded["schema_version"] == 1


# ── 5. Obsidian Offline Circuit Breaker ──────────────────────────────────────

def test_obsidian_circuit_breaker(monkeypatch):
    monkeypatch.setattr("memory.obsidian.OBSIDIAN_API_KEY", "dummy_test_key")
    reset_obsidian_status()

    import memory.obsidian as obs
    assert obs._OBSIDIAN_UNREACHABLE is False

    with patch("requests.put", side_effect=Exception("Connection refused")):
        res1 = write_note("Test-1", "Content 1")
        assert res1 is False
        assert obs._OBSIDIAN_UNREACHABLE is True

    # Subsequent call must short-circuit without calling requests
    with patch("requests.put") as mock_put:
        res2 = write_note("Test-2", "Content 2")
        assert res2 is False
        mock_put.assert_not_called()

    reset_obsidian_status()
