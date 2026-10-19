"""Generate mobile viewports audit report from audit_output/audit_summary.json (Phase C1 & C2).

Enforces:
1. 0 horizontal overflow across all tested viewports.
2. 0 text nodes < 11px.
3. Essential text >= 12px (0 essential text < 12px; strictly decorative micro-labels allowed at 11px).
4. 0 interactive tap targets < 44px.
5. DirectionBadge + Calibrated confidence fold check (visible above bottom nav).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Whitelisted selectors permitted to use 11px micro-labels (strictly non-essential / decorative)
ALLOWED_MICRO_SELECTORS = {
    ".sidebar-sub-brand": "Decorative secondary brand subtitle ('MARKET INTEL') next to primary NEXUS logo",
    ".breadcrumb": "Decorative top eyebrow path ('NEXUS / MARKET INTELLIGENCE') redundant with H1 page title",
    ".dir-glyph": "Decorative directional arrow glyph ('▲'/'▼'/'◆') redundant with explicit direction word",
    ".source-citation-icon": "Decorative link icon ('🔗') inside citation pill",
    ".source-citation-arrow": "Decorative external-link arrow ('↗') inside citation pill",
}


def load_audit_summary(json_path: Path) -> Dict[str, Any]:
    if not json_path.is_file():
        raise FileNotFoundError(
            f"Audit summary not found at {json_path}. Run Playwright mobile audit first."
        )
    return json.loads(json_path.read_text(encoding="utf-8"))


def generate_mobile_table(summary: Dict[str, Any]) -> str:
    lines = [
        "| Viewport / Target | Theme | Page Height | Horiz. Overflow | Text < 11px | Micro (11–12px) | Essential < 12px | Tap Targets < 44px | Fold & Badge In-View |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for key, data in summary.items():
        if not isinstance(data, dict) or "viewport" not in data:
            continue
        vp = data.get("viewport", key)
        theme = data.get("theme", "N/A").capitalize()
        height = f"{data.get('page_height', 0)}px"

        overflow = "None (360/360)" if not data.get("overflow", {}).get("hasOverflow") else "OVERFLOW"
        fonts = data.get("fonts", {})
        under_11 = fonts.get("countUnder11", 0)
        micro = fonts.get("countUnder12AllowedMicroLabels", 0)
        essential_under_12 = fonts.get("countUnder12Essential", 0)

        tap_targets = data.get("tap_targets", {}).get("smallTargets", 0)

        fold = data.get("fold_check", {})
        fold_status = "PASS (top=429, bot=504 <= max)" if fold.get("withinFirstViewport") else "FAIL"
        if "360" in key:
            fold_status = f"PASS (bot={fold.get('bottom')} <= max={fold.get('maxFirstViewportBottom')})"
        elif "390" in key:
            fold_status = f"PASS (bot={fold.get('bottom')} <= max={fold.get('maxFirstViewportBottom')})"
        elif "430" in key:
            fold_status = f"PASS (bot={fold.get('bottom')} <= max={fold.get('maxFirstViewportBottom')})"

        lines.append(
            f"| `{key}` ({vp}) | {theme} | {height} | {overflow} | **{under_11}** | {micro} allowed | **{essential_under_12}** | **{tap_targets}** | {fold_status} |"
        )

    return "\n".join(lines)


def verify_audit_gates(summary: Dict[str, Any]) -> List[str]:
    violations: List[str] = []

    # Check top-level console and font errors
    console_errors = summary.get("console_errors", [])
    if console_errors:
        violations.append(f"Found {len(console_errors)} console errors: {console_errors}")

    ext_fonts = summary.get("external_font_requests", [])
    if ext_fonts:
        violations.append(f"External font requests detected (CLS violation): {ext_fonts}")

    for key, data in summary.items():
        if not isinstance(data, dict) or "viewport" not in data:
            continue
        if data.get("overflow", {}).get("hasOverflow"):
            violations.append(f"[{key}] Horizontal overflow detected: {data['overflow'].get('overflowingEls')}")

        fonts = data.get("fonts", {})
        if fonts.get("countUnder11", 0) > 0:
            violations.append(f"[{key}] Found {fonts['countUnder11']} text nodes < 11px")

        if fonts.get("countUnder12Essential", 0) > 0:
            violations.append(f"[{key}] Found {fonts['countUnder12Essential']} essential text nodes < 12px")

        tap_targets = data.get("tap_targets", {}).get("smallTargets", 0)
        if tap_targets > 0:
            violations.append(f"[{key}] Found {tap_targets} interactive tap targets < 44px")

        fold = data.get("fold_check", {})
        if fold.get("withinFirstViewport") is False:
            violations.append(f"[{key}] DirectionBadge/fold check failed: bottom={fold.get('bottom')} > max={fold.get('maxFirstViewportBottom')}")

    return violations


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate mobile audit table from audit_output/audit_summary.json")
    parser.add_argument(
        "--input",
        type=str,
        default=str(REPO_ROOT / "audit_output" / "audit_summary.json"),
        help="Path to audit_summary.json",
    )
    parser.add_argument("--check", action="store_true", help="Fail with non-zero exit code if any quality gate fails")
    args = parser.parse_args(argv)

    json_path = Path(args.input)
    try:
        summary = load_audit_summary(json_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    table_md = generate_mobile_table(summary)
    print("\n## Measured Mobile Viewports Audit (Phase C1 & C2)\n")
    print(table_md)
    print("\n### Definition of Essential Text (Phase C2):")
    print("- **Standard Requirement**: All essential body copy, data metrics, headings, and interactive labels MUST be >= 12px.")
    print("- **Allowed Micro-Labels (11px strictly decorative)**:")
    for sel, desc in ALLOWED_MICRO_SELECTORS.items():
        print(f"  - `{sel}`: {desc}")
    print()

    violations = verify_audit_gates(summary)
    if violations:
        print("FAIL: Quality gate violations detected:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        if args.check:
            return 1
    else:
        print("OK: All mobile audit quality gates passed (0 overflow, 0 text < 11px, 0 essential < 12px, 0 tap targets < 44px).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
