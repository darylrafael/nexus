"""Unit tests for Phase 6 & Phase A: Packaging, REQUIRED_FILES, Untracked Guard, Secret Scanning, and Hygiene."""

import pathlib
import subprocess
import zipfile

import pytest

from core.packaging import (
    REQUIRED_FILES,
    REQUIRED_PACKAGES,
    check_no_percent_paths,
    check_untracked_files,
    collect_allowlisted_files,
    is_allowed_release_path,
    is_forbidden_path,
    scan_files_for_personal_paths,
    scan_files_for_secrets,
    verify_zip_contents,
)
from core.paths import REPO_ROOT


def test_no_percent_prefixed_paths_in_repo():
    """Phase 6.1: Ensure no '%SystemDrive%' or other '%' path exists in repo root."""
    offenders = check_no_percent_paths(REPO_ROOT)
    assert offenders == [], f"Found forbidden %-prefixed paths in repo: {offenders}"


def test_forbidden_patterns_rejected_by_denylist():
    """Phase 6.2 & A1: Verify all forbidden patterns are rejected by the denylist."""
    forbidden_samples = [
        "nexus_sessions.db",
        "data/cache.db",
        "runs/test.sqlite",
        "runs/test.sqlite3",
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
        assert not is_allowed_release_path(sample), f"Expected {sample} to be rejected"

    allowed_samples = [
        ".env.example",
        "llm_client.py",
        "LEGAL.md",
        "RUNBOOK.md",
        "requirements.lock",
        ".python-version",
        "register_tasks.ps1",
        ".dockerignore",
        "pytest.ini",
        "README.md",
        "core/paths.py",
        "core/packaging.py",
        "scripts/evaluate.py",
        "dashboard/src/app/page.js",
        "runs/global/nexus_stats.json",
    ]
    for sample in allowed_samples:
        assert is_allowed_release_path(sample), f"Expected {sample} to be allowed"


def test_untracked_file_causes_hard_failure_in_git_repo(tmp_path: pathlib.Path):
    """Phase A1: Untracked files must cause a hard failure with a clear message."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(fake_repo), check=True)
    (fake_repo / "tracked.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.py"], cwd=str(fake_repo), check=True)

    # Create an untracked file
    (fake_repo / "forgotten_module.py").write_text("y = 2\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        check_untracked_files(fake_repo)
    assert "untracked file forgotten_module.py would be missing from the package: git add it or ignore it" in str(
        exc_info.value
    )


def test_collect_allowlisted_files_works_without_dot_git(tmp_path: pathlib.Path):
    """Phase A4: When .git is absent, collect_allowlisted_files walks the filesystem with the same denylist."""
    extracted = tmp_path / "unzipped_tree"
    extracted.mkdir()
    (extracted / "llm_client.py").write_text("x = 1\n", encoding="utf-8")
    (extracted / ".env.example").write_text("OPENROUTER_API_KEY=\n", encoding="utf-8")
    (extracted / ".env").write_text("OPENROUTER_API_KEY=secret\n", encoding="utf-8")
    (extracted / "nexus_sessions.db").write_bytes(b"sqlite")
    cache_dir = extracted / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "llm_client.cpython-311.pyc").write_bytes(b"pyc")

    collected = collect_allowlisted_files(extracted)
    assert "llm_client.py" in collected
    assert ".env.example" in collected
    assert ".env" not in collected
    assert "nexus_sessions.db" not in collected
    assert not any("__pycache__" in f for f in collected)


def test_release_zip_contains_only_allowlisted_files_and_no_forbidden_patterns(tmp_path: pathlib.Path):
    """Phase 6.2, A1, A2, A4, A5: Build release zip in tmp_path and inspect every entry & required manifest."""
    out_zip = tmp_path / "nexus_test_bundle.zip"
    # Use strict_untracked=False inside unit test in case developer has work-in-progress files,
    # while build_release_zip enforces strict_untracked=True when .git is present.
    files = collect_allowlisted_files(REPO_ROOT, strict_untracked=False)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(REPO_ROOT / rel, arcname=rel)

    assert len(files) > 50
    assert out_zip.is_file()

    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()

    # Check all REQUIRED_FILES and REQUIRED_PACKAGES are present (Phase A2 & A5)
    for req_file in REQUIRED_FILES:
        assert req_file in names, f"Required file missing from zip: {req_file}"
    for req_pkg in REQUIRED_PACKAGES:
        assert any(n.startswith(req_pkg) for n in names), f"Required package missing from zip: {req_pkg}"

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


def test_removing_required_file_makes_verification_fail(tmp_path: pathlib.Path):
    """Phase A5: Removing a required file (e.g. llm_client.py) from the zip makes verify_zip_contents fail."""
    files = collect_allowlisted_files(REPO_ROOT, strict_untracked=False)
    incomplete_zip = tmp_path / "missing_llm_client.zip"
    with zipfile.ZipFile(incomplete_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            if rel == "llm_client.py":
                continue
            zf.write(REPO_ROOT / rel, arcname=rel)

    violations = verify_zip_contents(incomplete_zip)
    assert any("Missing required file in zip: llm_client.py" in v for v in violations), (
        f"Expected missing llm_client.py violation, got: {violations}"
    )


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
    """Phase 6.3 & A4: Secret scan passes on repo (with or without .git) and detects synthetic API keys."""
    files = collect_allowlisted_files(REPO_ROOT, strict_untracked=False)
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


def test_personal_path_scan_passes_on_repo_and_catches_leaks(tmp_path: pathlib.Path):
    """Phase A3: Personal path scan passes on repo and catches leaked local/tooling paths."""
    files = collect_allowlisted_files(REPO_ROOT, strict_untracked=False)
    findings = scan_files_for_personal_paths(files, REPO_ROOT)
    assert findings == [], f"Personal/tooling path scan found issues in repository: {findings}"

    # Negative example (synthetic leaks caught)
    tool_word = "anti" + "gravity"
    bs = chr(92)
    fake_win = f"PATH = \"C:{bs}Users{bs}JohnDoe{bs}project{bs}file.txt\"\n"
    fake_leaks = [
        ("leak_win.py", fake_win),
        ("leak_linux.py", 'PATH = "' + "/ho" + "me/developer/nexus/config.py\"\n"),
        ("leak_mac.py", 'PATH = "' + "/Us" + "ers/alice/secrets.json\"\n"),
        ("leak_gemini.py", 'PATH = "/tmp/' + ".ge" + 'mini/cache/model.bin"\n'),
        ("leak_tool.py", f'PATH = "/tmp/{tool_word}/brain/data"\n'),
        ("leak_uuid.py", 'SESSION = "' + "12345678" + "-abcd" + '-ef01-2345-6789abcdef01"\n'),
    ]
    for fname, content in fake_leaks:
        (tmp_path / fname).write_text(content, encoding="utf-8")

    leak_findings = scan_files_for_personal_paths([f[0] for f in fake_leaks], tmp_path)
    assert len(leak_findings) == len(fake_leaks), f"Expected {len(fake_leaks)} findings, got: {leak_findings}"

    # Positive example (clean generic code passes)
    clean_code = (
        'import os\n'
        'from pathlib import Path\n'
        'DEFAULT_DIR = Path("./audit_output")\n'
        'USER_CONFIG = os.environ.get("NEXUS_CONFIG", "./config.yaml")\n'
    )
    (tmp_path / "clean_module.py").write_text(clean_code, encoding="utf-8")
    clean_findings = scan_files_for_personal_paths(["clean_module.py"], tmp_path)
    assert clean_findings == []

