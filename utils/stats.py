"""
utils/stats.py

Mathematical and statistical evaluation engine for Nexus IHSG Intelligence.
Audience: Skeptical buy-side analyst / outside viewers.
Rules:
- Explicit scorable weights: 50% Index Direction + 30% Sector + 20% Flow.
- Dynamic normalization across scorable components only. Returns None if 0 scorable.
- Wilson 95% confidence intervals on hit rates.
- Benchmark baselines: Always Bearish, Always Bullish, Majority Class, Persistence.
- Payoff metrics: Separate Long-Only and Long/Short returns in basis points (bps).
- Honest sample size flagging: n < 30 labeled 'Insufficient sample'.
- Calibration: Brier score and stated vs realized confidence.
"""
from __future__ import annotations

import math
from typing import Any

SCORING_WEIGHTS = {
    "direction": 0.50,
    "sector": 0.30,
    "flow": 0.20,
}


def format_accuracy_metric(correct: int, scorable: int) -> dict[str, Any]:
    """Format accuracy metric enforcing small-n rules:
    - If scorable < 5: pct is None, label is 'Insufficient data'
    - If 5 <= scorable < 30: pct is calculated, label is 'n = X, sample too small'
    - If scorable >= 30: pct is calculated, label is 'n = X'
    """
    if scorable < 5:
        return {
            "pct": None,
            "n": scorable,
            "correct": correct,
            "label": "Insufficient data",
            "is_sufficient": False,
        }
    pct = round((correct / scorable) * 100, 1)
    if scorable < 30:
        label = f"n = {scorable}, sample too small"
        is_sufficient = False
    else:
        label = f"n = {scorable}"
        is_sufficient = True
    return {
        "pct": pct,
        "n": scorable,
        "correct": correct,
        "label": label,
        "is_sufficient": is_sufficient,
    }


def compute_session_accuracy(
    ihsg_correct: bool | None,
    foreign_flow_correct: bool | None,
    sector_accuracy: dict[str, Any] | None = None,
) -> int | None:
    """Compute overall session accuracy percentage using the explicit blend:

    50% Index Direction + 30% Sector + 20% Flow (SCORING_WEIGHTS).
    Dynamically normalizes across scorable components only.
    Returns None if no items are scorable (never fabricates 0%).
    """
    weights: list[float] = []
    scores: list[float] = []

    # 1. Index Direction (50%)
    if isinstance(ihsg_correct, bool):
        weights.append(SCORING_WEIGHTS["direction"])
        scores.append(1.0 if ihsg_correct else 0.0)

    # 2. Sector Accuracy (30% aggregate)
    if isinstance(sector_accuracy, dict):
        scorable_sectors = [v for v in sector_accuracy.values() if isinstance(v, bool)]
        if scorable_sectors:
            sec_score = sum(1.0 for v in scorable_sectors if v) / len(scorable_sectors)
            weights.append(SCORING_WEIGHTS["sector"])
            scores.append(sec_score)

    # 3. Foreign Flow (20%)
    if isinstance(foreign_flow_correct, bool):
        weights.append(SCORING_WEIGHTS["flow"])
        scores.append(1.0 if foreign_flow_correct else 0.0)

    if not weights or sum(weights) == 0:
        return None

    # Dynamically normalize weights
    total_weight = sum(weights)
    weighted_score = sum(s * (w / total_weight) for s, w in zip(scores, weights))
    return int(round(weighted_score * 100))


def compute_wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float | None, float | None]:
    """Compute Wilson score interval for binomial proportion.

    Returns (lower_pct, upper_pct) rounded to 1 decimal place, or (None,
    None) if n == 0.
    """
    if n <= 0 or k < 0:
        return None, None
    k = min(k, n)
    # z for 95% confidence is ~1.95996
    z = 1.959964
    p_hat = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1 - p_hat) / n) + (z2 / (4 * n * n)))

    lower = max(0.0, center - margin) * 100
    upper = min(1.0, center + margin) * 100
    return round(lower, 1), round(upper, 1)


def compute_brier_score(predictions: list[float], outcomes: list[int]) -> float | None:
    """Compute Brier score for probabilistic calibration:

    (1/N) * sum((prob - outcome)^2).
    Lower is better (0.0 is perfect, 0.25 is random guessing for 50/50 binary).
    """
    if not predictions or len(predictions) != len(outcomes):
        return None
    total_sq_err = sum((p - o) ** 2 for p, o in zip(predictions, outcomes))
    return round(total_sq_err / len(predictions), 4)


