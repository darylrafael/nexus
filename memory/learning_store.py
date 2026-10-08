"""
Learning Store — persists review results and performance stats to Obsidian.

FIXES vs original:
- build_learning_context: caps injected lessons to avoid bloating context window
- update_performance_stats: deduplicates lessons before storing
- load_recent_learnings: adds JSON parse guard + validates required fields
"""
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from core.time import jakarta_now
from memory.obsidian import write_note, read_note, read_recent_notes
from memory.artifacts import load_json_artifact, save_json_artifact, ARTIFACT_ROOT
from utils.stats import compute_canonical_stats

STATS_NOTE = "nexus-performance-stats"
MAX_LESSONS_STORED = 50      # cap total lessons in stats note
MAX_LESSONS_INJECTED = 5     # cap lessons injected into morning prompt
MAX_BLIND_SPOTS_INJECTED = 3


# ═══════════════════════════════════════════════════════════════════════════════
# REGIME DETECTION & HEURISTIC LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════

def detect_market_regime(review_or_learning: dict) -> str:
    """Classify market regime into BULLISH_TREND, BEARISH_TREND, or SIDEWAYS_VOLATILE."""
    if not isinstance(review_or_learning, dict):
        return "SIDEWAYS_VOLATILE"
    
    ihsg_actual = str(review_or_learning.get("ihsg_actual", ""))
    pct = review_or_learning.get("ihsg_actual_pct")
    try:
        pct_val = float(pct) if pct is not None else 0.0
    except (ValueError, TypeError):
        pct_val = 0.0
        
    if pct_val >= 0.5 or (ihsg_actual.lower() == "bullish" and pct_val >= 0.2):
        return "BULLISH_TREND"
    elif pct_val <= -0.5 or (ihsg_actual.lower() == "bearish" and pct_val <= -0.2):
        return "BEARISH_TREND"
    else:
        return "SIDEWAYS_VOLATILE"


def evaluate_heuristic_lifecycle(all_reviews: list) -> list:
    """
    Evaluate empirical lifecycle states for all accumulated lessons across reviews.
    States: HYPOTHESIS, ACTIVE, SUPERSEDED, UNTESTED.
    """
    # Collect all unique lessons preserving chronological order
    all_lessons = []
    for r in all_reviews:
        for lesson in r.get("lessons", []):
            if lesson and lesson not in all_lessons:
                all_lessons.append(lesson)

    heuristics = []
    for idx, rule_text in enumerate(all_lessons):
        evidence = []
        observed_regimes = set()
        last_observed = ""

        # Walk reviews (newest to oldest if available)
        for rev in sorted(all_reviews, key=lambda x: x.get("date", ""), reverse=True):
            rev_lessons = rev.get("lessons", [])
            has_lesson = any(rule_text in l or l in rule_text for l in rev_lessons)
            if has_lesson:
                rev_date = rev.get("date", "")
                if not last_observed:
                    last_observed = rev_date
                regime = rev.get("market_regime") or detect_market_regime(rev)
                observed_regimes.add(regime)
                outcome = "VALIDATED" if rev.get("ihsg_correct") is True else "CONTRADICTED"
                evidence.append({
                    "date": rev_date,
                    "outcome": outcome,
                    "regime": regime,
                    "ihsg_actual": rev.get("ihsg_actual", "Unknown"),
                    "ihsg_actual_pct": rev.get("ihsg_actual_pct", 0.0),
                    "summary": rev.get("summary", "")
                })

        observed = len(evidence)
        validated = sum(1 for e in evidence if e["outcome"] == "VALIDATED")
        contradicted = sum(1 for e in evidence if e["outcome"] == "CONTRADICTED")
        total_tested = validated + contradicted
        validation_rate = round((validated / total_tested) * 100, 1) if total_tested > 0 else None

        if observed >= 2 and validation_rate is not None and validation_rate >= 50.0:
            status = "ACTIVE"
        elif observed >= 2 and validation_rate is not None and validation_rate < 50.0:
            status = "SUPERSEDED"
        elif observed == 1:
            status = "ACTIVE" if validated == 1 else "HYPOTHESIS"
        else:
            status = "UNTESTED"

        heuristics.append({
            "id": f"rule-{idx + 1}",
            "rule": rule_text,
            "status": status,
            "observed": observed,
            "validated": validated,
            "contradicted": contradicted,
            "validation_rate": validation_rate,
            "regimes": sorted(list(observed_regimes)),
            "last_observed": last_observed,
            "evidence": evidence
        })

    return heuristics



