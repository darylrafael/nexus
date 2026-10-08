"""
scripts/rescore_history.py

Re-derives IHSG actuals from authoritative consecutive closes and rescores
all historical evening runs.
- Corrects 2026-09-23 (+1.56% Bullish), 2026-09-29 (-0.43% Bearish), and 2026-10-05 (+1.36% Bullish).
- Resolves schema migration (tags schema_version: 1 if legacy flat schema).
- Ensures 2026-09-22 and 2026-09-23 are included in processed_dates.
- Rebuilds runs/global/nexus_stats.json idempotently via compute_canonical_stats.
- Defaults to --dry-run; applies changes with --apply (creating .bak backups).
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.direction import classify_direction
from utils.stats import compute_canonical_stats, compute_session_accuracy

# Authoritative candle corrections discovered during audit:
# (date_str): {close, prev, change_pts, change_pct, signal}
AUTHORITATIVE_CORRECTIONS = {
    "2026-09-23": {
        "ihsg_close": 6374.91,
        "ihsg_prev": 6277.04,
        "ihsg_change_pts": 97.87,
        "ihsg_change_pct": 1.56,
        "ihsg_signal": "Bullish",
    },
    "2026-09-29": {
        "ihsg_close": 6121.70,
        "ihsg_prev": 6147.86,
        "ihsg_change_pts": -26.16,
        "ihsg_change_pct": -0.43,
        "ihsg_signal": "Bearish",
    },
    "2026-10-05": {
        "ihsg_close": 6118.86,
        "ihsg_prev": 6036.89,
        "ihsg_change_pts": 81.97,
        "ihsg_change_pct": 1.36,
        "ihsg_signal": "Bullish",
    },
}


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None


def save_json(path: Path, data: Dict[str, Any], backup: bool = True):
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copyfile(path, backup_path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rescore_run(run_dir: Path, apply: bool) -> Optional[Dict[str, Any]]:
    date_str = run_dir.name
    actuals_path = run_dir / "evening_actuals.json"
    review_path = run_dir / "evening_review.json"
    pred_path = run_dir / "morning_prediction.json"

    actuals = load_json(actuals_path)
    review = load_json(review_path)
    pred = load_json(pred_path)

    if not actuals or not review:
        return None

    diffs: List[str] = []

    # 1. Check Schema Version in actuals
    if "schema_version" not in actuals:
        diffs.append("schema_version: missing -> 1")
        actuals["schema_version"] = 1

    # 2. Check IHSG Corrections
    if date_str in AUTHORITATIVE_CORRECTIONS:
        corr = AUTHORITATIVE_CORRECTIONS[date_str]
        for k, v in corr.items():
            old_val = actuals.get(k)
            if old_val != v:
                diffs.append(f"actuals.{k}: {old_val} -> {v}")
                actuals[k] = v

        # If actuals has namespaced ihsg object, update it too
        if isinstance(actuals.get("ihsg"), dict):
            actuals["ihsg"]["close"] = corr["ihsg_close"]
            actuals["ihsg"]["prev"] = corr["ihsg_prev"]
            actuals["ihsg"]["change_pts"] = corr["ihsg_change_pts"]
            actuals["ihsg"]["change_pct"] = corr["ihsg_change_pct"]
            actuals["ihsg"]["signal"] = corr["ihsg_signal"]

    # 3. Re-evaluate review fields canonically
    ihsg_actual_pct = actuals.get("ihsg_change_pct")
    if ihsg_actual_pct is not None:
        canonical_dir = classify_direction(ihsg_actual_pct)
    else:
        canonical_dir = actuals.get("ihsg_signal", "Unknown")

    if review.get("ihsg_actual") != canonical_dir:
        diffs.append(f"review.ihsg_actual: {review.get('ihsg_actual')} -> {canonical_dir}")
        review["ihsg_actual"] = canonical_dir

    if review.get("ihsg_actual_pct") != ihsg_actual_pct:
        diffs.append(f"review.ihsg_actual_pct: {review.get('ihsg_actual_pct')} -> {ihsg_actual_pct}")
        review["ihsg_actual_pct"] = ihsg_actual_pct

    # Determine ihsg_correct
    pred_dir = review.get("ihsg_predicted") or (pred.get("ihsg_signal") if pred else "")
    if (pred_dir or "").strip().lower() == "mixed":
        pred_dir = "Neutral"

    if canonical_dir in ["Unknown", "Unscorable", "Unavailable", ""] or ihsg_actual_pct is None:
        new_ihsg_corr = None
    else:
        new_ihsg_corr = ((pred_dir or "").strip().lower() == canonical_dir.lower())

    if review.get("ihsg_correct") != new_ihsg_corr:
        diffs.append(f"review.ihsg_correct: {review.get('ihsg_correct')} -> {new_ihsg_corr}")
        review["ihsg_correct"] = new_ihsg_corr

    # Foreign flow check
    ff_act = actuals.get("foreign_flow_signal", "Unknown")
    ff_pred = review.get("foreign_flow_predicted") or (pred.get("foreign_flow_signal") if pred else "")
    if ff_act in ["Unknown", "N/A", ""] or not ff_pred or ff_pred in ["Unknown", "N/A", ""]:
        new_ff_corr = None
    else:
        new_ff_corr = (ff_act.strip().lower() == ff_pred.strip().lower())

    if review.get("foreign_flow_correct") != new_ff_corr:
        diffs.append(f"review.foreign_flow_correct: {review.get('foreign_flow_correct')} -> {new_ff_corr}")
        review["foreign_flow_correct"] = new_ff_corr

    # Recompute accuracy score
    new_acc = compute_session_accuracy(
        ihsg_correct=review.get("ihsg_correct"),
        foreign_flow_correct=review.get("foreign_flow_correct"),
        sector_accuracy=review.get("sector_accuracy"),
    )

    if review.get("accuracy_score") != new_acc:
        diffs.append(f"review.accuracy_score: {review.get('accuracy_score')} -> {new_acc}")
        review["accuracy_score"] = new_acc
        review["error_rate_pct"] = (100 - new_acc) if new_acc is not None else None

    # Print report for this run
    if diffs:
        print(f"\n[Run {date_str}] Changes:")
        for d in diffs:
            print(f"  * {d}")
    else:
        print(f"[Run {date_str}] OK (No changes)")

    if apply:
        save_json(actuals_path, actuals, backup=True)
        save_json(review_path, review, backup=True)

    return review


def main():
    parser = argparse.ArgumentParser(description="Rescore historical Nexus runs.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply modifications and create backups (.bak). Defaults to dry-run.",
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"=== Nexus History Rescorer ({mode}) ===")

    runs_root = PROJECT_ROOT / "runs"
    if not runs_root.exists():
        print(f"Error: {runs_root} does not exist.")
        sys.exit(1)

    all_reviews: List[Dict[str, Any]] = []

    run_dirs = sorted([
        d for d in runs_root.iterdir()
        if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name)
    ])

    for r_dir in run_dirs:
        res = rescore_run(r_dir, apply=args.apply)
        if res:
            all_reviews.append(res)

    print(f"\nProcessed {len(all_reviews)} sessions across historical runs.")

    # Canonical stats recalculation
    canonical_stats = compute_canonical_stats(all_reviews)

    # Backwards-compatibility aliases
    canonical_stats["ihsg_accuracy_pct"] = canonical_stats["direction_accuracy_pct"] or 0.0
    canonical_stats["ihsg_correct_count"] = canonical_stats["direction_correct_count"]
    canonical_stats["ff_accuracy_pct"] = canonical_stats["flow_accuracy_pct"] or 0.0
    canonical_stats["ff_correct_count"] = canonical_stats["flow_correct_count"]
    canonical_stats["total_accuracy_sum"] = sum(
        float(r.get("accuracy_score", 0)) for r in all_reviews if r.get("accuracy_score") is not None
    )

    print("\nCanonical Stats Summary:")
    print(f"  - Total Sessions: {canonical_stats['total_sessions']}")
    print(f"  - Processed Dates ({len(canonical_stats['processed_dates'])}): {canonical_stats['processed_dates']}")
    print(f"  - IHSG Direction Accuracy: {canonical_stats['direction_accuracy_pct']}% ({canonical_stats['direction_correct_count']}/{canonical_stats['direction_scorable_sessions']})")
    print(f"  - Foreign Flow Accuracy: {canonical_stats['flow_accuracy_pct']}% ({canonical_stats['flow_correct_count']}/{canonical_stats['flow_scorable_sessions']})")
    print(f"  - Sector Accuracy: {canonical_stats['sector_accuracy_pct']}% ({canonical_stats['sector_correct_count']}/{canonical_stats['sector_verifiable_count']})")
    print(f"  - Rolling Avg Session Accuracy: {canonical_stats['rolling_avg_accuracy']}%")

    stats_path = runs_root / "global" / "nexus_stats.json"
    if args.apply:
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        save_json(stats_path, canonical_stats, backup=True)
        print(f"\nSaved updated canonical stats to: {stats_path}")
    else:
        print(f"\n[DRY RUN] Would write updated canonical stats to: {stats_path}")
        print("Run with '--apply' to persist all changes.")


if __name__ == "__main__":
    main()