CALIBRATION_PRIOR_STRENGTH = 30
CALIBRATION_PRIOR_CAP_PCT = 55.0


def compute_empirical_calibrated_confidence(
    direction_correct: int,
    direction_scorable: int,
    stated_confidence_pct: float | None,
    prior_strength: int = CALIBRATION_PRIOR_STRENGTH,
    prior_cap_pct: float = CALIBRATION_PRIOR_CAP_PCT,
) -> dict[str, Any]:
    """Compute empirical Bayes linear shrinkage calibrated confidence.

    Formula:
      w = min(n / N0, 1.0)
      p_realized = (k / n) * 100.0  (if n > 0 else 50.0)
      p_prior = min(stated_confidence_pct, prior_cap_pct)
      p_calibrated = round(w * p_realized + (1.0 - w) * p_prior, 1)

    With n < 30, labeled 'illustrative shrinkage estimate'.
    """
    n = max(0, int(direction_scorable))
    k = max(0, min(int(direction_correct), n))
    raw_realized = (k / n) * 100.0 if n > 0 else 50.0
    if stated_confidence_pct is None:
        return {
            "calibrated_confidence_pct": None,
            "sample_size_n": n,
            "prior_pct": prior_cap_pct,
            "prior_strength_n0": prior_strength,
            "empirical_weight": 0.0,
            "realized_hit_rate_pct": round(raw_realized, 1) if n > 0 else None,
            "status_label": "insufficient_data",
            "confidence_label": "Insufficient data for calibration",
        }
    w = min(n / float(prior_strength), 1.0) if prior_strength > 0 else 1.0
    p_prior = min(float(stated_confidence_pct), float(prior_cap_pct))
    cal_pct = round(w * raw_realized + (1.0 - w) * p_prior, 1)
    is_sufficient = n >= prior_strength
    status_label = "calibrated" if is_sufficient else "illustrative shrinkage estimate"
    conf_label = (
        f"Calibrated confidence ({cal_pct}%, n = {n})"
        if is_sufficient
        else f"Illustrative shrinkage estimate ({cal_pct}%, n = {n} < {prior_strength})"
    )
    return {
        "calibrated_confidence_pct": cal_pct,
        "sample_size_n": n,
        "prior_pct": p_prior,
        "prior_strength_n0": prior_strength,
        "empirical_weight": round(w, 4),
        "realized_hit_rate_pct": round(raw_realized, 1) if n > 0 else None,
        "status_label": status_label,
        "confidence_label": conf_label,
    }


from core.paths import get_runs_dir
from core.provenance import check_run_dir_provenance, has_mock_provenance


