"""Unit tests for Phase 6: Packaging, Secret Scanning, and Hygiene."""

import pathlib
import zipfile

from core.packaging import (
    build_release_zip,
    check_no_percent_paths,
    collect_allowlisted_files,
    is_allowed_release_path,
    is_forbidden_path,
    scan_files_for_secrets,
    verify_zip_contents,
)
from core.paths import REPO_ROOT


def test_no_percent_prefixed_paths_in_repo():
    """Phase 6.1: Ensure no '%SystemDrive%' or other '%' path exists in repo root."""
    offenders = check_no_percent_paths(REPO_ROOT)
    assert offenders == [], f"Found forbidden %-prefixed paths in repo: {offenders}"


def test_forbidden_patterns_rejected_by_allowlist():
    """Phase 6.2: Verify all forbidden patterns are rejected by the allowlist."""
    forbidden_samples = [
        "nexus_sessions.db",
        "data/cache.db",
        "runs/test.sqlite",
        ".ruff_cache/0.15.6/cache",
        "scripts/fix_dashboard_audit.py",
        "scripts/package_deliverables.py",
        "agents/__pycache__/market_agent.cpython-311.pyc",
        "dashboard/node_modules/next/package.json",
        "dashboard/.next/BUILD_ID",
        ".env",
        ".env.local",
        "config.py.bak",
        "%SystemDrive%/ProgramData/Microsoft/Windows/Caches/cversions.2.db",
    ]
    for sample in forbidden_samples:
        is_forb, reason = is_forbidden_path(sample)
        assert is_forb, f"Expected {sample} to be marked forbidden"
        assert reason != ""
        assert not is_allowed_release_path(sample), f"Expected {sample} to be rejected by allowlist"

    # Verify legitimate files are allowed
    allowed_samples = [
        ".env.example",
        "README.md",
        "core/paths.py",
        "core/packaging.py",
        "scripts/evaluate.py",
        "dashboard/src/app/page.js",
        "runs/global/nexus_stats.json",
    ]
    for sample in allowed_samples:
        assert is_allowed_release_path(sample), f"Expected {sample} to be allowed"


def test_release_zip_contains_only_allowlisted_files_and_no_forbidden_patterns(tmp_path: pathlib.Path):
    """Phase 6.2: Build release zip in tmp_path and inspect every entry."""
    out_zip = tmp_path / "nexus_test_bundle.zip"
    count, files = build_release_zip(out_zip, REPO_ROOT)
    assert count > 50
    assert out_zip.is_file()

    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()

    assert ".env.example" in names
    assert ".env" not in names
    assert "nexus_sessions.db" not in names
    assert "scripts/fix_dashboard_audit.py" not in names
    assert "scripts/package_deliverables.py" not in names

    for name in names:
        assert not name.endswith(".db"), f"Database file leaked into zip: {name}"
        assert not name.endswith(".bak"), f"Backup file leaked into zip: {name}"
        assert ".ruff_cache" not in name
        assert "__pycache__" not in name
        assert "node_modules" not in name
        assert ".next/" not in name
        assert not any(seg.startswith("%") for seg in name.split("/"))

    assert verify_zip_contents(out_zip) == []


def test_verify_zip_contents_detects_contaminated_archive(tmp_path: pathlib.Path):
    """Phase 6.2: verify_zip_contents fails if a forbidden file is added to a zip."""
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr(".env.example", "OPENROUTER_API_KEY=\n")
        zf.writestr("nexus_sessions.db", "sqlite-bytes")
        zf.writestr("scripts/fix_dashboard_audit.py", "print(1)")

    violations = verify_zip_contents(bad_zip)
    assert any("nexus_sessions.db" in v for v in violations)
    assert any("scripts/fix_dashboard_audit.py" in v for v in violations)


def test_secret_scan_passes_on_repo_and_catches_leaks(tmp_path: pathlib.Path):
    """Phase 6.3: Secret scan passes on repo and detects synthetic API keys."""
    files = collect_allowlisted_files(REPO_ROOT)
    findings = scan_files_for_secrets(files, REPO_ROOT)
    assert findings == [], f"Secret scan found issues in repository: {findings}"

    # Verify synthetic secret detection
    (tmp_path / ".env.example").write_text("OPENROUTER_API_KEY=your_key\n", encoding="utf-8")
    fake_secret = "sk-or-v1-" + ("a" * 32)
    (tmp_path / "leaked.py").write_text(f'KEY = "{fake_secret}"\n', encoding="utf-8")
    synth_findings = scan_files_for_secrets([".env.example", "leaked.py"], tmp_path)
    assert any("OpenRouter key" in f for f in synth_findings)


def test_session_py_has_no_unused_global_db_path():
    """Phase 6.4: memory/session.py has no `global DB_PATH` and uses configurable path."""
    session_code = (REPO_ROOT / "memory" / "session.py").read_text(encoding="utf-8")
    assert "global DB_PATH" not in session_code
