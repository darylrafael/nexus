"""Allowlist-based release packager, verifier, and smoke tester for Nexus.

Enforces Phase A & Phase 6 requirements:
- A1: Allowlist = `git ls-files` (tracked files) minus an explicit DENYLIST of
  forbidden patterns (`*.db`, `*.sqlite*`, `*.bak`, `*.pyc`, `*.log`, `.env` and
  `.env.*`, `__pycache__`, `node_modules`, `.next`, `.ruff_cache`, `.pytest_cache`,
  `.git`, any path segment starting with `%`, `scripts/fix_dashboard_audit.py`,
  `scripts/package_deliverables.py`). Untracked files cause a hard failure with
  a clear message:
  `"untracked file X would be missing from the package: git add it or ignore it"`.
- A4: When `.git` is absent (e.g. inside an extracted release archive), falls
  back to walking the filesystem with the same denylist instead of calling `git`.
- A5: Verifies `REQUIRED_FILES` and `REQUIRED_PACKAGES` exist in the built zip,
  in addition to checking forbidden patterns and secret patterns.
- A3: Provides an isolated package smoke test (`smoke_test_release_zip`) that
  extracts the zip into an empty temp directory (no `.git`, no `.env`, clean env),
  verifies core imports and `pytest -q`, and confirms `runs/` and `*.db` are
  untouched.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile
from typing import Dict, Iterable, List, Sequence, Tuple

from core.paths import REPO_ROOT

REQUIRED_FILES: Tuple[str, ...] = (
    "llm_client.py",
    "config.py",
    "main.py",
    "scheduler.py",
    "schemas.py",
    "requirements.txt",
    "requirements.lock",
    ".python-version",
    "pyproject.toml",
    "pytest.ini",
    ".env.example",
    ".dockerignore",
    "register_tasks.ps1",
    "README.md",
    "LEGAL.md",
    "RUNBOOK.md",
    "METHODOLOGY.md",
    "SECURITY.md",
    "dashboard/package.json",
    "dashboard/package-lock.json",
)

REQUIRED_PACKAGES: Tuple[str, ...] = (
    "agents/",
    "core/",
    "data_sources/",
    "memory/",
    "utils/",
    "orchestrator/",
    "delivery/",
    "demo_data/",
)

FORBIDDEN_EXACT_PATHS = frozenset({
    "scripts/fix_dashboard_audit.py",
    "scripts/package_deliverables.py",
    ".env",
})

FORBIDDEN_DIR_SEGMENTS = frozenset({
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".next",
    "out",
    ".pytest_cache",
    ".git",
    ".superpowers",
    "superpowers",
    "venv",
    ".venv",
    "env",
    ".idea",
    ".vscode",
})

FORBIDDEN_GLOBS = (
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.sqlite*",
    "*.bak",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    ".env.*",
)

SECRET_PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    ("OpenRouter key (sk-or-v1-)", re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}")),
    ("Google/Gemini key (AIza)", re.compile(r"AIza[0-9A-Za-z_-]{20,}")),
    ("Telegram Bot Token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("Tavily API key (tvly-)", re.compile(r"tvly-[A-Za-z0-9_-]{12,}")),
)


def normalize_rel_path(path_str: str) -> str:
    norm = path_str.replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    return norm.lstrip("/")


def is_forbidden_path(rel_path: str) -> Tuple[bool, str]:
    """Return (True, reason) if `rel_path` matches any forbidden packaging rule."""
    norm = normalize_rel_path(rel_path)
    if not norm:
        return True, "empty_path"

    parts = norm.split("/")
    for part in parts:
        if part.startswith("%"):
            return True, f"percent_prefixed_segment:{part}"
        if part in FORBIDDEN_DIR_SEGMENTS:
            return True, f"forbidden_dir_segment:{part}"

    if norm in FORBIDDEN_EXACT_PATHS:
        return True, f"forbidden_exact_path:{norm}"

    filename = parts[-1]
    if filename == ".env.example":
        return False, ""

    for pattern in FORBIDDEN_GLOBS:
        if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(norm, pattern):
            return True, f"forbidden_glob:{pattern}"

    return False, ""


def is_allowed_release_path(rel_path: str) -> bool:
    """Return True if `rel_path` is not excluded by the explicit denylist."""
    norm = normalize_rel_path(rel_path)
    forbidden, _ = is_forbidden_path(norm)
    return not forbidden


def check_untracked_files(repo_root: pathlib.Path = REPO_ROOT) -> List[str]:
    """Return untracked (non-ignored) files when `.git` is present.

    Raises RuntimeError if any untracked file exists so nothing required is
    silently dropped from the release package.
    """
    if not (repo_root / ".git").exists():
        return []

    res = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    untracked: List[str] = []
    for line in res.stdout.splitlines():
        norm = normalize_rel_path(line.strip())
        if not norm:
            continue
        if (repo_root / norm).is_file():
            untracked.append(norm)

    if untracked:
        first = untracked[0]
        raise RuntimeError(
            f"untracked file {first} would be missing from the package: git add it or ignore it "
            f"(all untracked: {untracked})"
        )
    return untracked


def _walk_filesystem_allowlisted(repo_root: pathlib.Path) -> List[str]:
    """Fallback file collector when `.git` is absent (e.g. inside an unzipped archive)."""
    selected: List[str] = []
    for root, dirs, files in os.walk(repo_root):
        root_path = pathlib.Path(root)
        # Prune forbidden directories in-place so os.walk does not descend into them
        dirs[:] = sorted(
            d for d in dirs
            if d not in FORBIDDEN_DIR_SEGMENTS and not d.startswith("%")
        )
        for fname in sorted(files):
            abs_file = root_path / fname
            rel = normalize_rel_path(str(abs_file.relative_to(repo_root)))
            if is_allowed_release_path(rel):
                selected.append(rel)
    return sorted(selected)


def collect_allowlisted_files(
    repo_root: pathlib.Path = REPO_ROOT,
    *,
    strict_untracked: bool = True,
) -> List[str]:
    """Collect release files via `git ls-files` minus the explicit denylist.

    If `.git` does not exist (e.g. inside an extracted release zip), falls back
    to walking `repo_root` with the same denylist.
    """
    if not (repo_root / ".git").exists():
        return _walk_filesystem_allowlisted(repo_root)

    if strict_untracked:
        check_untracked_files(repo_root)

    res = subprocess.run(
        ["git", "ls-files"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    selected: List[str] = []
    for line in sorted(set(res.stdout.splitlines())):
        norm = normalize_rel_path(line.strip())
        if not norm:
            continue
        abs_file = repo_root / norm
        if not abs_file.is_file():
            continue
        if is_allowed_release_path(norm):
            selected.append(norm)

    return selected


def check_no_percent_paths(repo_root: pathlib.Path = REPO_ROOT) -> List[str]:
    """Find any file or directory under repo_root whose name starts with '%'."""
    offenders: List[str] = []
    for item in repo_root.iterdir():
        if item.name.startswith("%"):
            offenders.append(normalize_rel_path(str(item.relative_to(repo_root))))
    return offenders


def scan_files_for_secrets(
    rel_paths: Iterable[str],
    repo_root: pathlib.Path = REPO_ROOT,
) -> List[str]:
    """Scan specified files for secret regex patterns and prohibited .env files."""
    findings: List[str] = []
    rel_list = [normalize_rel_path(p) for p in rel_paths]

    if ".env.example" not in rel_list:
        findings.append("Missing required .env.example in tracked/packaged files")

    for rel in rel_list:
        base = rel.split("/")[-1]
        if base == ".env" or (base.startswith(".env.") and base != ".env.example"):
            findings.append(f"Prohibited environment file present: {rel}")
            continue

        abs_path = repo_root / rel
        if not abs_path.is_file():
            continue
        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                findings.append(f"Secret pattern '{label}' matched in {rel}")

    return findings


def verify_zip_contents(zip_path: pathlib.Path) -> List[str]:
    """Inspect a built zip archive and return a list of any policy violations."""
    violations: List[str] = []
    if not zip_path.is_file():
        return [f"Zip archive does not exist: {zip_path}"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [normalize_rel_path(n) for n in zf.namelist() if not n.endswith("/")]
        name_set = set(names)

        for req_file in REQUIRED_FILES:
            if req_file not in name_set:
                violations.append(f"Missing required file in zip: {req_file}")

        for req_pkg in REQUIRED_PACKAGES:
            if not any(n.startswith(req_pkg) for n in names):
                violations.append(f"Missing required package in zip: {req_pkg}")

        for name in names:
            forbidden, reason = is_forbidden_path(name)
            if forbidden:
                violations.append(f"Forbidden entry in zip: {name} ({reason})")
            elif not is_allowed_release_path(name):
                violations.append(f"Non-allowlisted entry in zip: {name}")

            try:
                raw = zf.read(name).decode("utf-8", errors="ignore")
            except Exception:
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(raw):
                    violations.append(f"Secret '{label}' found inside zip entry {name}")

    return violations


def build_release_zip(
    output_zip: pathlib.Path,
    repo_root: pathlib.Path = REPO_ROOT,
) -> Tuple[int, List[str]]:
    """Build the clean allowlisted release zip and verify its contents."""
    files = collect_allowlisted_files(repo_root, strict_untracked=True)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(repo_root / rel, arcname=rel)

    violations = verify_zip_contents(output_zip)
    if violations:
        raise RuntimeError(
            "Release zip failed verification:\n" + "\n".join(f"  - {v}" for v in violations)
        )
    return len(files), files


def _snapshot_dir_sha256(root: pathlib.Path) -> Dict[str, str]:
    snap: Dict[str, str] = {}
    if not root.exists():
        return snap
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = normalize_rel_path(str(p.relative_to(root)))
            snap[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def smoke_test_release_zip(
    zip_path: pathlib.Path,
    *,
    use_fresh_venv: bool = False,
    install_deps: bool = False,
) -> Dict[str, object]:
    """Extract `zip_path` to an isolated temp directory (no .git, no .env) and run smoke tests.

    Verifies:
    1. `verify_zip_contents(zip_path)` passes.
    2. Extracted tree has no `.git`, no `.env`, and no `*.db`.
    3. Core pipeline imports succeed with `NEXUS_SKIP_ENV_VALIDATION=1`.
    4. `pytest -q` passes inside the extracted tree.
    5. `runs/` checksums and absence of `*.db` files are unchanged after `pytest -q`.
    """
    violations = verify_zip_contents(zip_path)
    if violations:
        raise RuntimeError(f"Zip failed pre-smoke verification: {violations}")

    with tempfile.TemporaryDirectory(prefix="nexus_pkg_smoke_") as tmp_dir:
        extract_root = pathlib.Path(tmp_dir) / "extracted"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        if (extract_root / ".git").exists():
            raise RuntimeError("Extracted zip must not contain .git directory")
        if (extract_root / ".env").exists():
            raise RuntimeError("Extracted zip must not contain .env file")

        runs_before = _snapshot_dir_sha256(extract_root.joinpath("runs"))
        dbs_before = list(extract_root.rglob("*.db"))
        if dbs_before:
            raise RuntimeError(f"Extracted zip contains .db files before test: {dbs_before}")

        python_exe = sys.executable
        if use_fresh_venv or install_deps:
            venv_dir = pathlib.Path(tmp_dir) / "smoke_venv"
            venv_cmd = [sys.executable, "-m", "venv"]
            if not install_deps:
                venv_cmd.append("--system-site-packages")
            venv_cmd.append(str(venv_dir))
            subprocess.run(venv_cmd, check=True, capture_output=True, text=True)
            if os.name == "nt":
                python_exe = str(venv_dir / "Scripts" / "python.exe")
            else:
                python_exe = str(venv_dir / "bin" / "python")

            if install_deps:
                req_file = (
                    extract_root / "requirements.lock"
                    if (extract_root / "requirements.lock").is_file()
                    else extract_root / "requirements.txt"
                )
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "-q", "-r", str(req_file), "pytest", "pytest-asyncio"],
                    cwd=str(extract_root),
                    check=True,
                )

        clean_env: Dict[str, str] = {}
        for k in ("PATH", "HOME", "USERPROFILE", "SystemRoot", "SystemDrive", "TEMP", "TMP", "PATHEXT"):
            if k in os.environ:
                clean_env[k] = os.environ[k]
        clean_env["NEXUS_SKIP_ENV_VALIDATION"] = "1"
        clean_env["NEXUS_IN_EXTRACTED_SMOKE_TEST"] = "1"
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"

        import_cmd = [
            python_exe,
            "-c",
            "import agents.market_agent, agents.evening_reviewer, agents.prediction_extractor, scheduler, config, llm_client; print('IMPORTS_OK')",
        ]
        imp_res = subprocess.run(
            import_cmd,
            cwd=str(extract_root),
            env=clean_env,
            capture_output=True,
            text=True,
        )
        if imp_res.returncode != 0:
            raise RuntimeError(
                f"Import smoke check failed (exit {imp_res.returncode}):\n"
                f"STDOUT: {imp_res.stdout}\nSTDERR: {imp_res.stderr}"
            )

        pytest_cmd = [python_exe, "-m", "pytest", "-q", "-o", "cache_dir=" + str(pathlib.Path(tmp_dir) / "pytest_cache")]
        pytest_res = subprocess.run(
            pytest_cmd,
            cwd=str(extract_root),
            env=clean_env,
            capture_output=True,
            text=True,
        )
        if pytest_res.returncode != 0:
            raise RuntimeError(
                f"Extracted pytest -q failed (exit {pytest_res.returncode}):\n"
                f"STDOUT: {pytest_res.stdout}\nSTDERR: {pytest_res.stderr}"
            )

        runs_after = _snapshot_dir_sha256(extract_root.joinpath("runs"))
        if runs_before != runs_after:
            raise RuntimeError("runs/ directory in extracted tree was modified during pytest!")

        dbs_after = list(extract_root.rglob("*.db"))
        if dbs_after:
            raise RuntimeError(f".db files were created in extracted tree during pytest: {dbs_after}")

        return {
            "imports_stdout": imp_res.stdout.strip(),
            "pytest_stdout": pytest_res.stdout.strip(),
            "runs_files_count": len(runs_after),
            "runs_unchanged": runs_before == runs_after,
            "db_files_created": len(dbs_after),
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nexus allowlist packager & hygiene check")
    parser.add_argument("--verify-hygiene", action="store_true", help="Run % path, untracked, and secret scans")
    parser.add_argument("--build-zip", type=str, help="Build allowlisted release zip at path")
    parser.add_argument("--verify-zip", type=str, help="Verify an existing release zip")
    parser.add_argument("--smoke-test-zip", type=str, help="Run isolated extraction + import + pytest smoke test on zip")
    parser.add_argument("--smoke-test-with-venv", action="store_true", help="Use a fresh venv during --smoke-test-zip")
    parser.add_argument("--smoke-test-install-deps", action="store_true", help="Create a fresh venv and pip install requirements.lock during --smoke-test-zip")
    args = parser.parse_args(argv)

    if args.verify_hygiene:
        pct_paths = check_no_percent_paths(REPO_ROOT)
        if pct_paths:
            print(f"ERROR: Paths starting with '%' found: {pct_paths}", file=sys.stderr)
            return 1
        try:
            files = collect_allowlisted_files(REPO_ROOT, strict_untracked=True)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        secret_findings = scan_files_for_secrets(files, REPO_ROOT)
        if secret_findings:
            print("ERROR: Secret scan failed:", file=sys.stderr)
            for item in secret_findings:
                print(f"  - {item}", file=sys.stderr)
            return 1
        print(f"OK: Hygiene, untracked check & secret scan passed across {len(files)} tracked files.")

    if args.build_zip:
        out_path = pathlib.Path(args.build_zip)
        try:
            count, _ = build_release_zip(out_path, REPO_ROOT)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"OK: Built verified allowlist zip at {out_path} ({count} files).")

    if args.verify_zip:
        zpath = pathlib.Path(args.verify_zip)
        violations = verify_zip_contents(zpath)
        if violations:
            print("ERROR: Zip verification failed:", file=sys.stderr)
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            return 1
        print(
            f"OK: Zip archive verified clean ({len(REQUIRED_FILES)} required files and "
            f"{len(REQUIRED_PACKAGES)} required packages present): {zpath}"
        )

    if args.smoke_test_zip:
        zpath = pathlib.Path(args.smoke_test_zip)
        try:
            res = smoke_test_release_zip(
                zpath,
                use_fresh_venv=args.smoke_test_with_venv,
                install_deps=args.smoke_test_install_deps,
            )
        except RuntimeError as exc:
            print(f"ERROR: Smoke test failed: {exc}", file=sys.stderr)
            return 1
        print(f"OK: Package smoke test passed: {res['imports_stdout']}")
        print(res["pytest_stdout"])
        print(
            f"OK: Post-test integrity verified (runs_files={res['runs_files_count']}, "
            f"runs_unchanged={res['runs_unchanged']}, db_files_created={res['db_files_created']})."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
