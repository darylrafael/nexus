import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.schedule import load_schedule_config, get_job_schedule
from core.locking import (
    acquire_run_lock,
    release_run_lock,
    run_lock_context,
)
from utils.dates import (
    is_late_night_stale,
    should_delegate_to_evening_review,
    resolve_evening_review_date,
)


# ── 1. Schedule Configuration ────────────────────────────────────────────────

def test_canonical_schedule_specification():
    cfg = load_schedule_config()
    assert cfg["timezone"] == "Asia/Jakarta"
    assert "morning_brief" in cfg["jobs"]
    assert "evening_review" in cfg["jobs"]

    m_job = get_job_schedule("morning_brief")
    assert m_job["time_wib"] == "06:55"
    assert m_job["hour_wib"] == 6
    assert m_job["minute_wib"] == 55
    assert m_job["cron_utc"] == "55 23 * * 0-4"

    e_job = get_job_schedule("evening_review")
    assert e_job["time_wib"] == "20:00"
    assert e_job["hour_wib"] == 20
    assert e_job["minute_wib"] == 0
    assert e_job["cron_utc"] == "0 13 * * 1-5"


# ── 2. Run Locking & Idempotency ─────────────────────────────────────────────

def test_run_lock_acquisition_and_release(tmp_path, monkeypatch):
    monkeypatch.setattr("core.locking.RUNS_DIR", tmp_path)

    date_key = "2026-10-09"
    run_type = "morning_brief"

    # 1. First acquisition succeeds
    assert acquire_run_lock(date_key, run_type) is True

    # 2. Duplicate concurrent acquisition fails
    assert acquire_run_lock(date_key, run_type) is False

    # 3. Release lock
    release_run_lock(date_key, run_type)

    # 4. Can acquire again after release
    assert acquire_run_lock(date_key, run_type) is True
    release_run_lock(date_key, run_type)


def test_run_lock_stale_override(tmp_path, monkeypatch):
    monkeypatch.setattr("core.locking.RUNS_DIR", tmp_path)

    date_key = "2026-10-09"
    run_type = "evening_review"

    lock_dir = tmp_path / date_key
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f".lock_{run_type}"

    # Simulate an abandoned lock from 45 minutes ago
    stale_time = (datetime.now() - timedelta(minutes=45)).isoformat()
    lock_file.write_text(json.dumps({
        "date": date_key,
        "run_type": run_type,
        "pid": 99999,
        "locked_at": stale_time
    }), encoding="utf-8")

    # Stale lock must be broken and acquired
    assert acquire_run_lock(date_key, run_type) is True
    release_run_lock(date_key, run_type)


def test_run_lock_context_manager(tmp_path, monkeypatch):
    monkeypatch.setattr("core.locking.RUNS_DIR", tmp_path)

    date_key = "2026-10-09"
    with run_lock_context(date_key, "morning_brief") as acquired:
        assert acquired is True
        # While inside context, secondary lock must fail
        assert acquire_run_lock(date_key, "morning_brief") is False

    # After exiting context, lock should be released
    assert acquire_run_lock(date_key, "morning_brief") is True
    release_run_lock(date_key, "morning_brief")


# ── 3. Date & Scheduling Guard Helpers ───────────────────────────────────────

def test_late_night_stale_guard():
    # 23:30 WIB -> stale (Anti-2AM)
    dt_stale_late = datetime(2026, 10, 8, 23, 30)
    assert is_late_night_stale(dt_stale_late) is True

    # 02:00 WIB -> stale
    dt_stale_early = datetime(2026, 10, 9, 2, 0)
    assert is_late_night_stale(dt_stale_early) is True

    # 20:00 WIB -> normal review window
    dt_normal = datetime(2026, 10, 8, 20, 0)
    assert is_late_night_stale(dt_normal) is False


def test_should_delegate_to_evening_review():
    dt_after_close = datetime(2026, 10, 8, 16, 30)
    # Post close, morning brief exists, evening review pending -> delegate
    assert should_delegate_to_evening_review(dt_after_close, brief_exists=True, review_exists=False) is True

    # Post close, but morning brief does NOT exist -> do not delegate
    assert should_delegate_to_evening_review(dt_after_close, brief_exists=False, review_exists=False) is False

    # Morning brief time (07:00) -> do not delegate
    dt_morning = datetime(2026, 10, 8, 7, 0)
    assert should_delegate_to_evening_review(dt_morning, brief_exists=True, review_exists=False) is False


def test_resolve_evening_review_date_with_target():
    assert resolve_evening_review_date(target_date="2026-09-30") == "2026-09-30"
