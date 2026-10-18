"""
Nexus Quantitative Evaluation & Benchmark Table Generator (scripts/evaluate.py)
Reads directly from canonical artifacts (runs/global/nexus_stats.json and runs/index.json).
Outputs deterministic Markdown tables and rewrites <!-- METRICS:START --> ... <!-- METRICS:END -->
blocks across README.md, CLAUDE.md, CHANGELOG.md, METHODOLOGY.md, and FIX_REPORT.md.
Rule 1: Every number in docs/reports must be produced by script from artifacts.
"""

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.paths import get_memory_dir, get_runs_dir

METRICS_START = "<!-- METRICS:START -->"
METRICS_END = "<!-- METRICS:END -->"

TARGET_DOCS = [
    BASE_DIR / "README.md",
    BASE_DIR / "CLAUDE.md",
    BASE_DIR / "CHANGELOG.md",
    BASE_DIR / "METHODOLOGY.md",
    BASE_DIR / "FIX_REPORT.md",
]


def format_pct(val):
    if val is None:
        return "N/A (Insufficient data)"
    return f"{float(val):.1f}%"


def format_bps(val):
    if val is None:
        return "N/A"
    num = float(val)
    return f"{num:+.1f} bps"


def build_metrics_markdown(stats: dict, raw_index: dict | list | None = None) -> str:
    dir_info = stats.get("direction_info", {})
    ci = stats.get("direction_ci_95", {})
    n = stats.get("sample_size_n", 0)
    is_sufficient = stats.get("is_sample_sufficient", False)
    scoring_version = stats.get("scoring_version", "2.2.0")
    rescored_at = stats.get("history_rescored_at", "2026-10-15")

    total_runs = n
    pending_runs = 0
    if isinstance(raw_index, dict):
        if "total_dates" in raw_index:
            total_runs = int(raw_index.get("total_dates", n))
            pending_runs = len(raw_index.get("pending_dates", []))
        elif isinstance(raw_index.get("runs"), list):
            runs_list = raw_index["runs"]
            total_runs = len(runs_list)
            pending_runs = sum(1 for e in runs_list if isinstance(e, dict) and not e.get("has_review"))
    elif isinstance(raw_index, list):
        total_runs = len(raw_index)
        pending_runs = sum(1 for e in raw_index if isinstance(e, dict) and not e.get("has_review"))

    lines = []
    lines.append(
        f"**Canonical Artifact Summary** (Scoring Engine `v{scoring_version}`, Rescored `{rescored_at}`, "
        f"Verified Runs: **{total_runs}**, Scored Reviews: **n={n}**, Unreviewed Pending: **{pending_runs}**)"
    )
    lines.append("")
    lines.append("### TABLE 1: HEADLINE DIRECTION TRACK RECORD & UNCERTAINTY")
    lines.append("| Metric | Realized Value | Statistical Note / Wilson 95% CI |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(
        f"| Scored Sessions (n) | **{n}** | "
        f"{'Sufficient (n >= 30)' if is_sufficient else '⚠️ Sample too small to conclude skill (n < 30)'} |"
    )
    lines.append(
        f"| Direction Hit Rate | **{format_pct(stats.get('direction_accuracy_pct'))}** "
        f"({stats.get('direction_correct_count')}/{stats.get('direction_scorable_sessions')}) | "
        f"95% Wilson CI: [{ci.get('lower_pct', '—')}%, {ci.get('upper_pct', '—')}%] |"
    )
    lines.append(
        f"| Rolling Accuracy | **{format_pct(stats.get('rolling_avg_accuracy'))}** | "
        f"Trailing dynamic 50/30/20 attribution average |"
    )
    lines.append("")

    baselines = stats.get("baselines", {})
    always_bearish = baselines.get("always_bearish_pct", 0)
    always_bearish_h = baselines.get("always_bearish_count", baselines.get("always_bearish_hits", 0))
    always_bearish_n = baselines.get("always_bearish_total", baselines.get("always_bearish_n", n))
    persistence = baselines.get("persistence_pct", 0)
    persistence_h = baselines.get("persistence_correct_count", baselines.get("persistence_hits", 0))
    persistence_n = baselines.get("persistence_scorable_sessions", baselines.get("persistence_n", max(0, n - 1)))
    always_bullish = baselines.get("always_bullish_pct", 0)
    always_bullish_h = baselines.get("always_bullish_count", baselines.get("always_bullish_hits", 0))
    always_bullish_n = baselines.get("always_bullish_total", baselines.get("always_bullish_n", n))
    model_dir = stats.get("direction_accuracy_pct", 0) or 0

    lines.append("### TABLE 2: EMPIRICAL NAIVE BASELINES COMPARISON")
    lines.append("| Strategy / Baseline | Accuracy (Hits/n) | Delta vs Nexus Model | Buy-Side Assessment |")
    lines.append("| :--- | :--- | :--- | :--- |")
    lines.append(
        f"| **Nexus Multi-Agent Model** | **{format_pct(model_dir)}** "
        f"({stats.get('direction_correct_count')}/{n}) | 0.0% | Active directional thesis |"
    )
    lines.append(
        f"| Always-Bearish (Down Only) | **{format_pct(always_bearish)}** "
        f"({always_bearish_h}/{always_bearish_n}) | {always_bearish - model_dir:+.1f}% | "
        f"Outperforms model due to prevailing market downtrend |"
    )
    lines.append(
        f"| Persistence (Repeat T-1) | **{format_pct(persistence)}** "
        f"({persistence_h}/{persistence_n}) | {persistence - model_dir:+.1f}% | "
        f"Exploits directional momentum across consecutive sessions |"
    )
    lines.append(
        f"| Always-Bullish (Up Only) | **{format_pct(always_bullish)}** "
        f"({always_bullish_h}/{always_bullish_n}) | {always_bullish - model_dir:+.1f}% | "
        f"Model outperforms permanent long bias |"
    )
    lines.append("")

    flow_info = stats.get("flow_info", {})
    sector_info = stats.get("sector_info", {})

    lines.append("### TABLE 3: PIPELINE SUB-COMPONENT SCORING BREAKDOWN")
    lines.append("| Component | Nominal Weight | Scorable (n) | Realized Hit Rate | Institutional Interpretation |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    lines.append(
        f"| IHSG Direction | 50% | n = {dir_info.get('n', 0)} | {format_pct(dir_info.get('pct'))} "
        f"({stats.get('direction_correct_count')}/{dir_info.get('n', 0)}) | "
        f"Primary directional bias (Bullish/Bearish/Neutral ±0.20% band) |"
    )
    lines.append(
        f"| Sector Breakdown | 30% | n = {sector_info.get('n', 0)} | {format_pct(sector_info.get('pct'))} "
        f"({stats.get('sector_correct_count')}/{sector_info.get('n', 0)}) | "
        f"Evaluated across 11 IDX-IC closing returns; midday snapshots rejected |"
    )
    lines.append(
        f"| Foreign Flow | 20% | n = {flow_info.get('n', 0)} | {flow_info.get('label', 'Insufficient data')} | "
        f"Suppressed from scoring when scorable n < 5; treated as institutional context |"
    )
    lines.append("")

    calib = stats.get("calibration", {})
    calib_note = calib.get("calibration_note", "illustrative shrinkage estimate")
    prior_n0 = calib.get("prior_strength_n0", 30)
    prior_cap = calib.get("prior_cap_pct", 55.0)

    lines.append("### TABLE 4: PROBABILISTIC CONFIDENCE CALIBRATION & BRIER SCORE")
    lines.append("| Calibration Metric | Measured Value | Plain Language Buy-Side Interpretation |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(
        f"| Model Stated Confidence (Uncalibrated) | **{format_pct(calib.get('average_stated_confidence_pct'))}** | "
        f"Raw uncalibrated LLM confidence output across n={n} scored sessions |"
    )
    lines.append(
        f"| Realized Direction Hit Rate | **{format_pct(stats.get('direction_accuracy_pct'))}** | "
        f"Actual empirical accuracy ({stats.get('direction_correct_count')}/{n} scored sessions) |"
    )
    lines.append(
        f"| Calibrated Confidence (Shrinkage) | **{format_pct(calib.get('calibrated_confidence_pct'))}** "
        f"(n={n}, {calib_note}) | "
        f"Bayesian shrinkage with prior strength N0={prior_n0} and prior cap {prior_cap:.1f}% |"
    )
    lines.append(
        f"| Brier Score | **{calib.get('brier_score', 0):.4f}** | "
        f"Probabilistic error (0.00 = perfect, 0.25 = random coin toss, >0.25 = overconfident) |"
    )
    lines.append("")

    payoff = stats.get("payoff", {})
    long_trades = payoff.get("long_only_trades", 0)
    short_trades = payoff.get("short_only_trades", 0)

    lines.append("### TABLE 5: ECONOMIC PAYOFF STRUCTURE (BASIS POINTS)")
    lines.append("| Strategy Portfolio | Realized Payoff (bps) | Trade Count | Tradability / Practical Feasibility |")
    lines.append("| :--- | :--- | :--- | :--- |")
    lines.append(
        f"| **Long-Only (Headline Payoff)** | **{format_bps(payoff.get('long_only_total_bps'))}** | "
        f"{long_trades} calls | Realizable long exposure on retail Indonesian brokerage accounts |"
    )
    lines.append(
        f"| Short-Side Payoff | **{format_bps(payoff.get('short_only_total_bps'))}** | "
        f"{short_trades} calls | **Theoretical only; not retail-tradable on IDX cash index** |"
    )
    lines.append(
        f"| Combined Theoretical Long/Short | **{format_bps(payoff.get('long_short_total_bps'))}** | "
        f"{long_trades + short_trades} calls | Pure hypothetical synthetic index return before borrow fees and slippage |"
    )
    lines.append("")

    rej = stats.get("rejected_lessons", [])
    valid_lessons = stats.get("all_lessons", [])
    lines.append("### TABLE 6: SELF-LEARNING LOOP HYGIENE & QUARANTINE AUDIT")
    lines.append(
        f"- Valid Injected Lessons: **{len(valid_lessons)}** "
        f"(sanitized, validated against stored actuals, genuine data_quality-passing sessions only)"
    )
    lines.append(
        f"- Quarantined / Rejected Lessons: **{len(rej)}** "
        f"(prevented from corrupting future pre-market intelligence)"
    )
    lines.append("")
    lines.append("| Session Date | Quarantine Reason | Sample Quarantined Content |")
    lines.append("| :--- | :--- | :--- |")
    for r in rej:
        sample = r.get("lesson", "")[:65] + "..." if len(r.get("lesson", "")) > 65 else r.get("lesson", "")
        lines.append(f"| {r.get('date')} | `{r.get('reason')}` | {sample} |")

    return "\n".join(lines)


