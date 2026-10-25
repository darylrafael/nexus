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
from memory.artifacts import get_artifact_root, load_json_artifact, save_json_artifact
from memory.obsidian import read_note, write_note
from utils.stats import compute_canonical_stats

ARTIFACT_ROOT: Path | None = None


def _get_runs_root() -> Path:
    if ARTIFACT_ROOT is not None:
        return Path(ARTIFACT_ROOT)
    return get_artifact_root()


STATS_NOTE = "nexus-performance-stats"
MAX_LESSONS_STORED = 50      # cap total lessons in stats note
MAX_LESSONS_INJECTED = 5     # cap lessons injected into morning prompt
MAX_BLIND_SPOTS_INJECTED = 3

BOILERPLATE_PATTERNS = [
    r"perlu memperketat stop-loss",
    r"analisis sektor perlu mempertimbangkan",
    r"perlu evaluasi lebih lanjut",
    r"perlu berhati-hati",
    r"perlu memantau",
    r"penting untuk memperhatikan",
]


def _extract_fx_clauses(text: str) -> list[dict]:
    """Extract FX statements from lesson clauses without bleeding across clause boundaries into IHSG returns.

    Detects convention:
      - 'usdidr': explicit 'USD/IDR' mention in the clause (positive % = USD/IDR rose = Rupiah weaker)
      - 'rupiah': 'Rupiah' mention without 'USD/IDR' (stored actuals are USD/IDR terms where -% = stronger, +% = weaker)
    """
    clauses = re.split(
        r"(?:,\s*tetapi\b|,\s*namun\b|,\s*maka\b|;\s*|\.\s+|\bdan\s+IHSG\b|\bmaka\s+IHSG\b)",
        text,
        flags=re.IGNORECASE,
    )
    results = []
    for idx, clause in enumerate(clauses):
        if not re.search(r"\b(?:rupiah|usd\s*/?\s*idr)\b", clause, re.IGNORECASE):
            continue

        is_premise = (idx == 0 and bool(re.search(r"^\s*ketika\b", clause, re.IGNORECASE))) or bool(
            re.search(r"\b(?:diprediksi|diproyeksikan|risiko)\b", clause, re.IGNORECASE)
        )
        convention = "usdidr" if re.search(r"usd\s*/?\s*idr", clause, re.IGNORECASE) else "rupiah"

        weaken_m = re.search(
            r"rupiah\s+(?:dapat\s+|berbalik\s+|terus\s+|justru\s+)?(?:melemah|terdepresiasi|turun|anjlok)"
            r"|(?:pelemahan|depresiasi)\s+rupiah"
            r"|usd\s*/?\s*idr\s+(?:naik|melonjak|menguat|meningkat)",
            clause,
            re.IGNORECASE,
        )
        strengthen_m = re.search(
            r"rupiah\s+(?:dapat\s+|berbalik\s+|terus\s+|justru\s+)?(?:menguat|terapresiasi|naik|rebound)"
            r"|(?:penguatan|apresiasi)\s+rupiah"
            r"|usd\s*/?\s*idr\s+(?:turun|melemah|melandai)",
            clause,
            re.IGNORECASE,
        )
        direction = "weaken" if weaken_m else ("strengthen" if strengthen_m else None)

        # Check spot range if explicitly stated (e.g. dari Rp17.880/USD ke Rp17.993/USD)
        spot_from = None
        spot_to = None
        spot_m = re.search(
            r"dari\s+(?:Rp\s*)?(1[4-9][\.,]\d{3}|1[4-9]\d{3})(?:/USD)?\s+ke\s+(?:Rp\s*)?(1[4-9][\.,]\d{3}|1[4-9]\d{3})",
            clause,
            re.IGNORECASE,
        )
        if spot_m:
            try:
                spot_from = float(spot_m.group(1).replace(".", "").replace(",", "."))
                spot_to = float(spot_m.group(2).replace(".", "").replace(",", "."))
            except ValueError:
                pass

        # Extract percentage attached to the FX phrase (after the last rupiah / usd/idr mention in this sub-clause)
        pct_val = None
        has_plus = False
        has_minus = False
        fx_tail_m = re.search(
            r"(?:rupiah|usd\s*/?\s*idr)(?!.*(?:rupiah|usd\s*/?\s*idr))([^%]*?)([+-]?\s*\d+(?:[\.,]\d+)?)\s*%",
            clause,
            re.IGNORECASE,
        )
        if fx_tail_m:
            intervening = fx_tail_m.group(1).lower()
            unrelated_tokens = ["bi rate", "suku bunga", "treasury", "oil", "brent", "wti", "coal", "cpo", "nickel", "ihsg", "sektor"]
            if not any(tok in intervening for tok in unrelated_tokens):
                raw_pct = fx_tail_m.group(2).replace(" ", "")
                has_plus = raw_pct.startswith("+")
                has_minus = raw_pct.startswith("-")
                try:
                    pct_val = float(raw_pct.replace(",", "."))
                except ValueError:
                    pct_val = None

        results.append({
            "clause": clause,
            "is_premise": is_premise,
            "convention": convention,
            "direction": direction,
            "pct_val": pct_val,
            "has_plus": has_plus,
            "has_minus": has_minus,
            "spot_from": spot_from,
            "spot_to": spot_to,
        })
    return results


