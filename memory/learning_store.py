"""
Learning Store — persists review results and performance stats to Obsidian.

FIXES vs original:
- build_learning_context: caps injected lessons to avoid bloating context window
- update_performance_stats: deduplicates lessons before storing
- load_recent_learnings: adds JSON parse guard + validates required fields
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from memory.obsidian import write_note, read_note, read_recent_notes
from memory.artifacts import load_json_artifact, save_json_artifact, ARTIFACT_ROOT

STATS_NOTE = "nexus-performance-stats"
MAX_LESSONS_STORED = 50      # cap total lessons in stats note
MAX_LESSONS_INJECTED = 5     # cap lessons injected into morning prompt
MAX_BLIND_SPOTS_INJECTED = 3


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
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
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
    # The caller typically expects oldest first to append newest at the end, wait, 
    # the original reversed them to be chronological. Let's return oldest first.
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
    """Append today's result to cumulative stats and save to local JSON + Obsidian."""
    stats = load_performance_stats()

    stats["total_sessions"] += 1
    stats["total_accuracy_sum"] += learning.get("accuracy_score", 0)
    stats["rolling_avg_accuracy"] = round(
        stats["total_accuracy_sum"] / stats["total_sessions"], 1
    )

    if learning.get("ihsg_correct"):
        stats["ihsg_correct_count"] += 1
    if learning.get("foreign_flow_correct"):
        stats["ff_correct_count"] += 1

    stats["ihsg_accuracy_pct"] = round(
        stats["ihsg_correct_count"] / stats["total_sessions"] * 100, 1
    )
    stats["ff_accuracy_pct"] = round(
        stats["ff_correct_count"] / stats["total_sessions"] * 100, 1
    )

    # Track recurring missed factors
    for factor in (learning.get("rca_unanticipated", []) +
                   learning.get("rca_underestimated", [])):
        if factor:
            stats["missed_factor_counts"][factor] = \
                stats["missed_factor_counts"].get(factor, 0) + 1

    # FIX: Deduplicate lessons + cap at MAX_LESSONS_STORED
    new_lessons = learning.get("lessons", [])
    existing = set(stats["all_lessons"])
    for lesson in new_lessons:
        if lesson and lesson not in existing:
            stats["all_lessons"].append(lesson)
            existing.add(lesson)
    # Keep only most recent lessons if over cap
    if len(stats["all_lessons"]) > MAX_LESSONS_STORED:
        stats["all_lessons"] = stats["all_lessons"][-MAX_LESSONS_STORED:]

    stats["last_updated"] = learning.get("date", "")

    content = f"""# Nexus Performance Statistics

Last updated: {stats['last_updated']}

## Overall
- Sessions tracked: {stats['total_sessions']}
- Rolling avg accuracy: **{stats['rolling_avg_accuracy']}%**
- IHSG direction accuracy: **{stats['ihsg_accuracy_pct']}%** ({stats['ihsg_correct_count']}/{stats['total_sessions']})
- Foreign flow accuracy: **{stats['ff_accuracy_pct']}%** ({stats['ff_correct_count']}/{stats['total_sessions']})

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

def build_learning_context(learnings: list) -> str:
    """Build calibration prompt block from recent learnings for morning brief.
    
    FIX: Caps injected lessons to MAX_LESSONS_INJECTED to avoid bloating
    the context window. Previously all accumulated lessons were injected.
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

    # Latest lessons — capped at MAX_LESSONS_INJECTED
    recent_lessons = []
    for l in learnings[-3:]:
        recent_lessons.extend(l.get("lessons", []))
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for lesson in recent_lessons:
        if lesson not in seen:
            seen.add(lesson)
            deduped.append(lesson)

    if deduped:
        lines.append("\n### 📌 Recent Lessons to Apply:")
        for lesson in deduped[-MAX_LESSONS_INJECTED:]:
            lines.append(f"  - {lesson}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _empty_stats() -> dict:
    return {
        "total_sessions": 0,
        "total_accuracy_sum": 0,
        "rolling_avg_accuracy": 0.0,
        "ihsg_correct_count": 0,
        "ff_correct_count": 0,
        "ihsg_accuracy_pct": 0.0,
        "ff_accuracy_pct": 0.0,
        "missed_factor_counts": {},
        "all_lessons": [],
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