def compute_canonical_stats(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Canonical statistical audit across all genuine, non-mock sessions."""
    direction_scorable = 0
    direction_correct = 0

    flow_scorable = 0
    flow_correct = 0

    sector_total = 0
    sector_correct = 0

    session_accuracies: list[float] = []
    processed_dates: list[str] = []
    all_lessons: list[str] = []
    missed_factors: dict[str, int] = {}
    rejected_mock_dates: list[str] = []

    # Baselines & calibration tracking
    actual_directions: list[str] = []
    predicted_directions: list[str] = []
    stated_confidences: list[float] = []
    brier_probs: list[float] = []
    brier_outcomes: list[int] = []

    # Payoff metrics (in basis points)
    long_payoffs_bps: list[float] = []
    short_payoffs_bps: list[float] = []

    # Filter out mock/synthetic provenance reviews and sort chronologically
    runs_root = get_runs_dir()
    valid_reviews = []
    for r in reviews:
        if not isinstance(r, dict) or not r.get("date"):
            continue
        r_date = str(r.get("date"))
        if has_mock_provenance(r) or check_run_dir_provenance(runs_root / r_date)[0]:
            rejected_mock_dates.append(r_date)
            continue
        valid_reviews.append(r)

    valid_reviews.sort(key=lambda x: str(x.get("date")))

    for r in valid_reviews:
        date_str = r.get("date")
        processed_dates.append(date_str)

        # ── Direction (Phase 3.2: null correctness is NEVER scorable and excluded from n) ──
        ihsg_corr = r.get("ihsg_correct")
        pred_dir = (r.get("ihsg_predicted") or "").strip().capitalize()
        act_dir = (r.get("ihsg_actual") or "").strip().capitalize()
        act_pct = r.get("ihsg_actual_pct")

        if ihsg_corr is True or ihsg_corr is False:
            direction_scorable += 1
            if ihsg_corr is True:
                direction_correct += 1

            if act_dir in ["Bullish", "Bearish", "Neutral"]:
                actual_directions.append(act_dir)
                predicted_directions.append(pred_dir)

            # Confidence tracking
            conf = r.get("ihsg_confidence")
            if conf is not None:
                try:
                    c_float = float(conf)
                    stated_confidences.append(c_float)
                    # Convert to probability of hit: if stated 80%, prob is 0.80
                    # Outcome is 1 if correct, 0 if incorrect
                    prob = c_float / 100.0 if c_float > 1.0 else c_float
                    brier_probs.append(prob)
                    brier_outcomes.append(1 if ihsg_corr is True else 0)
                except (ValueError, TypeError):
                    pass

            # Payoff tracking (only if actual pct is available)
            if act_pct is not None:
                try:
                    chg_pct = float(act_pct)
                    bps = chg_pct * 100.0  # 1% = 100 bps
                    if pred_dir in ["Bullish", "Overweight", "Up"]:
                        long_payoffs_bps.append(bps)
                    elif pred_dir in ["Bearish", "Underweight", "Down"]:
                        short_payoffs_bps.append(-bps)
                except (ValueError, TypeError):
                    pass

        # ── Foreign Flow ──
        ff_corr = r.get("foreign_flow_correct")
        if isinstance(ff_corr, bool):
            flow_scorable += 1
            if ff_corr:
                flow_correct += 1

        # ── Sectors ──
        sec_acc = r.get("sector_accuracy")
        if isinstance(sec_acc, dict):
            for v in sec_acc.values():
                if isinstance(v, bool):
                    sector_total += 1
                    if v:
                        sector_correct += 1

        # ── Overall session accuracy ──
        acc_score = r.get("accuracy_score")
        if acc_score is not None and isinstance(acc_score, (int, float)):
            session_accuracies.append(float(acc_score))

        # ── Lessons & RCA ──
        for l in r.get("lessons", []):
            if isinstance(l, str) and l and l not in all_lessons:
                all_lessons.append(l)

        for f in (r.get("rca_unanticipated", []) + r.get("rca_underestimated", [])):
            if f and isinstance(f, str):
                missed_factors[f] = missed_factors.get(f, 0) + 1

    # Direction Hit Rate & Wilson 95% CI
    dir_metric = format_accuracy_metric(direction_correct, direction_scorable)
    flow_metric = format_accuracy_metric(flow_correct, flow_scorable)
    sec_metric = format_accuracy_metric(sector_correct, sector_total)

    dir_pct = dir_metric["pct"]
    dir_ci_lower, dir_ci_upper = compute_wilson_ci(direction_correct, direction_scorable)

    flow_pct = flow_metric["pct"]
    sec_pct = sec_metric["pct"]
    rolling_avg = round(sum(session_accuracies) / len(session_accuracies), 1) if session_accuracies else None

    # Baselines
    n_dir = len(actual_directions)
    always_bearish_count = sum(1 for a in actual_directions if a == "Bearish")
    always_bullish_count = sum(1 for a in actual_directions if a == "Bullish")
    always_bearish_pct = round((always_bearish_count / n_dir) * 100, 1) if n_dir > 0 else None
    always_bullish_pct = round((always_bullish_count / n_dir) * 100, 1) if n_dir > 0 else None
    majority_class_pct = max(always_bearish_pct or 0.0, always_bullish_pct or 0.0) if n_dir > 0 else None

    # Persistence baseline (session t actual = session t-1 actual)
    persistence_correct = 0
    persistence_scorable = 0
    for i in range(1, len(actual_directions)):
        persistence_scorable += 1
        if actual_directions[i] == actual_directions[i - 1]:
            persistence_correct += 1
    persistence_pct = round((persistence_correct / persistence_scorable) * 100, 1) if persistence_scorable > 0 else None

    # Calibration & Brier
    avg_stated_conf = round(sum(stated_confidences) / len(stated_confidences), 1) if stated_confidences else None
    brier_score = compute_brier_score(brier_probs, brier_outcomes)
    cal_info = compute_empirical_calibrated_confidence(
        direction_correct=direction_correct,
        direction_scorable=direction_scorable,
        stated_confidence_pct=avg_stated_conf,
    )
    calibrated_conf = cal_info["calibrated_confidence_pct"]

    # Payoff metrics (separate Long-Only and Theoretical Short-Only)
    long_total_bps = round(sum(long_payoffs_bps), 1) if long_payoffs_bps else 0.0
    # Suppress average payoffs and win/loss ratios when sample n < 30
    long_avg_bps = round(sum(long_payoffs_bps) / len(long_payoffs_bps), 1) if (direction_scorable >= 30 and long_payoffs_bps) else None
    short_total_bps = round(sum(short_payoffs_bps), 1) if short_payoffs_bps else 0.0
    short_avg_bps = round(sum(short_payoffs_bps) / len(short_payoffs_bps), 1) if (direction_scorable >= 30 and short_payoffs_bps) else None
    long_short_total_bps = round(long_total_bps + short_total_bps, 1)

    # Rolling 20 sessions
    rolling_20_acc = None
    if len(session_accuracies) >= 20:
        rolling_20_acc = round(sum(session_accuracies[-20:]) / 20, 1)
    elif session_accuracies:
        rolling_20_acc = rolling_avg

    is_sample_sufficient = direction_scorable >= 30

    return {
        "total_sessions": len(processed_dates),
        "processed_dates": processed_dates,
        "rejected_mock_dates": rejected_mock_dates,
        "is_sample_sufficient": is_sample_sufficient,
        "sample_size_n": direction_scorable,
        "sample_warning": None if is_sample_sufficient else f"Insufficient sample size (n = {direction_scorable} < 30) for statistical significance.",
        
        # Direction
        "direction_accuracy_pct": dir_pct,
        "direction_correct_count": direction_correct,
        "direction_scorable_sessions": direction_scorable,
        "direction_info": dir_metric,
        "direction_ci_95": {
            "lower_pct": dir_ci_lower,
            "upper_pct": dir_ci_upper,
            "confidence_level": 0.95,
        },

        # Baselines
        "baselines": {
            "always_bearish_pct": always_bearish_pct,
            "always_bearish_count": always_bearish_count,
            "always_bearish_total": n_dir,
            "always_bullish_pct": always_bullish_pct,
            "always_bullish_count": always_bullish_count,
            "always_bullish_total": n_dir,
            "majority_class_pct": majority_class_pct,
            "persistence_pct": persistence_pct,
            "persistence_correct_count": persistence_correct,
            "persistence_scorable_sessions": persistence_scorable,
        },

        # Calibration
        "calibration": {
            "average_stated_confidence_pct": avg_stated_conf,
            "calibrated_confidence_pct": calibrated_conf,
            "sample_size_n": direction_scorable,
            "prior_pct": cal_info["prior_pct"],
            "prior_strength_n0": cal_info["prior_strength_n0"],
            "empirical_weight": cal_info["empirical_weight"],
            "realized_hit_rate_pct": cal_info["realized_hit_rate_pct"],
            "status_label": cal_info["status_label"],
            "brier_score": brier_score,
            "brier_interpretation": "Brier score measures probabilistic error (0.0 is perfect, 0.25 is random coin flip).",
            "confidence_label": cal_info["confidence_label"],
            "formula": "w * (k / n * 100) + (1 - w) * min(stated_conf, 55.0), where w = min(n / 30, 1.0)",
        },

        # Payoffs
        "payoff": {
            "headline_payoff_bps": long_total_bps,
            "long_only_total_bps": long_total_bps,
            "long_only_avg_bps": long_avg_bps,
            "long_only_trades": len(long_payoffs_bps),
            "short_only_total_bps": short_total_bps,
            "short_only_avg_bps": short_avg_bps,
            "short_only_trades": len(short_payoffs_bps),
            "short_side_note": "theoretical, not retail-tradable",
            "long_short_total_bps": long_short_total_bps,
            "note": "Theoretical index performance before commissions, financing, borrow fees, and execution slippage. Not retail trading returns.",
        },

        # Flow & Sector
        "flow_accuracy_pct": flow_pct,
        "flow_correct_count": flow_correct,
        "flow_scorable_sessions": flow_scorable,
        "flow_info": flow_metric,
        "sector_accuracy_pct": sec_pct,
        "sector_correct_count": sector_correct,
        "sector_verifiable_count": sector_total,
        "sector_info": sec_metric,

        # Overall
        "rolling_avg_accuracy": rolling_avg,
        "rolling_20_accuracy": rolling_20_acc,
        "all_lessons": all_lessons,
        "missed_factor_counts": missed_factors,
        "last_updated": max(processed_dates) if processed_dates else "",
    }