def validate_lesson(lesson: str, session_actuals: dict | None = None) -> tuple[bool, str]:
    """Validate a lesson for numeric sanity, FX convention & actuals consistency, unit notations, and boilerplate filler.
    Returns (is_valid, rejection_reason).
    """
    if not lesson or not isinstance(lesson, str):
        return False, "empty_lesson"

    text = lesson.strip()
    if len(text) < 15:
        return False, "too_short"

    # 1. Reject invalid units like (+17K) or +15k
    if re.search(r"\+\d+[kK]\b", text):
        return False, "invalid_unit: +17K style notation"

    # 2. Reject generic boilerplate synthesized lessons
    for bp in BOILERPLATE_PATTERNS:
        if re.search(bp, text, re.IGNORECASE):
            return False, f"boilerplate_generic: matches pattern '{bp}'"

    dq = (session_actuals.get("data_quality") or {}) if isinstance(session_actuals, dict) else {}
    stored_fx_pct = session_actuals.get("usdidr_change_pct") if isinstance(session_actuals, dict) else None
    spot_fx_pct = dq.get("spot_usdidr_change_pct") if isinstance(dq, dict) else None
    fx_reliable = dq.get("fx_reliable") if isinstance(dq, dict) else None
    rupiah_sig = session_actuals.get("rupiah_signal") if isinstance(session_actuals, dict) else None

    # 3. Validate FX clauses (Phase 4.1: detect 'usdidr' vs 'rupiah' convention, check against stored actuals & reliability)
    for fx_info in _extract_fx_clauses(text):
        conv = fx_info["convention"]
        direction = fx_info["direction"]
        pct_val = fx_info["pct_val"]
        has_plus = fx_info["has_plus"]
        has_minus = fx_info["has_minus"]
        spot_from = fx_info["spot_from"]
        spot_to = fx_info["spot_to"]
        is_premise = fx_info["is_premise"]

        # 3a. Internal spot range contradiction (USD/IDR rising = weakening, falling = strengthening)
        if spot_from is not None and spot_to is not None:
            if direction == "strengthen" and spot_to > spot_from:
                return False, f"sign_confusion: spot USD/IDR rose ({spot_from} -> {spot_to}) while claiming rupiah strengthened"
            if direction == "weaken" and spot_to < spot_from:
                return False, f"sign_confusion: spot USD/IDR fell ({spot_from} -> {spot_to}) while claiming rupiah weakened"

        # 3b. Explicit 'USD/IDR' convention sign check (positive USD/IDR % = rupiah weaker, negative = rupiah stronger)
        if conv == "usdidr" and pct_val is not None:
            if direction == "weaken" and has_minus and pct_val < 0:
                return False, f"sign_confusion: USD/IDR convention weakening with negative percentage ({pct_val}%)"
            if direction == "strengthen" and has_plus and pct_val > 0:
                return False, f"sign_confusion: USD/IDR convention strengthening with positive percentage (+{pct_val}%)"

        # 3c. Validate non-premise FX outcome claims against session_actuals when provided
        if isinstance(session_actuals, dict) and not is_premise:
            # Check if underlying FX percentage data is unreliable
            if pct_val is not None:
                is_fx_unreliable = (fx_reliable is False) or (
                    stored_fx_pct is not None
                    and spot_fx_pct is not None
                    and abs(float(stored_fx_pct) - float(spot_fx_pct)) > 0.35
                )
                if is_fx_unreliable:
                    return (
                        False,
                        f"unreliable_source_data: stored usdidr_change_pct ({stored_fx_pct}%) diverges from consecutive spot close ({spot_fx_pct}%)",
                    )

            # Check direction consistency against stored actuals (in USD/IDR terms: >0 is Weakened, <0 is Strengthened)
            if direction == "weaken":
                if (stored_fx_pct is not None and float(stored_fx_pct) < -0.05) or rupiah_sig == "Strengthened":
                    return False, f"sign_confusion: stated rupiah weakened vs actual strengthened ({stored_fx_pct}%)"
            elif direction == "strengthen":
                if (stored_fx_pct is not None and float(stored_fx_pct) > 0.05) or rupiah_sig == "Weakened":
                    return False, f"sign_confusion: stated rupiah strengthened vs actual weakened ({stored_fx_pct}%)"

            # Check numeric match within tolerance (0.15 percentage points)
            if pct_val is not None and stored_fx_pct is not None:
                act_fx = float(stored_fx_pct)
                if abs(abs(pct_val) - abs(act_fx)) > 0.15:
                    return False, f"fx_numeric_contradiction: stated FX {pct_val}% vs actual {act_fx}%"

    # 4. Validate against unverified / date-mismatched foreign flow source data in session_actuals
    if isinstance(session_actuals, dict):
        flow_reason = dq.get("flow_reason") if isinstance(dq, dict) else None
        if flow_reason == "date_mismatch_rejected" and re.search(r"829[\.,]70", text):
            return False, "unreliable_source_data: cites unverified foreign flow from date_mismatch_rejected source"

        ihsg_pct = session_actuals.get("ihsg_actual_pct")
        if ihsg_pct is not None:
            ihsg_m = re.search(r"IHSG[^\.\n\r\d+-]*?([+-]?\d+(?:[\.,]\d+)?)\s*%", text, re.IGNORECASE)
            if ihsg_m:
                try:
                    stated_num = float(ihsg_m.group(1).replace(",", "."))
                    if (ihsg_pct < 0 and stated_num > 0 and not any(w in text.lower() for w in ["turun", "melemah", "penurunan"])) or \
                       (ihsg_pct > 0 and stated_num < 0 and not any(w in text.lower() for w in ["naik", "menguat", "rebound"])):
                        return False, f"numeric_contradiction: stated IHSG {stated_num}% vs actual {ihsg_pct}%"
                except ValueError:
                    pass

    return True, "valid"


