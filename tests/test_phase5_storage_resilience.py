import concurrent.futures
import pytest
from unittest.mock import patch
import requests

from memory.artifacts import (
    atomic_write_file,
    save_json_artifact,
    load_json_artifact,
)
from memory.obsidian import write_note, read_note, read_recent_notes
from memory.session import _get_conn, init_db, log_session, export_telemetry_json
from memory.learning_store import save_learning, update_performance_stats


def test_atomic_write_file_basic(tmp_path):
    target = tmp_path / "test_artifact.json"
    content = '{"status": "ok", "count": 42}'
    
    written_path = atomic_write_file(target, content)
    assert written_path == target
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content

    # Check that no temp files remain in directory
    temp_files = list(tmp_path.glob(".tmp_*"))
    assert len(temp_files) == 0


def test_atomic_write_file_overwrite(tmp_path):
    target = tmp_path / "data.txt"
    atomic_write_file(target, "first content")
    assert target.read_text(encoding="utf-8") == "first content"

    atomic_write_file(target, "updated content")
    assert target.read_text(encoding="utf-8") == "updated content"


def test_atomic_write_cleanup_on_failure(tmp_path):
    target = tmp_path / "fail.txt"
    target.write_text("initial", encoding="utf-8")

    # Simulate an error during os.replace
    with patch("os.replace", side_effect=OSError("Disk write error")):
        with pytest.raises(OSError):
            atomic_write_file(target, "new failing content")

    # Original content preserved
    assert target.read_text(encoding="utf-8") == "initial"
    # No temporary file left
    temp_files = list(tmp_path.glob(".tmp_*"))
    assert len(temp_files) == 0


def test_save_and_load_json_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr("memory.artifacts.ARTIFACT_ROOT", tmp_path)
    
    payload = {"accuracy": 85.5, "notes": ["lesson 1", "lesson 2"]}
    saved = save_json_artifact("2026-10-08", "summary.json", payload)
    
    assert saved.exists()
    loaded = load_json_artifact("2026-10-08", "summary.json")
    assert loaded == payload


def test_obsidian_offline_resilience():
    # When Obsidian API is down (ConnectionError)
    with patch("requests.put", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        success = write_note("test-note", "# Test Content")
        assert success is False

    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        content = read_note("test-note")
        assert content == ""

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        recent = read_recent_notes(days=7)
        assert recent == ""


def test_learning_store_resilience_when_obsidian_offline(tmp_path, monkeypatch):
    monkeypatch.setattr("memory.learning_store.ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr("memory.artifacts.ARTIFACT_ROOT", tmp_path)

    sample_learning = {
        "date": "2026-10-08",
        "summary": "Market moved bullish",
        "accuracy_score": 80.0,
        "ihsg_predicted": "BULLISH",
        "ihsg_actual": "BULLISH",
        "ihsg_correct": True,
        "foreign_flow_predicted": "NET_BUY",
        "foreign_flow_actual": "NET_BUY",
        "foreign_flow_correct": True,
        "sector_accuracy": {"Finance": True},
        "lessons": ["Follow bank flow"],
    }

    # Even if Obsidian write fails, save_learning and update_performance_stats should not crash
    with patch("memory.learning_store.write_note", return_value=False):
        save_res = save_learning("2026-10-08", sample_learning)
        assert save_res is False  # reports obsidian failed cleanly

        stat_res = update_performance_stats(sample_learning)
        assert stat_res is False  # reports obsidian sync failed cleanly

    # But local artifact was saved!
    local_stats = load_json_artifact("global", "nexus_stats.json")
    assert local_stats is not None
    assert local_stats["total_sessions"] >= 1
    assert local_stats["direction_correct_count"] >= 1


def test_sqlite_wal_mode_and_concurrency(tmp_path, monkeypatch):
    db_file = tmp_path / "test_sessions.db"
    monkeypatch.setattr("memory.session.DB_PATH", db_file)

    conn = _get_conn()
    journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
    conn.close()

    assert journal_mode.lower() == "wal"
    assert busy_timeout == 30000

    init_db()

    # Test concurrent logging across 5 threads
    def worker(i):
        return log_session(
            query=f"query-{i}",
            agent="market_agent",
            model="gpt-oss-120b",
            result=f"result-{i}",
            success=True,
            duration_ms=100 + i
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        session_ids = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(session_ids) == 10
    assert len(set(session_ids)) == 10

    # Test telemetry export
    telemetry_path = tmp_path / "telemetry.json"
    telemetry = export_telemetry_json(output_path=telemetry_path)
    assert telemetry["stats"]["totalRuns"] == 10
    assert telemetry_path.exists()


def test_managed_connection_auto_closes_on_normal_exit(tmp_path):
    """Phase D3: _ManagedConnection automatically commits and closes on normal with-block exit."""
    import sqlite3
    from memory.session import _ManagedConnection

    db_file = tmp_path / "managed_test.db"
    conn = sqlite3.connect(db_file, factory=_ManagedConnection)
    with conn:
        conn.execute("CREATE TABLE items (id INT, val TEXT);")
        conn.execute("INSERT INTO items VALUES (1, 'hello');")

    # Connection must be closed on exiting 'with conn'
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
        conn.execute("SELECT * FROM items;")

    # Verify committed changes persisted on a new connection
    conn2 = sqlite3.connect(db_file)
    row = conn2.execute("SELECT val FROM items WHERE id=1;").fetchone()
    conn2.close()
    assert row[0] == "hello"


def test_managed_connection_rolls_back_and_closes_on_exception(tmp_path):
    """Phase D3: _ManagedConnection rolls back transaction and closes even when an exception is raised."""
    import sqlite3
    from memory.session import _ManagedConnection

    db_file = tmp_path / "managed_rollback.db"
    conn0 = sqlite3.connect(db_file)
    conn0.execute("CREATE TABLE items (id INT, val TEXT);")
    conn0.commit()
    conn0.close()

    conn = sqlite3.connect(db_file, factory=_ManagedConnection)
    with pytest.raises(ValueError, match="simulated failure"):
        with conn:
            conn.execute("INSERT INTO items VALUES (2, 'aborted');")
            raise ValueError("simulated failure")

    # Connection must be closed
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
        conn.execute("SELECT * FROM items;")

    # Verify aborted row was rolled back
    conn2 = sqlite3.connect(db_file)
    rows = conn2.execute("SELECT * FROM items;").fetchall()
    conn2.close()
    assert len(rows) == 0

