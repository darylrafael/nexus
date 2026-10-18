"""Allowlist-based release packager and repository hygiene verifier for Nexus.

Enforces Phase 6 requirements:
- Builds public release archives strictly from tracked files (`git ls-files`)
  plus explicit allowed project paths (`EXPLICIT_ALLOWED_EXTRAS`), filtered
  through a strict allowlist.
- Rejects and verifies absence of forbidden patterns:
  SQLite DB files (`*.db`), `.ruff_cache`, `scripts/fix_dashboard_audit.py`,
  `scripts/package_deliverables.py`, `__pycache__`, `node_modules`, `.next`,
  `.env`, `*.bak`, and any path component starting with `%`.
- Scans tracked and packaged files for leaked API keys (`sk-or-v1-`, `AIza`,
  Telegram bot token pattern, `tvly-`) and confirms only `.env.example` is
  present.
"""

from __future__ import annotations

import argparse
import fnmatch
import pathlib
import re
import subprocess
import sys
import zipfile
from typing import Iterable, List, Sequence, Tuple

from core.paths import REPO_ROOT

ALLOWED_ROOT_FILES = frozenset({
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "FIX_REPORT.md",
    "METHODOLOGY.md",
    "README.md",
    "SECURITY.md",
    "config.py",
    "main.py",
    "pyproject.toml",
    "requirements.txt",
    "scheduler.py",
    "schemas.py",
})

ALLOWED_DIR_PREFIXES = (
    ".github/workflows/",
    "agents/",
    "core/",
    "data/",
    "data_sources/",
    "delivery/",
    "memory/",
    "orchestrator/",
    "prompts/",
    "runs/",
    "scripts/",
    "tests/",
    "utils/",
    "dashboard/data/",
    "dashboard/public/",
    "dashboard/scripts/",
    "dashboard/src/",
    "dashboard/tests/",
)

ALLOWED_DASHBOARD_FILES = frozenset({
    "dashboard/README.md",
    "dashboard/eslint.config.mjs",
    "dashboard/jsconfig.json",
    "dashboard/next.config.mjs",
    "dashboard/package-lock.json",
    "dashboard/package.json",
    "dashboard/postcss.config.mjs",
})

# Explicit extra directories scanned for new project files not yet committed
EXPLICIT_EXTRA_DIRS = (
    "core",
    "data",
    "scripts",
    "tests",
    "dashboard/data",
    "dashboard/src",
    "dashboard/tests",
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
})

FORBIDDEN_GLOBS = (
    "*.db",
    "*.sqlite",
    "*.sqlite3",
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
    """Return True only if `rel_path` is explicitly allowlisted AND not forbidden."""
    norm = normalize_rel_path(rel_path)
    forbidden, _ = is_forbidden_path(norm)
    if forbidden:
        return False

    if norm in ALLOWED_ROOT_FILES or norm in ALLOWED_DASHBOARD_FILES:
        return True

    if any(norm.startswith(prefix) for prefix in ALLOWED_DIR_PREFIXES):
        return True

    return False


def collect_allowlisted_files(repo_root: pathlib.Path = REPO_ROOT) -> List[str]:
    """Collect release files via `git ls-files` plus explicit allowed extras."""
    res = subprocess.run(
        ["git", "ls-files"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    candidates = set()
    for line in res.stdout.splitlines():
        norm = normalize_rel_path(line.strip())
        if norm:
            candidates.add(norm)

    for extra_dir in EXPLICIT_EXTRA_DIRS:
        abs_dir = repo_root / extra_dir
        if abs_dir.is_dir():
            for child in abs_dir.rglob("*"):
                if child.is_file():
                    rel = normalize_rel_path(str(child.relative_to(repo_root)))
                    candidates.add(rel)

    selected: List[str] = []
    for rel in sorted(candidates):
        abs_file = repo_root / rel
        if not abs_file.is_file():
            continue
        if is_allowed_release_path(rel):
            selected.append(rel)

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

        if ".env.example" not in names:
            violations.append("Missing .env.example in zip archive")

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
    files = collect_allowlisted_files(repo_root)
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nexus allowlist packager & hygiene check")
    parser.add_argument("--verify-hygiene", action="store_true", help="Run % path and secret scans")
    parser.add_argument("--build-zip", type=str, help="Build allowlisted release zip at path")
    parser.add_argument("--verify-zip", type=str, help="Verify an existing release zip")
    args = parser.parse_args(argv)

    if args.verify_hygiene:
        pct_paths = check_no_percent_paths(REPO_ROOT)
        if pct_paths:
            print(f"ERROR: Paths starting with '%' found: {pct_paths}", file=sys.stderr)
            return 1
        files = collect_allowlisted_files(REPO_ROOT)
        secret_findings = scan_files_for_secrets(files, REPO_ROOT)
        if secret_findings:
            print("ERROR: Secret scan failed:", file=sys.stderr)
            for item in secret_findings:
                print(f"  - {item}", file=sys.stderr)
            return 1
        print(f"OK: Hygiene & secret scan passed across {len(files)} allowlisted files.")

    if args.build_zip:
        out_path = pathlib.Path(args.build_zip)
        count, _ = build_release_zip(out_path, REPO_ROOT)
        print(f"OK: Built verified allowlist zip at {out_path} ({count} files).")

    if args.verify_zip:
        zpath = pathlib.Path(args.verify_zip)
        violations = verify_zip_contents(zpath)
        if violations:
            print("ERROR: Zip verification failed:", file=sys.stderr)
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            return 1
        print(f"OK: Zip archive verified clean: {zpath}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