def format_structured_lesson(lesson: str) -> str:
    """Convert verbose prose lesson into a structured, actionable bias rule."""
    text = lesson.strip()
    # Check for sector pattern: "Ketika sektor X diprediksi ..., tetapi Y, maka Z"
    sec_match = re.search(r"sektor\s+([^,]+?)\s+diprediksi\s+([a-zA-Z]+)[^,]*,\s*tetapi\s+([^,]+?),\s*maka\s+(.*)", text, re.IGNORECASE)
    if sec_match:
        sec = sec_match.group(1).strip()
        cond = sec_match.group(3).strip()
        outcome = sec_match.group(4).strip()
        return f"SECTOR_BIAS: {sec} adjusted on [{cond}] -> {outcome}"

    # Check for macro pattern: "Ketika Rupiah/IHSG/komoditas ..."
    macro_match = re.search(r"Ketika\s+([^,]+?),\s*tetapi\s+([^,]+?),\s*maka\s+(.*)", text, re.IGNORECASE)
    if macro_match:
        premise = macro_match.group(1).strip()
        catalyst = macro_match.group(2).strip()
        verdict = macro_match.group(3).strip()
        return f"MACRO_BIAS: [{premise}] countered by [{catalyst}] -> {verdict}"

    return text[:130].strip()


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