def sync_doc_metric_blocks(metrics_md: str, check_only: bool = False) -> list[str]:
    """
    Rewrites or verifies <!-- METRICS:START --> ... <!-- METRICS:END --> blocks
    in all target documentation files. Returns list of files with diffs.
    """
    pattern = re.compile(
        re.escape(METRICS_START) + r".*?" + re.escape(METRICS_END),
        re.DOTALL,
    )
    replacement = f"{METRICS_START}\n{metrics_md}\n{METRICS_END}"
    mismatched = []

    for doc_path in TARGET_DOCS:
        if not doc_path.exists():
            continue
        content = doc_path.read_text(encoding="utf-8")
        if METRICS_START not in content or METRICS_END not in content:
            mismatched.append(f"{doc_path.name} (missing markers)")
            continue
        new_content = pattern.sub(lambda _: replacement, content)
        if new_content != content:
            mismatched.append(doc_path.name)
            if not check_only:
                doc_path.write_text(new_content, encoding="utf-8")

    return mismatched


def generate_evaluation_report(check_only: bool = False, write_docs: bool = True) -> str:
    stats_file = get_memory_dir() / "nexus_stats.json"
    if not stats_file.exists():
        print(f"Error: {stats_file} not found.", file=sys.stderr)
        sys.exit(1)

    with open(stats_file, "r", encoding="utf-8") as f:
        stats = json.load(f)

    index_file = get_runs_dir() / "index.json"
    raw_index = None
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                raw_index = json.load(f)
        except Exception:
            raw_index = None

    metrics_md = build_metrics_markdown(stats, raw_index)

    if write_docs or check_only:
        mismatched = sync_doc_metric_blocks(metrics_md, check_only=check_only)
        if check_only and mismatched:
            print(f"Metrics block mismatch in: {', '.join(mismatched)}", file=sys.stderr)
            sys.exit(1)

    print(metrics_md)
    return metrics_md


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and sync canonical metric blocks.")
    parser.add_argument("--check", action="store_true", help="Verify docs match generated metrics without writing.")
    parser.add_argument("--no-write", action="store_true", help="Print metrics to stdout without rewriting docs.")
    args = parser.parse_args()
    generate_evaluation_report(check_only=args.check, write_docs=not args.no_write)
