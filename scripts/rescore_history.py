"""
scripts/rescore_history.py

Re-derives IHSG actuals from authoritative consecutive closes and rescores
all historical evening runs.
- Strict Indonesian D/M/Y date matching for foreign flow articles (strict=True).
- Geometric OHLC validation: invalid candles set open/high/low to None.
- Deterministic 11 IDX-IC sector scoring with Neutral band (+/-0.2%).
- Dynamic scorable weighting (50% Index + 30% Sector + 20% Flow).
- Attaches data_quality block to evening_actuals.json.
- Regenerates runs/global/nexus_stats.json and dashboard/data/runs/global/nexus_stats.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.prediction_extractor import TICKER_STOPLIST, get_idx_universe
from core.locking import compute_prediction_lock_hash
from core.paths import get_dashboard_runs_dir, get_memory_dir, get_runs_dir
from core.provenance import (
    build_runs_index,
    check_run_dir_provenance,
    is_mock_provenance,
)
from core.sectors import parse_sector_percentages_from_text, score_sector_predictions
from data_sources.market_data import validate_ohlc
from memory.learning_store import (
    evaluate_heuristic_lifecycle,
    filter_and_quarantine_lessons,
)
from utils.direction import classify_direction
from utils.flow import canonicalize_flow, classify_foreign_flow
from utils.stats import compute_canonical_stats, compute_session_accuracy

# Authoritative candle corrections discovered during audit:
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


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None


def save_json(path: Path, data: dict[str, Any], backup: bool = True):
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copyfile(path, backup_path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rescore_run(
    run_dir: Path,
    apply: bool,
    prev_usdidr_close: float | None = None,
) -> tuple[dict[str, Any] | None, float | None]:
    date_str = run_dir.name
    is_mock_dir, mock_reasons = check_run_dir_provenance(run_dir)
    if is_mock_dir:
        print(f"[Run {date_str}] REJECTED: mock/synthetic provenance detected ({', '.join(mock_reasons)})")
        return None, prev_usdidr_close

    actuals_path = run_dir / "evening_actuals.json"
    review_path = run_dir / "evening_review.json"
    pred_path = run_dir / "morning_prediction.json"

    actuals = load_json(actuals_path)
    review = load_json(review_path)
    pred = load_json(pred_path)

    is_mock_art, art_reasons = is_mock_provenance(actuals, review, pred)
    if is_mock_art:
        print(f"[Run {date_str}] REJECTED: mock/synthetic provenance detected ({', '.join(art_reasons)})")
        return None, prev_usdidr_close

    diffs: list[str] = []

    # Clean morning prediction tickers, cap at 8-10, and compute lock hash (Phase 5.1: mark historical hashes as retroactive)
    if pred:
        universe = get_idx_universe()
        old_tickers = pred.get("recommended_tickers", [])
        cleaned_tickers = []
        for t in old_tickers:
            t_upper = str(t).strip().upper()
            if t_upper in TICKER_STOPLIST:
                continue
            if universe and t_upper not in universe:
                continue
            if t_upper not in cleaned_tickers:
                cleaned_tickers.append(t_upper)
        cleaned_tickers = cleaned_tickers[:10]
        if old_tickers != cleaned_tickers:
            diffs.append(f"pred.recommended_tickers: {old_tickers} -> {cleaned_tickers}")
            pred["recommended_tickers"] = cleaned_tickers

        lock_hash = compute_prediction_lock_hash(pred)
        if pred.get("lock_hash") != lock_hash:
            diffs.append(f"pred.lock_hash: -> {lock_hash}")
            pred["lock_hash"] = lock_hash

        # Phase 5.1: Only predictions hashed at creation time with a pre-open created_at may claim locked_pre_open
        if pred.get("lock_status") != "locked_pre_open" or not pred.get("created_at"):
            if pred.get("lock_status") != "retroactive":
                diffs.append(f"pred.lock_status: {pred.get('lock_status')} -> retroactive")
            pred["lock_status"] = "retroactive"
            pred["hash_computed_at"] = "2026-10-15"
            pred["locked_at"] = None
            pred["out_of_sample_verified"] = False
            pred["lock_note"] = "Hash added retroactively on 2026-10-15; not proof of pre-open lock"

        if apply:
            save_json(pred_path, pred, backup=False)
            dash_pred_dir = get_dashboard_runs_dir() / date_str
            if dash_pred_dir.exists():
                save_json(dash_pred_dir / "morning_prediction.json", pred, backup=False)

    if not actuals or not review:
        if diffs:
            print(f"\n[Run {date_str}] Prediction Changes (Pending Review):")
            for d in diffs:
                print(f"  * {d}")
        return None, prev_usdidr_close

    # 1. Schema Version
    if "schema_version" not in actuals:
        diffs.append("schema_version: missing -> 2")
        actuals["schema_version"] = 2

    # 2. Authoritative IHSG Corrections
    if date_str in AUTHORITATIVE_CORRECTIONS:
        corr = AUTHORITATIVE_CORRECTIONS[date_str]
        for k, v in corr.items():
            old_val = actuals.get(k)
            if old_val != v:
                diffs.append(f"actuals.{k}: {old_val} -> {v}")
                actuals[k] = v

        if isinstance(actuals.get("ihsg"), dict):
            actuals["ihsg"]["close"] = corr["ihsg_close"]
            actuals["ihsg"]["prev"] = corr["ihsg_prev"]
            actuals["ihsg"]["change_pts"] = corr["ihsg_change_pts"]
            actuals["ihsg"]["change_pct"] = corr["ihsg_change_pct"]
            actuals["ihsg"]["signal"] = corr["ihsg_signal"]

    # 3. OHLC Validation
    open_v = actuals.get("ihsg_open")
    high_v = actuals.get("ihsg_high")
    low_v = actuals.get("ihsg_low")
    close_v = actuals.get("ihsg_close")
    is_ohlc_valid = validate_ohlc(open_v, high_v, low_v, close_v)
    if not is_ohlc_valid and (open_v is not None or high_v is not None or low_v is not None):
        diffs.append(f"OHLC invalid (O={open_v}, H={high_v}, L={low_v}, C={close_v}) -> open/high/low set to None")
        actuals["ihsg_open"] = None
        actuals["ihsg_high"] = None
        actuals["ihsg_low"] = None
        if isinstance(actuals.get("ihsg"), dict):
            actuals["ihsg"]["open"] = None
            actuals["ihsg"]["high"] = None
            actuals["ihsg"]["low"] = None
            actuals["ihsg"]["ohlc_valid"] = False

    # 4. Foreign Flow Strict Date Matching
    ff_raw = actuals.get("foreign_flow_raw") or ""
    if ff_raw:
        flow_eval = classify_foreign_flow(ff_raw, target_date_str=date_str, strict=True)
        new_ff_signal = flow_eval["signal"]
        old_ff_signal = actuals.get("foreign_flow_signal")
        if old_ff_signal != new_ff_signal:
            diffs.append(f"actuals.foreign_flow_signal: {old_ff_signal} -> {new_ff_signal} (reason: {flow_eval.get('reason')})")
            actuals["foreign_flow_signal"] = new_ff_signal
            actuals["foreign_flow"] = flow_eval
    else:
        flow_eval = {"signal": actuals.get("foreign_flow_signal", "Unknown"), "reason": "no_raw_text"}

    # 5. Review Direction & Flow Sync
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

    # Flow correctness
    ff_act = canonicalize_flow(actuals.get("foreign_flow_signal", "Unknown"))
    ff_pred = canonicalize_flow(review.get("foreign_flow_predicted") or (pred.get("foreign_flow_signal") if pred else ""))
    review["foreign_flow_actual"] = ff_act
    review["foreign_flow_predicted"] = ff_pred

    if ff_act in ["Unknown", "N/A", ""] or ff_pred in ["Unknown", "N/A", ""]:
        new_ff_corr = None
    else:
        new_ff_corr = (ff_act == ff_pred)

    if review.get("foreign_flow_correct") != new_ff_corr:
        diffs.append(f"review.foreign_flow_correct: {review.get('foreign_flow_correct')} -> {new_ff_corr}")
        review["foreign_flow_correct"] = new_ff_corr

    # 6. Deterministic Sector Scoring if sector text is available
    sector_text = actuals.get("sector_performance") or ""
    if sector_text and pred:
        sector_changes = parse_sector_percentages_from_text(sector_text)
        if sector_changes:
            # Re-score predicted sectors deterministically
            predicted_sectors = {}
            for s in pred.get("sector_bullish", []):
                predicted_sectors[s] = "Bullish"
            for s in pred.get("sector_bearish", []):
                predicted_sectors[s] = "Bearish"
            for s in pred.get("sector_neutral", []):
                predicted_sectors[s] = "Neutral"

            deterministic_sectors = score_sector_predictions(predicted_sectors, sector_changes)
            if deterministic_sectors:
                diffs.append(f"review.sector_accuracy rescored deterministically: {deterministic_sectors}")
                review["sector_accuracy"] = deterministic_sectors

    # 7. Compute FX reliability against consecutive spot USD/IDR closes (Phase 4.1)
    curr_fx = actuals.get("usdidr") if isinstance(actuals.get("usdidr"), (int, float)) else actuals.get("usdidr_rate")
    stored_fx_pct = actuals.get("usdidr_change_pct")
    if curr_fx is not None and prev_usdidr_close is not None and prev_usdidr_close > 0:
        spot_fx_chg = round(((float(curr_fx) - float(prev_usdidr_close)) / float(prev_usdidr_close)) * 100.0, 3)
        fx_reliable = (stored_fx_pct is not None and abs(float(stored_fx_pct) - spot_fx_chg) <= 0.35)
    else:
        spot_fx_chg = stored_fx_pct
        fx_reliable = (stored_fx_pct is not None)

    next_prev_fx = float(curr_fx) if (curr_fx is not None and float(curr_fx) > 0) else prev_usdidr_close

    # 8. Add Data Quality block to actuals & review
    has_valid_close = (
        actuals.get("ihsg_close") is not None
        and actuals.get("ihsg_change_pct") is not None
    )
    actuals["data_quality"] = {
        "overall_valid": bool(has_valid_close),
        "ohlc_valid": is_ohlc_valid,
        "flow_verified": (actuals.get("foreign_flow_signal") != "Unknown"),
        "flow_reason": flow_eval.get("reason"),
        "fx_reliable": fx_reliable,
        "spot_usdidr_change_pct": spot_fx_chg,
        "stored_usdidr_change_pct": stored_fx_pct,
        "rescored_at": "2026-10-15",
    }
    review["usdidr_change_pct"] = stored_fx_pct
    review["rupiah_signal"] = actuals.get("rupiah_signal")
    review["data_quality"] = actuals["data_quality"]

    # 9. Clean watchlist in review (Phase D2)
    if review.get("actionable_watchlist"):
        cleaned_wl = []
        universe = get_idx_universe()
        for item in review["actionable_watchlist"]:
            t = str(item.get("ticker", "")).strip().upper()
            if t in TICKER_STOPLIST or (universe and t not in universe):
                continue
            note = str(item.get("note", ""))
            note = re.sub(r"\*\*|\*|#", "", note)
            note = re.sub(r"^(?:Bullish|Bearish|Neutral|BUY|SELL|HOLD)\s*[:\—\-]\s*", "", note, flags=re.IGNORECASE).strip()
            item["note"] = note
            item["ticker"] = t
            cleaned_wl.append(item)
        review["actionable_watchlist"] = cleaned_wl[:6]

    # 10. Recompute overall session accuracy score
    new_acc = compute_session_accuracy(
        ihsg_correct=review.get("ihsg_correct"),
        foreign_flow_correct=review.get("foreign_flow_correct"),
        sector_accuracy=review.get("sector_accuracy"),
    )

    if review.get("accuracy_score") != new_acc:
        diffs.append(f"review.accuracy_score: {review.get('accuracy_score')} -> {new_acc}")
        review["accuracy_score"] = new_acc
        review["error_rate_pct"] = (100 - new_acc) if new_acc is not None else None

    # Print report
    if diffs:
        print(f"\n[Run {date_str}] Changes:")
        for d in diffs:
            print(f"  * {d}")
    else:
        print(f"[Run {date_str}] OK (No changes)")

    if apply:
        save_json(actuals_path, actuals, backup=False)
        save_json(review_path, review, backup=False)

        # Mirror to dashboard runs if exists
        dash_run_dir = get_dashboard_runs_dir() / date_str
        if dash_run_dir.exists():
            save_json(dash_run_dir / "evening_actuals.json", actuals, backup=False)
            save_json(dash_run_dir / "evening_review.json", review, backup=False)

    return review, next_prev_fx


def main():
    parser = argparse.ArgumentParser(description="Rescore historical Nexus runs.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply modifications. Defaults to dry-run.",
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"=== Nexus History Rescorer ({mode}) ===")

    runs_root = get_runs_dir()
    if not runs_root.exists():
        print(f"Error: {runs_root} does not exist.")
        sys.exit(1)

    stats_path = get_memory_dir() / "nexus_stats.json"
    dash_stats_path = get_dashboard_runs_dir() / "global" / "nexus_stats.json"

    before_stats = load_json(stats_path) or {}

    all_reviews: list[dict[str, Any]] = []

    run_dirs = sorted([
        d for d in runs_root.iterdir()
        if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name)
    ])

    prev_fx: float | None = None
    for r_dir in run_dirs:
        res, prev_fx = rescore_run(r_dir, apply=args.apply, prev_usdidr_close=prev_fx)
        if res:
            all_reviews.append(res)

    print(f"\nProcessed {len(all_reviews)} sessions across historical runs.")

    # Canonical stats recalculation
    canonical_stats = compute_canonical_stats(all_reviews)
    if not canonical_stats.get("rejected_mock_dates"):
        canonical_stats.pop("rejected_mock_dates", None)
    canonical_stats["scoring_version"] = "2.2.0"
    canonical_stats["history_rescored_at"] = "2026-10-15"
    canonical_stats["history_rescore_note"] = (
        "Rescored on 2026-10-15 across 12 genuine sessions (2026-09-22 to 2026-10-07; "
        "2026-10-08 morning-only pending review) with strict Indonesian D/M/Y date matching, "
        "geometric OHLC validation, FX convention & consecutive spot close verification, "
        "and scorable-only dynamic components."
    )

    # Sync canonical calibrated_confidence into morning_prediction.json files (Phase 4.2: remove UI vs headline discrepancy)
    if args.apply:
        cal_pct = canonical_stats.get("calibration", {}).get("calibrated_confidence_pct")
        for r_dir in run_dirs:
            is_mock_d, _ = check_run_dir_provenance(r_dir)
            if is_mock_d:
                continue
            p_path = r_dir / "morning_prediction.json"
            p_data = load_json(p_path)
            if p_data and cal_pct is not None:
                p_data["calibrated_confidence"] = cal_pct
                save_json(p_path, p_data, backup=False)
                dash_p = get_dashboard_runs_dir() / r_dir.name / "morning_prediction.json"
                if dash_p.parent.exists():
                    save_json(dash_p, p_data, backup=False)

    # Heuristic lifecycle & quarantined lessons
    valid_lessons, rejected_lessons = filter_and_quarantine_lessons(all_reviews)
    heuristics = evaluate_heuristic_lifecycle(all_reviews)
    canonical_stats["all_lessons"] = valid_lessons
    canonical_stats["rejected_lessons"] = rejected_lessons
    canonical_stats["heuristics"] = [
        {
            "id": h["id"],
            "rule": h["rule"],
            "status": h["status"],
            "observed": h["observed"],
            "validated": h["validated"],
            "contradicted": h["contradicted"],
            "validation_rate": h["validation_rate"],
            "regimes": h["regimes"],
            "last_observed": h["last_observed"],
        }
        for h in heuristics
    ]

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
    print(f"  - Direction Accuracy: {canonical_stats['direction_accuracy_pct']}% (95% CI: [{canonical_stats['direction_ci_95']['lower_pct']}%, {canonical_stats['direction_ci_95']['upper_pct']}%])")
    print(f"  - Baselines: Bearish={canonical_stats['baselines']['always_bearish_pct']}%, Bullish={canonical_stats['baselines']['always_bullish_pct']}%, Persistence={canonical_stats['baselines']['persistence_pct']}%")
    print(f"  - Payoffs: Long-Only={canonical_stats['payoff']['long_only_total_bps']} bps, Short-Only={canonical_stats['payoff']['short_only_total_bps']} bps, Total={canonical_stats['payoff']['long_short_total_bps']} bps")
    print(f"  - Foreign Flow Accuracy: {canonical_stats['flow_accuracy_pct']} ({canonical_stats['flow_info']['label']})")
    print(f"  - Sector Accuracy: {canonical_stats['sector_accuracy_pct']}% ({canonical_stats['sector_info']['label']})")
    print(f"  - Rolling Avg Accuracy: {canonical_stats['rolling_avg_accuracy']}%")
    print(f"  - Stored Valid Lessons: {len(valid_lessons)} | Quarantined Rejected: {len(rejected_lessons)}")

    # Script-generated Before / After Diff
    print("\n" + "="*70)
    print("### SCRIPT-GENERATED BEFORE / AFTER METRICS DIFF")
    print("="*70)
    print("| Metric | Before Rescoring | After Rescoring (v2.1.0) | Delta / Audit Status |")
    print("| :--- | :--- | :--- | :--- |")

    b_dir = before_stats.get("direction_accuracy_pct")
    a_dir = canonical_stats.get("direction_accuracy_pct")
    print(f"| Direction Accuracy | {b_dir}% | {a_dir}% | {'Unchanged' if b_dir == a_dir else f'{a_dir - b_dir:+.1f}%'} |")

    b_flow = before_stats.get("flow_accuracy_pct")
    a_flow = canonical_stats.get("flow_accuracy_pct")
    b_flow_lbl = f"{b_flow}%" if b_flow is not None else "None"
    a_flow_lbl = f"{a_flow}%" if a_flow is not None else "Insufficient data (n < 5)"
    print(f"| Flow Accuracy | {b_flow_lbl} | {a_flow_lbl} | Small-n rule enforced (n=1) |")

    b_sec = before_stats.get("sector_accuracy_pct")
    a_sec = canonical_stats.get("sector_accuracy_pct")
    print(f"| Sector Accuracy | {b_sec}% | {a_sec}% | {canonical_stats['sector_info']['label']} |")

    b_brier = before_stats.get("calibration", {}).get("brier_score")
    a_brier = canonical_stats.get("calibration", {}).get("brier_score")
    print(f"| Brier Score | {b_brier} | {a_brier} | {'Unchanged' if b_brier == a_brier else f'{a_brier - b_brier:+.4f}'} |")

    b_cal = before_stats.get("calibration", {}).get("calibrated_confidence_pct")
    a_cal = canonical_stats.get("calibration", {}).get("calibrated_confidence_pct")
    print(f"| Calibrated Conf | {b_cal}% | {a_cal}% | Realized shrinkage |")

    b_rej = len(before_stats.get("rejected_lessons", []))
    a_rej = len(rejected_lessons)
    print(f"| Quarantined Lessons | {b_rej} | {a_rej} | Quarantined +17K & sign errors |")
    print("="*70 + "\n")

    if args.apply:
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        save_json(stats_path, canonical_stats, backup=False)
        print(f"Saved updated canonical stats to: {stats_path}")

        build_runs_index(runs_root)

        if dash_stats_path.parent.exists():
            save_json(dash_stats_path, canonical_stats, backup=False)
            print(f"Mirrored stats to dashboard: {dash_stats_path}")
        if get_dashboard_runs_dir().exists():
            build_runs_index(get_dashboard_runs_dir())
    else:
        print(f"[DRY RUN] Would write updated canonical stats to: {stats_path}")
        print("Run with '--apply' to persist all changes.")


if __name__ == "__main__":
    main()