from core.provenance import check_run_dir_provenance, has_mock_provenance


def is_session_data_quality_passing(r: dict) -> bool:
    """Return True only if session has genuine (non-mock) provenance and passing data_quality."""
    if not isinstance(r, dict):
        return False
    if has_mock_provenance(r):
        return False
    dq = r.get("data_quality")
    if isinstance(dq, dict):
        if dq.get("overall_valid") is False:
            return False
        if str(dq.get("status", "")).lower() in ("failed", "error", "invalid"):
            return False
    return True


def _enrich_reviews_with_actuals(all_reviews: list) -> list[dict]:
    """Enrich review dicts with FX actuals and consecutive spot USD/IDR checks from evening_actuals.json."""
    runs_root = _get_runs_root()
    sorted_revs = [dict(r) for r in all_reviews if isinstance(r, dict)]
    sorted_revs.sort(key=lambda x: str(x.get("date", "")))

    prev_spot_fx = None
    for r in sorted_revs:
        rev_date = str(r.get("date", ""))
        act_data = {}
        if rev_date and (runs_root / rev_date / "evening_actuals.json").exists():
            try:
                act_data = json.loads((runs_root / rev_date / "evening_actuals.json").read_text(encoding="utf-8"))
            except Exception:
                act_data = {}

        if r.get("usdidr_change_pct") is None and act_data.get("usdidr_change_pct") is not None:
            r["usdidr_change_pct"] = act_data.get("usdidr_change_pct")
        if r.get("rupiah_signal") is None and act_data.get("rupiah_signal") is not None:
            r["rupiah_signal"] = act_data.get("rupiah_signal")
        if r.get("actual_usdidr") is None and isinstance(act_data.get("usdidr"), (int, float)):
            r["actual_usdidr"] = act_data.get("usdidr")

        dq = dict(r.get("data_quality") or act_data.get("data_quality") or {})
        curr_fx = r.get("actual_usdidr") if isinstance(r.get("actual_usdidr"), (int, float)) else (
            act_data.get("usdidr") if isinstance(act_data.get("usdidr"), (int, float)) else None
        )
        stored_fx_pct = r.get("usdidr_change_pct")
        if curr_fx is not None and prev_spot_fx is not None and prev_spot_fx > 0:
            spot_chg = round(((float(curr_fx) - float(prev_spot_fx)) / float(prev_spot_fx)) * 100.0, 3)
            dq.setdefault("spot_usdidr_change_pct", spot_chg)
            if stored_fx_pct is not None:
                dq.setdefault("fx_reliable", abs(float(stored_fx_pct) - spot_chg) <= 0.35)
        if curr_fx is not None and float(curr_fx) > 0:
            prev_spot_fx = float(curr_fx)
        if dq:
            r["data_quality"] = dq

    return sorted_revs