# ═══════════════════════════════════════════════════════════════════════════════
# SAVE / LOAD INDIVIDUAL LEARNING ENTRIES
# ═══════════════════════════════════════════════════════════════════════════════

def save_learning(date: str, learning: dict) -> bool:
    """Save a structured learning dict to Obsidian as a markdown note."""
    lessons_md = ""
    for i, lesson in enumerate(learning.get("lessons", []), 1):
        lessons_md += f"{i}. {lesson}\n"

    rca = _format_rca(learning)

    content = f"""# Nexus Evening Review — {date}

## Summary
{learning.get('summary', '')}

## Accuracy Score: {learning.get('accuracy_score', 0)}% | Error Rate: {learning.get('error_rate_pct', 0)}%

| Metric | Predicted | Actual | Correct |
|--------|-----------|--------|---------|
| IHSG Direction | {learning.get('ihsg_predicted','?')} ({learning.get('ihsg_confidence','?')}%) | {learning.get('ihsg_actual','?')} ({learning.get('ihsg_actual_pct', 0):+.2f}%) | {'✅' if learning.get('ihsg_correct') else '❌'} |
| Foreign Flow | {learning.get('foreign_flow_predicted','?')} | {learning.get('foreign_flow_actual','?')} | {'✅' if learning.get('foreign_flow_correct') else '❌'} |
| USD/IDR | — | {learning.get('actual_usdidr','?')} | — |

## Sector Accuracy
{_format_sector_accuracy(learning.get('sector_accuracy', {}))}

## Root Cause Analysis
{rca}

## Lessons Learned
{lessons_md if lessons_md else '_(Prediction was correct — no corrective lessons needed.)_'}

## Raw Data
```json
{json.dumps(learning, ensure_ascii=False, indent=2)}
```
"""
    # Dual-write: already saved to JSON by evening_reviewer, now push to Obsidian
    return write_note(f"{date} - Evening Review", content)


def load_recent_learnings(days: int = 14) -> list:
    """
    Load recent learning entries directly from local JSON artifacts.
    This eliminates the Obsidian dependency for the self-learning loop.
    """
    cutoff = (jakarta_now() - timedelta(days=days)).strftime("%Y-%m-%d")
    learnings = []
    
    if not ARTIFACT_ROOT.exists():
        return []

    # Iterate through runs/ directories
    for run_dir in sorted(ARTIFACT_ROOT.iterdir(), reverse=True):
        if not run_dir.is_dir() or not re.match(r"\d{4}-\d{2}-\d{2}", run_dir.name):
            continue
        if run_dir.name < cutoff:
            break
        
        review_file = run_dir / "evening_review.json"
        if review_file.exists():
            try:
                data = json.loads(review_file.read_text(encoding="utf-8"))
                if "ihsg_correct" in data:
                    learnings.append(data)
            except Exception as e:
                print(f"  [learning_store] skipped malformed json in {run_dir.name}: {e}")

    # Return chronological order (oldest first in the loaded window, or reverse as needed by caller)
    learnings.reverse()
    print(f"  [learning_store] loaded {len(learnings)} learning entries from local artifacts (last {days}d)")
    return learnings


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE STATS (rolling)
# ═══════════════════════════════════════════════════════════════════════════════

