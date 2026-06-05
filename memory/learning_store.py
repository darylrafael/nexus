"""
Learning Store — persists review results and performance stats to Obsidian.
"""
import json
import re
from datetime import datetime
from memory.obsidian import write_note, read_note, read_recent_notes


STATS_NOTE = "nexus-performance-stats"


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
    return write_note(f"{date} - Evening Review", content)


def load_recent_learnings(days: int = 14) -> list:
    """Load recent learning entries, return list of dicts parsed from JSON blocks."""
    raw = read_recent_notes(days=days)
    if not raw:
        return []
    learnings = []
    for block in re.finditer(r"```json\s*(.*?)\s*```", raw, re.DOTALL):
        try:
            data = json.loads(block.group(1))
            if "ihsg_predicted" in data:  # basic sanity check
                learnings.append(data)
        except json.JSONDecodeError:
            continue
    return learnings


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE STATS (rolling)
# ═══════════════════════════════════════════════════════════════════════════════

def load_performance_stats() -> dict:
    """Load cumulative stats from Obsidian."""
    raw = read_note(STATS_NOTE)
    if not raw:
        return _empty_stats()
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return _empty_stats()


def update_performance_stats(learning: dict) -> bool:
    """Append today's result to cumulative stats and save."""
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

    # Track all lessons
    stats["all_lessons"].extend(learning.get("lessons", []))
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

## All Accumulated Lessons
{_format_all_lessons(stats['all_lessons'])}

```json
{json.dumps(stats, ensure_ascii=False, indent=2)}
```
"""
    return write_note(STATS_NOTE, content)


# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATION CONTEXT (injected into morning brief)
# ═══════════════════════════════════════════════════════════════════════════════

def build_learning_context(learnings: list) -> str:
    """Build calibration prompt block from recent learnings for morning brief."""
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

    # Recurring blind spots
    blind_spots = stats.get("missed_factor_counts", {})
    recurring = [f for f, c in sorted(blind_spots.items(), key=lambda x: -x[1]) if c >= 2][:3]
    if recurring:
        lines.append(f"\n### ⚠️ Recurring Blind Spots (apply extra scrutiny today):")
        for bs in recurring:
            lines.append(f"  - {bs} (missed {blind_spots[bs]}x)")

    # Latest lessons
    recent_lessons = []
    for l in learnings[-3:]:
        recent_lessons.extend(l.get("lessons", []))
    if recent_lessons:
        lines.append("\n### 📌 Recent Lessons to Apply:")
        for lesson in recent_lessons[-4:]:
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
        lines.append(f"- {sector}: {'✅' if correct else '❌'}")
    return "\n".join(lines)


def _format_rca(learning: dict) -> str:
    sections = {
        "Unanticipated factors":       "rca_unanticipated",
        "Overestimated factors":        "rca_overestimated",
        "Underestimated factors":       "rca_underestimated",
        "Information delay":            "rca_info_delay",
        "Inverse correlation cases":    "rca_inverse_correlation",
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
    return "\n".join(f"{i+1}. {l}" for i, l in enumerate(lessons[-20:]))
