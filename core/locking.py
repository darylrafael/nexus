import os
import json
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from core.time import jakarta_now

RUNS_DIR = Path(__file__).parent.parent / "runs"
LOCK_STALE_TIMEOUT_MINUTES = 30


def _get_lock_path(date_key: str, run_type: str) -> Path:
    lock_dir = RUNS_DIR / date_key
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f".lock_{run_type}"


def acquire_run_lock(date_key: str, run_type: str) -> bool:
    """
    Acquire an idempotent run lock for a specific date and run type (e.g., 'morning_brief' or 'evening_review').
    Guarantees that cloud runner and local laptop cannot execute overlapping or duplicate runs.
    Returns True if lock was acquired, False if already held by another active process.
    """
    lock_path = _get_lock_path(date_key, run_type)
    now = jakarta_now()

    if lock_path.exists():
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            locked_at_str = data.get("locked_at")
            if locked_at_str:
                locked_at = datetime.fromisoformat(locked_at_str)
                if locked_at.tzinfo is None:
                    age = now.replace(tzinfo=None) - locked_at
                else:
                    age = now - locked_at

                if age < timedelta(minutes=LOCK_STALE_TIMEOUT_MINUTES):
                    # Active lock held
                    return False
                else:
                    # Stale lock, proceed to break it
                    print(f"[locking] Breaking stale lock for {date_key} ({run_type}) aged {age}")
        except Exception:
            pass

    payload = {
        "date": date_key,
        "run_type": run_type,
        "pid": os.getpid(),
        "runner": "github_actions" if os.getenv("GITHUB_ACTIONS") else "local_environment",
        "locked_at": now.isoformat(),
    }

    try:
        lock_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[locking] Failed to write lock file {lock_path}: {e}")
        return False


def release_run_lock(date_key: str, run_type: str) -> None:
    """Release the run lock file."""
    lock_path = _get_lock_path(date_key, run_type)
    if lock_path.exists():
        try:
            lock_path.unlink()
        except Exception as e:
            print(f"[locking] Warning: could not delete lock {lock_path}: {e}")


@contextmanager
def run_lock_context(date_key: str, run_type: str):
    """Context manager for managing run lock acquisition and automatic release."""
    acquired = acquire_run_lock(date_key, run_type)
    if not acquired:
        yield False
        return
    try:
        yield True
    finally:
        release_run_lock(date_key, run_type)
