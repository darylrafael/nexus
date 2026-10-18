"""
tests/conftest.py
Global pytest configuration for Nexus test suite.
Provides:
- Dummy environment variables so tests never require a real .env.
- Automatic isolated directories (NEXUS_RUNS_DIR, NEXUS_DB_PATH, NEXUS_MEMORY_DIR,
  NEXUS_VAULT_DIR, NEXUS_DASHBOARD_RUNS_DIR) via tmp_path for every test.
- Session-level integrity guard that computes SHA-256 checksums of real runs/,
  data/, dashboard/data/runs/, and repo-root *.db files before and after the test
  session, failing the suite if any real file was created, modified, or deleted.
"""
import hashlib
import os
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Enforce skip flags and dummy required credentials before imports
os.environ["NEXUS_SKIP_ENV_VALIDATION"] = "1"
os.environ["SKIP_ENV_VALIDATION"] = "1"
os.environ.setdefault("OPENROUTER_API_KEY", "dummy_test_openrouter_key")
os.environ.setdefault("TAVILY_API_KEY", "dummy_test_tavily_key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy_test_telegram_token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456789")
os.environ.setdefault("OBSIDIAN_API_KEY", "dummy_test_obsidian_key")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return "unreadable"


def _snapshot_protected_paths() -> dict[str, str]:
    """Build a deterministic {relative_path: sha256} map of real runs/, data/, and *.db."""
    snapshot: dict[str, str] = {}
    protected_dirs = [
        REPO_ROOT / "runs",
        REPO_ROOT / "data",
        REPO_ROOT / "dashboard" / "data" / "runs",
    ]
    for d in protected_dirs:
        if d.exists():
            for p in sorted(d.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(REPO_ROOT).as_posix()
                    snapshot[rel] = _hash_file(p)

    for db_p in sorted(REPO_ROOT.glob("*.db*")):
        if db_p.is_file():
            rel = db_p.relative_to(REPO_ROOT).as_posix()
            snapshot[rel] = _hash_file(db_p)

    return snapshot


@pytest.fixture(scope="session", autouse=True)
def guard_real_repo_artifacts():
    """
    Session-level guard: fails the test suite if anything under the real
    runs/, data/, dashboard/data/runs/, or repo-root *.db changed during pytest.
    """
    before = _snapshot_protected_paths()
    yield
    after = _snapshot_protected_paths()
    if before != after:
        added = sorted(set(after.keys()) - set(before.keys()))
        removed = sorted(set(before.keys()) - set(after.keys()))
        modified = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
        details = []
        if added:
            details.append(f"Added: {added}")
        if removed:
            details.append(f"Removed: {removed}")
        if modified:
            details.append(f"Modified: {modified}")
        pytest.fail(
            "CRITICAL: Test suite mutated real repository data/runs/db files! "
            + " | ".join(details)
        )


@pytest.fixture(autouse=True)
def isolated_nexus_environment(tmp_path, monkeypatch):
    """
    Ensure every test operates on isolated tmp_path directories for runs,
    memory, vault, dashboard mirror, and SQLite sessions database.
    """
    runs_dir = tmp_path / "runs"
    memory_dir = runs_dir / "global"
    vault_dir = tmp_path / "vault"
    dash_runs_dir = tmp_path / "dashboard_runs"
    test_db = tmp_path / "nexus_sessions_test.db"

    runs_dir.mkdir(parents=True, exist_ok=True)
    memory_dir.mkdir(parents=True, exist_ok=True)
    vault_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("NEXUS_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("NEXUS_MEMORY_DIR", str(memory_dir))
    monkeypatch.setenv("NEXUS_VAULT_DIR", str(vault_dir))
    monkeypatch.setenv("NEXUS_DASHBOARD_RUNS_DIR", str(dash_runs_dir))
    monkeypatch.setenv("NEXUS_DB_PATH", str(test_db))
    monkeypatch.setenv("NEXUS_SESSIONS_DB", str(test_db))

    from memory.session import set_db_path, init_db
    from memory.obsidian import reset_obsidian_status

    set_db_path(None)
    init_db(force=True)
    reset_obsidian_status()
    yield {
        "runs_dir": runs_dir,
        "memory_dir": memory_dir,
        "vault_dir": vault_dir,
        "dash_runs_dir": dash_runs_dir,
        "db_path": test_db,
    }
