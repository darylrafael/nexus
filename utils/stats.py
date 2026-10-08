from typing import Any, Optional


def compute_session_accuracy(
    ihsg_correct: Optional[bool],
    foreign_flow_correct: Optional[bool],
    sector_accuracy: Optional[dict[str, Any]] = None,
) -> Optional[int]:
    """Compute overall session accuracy percentage.

    Returns None if no items are scorable (avoids reporting 0% when un-
    scorable).
    """
    correct = 0
    total = 0

    if isinstance(ihsg_correct, bool):
        correct += int(ihsg_correct)
        total += 1

    if isinstance(foreign_flow_correct, bool):
        correct += int(foreign_flow_correct)
        total += 1

    if isinstance(sector_accuracy, dict):
        for val in sector_accuracy.values():
            if isinstance(val, bool):
                correct += int(val)
                total += 1

    if total == 0:
        return None

    return int(round(correct / total * 100))


def compute_canonical_stats(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Canonical stats computation across all sessions.

    Separates direction accuracy, foreign flow accuracy, and sector
    accuracy.
    """
    direction_scorable = 0
    direction_correct = 0

    flow_scorable = 0
    flow_correct = 0

    sector_total = 0
    sector_correct = 0

    session_accuracies = []
    processed_dates = []
    all_lessons = []
    missed_factors = {}

    for r in reviews:
        date = r.get("date")
        if not date:
            continue
        processed_dates.append(date)

        # Direction
        ihsg_corr = r.get("ihsg_correct")
        if isinstance(ihsg_corr, bool):
            direction_scorable += 1
            if ihsg_corr:
                direction_correct += 1

        # Flow
        ff_corr = r.get("foreign_flow_correct")
        if isinstance(ff_corr, bool):
            flow_scorable += 1
            if ff_corr:
                flow_correct += 1

        # Sector
        sec_acc = r.get("sector_accuracy")
        if isinstance(sec_acc, dict):
            for v in sec_acc.values():
                if isinstance(v, bool):
                    sector_total += 1
                    if v:
                        sector_correct += 1

        # Overall session accuracy
        acc_score = r.get("accuracy_score")
        if acc_score is not None and isinstance(acc_score, (int, float)):
            session_accuracies.append(float(acc_score))

        # Lessons
        for l in r.get("lessons", []):
            if l and l not in all_lessons:
                all_lessons.append(l)

        # RCA missed factors
        for f in (r.get("rca_unanticipated", []) + r.get("rca_underestimated", [])):
            if f:
                missed_factors[f] = missed_factors.get(f, 0) + 1

    dir_pct = round((direction_correct / direction_scorable) * 100, 1) if direction_scorable > 0 else None
    flow_pct = round((flow_correct / flow_scorable) * 100, 1) if flow_scorable > 0 else None
    sec_pct = round((sector_correct / sector_total) * 100, 1) if sector_total > 0 else None

    rolling_avg = round(sum(session_accuracies) / len(session_accuracies), 1) if session_accuracies else None

    return {
        "total_sessions": len(processed_dates),
        "processed_dates": sorted(processed_dates),
        "direction_accuracy_pct": dir_pct,
        "direction_correct_count": direction_correct,
        "direction_scorable_sessions": direction_scorable,
        "flow_accuracy_pct": flow_pct,
        "flow_correct_count": flow_correct,
        "flow_scorable_sessions": flow_scorable,
        "sector_accuracy_pct": sec_pct,
        "sector_correct_count": sector_correct,
        "sector_verifiable_count": sector_total,
        "rolling_avg_accuracy": rolling_avg,
        "all_lessons": all_lessons,
        "missed_factor_counts": missed_factors,
        "last_updated": max(processed_dates) if processed_dates else "",
    }
