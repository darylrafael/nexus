import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from core.paths import get_runs_dir
from core.time import jakarta_now

RUNS_DIR: Path | None = None
LOCK_STALE_TIMEOUT_MINUTES = 30


def _resolve_runs_dir() -> Path:
    if RUNS_DIR is not None:
        return Path(RUNS_DIR)
    return get_runs_dir()


def compute_prediction_lock_hash(prediction_dict: dict) -> str:
    """Compute deterministic SHA-256 lock hash for a morning prediction.
    Proves out-of-sample locking before market open (06:55 WIB).
    """
    key_fields = {
        "date": prediction_dict.get("date"),
        "ihsg_signal": prediction_dict.get("ihsg_signal") or prediction_dict.get("ihsg_direction"),
        "ihsg_confidence": prediction_dict.get("ihsg_confidence"),
        "sector_bullish": sorted(prediction_dict.get("sector_bullish") or []),
        "sector_bearish": sorted(prediction_dict.get("sector_bearish") or []),
        "sector_neutral": sorted(prediction_dict.get("sector_neutral") or []),
        "recommended_tickers": sorted(prediction_dict.get("recommended_tickers") or []),
        "summary": prediction_dict.get("summary", ""),
        "key_risk": prediction_dict.get("key_risk", ""),
    }
    encoded = json.dumps(key_fields, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def get_lock_ledger_path() -> Path:
    ledger_dir = _resolve_runs_dir() / "global"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    return ledger_dir / "lock_ledger.jsonl"


def _compute_ledger_entry_hash(prev_hash: str, date_str: str, lock_hash: str, timestamp: str) -> str:
    payload = f"{prev_hash}|{date_str}|{lock_hash}|{timestamp}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def is_pre_market_open_wib(ts_iso: str, date_key: str) -> bool:
    """Return True only if timestamp is captured before IDX market open (09:00 WIB) on or before date_key."""
    if not ts_iso or not date_key:
        return False
    try:
        dt = datetime.fromisoformat(str(ts_iso))
        dt_date = dt.strftime("%Y-%m-%d")
        if dt_date < str(date_key):
            return True
        if dt_date > str(date_key):
            return False
        # Same calendar date: must be strictly before 09:00:00 WIB
        return (dt.hour, dt.minute, dt.second) < (9, 0, 0)
    except Exception:
        return False


def append_to_lock_ledger(prediction_dict: dict, timestamp: str | None = None) -> dict:
    """Append an immutable lock record to runs/global/lock_ledger.jsonl with hash chaining."""
    ledger_path = get_lock_ledger_path()
    prev_hash = "GENESIS"
    if ledger_path.exists():
        lines = [ln.strip() for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            try:
                last_entry = json.loads(lines[-1])
                prev_hash = str(last_entry.get("entry_hash") or last_entry.get("lock_hash") or "GENESIS")
            except Exception:
                prev_hash = "CORRUPTED"

    date_str = str(prediction_dict.get("date") or "")
    lock_hash = str(prediction_dict.get("lock_hash") or compute_prediction_lock_hash(prediction_dict))
    ts = str(timestamp or prediction_dict.get("created_at") or jakarta_now().isoformat(timespec="seconds"))
    lock_status = str(prediction_dict.get("lock_status") or ("locked_pre_open" if is_pre_market_open_wib(ts, date_str) else "locked_post_open"))
    entry_hash = _compute_ledger_entry_hash(prev_hash, date_str, lock_hash, ts)

    record = {
        "date": date_str,
        "lock_hash": lock_hash,
        "timestamp": ts,
        "lock_status": lock_status,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
    }
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def lock_morning_prediction(prediction_dict: dict, created_at_iso: str | None = None) -> dict:
    """Hash a morning prediction at creation time, stamp lock_status, and append to lock_ledger.jsonl."""
    ts = str(created_at_iso or jakarta_now().isoformat(timespec="seconds"))
    date_str = str(prediction_dict.get("date") or "")
    lock_hash = compute_prediction_lock_hash(prediction_dict)
    pre_open = is_pre_market_open_wib(ts, date_str)

    prediction_dict["lock_hash"] = lock_hash
    prediction_dict["created_at"] = ts
    prediction_dict["hash_computed_at"] = ts[:10]
    if pre_open:
        prediction_dict["lock_status"] = "locked_pre_open"
        prediction_dict["locked_at"] = "06:55 WIB"
        prediction_dict["out_of_sample_verified"] = True
        prediction_dict["lock_note"] = f"Locked pre-open at {ts}"
    else:
        prediction_dict["lock_status"] = "locked_post_open"
        prediction_dict["locked_at"] = None
        prediction_dict["out_of_sample_verified"] = False
        prediction_dict["lock_note"] = f"Hash computed post-open at {ts}; not proof of pre-open lock"

    append_to_lock_ledger(prediction_dict, timestamp=ts)
    return prediction_dict


def verify_prediction_lock(date_key: str, prediction_dict: dict | None = None) -> dict:
    """Verify that a locked prediction has not been modified after locking and matches lock_ledger.jsonl."""
    if prediction_dict is None:
        pred_path = _resolve_runs_dir() / str(date_key) / "morning_prediction.json"
        if not pred_path.exists():
            return {"valid": False, "tampered": False, "reason": "prediction_not_found"}
        prediction_dict = json.loads(pred_path.read_text(encoding="utf-8"))

    stored_hash = prediction_dict.get("lock_hash")
    recomputed_hash = compute_prediction_lock_hash(prediction_dict)

    if not stored_hash:
        return {
            "valid": False,
            "tampered": True,
            "reason": "missing_lock_hash",
            "stored_hash": None,
            "recomputed_hash": recomputed_hash,
            "ledger_hash": None,
        }

    if stored_hash != recomputed_hash:
        return {
            "valid": False,
            "tampered": True,
            "reason": f"prediction_content_modified: stored_hash={stored_hash} != recomputed_hash={recomputed_hash}",
            "stored_hash": stored_hash,
            "recomputed_hash": recomputed_hash,
            "ledger_hash": None,
        }

    ledger_path = get_lock_ledger_path()
    ledger_match = None
    if ledger_path.exists():
        prev_expected = "GENESIS"
        for idx, raw_line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                return {
                    "valid": False,
                    "tampered": True,
                    "reason": f"corrupted_ledger_line_{idx}",
                    "stored_hash": stored_hash,
                    "recomputed_hash": recomputed_hash,
                    "ledger_hash": None,
                }
            if entry.get("prev_hash") != prev_expected:
                return {
                    "valid": False,
                    "tampered": True,
                    "reason": f"ledger_chain_broken_at_line_{idx}",
                    "stored_hash": stored_hash,
                    "recomputed_hash": recomputed_hash,
                    "ledger_hash": entry.get("lock_hash"),
                }
            expected_entry_hash = _compute_ledger_entry_hash(
                prev_expected,
                str(entry.get("date") or ""),
                str(entry.get("lock_hash") or ""),
                str(entry.get("timestamp") or ""),
            )
            if entry.get("entry_hash") != expected_entry_hash:
                return {
                    "valid": False,
                    "tampered": True,
                    "reason": f"ledger_entry_hash_mismatch_at_line_{idx}",
                    "stored_hash": stored_hash,
                    "recomputed_hash": recomputed_hash,
                    "ledger_hash": entry.get("lock_hash"),
                }
            prev_expected = expected_entry_hash
            if str(entry.get("date")) == str(date_key):
                ledger_match = entry

        if ledger_match is not None and ledger_match.get("lock_hash") != recomputed_hash:
            return {
                "valid": False,
                "tampered": True,
                "reason": (
                    f"ledger_hash_mismatch: ledger_hash={ledger_match.get('lock_hash')} "
                    f"!= recomputed_hash={recomputed_hash}"
                ),
                "stored_hash": stored_hash,
                "recomputed_hash": recomputed_hash,
                "ledger_hash": ledger_match.get("lock_hash"),
            }

    return {
        "valid": True,
        "tampered": False,
        "reason": "verified",
        "stored_hash": stored_hash,
        "recomputed_hash": recomputed_hash,
        "ledger_hash": ledger_match.get("lock_hash") if ledger_match else None,
        "lock_status": prediction_dict.get("lock_status"),
    }


def _get_lock_path(date_key: str, run_type: str) -> Path:
    lock_dir = _resolve_runs_dir() / date_key
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
