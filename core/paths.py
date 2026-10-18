"""
core/paths.py

Single canonical path resolver for all Nexus directories and files.
All artifact, database, memory, vault, and data paths must be resolved through
this module so that tests and CI can isolate filesystem writes via environment
variables (NEXUS_RUNS_DIR, NEXUS_DB_PATH, NEXUS_MEMORY_DIR, NEXUS_VAULT_DIR,
NEXUS_DASHBOARD_RUNS_DIR, NEXUS_DATA_DIR).
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_RUNS_SUBDIR = "runs"
_DEFAULT_DB_FILENAME = "nexus_sessions.db"


def get_runs_dir() -> Path:
    """Resolve the active runs directory (configurable via NEXUS_RUNS_DIR)."""
    env_val = os.getenv("NEXUS_RUNS_DIR")
    if env_val:
        return Path(env_val)
    return REPO_ROOT / _DEFAULT_RUNS_SUBDIR


def get_memory_dir() -> Path:
    """Resolve the global memory/stats directory (configurable via NEXUS_MEMORY_DIR)."""
    env_val = os.getenv("NEXUS_MEMORY_DIR")
    if env_val:
        return Path(env_val)
    return get_runs_dir() / "global"


def get_db_path() -> Path:
    """Resolve the SQLite sessions database path (configurable via NEXUS_DB_PATH or NEXUS_SESSIONS_DB)."""
    env_val = os.getenv("NEXUS_DB_PATH") or os.getenv("NEXUS_SESSIONS_DB")
    if env_val:
        return Path(env_val)
    return REPO_ROOT / _DEFAULT_DB_FILENAME


def get_vault_dir() -> Path:
    """Resolve the local vault directory (configurable via NEXUS_VAULT_DIR)."""
    env_val = os.getenv("NEXUS_VAULT_DIR")
    if env_val:
        return Path(env_val)
    return get_runs_dir() / "vault"


def get_dashboard_runs_dir() -> Path:
    """Resolve the Next.js dashboard runs mirror directory.

    When NEXUS_DASHBOARD_RUNS_DIR is set, uses that path.
    When NEXUS_RUNS_DIR is overridden (e.g. in tests), redirects inside
    NEXUS_RUNS_DIR so writes never escape to the real dashboard/data/runs.
    """
    env_dash = os.getenv("NEXUS_DASHBOARD_RUNS_DIR")
    if env_dash:
        return Path(env_dash)
    env_runs = os.getenv("NEXUS_RUNS_DIR")
    if env_runs:
        return Path(env_runs) / "_dashboard_mirror"
    return REPO_ROOT / "dashboard" / "data" / _DEFAULT_RUNS_SUBDIR


def get_data_dir() -> Path:
    """Resolve static reference data directory (configurable via NEXUS_DATA_DIR)."""
    env_val = os.getenv("NEXUS_DATA_DIR")
    if env_val:
        return Path(env_val)
    return REPO_ROOT / "data"