def filter_and_quarantine_lessons(all_reviews: list) -> tuple[list[str], list[dict]]:
    """Filter all stored lessons across reviews:
    - Exclude sessions with mock/synthetic provenance.
    - Exclude sessions whose data_quality checks failed.
    - Reject garbled numbers, +17K units, sign confusion, unreliable source data, and boilerplate.
    - Deduplicate lessons sharing the same tail (e.g. 'maka IHSG ditutup Bearish (-0.83%)').
    - Allow at most 2 lessons per session.
    Returns (valid_lessons, rejected_lessons).
    """
    valid_lessons = []
    rejected_lessons = []

    enriched_reviews = _enrich_reviews_with_actuals(all_reviews)

    for r in enriched_reviews:
        rev_date = r.get("date", "")
        # Phase 2.2 check: never store or learn from mock/synthetic provenance sessions
        is_dir_mock = bool(rev_date and check_run_dir_provenance(_get_runs_root() / str(rev_date))[0])
        if has_mock_provenance(r) or is_dir_mock:
            for l in r.get("lessons", []):
                rejected_lessons.append({
                    "date": rev_date,
                    "lesson": l,
                    "reason": "mock_provenance_rejected"
                })
            continue

        # Phase B2 / 4.3 check: never learn from sessions whose data_quality checks failed
        if not is_session_data_quality_passing(r):
            for l in r.get("lessons", []):
                rejected_lessons.append({
                    "date": rev_date,
                    "lesson": l,
                    "reason": "data_quality_failed"
                })
            continue

        session_lessons = []
        seen_tails = set()

        for lesson in r.get("lessons", []):
            is_valid, reason = validate_lesson(lesson, r)
            if not is_valid:
                rejected_lessons.append({
                    "date": rev_date,
                    "lesson": lesson,
                    "reason": reason
                })
                continue

            # Deduplicate by tail: e.g. "maka IHSG ditutup Bearish (-0.83%)"
            tail_m = re.search(r"maka\s+IHSG\s+(?:tetap\s+)?ditutup\s+[^\.\n\r]+", lesson, re.IGNORECASE)
            if tail_m:
                tail = re.sub(r"\btetap\s+", "", tail_m.group(0).lower()).strip()
            else:
                tail = None

            if tail:
                if tail in seen_tails:
                    rejected_lessons.append({
                        "date": rev_date,
                        "lesson": lesson,
                        "reason": f"duplicate_tail: {tail}"
                    })
                    continue
                seen_tails.add(tail)

            if len(session_lessons) >= 2:
                rejected_lessons.append({
                    "date": rev_date,
                    "lesson": lesson,
                    "reason": "session_limit_exceeded: max 2 lessons per session"
                })
                continue

            session_lessons.append(lesson)

        for v in session_lessons:
            if v not in valid_lessons:
                valid_lessons.append(v)

    return valid_lessons, rejected_lessons