def load_performance_stats() -> dict:
    """Load cumulative stats from local JSON, fallback to Obsidian if needed."""
    # Try local first
    local_stats = load_json_artifact("global", "nexus_stats.json")
    if local_stats:
        return local_stats

    # Fallback to Obsidian
    raw = read_note(STATS_NOTE)
    if not raw:
        return _empty_stats()
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            print(f"  [learning_store] obsidian stats parse failed: {e}")
    return _empty_stats()


def update_performance_stats(learning: dict) -> bool:
    """Append today's result to cumulative stats and save to local JSON + Obsidian.
    Uses canonical calculation to ensure separate metrics and accurate scorable denominators.
    """
    # Load all historical reviews to compute idempotent, canonical stats
    reviews_by_date = {}
    if ARTIFACT_ROOT.exists():
        for run_dir in sorted(ARTIFACT_ROOT.iterdir()):
            if run_dir.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", run_dir.name):
                rev_file = run_dir / "evening_review.json"
                if rev_file.exists():
                    try:
                        rev_data = json.loads(rev_file.read_text(encoding="utf-8"))
                        if isinstance(rev_data, dict) and rev_data.get("date"):
                            reviews_by_date[rev_data["date"]] = rev_data
                    except Exception:
                        pass

    # Incorporate current learning
    if isinstance(learning, dict) and learning.get("date"):
        reviews_by_date[learning["date"]] = learning

    all_reviews = [reviews_by_date[d] for d in sorted(reviews_by_date.keys())]
    stats = compute_canonical_stats(all_reviews)

    # Heuristic lifecycle calculation
    heuristics = evaluate_heuristic_lifecycle(all_reviews)
    stats["heuristics"] = [
        {
            "id": h["id"],
            "rule": h["rule"],
            "status": h["status"],
            "observed": h["observed"],
            "validated": h["validated"],
            "contradicted": h["contradicted"],
            "validation_rate": h["validation_rate"],
            "regimes": h["regimes"],
            "last_observed": h["last_observed"]
        }
        for h in heuristics
    ]
    stats["active_heuristics_count"] = sum(1 for h in heuristics if h["status"] == "ACTIVE")
    stats["superseded_heuristics_count"] = sum(1 for h in heuristics if h["status"] == "SUPERSEDED")
    stats["hypothesis_heuristics_count"] = sum(1 for h in heuristics if h["status"] == "HYPOTHESIS")

    # Backwards compatibility aliases
    stats["ihsg_accuracy_pct"] = stats["direction_accuracy_pct"] or 0.0
    stats["ihsg_correct_count"] = stats["direction_correct_count"]
    stats["ff_accuracy_pct"] = stats["flow_accuracy_pct"] or 0.0
    stats["ff_correct_count"] = stats["flow_correct_count"]
    stats["total_accuracy_sum"] = sum(
        float(r.get("accuracy_score", 0)) for r in all_reviews if r.get("accuracy_score") is not None
    )

    # Format human markdown
    dir_str = f"**{stats['direction_accuracy_pct']}%** ({stats['direction_correct_count']}/{stats['direction_scorable_sessions']})" if stats['direction_accuracy_pct'] is not None else "N/A"
    flow_str = f"**{stats['flow_accuracy_pct']}%** ({stats['flow_correct_count']}/{stats['flow_scorable_sessions']})" if stats['flow_accuracy_pct'] is not None else "N/A"
    sec_str = f"**{stats['sector_accuracy_pct']}%** ({stats['sector_correct_count']}/{stats['sector_verifiable_count']})" if stats['sector_accuracy_pct'] is not None else "N/A"
    avg_str = f"**{stats['rolling_avg_accuracy']}%**" if stats['rolling_avg_accuracy'] is not None else "N/A"

    content = f"""# Nexus Performance Statistics

Last updated: {stats['last_updated']}

## Overall
- Sessions tracked: {stats['total_sessions']}
- Rolling avg session accuracy: {avg_str}
- IHSG direction accuracy: {dir_str}
- Foreign flow accuracy: {flow_str}
- Sector accuracy: {sec_str}

## Heuristic Rules Lifecycle
- Active Heuristics: **{stats['active_heuristics_count']}**
- Hypotheses (Testing): **{stats['hypothesis_heuristics_count']}**
- Superseded Heuristics: **{stats['superseded_heuristics_count']}**

## Top Recurring Blind Spots
{_format_blind_spots(stats['missed_factor_counts'])}

## All Accumulated Lessons (last {MAX_LESSONS_STORED})
{_format_all_lessons(stats['all_lessons'])}

```json
{json.dumps(stats, ensure_ascii=False, indent=2)}
```
"""
    # Dual-write
    try:
        save_json_artifact("global", "nexus_stats.json", stats)
    except Exception as e:
        print(f"  [learning_store] failed to save local stats artifact: {e}")

    return write_note(STATS_NOTE, content)


# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATION CONTEXT (injected into morning brief)
# ═══════════════════════════════════════════════════════════════════════════════

def build_learning_context(learnings: list, current_regime: str = None) -> str:
    """Build calibration prompt block from recent learnings for morning brief.
    
    Incorporates:
    - Recent performance stats (rolling accuracy, session history)
    - Recurring blind spots
    - Empirical heuristic lifecycle prioritization with exponential time-decay weighting and regime awareness.
    """
    if not learnings:
        return ""

    stats = load_performance_stats()
    lines = ["\n## 🧠 Past Performance Calibration (READ CAREFULLY)\n"]
    lines.append(
        f"Rolling accuracy: **{stats.get('rolling_avg_accuracy', 0)}%** over "
        f"{stats.get('total_sessions', 0)} sessions | "
        f"IHSG: {stats.get('ihsg_accuracy_pct', 0)}% | "
        f"Foreign Flow: {stats.get('ff_accuracy_pct', 0)}%\n"
    )

    lines.append("### Recent Session Results:")
    for l in learnings[-5:]:
        date   = l.get("date", "?")
        status = "✅" if l.get("ihsg_correct") else "❌"
        pct    = l.get("ihsg_actual_pct", 0)
        lines.append(
            f"- {date}: {l.get('ihsg_predicted','?')} → {l.get('ihsg_actual','?')} "
            f"({pct:+.2f}%) {status} | accuracy {l.get('accuracy_score', 0)}%"
        )
        unanticipated = l.get("rca_unanticipated", [])
        if unanticipated:
            lines.append(f"  Missed: {', '.join(unanticipated[:2])}")

    # Recurring blind spots — capped
    blind_spots = stats.get("missed_factor_counts", {})
    recurring = [
        f for f, c in sorted(blind_spots.items(), key=lambda x: -x[1]) if c >= 2
    ][:MAX_BLIND_SPOTS_INJECTED]
    if recurring:
        lines.append(f"\n### ⚠️ Recurring Blind Spots (apply extra scrutiny today):")
        for bs in recurring:
            lines.append(f"  - {bs} (missed {blind_spots[bs]}x)")

    # Heuristic lifecycle evaluation across all available learnings
    heuristics_meta = {h["rule"]: h for h in evaluate_heuristic_lifecycle(learnings)}

    # Determine regime (inferred from latest learning if not specified)
    inferred_regime = current_regime
    if not inferred_regime and learnings:
        inferred_regime = learnings[-1].get("market_regime") or detect_market_regime(learnings[-1])

    # Score and rank candidate lessons using exponential time decay + lifecycle status + regime match
    now_dt = jakarta_now()
    scored_lessons = []
    seen = set()

    for l in reversed(learnings):
        rev_date_str = l.get("date", "")
        try:
            rev_dt = datetime.strptime(rev_date_str, "%Y-%m-%d")
            delta_days = max(0, (now_dt.date() - rev_dt.date()).days)
        except Exception:
            delta_days = 7

        recency_weight = math.exp(-0.08 * delta_days)
        rev_regime = l.get("market_regime") or detect_market_regime(l)

        for lesson in l.get("lessons", []):
            if not lesson or lesson in seen:
                continue
            seen.add(lesson)

            meta = heuristics_meta.get(lesson, {})
            status = meta.get("status", "HYPOTHESIS")
            val_rate = meta.get("validation_rate") or 50.0

            if status == "ACTIVE":
                status_mult = 1.3
            elif status == "SUPERSEDED":
                status_mult = 0.15
            else:
                status_mult = 1.0

            regime_mult = 1.35 if (inferred_regime and (inferred_regime in meta.get("regimes", []) or inferred_regime == rev_regime)) else 1.0

            final_score = recency_weight * status_mult * regime_mult * (1.0 + (val_rate / 100.0))
            scored_lessons.append({
                "lesson": lesson,
                "score": final_score,
                "status": status,
                "regime": rev_regime
            })

    # Sort descending by composite score
    scored_lessons.sort(key=lambda x: x["score"], reverse=True)
    selected_lessons = scored_lessons[:MAX_LESSONS_INJECTED]

    if selected_lessons:
        regime_banner = f" (Calibrated for {inferred_regime})" if inferred_regime else ""
        lines.append(f"\n### 📌 Calibrated Empirical Rules & Lessons{regime_banner}:")
        for item in selected_lessons:
            status_tag = f"[{item['status']}]"
            regime_tag = f"[{item['regime']}]" if item.get("regime") else ""
            lines.append(f"  - {status_tag}{regime_tag} {item['lesson']}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _empty_stats() -> dict:
    return {
        "total_sessions": 0,
        "processed_dates": [],
        "direction_accuracy_pct": None,
        "direction_correct_count": 0,
        "direction_scorable_sessions": 0,
        "flow_accuracy_pct": None,
        "flow_correct_count": 0,
        "flow_scorable_sessions": 0,
        "sector_accuracy_pct": None,
        "sector_correct_count": 0,
        "sector_verifiable_count": 0,
        "rolling_avg_accuracy": None,
        "ihsg_correct_count": 0,
        "ff_correct_count": 0,
        "ihsg_accuracy_pct": 0.0,
        "ff_accuracy_pct": 0.0,
        "missed_factor_counts": {},
        "all_lessons": [],
        "heuristics": [],
        "active_heuristics_count": 0,
        "superseded_heuristics_count": 0,
        "hypothesis_heuristics_count": 0,
        "last_updated": ""
    }


def _format_sector_accuracy(sector_acc: dict) -> str:
    if not sector_acc:
        return "_No sector predictions extracted._"
    lines = []
    for sector, correct in sector_acc.items():
        if correct is True:
            icon = "✅"
        elif correct is False:
            icon = "❌"
        else:
            icon = "❓ (insufficient data)"
        lines.append(f"- {sector}: {icon}")
    return "\n".join(lines)


def _format_rca(learning: dict) -> str:
    sections = {
        "Unanticipated factors":    "rca_unanticipated",
        "Overestimated factors":    "rca_overestimated",
        "Underestimated factors":   "rca_underestimated",
        "Information delay":        "rca_info_delay",
        "Inverse correlation cases":"rca_inverse_correlation",
    }
    lines = []
    for label, key in sections.items():
        items = learning.get(key, [])
        if items:
            lines.append(f"**{label}:**")
            for item in items:
                lines.append(f"  - {item}")
    return "\n".join(lines) if lines else "_No significant errors to analyze._"


def _format_blind_spots(counts: dict) -> str:
    if not counts:
        return "_None yet._"
    sorted_items = sorted(counts.items(), key=lambda x: -x[1])
    return "\n".join(f"- {f} ({c}x)" for f, c in sorted_items[:10])


def _format_all_lessons(lessons: list) -> str:
    if not lessons:
        return "_No lessons accumulated yet._"
    return "\n".join(f"{i+1}. {l}" for i, l in enumerate(lessons))