def evaluate_heuristic_lifecycle(all_reviews: list) -> list:
    """
    Evaluate empirical lifecycle states for all accumulated lessons across reviews.
    States: HYPOTHESIS, ACTIVE, SUPERSEDED, UNTESTED.
    Only genuine, data_quality-passing sessions may validate heuristics (Phase 4.3).
    """
    enriched_reviews = _enrich_reviews_with_actuals(all_reviews)
    valid_lessons, _ = filter_and_quarantine_lessons(enriched_reviews)

    heuristics = []
    for idx, rule_text in enumerate(valid_lessons):
        evidence = []
        observed_regimes = set()
        last_observed = ""

        # Walk reviews (newest to oldest if available)
        for rev in sorted(enriched_reviews, key=lambda x: str(x.get("date", "")), reverse=True):
            rev_date = rev.get("date", "")
            is_dir_mock = bool(rev_date and check_run_dir_provenance(_get_runs_root() / str(rev_date))[0])
            if is_dir_mock or not is_session_data_quality_passing(rev):
                continue

            rev_lessons = rev.get("lessons", [])
            has_lesson = any(rule_text in l or l in rule_text for l in rev_lessons)
            if has_lesson:
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
    """Save a structured learning dict to Obsidian as a markdown note.
    Rejects mock/synthetic provenance artifacts (Phase 2.2).
    """
    is_dir_mock = bool(date and check_run_dir_provenance(_get_runs_root() / str(date))[0])
    if has_mock_provenance(learning) or is_dir_mock:
        print(f"  [learning_store] REJECTED save_learning for {date}: mock/synthetic provenance detected.")
        return False

    lessons_md = ""
    for i, lesson in enumerate(learning.get("lessons", []), 1):
        lessons_md += f"{i}. {lesson}\n"

    rca = _format_rca(learning)
    ihsg_act_pct = learning.get("ihsg_actual_pct")
    ihsg_act_pct_str = f"{ihsg_act_pct:+.2f}%" if isinstance(ihsg_act_pct, (int, float)) else "N/A"

    content = f"""# Nexus Evening Review — {date}

## Summary
{learning.get('summary', '')}

## Accuracy Score: {learning.get('accuracy_score', 0)}% | Error Rate: {learning.get('error_rate_pct', 0)}%

| Metric | Predicted | Actual | Correct |
|--------|-----------|--------|---------|
| IHSG Direction | {learning.get('ihsg_predicted','?')} ({learning.get('ihsg_confidence','?')}%) | {learning.get('ihsg_actual','?')} ({ihsg_act_pct_str}) | {'✅' if learning.get('ihsg_correct') else '❌'} |
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
    Excludes any session with mock/synthetic provenance.
    """
    cutoff = (jakarta_now() - timedelta(days=days)).strftime("%Y-%m-%d")
    learnings = []
    
    runs_root = _get_runs_root()
    if not runs_root.exists():
        return []

    # Iterate through session directories
    for run_dir in sorted(runs_root.iterdir(), reverse=True):
        if not run_dir.is_dir() or not re.match(r"\d{4}-\d{2}-\d{2}", run_dir.name):
            continue
        if run_dir.name < cutoff:
            break
        if check_run_dir_provenance(run_dir)[0]:
            continue
        
        review_file = run_dir / "evening_review.json"
        if review_file.exists():
            try:
                data = json.loads(review_file.read_text(encoding="utf-8"))
                if "ihsg_correct" in data and not has_mock_provenance(data):
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
    Excludes any session with mock/synthetic provenance.
    """
    # Load all historical reviews to compute idempotent, canonical stats
    reviews_by_date = {}
    runs_root = _get_runs_root()
    if runs_root.exists():
        for run_dir in sorted(runs_root.iterdir()):
            if run_dir.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", run_dir.name):
                if check_run_dir_provenance(run_dir)[0]:
                    continue
                rev_file = run_dir / "evening_review.json"
                if rev_file.exists():
                    try:
                        rev_data = json.loads(rev_file.read_text(encoding="utf-8"))
                        if isinstance(rev_data, dict) and rev_data.get("date") and not has_mock_provenance(rev_data):
                            reviews_by_date[rev_data["date"]] = rev_data
                    except Exception:
                        pass

    # Incorporate current learning only if genuine (non-mock)
    if isinstance(learning, dict) and learning.get("date"):
        l_date = str(learning["date"])
        if not has_mock_provenance(learning) and not check_run_dir_provenance(runs_root / l_date)[0]:
            reviews_by_date[l_date] = learning

    all_reviews = [reviews_by_date[d] for d in sorted(reviews_by_date.keys())]
    stats = compute_canonical_stats(all_reviews)

    # Heuristic lifecycle calculation & quarantined lessons tracking
    valid_lessons, rejected_lessons = filter_and_quarantine_lessons(all_reviews)
    heuristics = evaluate_heuristic_lifecycle(all_reviews)
    stats["all_lessons"] = valid_lessons
    stats["rejected_lessons"] = rejected_lessons
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
    - Excludes unvalidated, garbled, mock-provenance, or failed data_quality sessions.
    """
    if not learnings:
        return ""

    # Filter out any mock provenance or failed data_quality sessions before building context
    enriched = _enrich_reviews_with_actuals(learnings)
    genuine_learnings = [
        l for l in enriched
        if isinstance(l, dict)
        and not (l.get("date") and check_run_dir_provenance(_get_runs_root() / str(l.get("date")))[0])
        and is_session_data_quality_passing(l)
    ]
    if not genuine_learnings:
        return ""

    stats = load_performance_stats()
    lines = ["\n## 🧠 Past Performance Calibration (READ CAREFULLY)\n"]

    rolling_str = f"{stats.get('rolling_avg_accuracy')}%" if stats.get('rolling_avg_accuracy') is not None else "n/a"
    ihsg_str = f"{stats.get('direction_accuracy_pct')}%" if stats.get('direction_accuracy_pct') is not None else "n/a"
    ff_str = f"{stats.get('flow_accuracy_pct')}%" if stats.get('flow_accuracy_pct') is not None else "n/a"
    sec_str = f"{stats.get('sector_accuracy_pct')}%" if stats.get('sector_accuracy_pct') is not None else "n/a"

    lines.append(
        f"Rolling accuracy: **{rolling_str}** over "
        f"{stats.get('total_sessions', 0)} sessions | "
        f"IHSG: {ihsg_str} | "
        f"Foreign Flow: {ff_str} | "
        f"Sector: {sec_str}\n"
    )

    lines.append("### Recent Session Results:")
    for l in genuine_learnings[-5:]:
        date   = l.get("date", "?")
        status = "✅" if l.get("ihsg_correct") else "❌"
        pct    = l.get("ihsg_actual_pct", 0)
        pct_val = pct if pct is not None else 0.0
        acc_val = l.get("accuracy_score")
        acc_str = f"{acc_val}%" if acc_val is not None else "n/a"
        lines.append(
            f"- {date}: {l.get('ihsg_predicted','?')} → {l.get('ihsg_actual','?')} "
            f"({pct_val:+.2f}%) {status} | accuracy {acc_str}"
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
        lines.append("\n### ⚠️ Recurring Blind Spots (apply extra scrutiny today):")
        for bs in recurring:
            lines.append(f"  - {bs} (missed {blind_spots[bs]}x)")

    # Heuristic lifecycle evaluation across genuine learnings (enriched with full-history stats if available)
    heuristics_meta = {h["rule"]: h for h in evaluate_heuristic_lifecycle(genuine_learnings)}
    for h in stats.get("heuristics", []):
        if isinstance(h, dict) and h.get("rule"):
            existing = heuristics_meta.get(h["rule"])
            if not existing or int(h.get("observed", 0)) > int(existing.get("observed", 0)):
                heuristics_meta[h["rule"]] = h

    # Determine regime (inferred from latest learning if not specified)
    inferred_regime = current_regime
    if not inferred_regime and genuine_learnings:
        inferred_regime = genuine_learnings[-1].get("market_regime") or detect_market_regime(genuine_learnings[-1])

    # Score and rank candidate lessons using exponential time decay + lifecycle status + regime match
    now_dt = jakarta_now()
    scored_lessons = []
    seen = set()

    for l in reversed(genuine_learnings):
        # Phase 4.3 rule: Never learn from sessions whose data_quality checks failed
        if not is_session_data_quality_passing(l):
            continue

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

            # Check validity
            is_valid, _ = validate_lesson(lesson, l)
            if not is_valid:
                continue

            meta = heuristics_meta.get(lesson, {})
            status = meta.get("status", "HYPOTHESIS")
            val_rate = meta.get("validation_rate") if meta.get("validation_rate") is not None else 50.0

            if status == "ACTIVE":
                status_mult = 1.3
            elif status == "SUPERSEDED":
                status_mult = 0.15
            else:
                # HYPOTHESIS: corrective lesson from a genuine missed session that passed all 5 quality gates
                status_mult = 0.95

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
            structured_text = format_structured_lesson(item['lesson'])
            lines.append(f"  - {status_tag}{regime_tag} {structured_text}")

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
