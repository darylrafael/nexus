"""
Evening Reviewer — runs at 19:00 WIB weekdays.
Full 7-step post-market evaluation and learning pipeline.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from llm_client import get_content, llm_chat
from agents.web_agent import search_multiple
from agents.prediction_extractor import extract_predictions, MarketPrediction
from data_sources.market_data import (
    COMMODITY_TICKERS,
    fetch_ihsg_snapshot,
    fetch_usdidr_snapshot,
    fetch_yfinance_commodity,
    jakarta_now,
)
from data_sources.news import search_text_with_sources
from memory.artifacts import load_json_artifact, save_json_artifact
from memory.obsidian import read_note
from memory.learning_store import save_learning, update_performance_stats

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Read morning brief (Obsidian → local artifact fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def load_morning_brief(date_key: str) -> tuple:
    """
    Read morning brief — tries Obsidian first, falls back to local artifact.

    Fallback path: runs/{date_key}/morning_brief.md
    This file is always written by market_agent.run_market_brief() regardless
    of whether Obsidian is running, so the evening review is resilient to
    Obsidian being offline.

    Returns (MarketPrediction, raw_brief_text) or (None, None) if not found.
    """
    note_title = f"{date_key} - IHSG Market Brief"
    raw = read_note(note_title)

    # Fallback to local artifacts directory if Obsidian is offline
    if not raw or len(raw.strip()) < 100:
        print(f"  [step1] [WARN] Obsidian returned nothing. Trying local artifact...")
        artifact_path = Path(__file__).parent.parent / "runs" / date_key / "morning_brief.md"
        if artifact_path.exists():
            raw = artifact_path.read_text(encoding="utf-8")
            print(f"  [step1] [OK] Loaded morning brief from local file: {artifact_path}")
        else:
            print(f"  [step1] [ERR] No local artifact found either: {artifact_path}")

    if not raw or len(raw.strip()) < 100:
        print(f"  [step1] [ERR] Morning brief not found for {date_key}. Stopping.")
        return None, None

    # Try structured JSON artifact first (faster + exact), fall back to parsing markdown
    structured = load_json_artifact(date_key, "morning_prediction.json")
    if structured:
        try:
            pred = MarketPrediction(**structured)
            print(f"  [step1] ✅ Structured prediction loaded from JSON artifact.")
        except Exception:
            pred = extract_predictions(raw, date_key)
            print(f"  [step1] ✅ Brief loaded (JSON artifact malformed; parsed markdown).")
    else:
        pred = extract_predictions(raw, date_key)
        print(f"  [step1] ✅ Brief loaded (no JSON artifact; parsed markdown).")

    print(f"  [step1]    IHSG pred={pred.ihsg_signal} ({pred.ihsg_confidence}%)")
    return pred, raw


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Collect actual market data
# ═══════════════════════════════════════════════════════════════════════════════

def collect_actual_data(date_id: str, target_date: str = None) -> dict:
    """Fetch IHSG, commodities, rupiah, top movers from yfinance/Yahoo + web search."""
    data = {}
    data["evidence_ids"] = []

    # IHSG
    print("  [step2] fetching IHSG actual...")
    try:
        data.update(fetch_ihsg_snapshot(target_date=target_date))
    except Exception as e:
        print(f"  [step2] IHSG error: {e}")
        data["ihsg_signal"] = "Unknown"

    # Rupiah (USD/IDR)
    print("  [step2] fetching USD/IDR...")
    try:
        data.update(fetch_usdidr_snapshot())
    except Exception as e:
        print(f"  [step2] USD/IDR error: {e}")
        data["usdidr"] = "N/A"

    # Commodities via yfinance
    print("  [step2] fetching commodity prices...")
    data["commodities"] = {}
    for name, ticker in COMMODITY_TICKERS.items():
        try:
            data["commodities"][name] = fetch_yfinance_commodity(name, ticker)
        except Exception as e:
            print(f"  [step2] commodity error for {name}: {e}")
            data["commodities"][name] = {"price": "N/A", "change_pct": 0, "signal": "Unknown"}

    # Coal, CPO, Nickel — web search (no free yfinance ticker)
    print("  [step2] fetching Coal/CPO/Nickel via web...")
    for name, query in {
        "Coal (Newcastle)": f"harga batu bara Newcastle hari ini {date_id}",
        "CPO":               f"harga CPO crude palm oil hari ini {date_id}",
        "Nickel (LME)":      f"harga nikel LME hari ini {date_id}",
    }.items():
        try:
            result, source_ids = search_text_with_sources(query, days=1, category=name, limit_chars=200)
            data["commodities"][name] = {"raw": result}
            data["evidence_ids"].extend(source_ids)
        except Exception as e:
            print(f"  [step2] web commodity error for {name}: {e}")
            data["commodities"][name] = {"raw": "N/A"}

    # Top gainers / losers
    print("  [step2] fetching top movers...")
    try:
        text, source_ids = search_text_with_sources(
            f"saham naik turun terbesar IHSG top gainer loser {date_id}",
            days=1,
            category="top_movers",
            limit_chars=600,
        )
        data["top_movers"] = text
        data["evidence_ids"].extend(source_ids)
    except Exception as e:
        print(f"  [step2] top movers error: {e}")
        data["top_movers"] = "N/A"

    # Sector performance (crucial for sector accuracy evaluation)
    print("  [step2] fetching sector performance...")
    try:
        text, source_ids = search_text_with_sources(
            f"performa sektor IHSG hari ini {date_id} sektor naik turun terbesar",
            days=1,
            category="sector_performance",
            limit_chars=600,
        )
        data["sector_performance"] = text
        data["evidence_ids"].extend(source_ids)
    except Exception as e:
        print(f"  [step2] sector performance error: {e}")
        data["sector_performance"] = "N/A"

    # Foreign flow
    print("  [step2] fetching foreign flow...")
    try:
        ff_raw, source_ids = search_text_with_sources(
            f"asing net buy sell IHSG investor asing {date_id}",
            days=1,
            category="foreign_flow",
            limit_chars=500,
        )
        data["foreign_flow_raw"] = ff_raw[:500]
        data["evidence_ids"].extend(source_ids)
        t = ff_raw.lower()
        if "net buy" in t or "beli asing" in t:
            data["foreign_flow_signal"] = "Accumulation"
        elif "net sell" in t or "jual asing" in t:
            data["foreign_flow_signal"] = "Distribution"
        else:
            data["foreign_flow_signal"] = "Stagnant/Sideways"
    except Exception as e:
        print(f"  [step2] foreign flow error: {e}")
        data["foreign_flow_signal"] = "Unknown"
        data["foreign_flow_raw"]    = "N/A"

    return data


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Search unexpected news
# ═══════════════════════════════════════════════════════════════════════════════

def collect_unexpected_news(date: str, date_id: str) -> str:
    """Run 5 targeted Tavily queries for surprise events."""
    print("  [step3] searching unexpected news...")
    queries = {
        "IHSG Movement Cause":  f"berita utama IHSG {date_id} penyebab pergerakan sentimen",
        "BI Policy Surprise":   f"kebijakan Bank Indonesia mendadak {date_id}",
        "Labor / Demo":         f"demo buruh unjuk rasa ekonomi industri {date_id}",
        "Global Market Shock":  f"global market shock crash rally {date} surprise",
        "Geopolitics Surprise": f"geopolitik berita mendadak Asia pasar modal {date_id}",
    }
    results = search_multiple(queries, days=1)
    combined = ""
    for category, text in results.items():
        combined += f"\n### {category}:\n{text[:400]}\n"
    return combined


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS & NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def _number(value, default: float = 0.0) -> float:
    """Return a safe numeric value when an LLM/API field is absent or malformed."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _boolean(value) -> bool:
    """Only accept real booleans; JSON strings such as 'false' are not truthy."""
    return value is True


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _accuracy_from_analysis(analysis: dict) -> int:
    ev = analysis.get("step4_evaluation", {})
    ev = ev if isinstance(ev, dict) else {}
    correct = 0
    total   = 0

    for key in ["ihsg_correct", "foreign_flow_correct"]:
        val = ev.get(key)
        if isinstance(val, bool):
            correct += int(val)
            total   += 1

    # Only count sectors where LLM had actual data (true/false), skip null
    sector_accuracy = ev.get("sector_accuracy", {})
    sector_accuracy = sector_accuracy if isinstance(sector_accuracy, dict) else {}
    for val in sector_accuracy.values():
        if isinstance(val, bool):
            correct += int(val)
            total   += 1

    return int(correct / total * 100) if total > 0 else 0


def _normalize_and_enrich_analysis(
    analysis: dict,
    pred: MarketPrediction,
    actual: dict,
    date_id: str
) -> dict:
    """
    Normalizes arbitrary LLM keys and guarantees substantive RCA, lessons,
    and summary via deterministic ground-truth synthesis if LLM outputs are empty or missing.
    Ensures Telegram and notes never receive empty evaluation sections.
    """
    if not isinstance(analysis, dict):
        analysis = {}

    # 1. Resolve step 4 evaluation
    ev = (
        analysis.get("step4_evaluation")
        or analysis.get("evaluation")
        or analysis.get("step4")
        or analysis.get("step_4")
        or analysis.get("eval")
        or {}
    )
    if not isinstance(ev, dict):
        ev = {}

    ihsg_actual = str(ev.get("ihsg_actual") or actual.get("ihsg_signal") or "Unknown")
    ihsg_actual_pct = _number(ev.get("ihsg_actual_pct", actual.get("ihsg_change_pct", 0.0)))

    # Determine ihsg_correct
    raw_ihsg_correct = ev.get("ihsg_correct")
    if isinstance(raw_ihsg_correct, bool):
        ihsg_correct = raw_ihsg_correct
    else:
        pred_sig = (pred.ihsg_signal or "").strip().lower()
        act_sig = ihsg_actual.strip().lower()
        if pred_sig in ["bullish", "green"] and (act_sig in ["bullish", "green"] or ihsg_actual_pct > 0):
            ihsg_correct = True
        elif pred_sig in ["bearish", "red"] and (act_sig in ["bearish", "red"] or ihsg_actual_pct < 0):
            ihsg_correct = True
        elif pred_sig in ["sideways", "stagnant"] and (act_sig in ["sideways", "stagnant"] or abs(ihsg_actual_pct) < 0.2):
            ihsg_correct = True
        else:
            ihsg_correct = False

    ff_actual = str(ev.get("foreign_flow_actual") or actual.get("foreign_flow_signal") or "Unknown")
    raw_ff_correct = ev.get("foreign_flow_correct")
    if isinstance(raw_ff_correct, bool):
        ff_correct = raw_ff_correct
    else:
        pred_ff = (pred.foreign_flow_signal or "").strip().lower()
        act_ff = ff_actual.strip().lower()
        ff_correct = (pred_ff == act_ff) and (pred_ff not in ["unknown", "n/a", ""])

    sector_accuracy = ev.get("sector_accuracy") or analysis.get("sector_accuracy") or {}
    if not isinstance(sector_accuracy, dict):
        sector_accuracy = {}

    # 2. Resolve step 5 RCA
    rca = (
        analysis.get("step5_rca")
        or analysis.get("rca")
        or analysis.get("step5")
        or analysis.get("step_5")
        or analysis.get("root_cause_analysis")
        or {}
    )
    if isinstance(rca, list):
        rca_dict = {"unanticipated_factors": [str(x) for x in rca if x]}
    elif isinstance(rca, dict):
        rca_dict = rca
    else:
        rca_dict = {}

    unanticipated = _string_list(
        rca_dict.get("unanticipated_factors")
        or rca_dict.get("unanticipated")
        or rca_dict.get("unexpected")
        or rca_dict.get("surprise")
        or analysis.get("unanticipated_factors")
    )
    overestimated = _string_list(
        rca_dict.get("overestimated_factors")
        or rca_dict.get("overestimated")
        or analysis.get("overestimated_factors")
    )
    underestimated = _string_list(
        rca_dict.get("underestimated_factors")
        or rca_dict.get("underestimated")
        or analysis.get("underestimated_factors")
    )
    info_delay = _string_list(
        rca_dict.get("information_delay_factors")
        or rca_dict.get("information_delay")
        or rca_dict.get("info_delay")
        or analysis.get("information_delay_factors")
    )
    inverse_correlation = _string_list(
        rca_dict.get("inverse_correlation_cases")
        or rca_dict.get("inverse_correlation")
        or rca_dict.get("inverse")
        or analysis.get("inverse_correlation_cases")
    )

    # 3. Resolve step 6 lessons
    lessons_raw = (
        analysis.get("step6_lessons")
        or analysis.get("lessons")
        or analysis.get("lesson")
        or analysis.get("learning")
        or analysis.get("step6")
        or analysis.get("step_6")
    )
    if isinstance(lessons_raw, str):
        lessons = [lessons_raw.strip()] if lessons_raw.strip() else []
    else:
        lessons = _string_list(lessons_raw)

    # 4. Resolve summary
    summary_raw = (
        analysis.get("summary_sentence")
        or analysis.get("summary")
        or analysis.get("overview")
        or analysis.get("conclusion")
        or ""
    )
    summary = str(summary_raw).strip() if summary_raw else ""

    # 5. DETERMINISTIC SYNTHESIS: Guarantee non-empty RCA, lessons, and summary
    has_rca = bool(unanticipated or overestimated or underestimated or info_delay or inverse_correlation)
    if not has_rca:
        pred_signal = pred.ihsg_signal or "Unknown"
        act_signal = ihsg_actual if ihsg_actual != "Unknown" else ("Bearish" if ihsg_actual_pct < 0 else "Bullish")
        if not ihsg_correct:
            if "bull" in pred_signal.lower() and "bear" in act_signal.lower():
                overestimated.append(
                    f"Optimisme pembukaan pasar IHSG tertekan aksi jual intraday (IHSG ditutup {act_signal} {ihsg_actual_pct:+.2f}%) berlawanan dengan ekspektasi {pred_signal}."
                )
            elif "bear" in pred_signal.lower() and "bull" in act_signal.lower():
                underestimated.append(
                    f"Kekuatan beli dan ketahanan IHSG melampaui estimasi (IHSG ditutup {act_signal} {ihsg_actual_pct:+.2f}%) berbanding proyeksi {pred_signal}."
                )
            else:
                unanticipated.append(
                    f"Arah pergerakan indeks IHSG ({act_signal} {ihsg_actual_pct:+.2f}%) mengalami deviasi dari proyeksi pagi ({pred_signal})."
                )
        if not ff_correct and ff_actual != "Unknown":
            unanticipated.append(
                f"Realisasi foreign flow tercatat {ff_actual} berbanding proyeksi pagi {pred.foreign_flow_signal}."
            )

        # Check for sharp commodity movements in actuals
        for c_name, c_data in actual.get("commodities", {}).items():
            if isinstance(c_data, dict):
                chg = _number(c_data.get("change_pct"))
                if abs(chg) >= 1.0:
                    unanticipated.append(
                        f"Pergerakan komoditas {c_name} ({chg:+.2f}%) mempengaruhi sentimen sektoral terkait."
                    )
                    break

        # Fallback if still empty
        if not (unanticipated or overestimated or underestimated or info_delay or inverse_correlation):
            unanticipated.append(
                f"Volatilitas pasar intraday membawa IHSG ditutup {act_signal} {ihsg_actual_pct:+.2f}% dengan foreign flow {ff_actual}."
            )

    if not lessons:
        act_sig = ihsg_actual if ihsg_actual != "Unknown" else ("Bearish" if ihsg_actual_pct < 0 else "Bullish")
        lessons.append(
            f"Ketika proyeksi pagi mengantisipasi IHSG {pred.ihsg_signal} (confidence {pred.ihsg_confidence}%), tetapi sentimen pasar berbalik dan IHSG ditutup {act_sig} {ihsg_actual_pct:+.2f}% (foreign flow {ff_actual}), maka perlu memperketat stop-loss sektoral dan mengevaluasi dinamika arus dana asing secara real-time."
        )

    if not summary:
        act_sig = ihsg_actual if ihsg_actual != "Unknown" else ("Bearish" if ihsg_actual_pct < 0 else "Bullish")
        summary = (
            f"IHSG ditutup {act_sig} {ihsg_actual_pct:+.2f}% (prediksi {pred.ihsg_signal}); "
            f"foreign flow tercatat {ff_actual} (prediksi {pred.foreign_flow_signal})."
        )

    return {
        "step4_evaluation": {
            "ihsg_correct": ihsg_correct,
            "ihsg_predicted": pred.ihsg_signal,
            "ihsg_actual": ihsg_actual,
            "ihsg_actual_pct": ihsg_actual_pct,
            "foreign_flow_correct": ff_correct,
            "foreign_flow_predicted": pred.foreign_flow_signal,
            "foreign_flow_actual": ff_actual,
            "sector_accuracy": sector_accuracy,
        },
        "step5_rca": {
            "unanticipated_factors": unanticipated,
            "overestimated_factors": overestimated,
            "underestimated_factors": underestimated,
            "information_delay_factors": info_delay,
            "inverse_correlation_cases": inverse_correlation,
        },
        "step6_lessons": lessons,
        "summary_sentence": summary,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4-6 — LLM: Evaluate, Root Cause Analysis, Generate Lessons
# ═══════════════════════════════════════════════════════════════════════════════

def run_llm_analysis(
    pred: MarketPrediction,
    actual: dict,
    news: str,
    morning_brief: str,
    date: str,
    date_id: str
) -> dict:
    """
    Single LLM call that performs:
    - Step 4: Quantitative accuracy evaluation
    - Step 5: Root Cause Analysis for misses
    - Step 6: Lesson generation
    Returns structured dict.
    """
    print("  [step4-6] running LLM evaluation...")

    # Build commodity summary string for prompt
    commodity_str = ""
    for name, val in actual.get("commodities", {}).items():
        if isinstance(val, dict) and "change_pct" in val:
            commodity_str += f"  - {name}: {val['change_pct']:+.2f}% (actual)\n"
        elif isinstance(val, dict) and "raw" in val:
            commodity_str += f"  - {name}: {val['raw'][:100]}\n"

    volume = actual.get("ihsg_volume")
    volume_str = f"{volume:,}" if isinstance(volume, (int, float)) else "N/A"

    prompt = f"""You are a quantitative analyst performing a post-market evaluation of a morning brief prediction.
Date: {date} ({date_id})

═══ MORNING PREDICTIONS ═══
IHSG Signal: {pred.ihsg_signal} (confidence: {pred.ihsg_confidence}%)
Foreign Flow: {pred.foreign_flow_signal} ({pred.foreign_flow_net})
Bullish Sectors: {', '.join(pred.sector_bullish) or 'None'}
Bearish Sectors: {', '.join(pred.sector_bearish) or 'None'}
Neutral Sectors:  {', '.join(pred.sector_neutral) or 'None'}
Commodity Signals: {json.dumps(pred.commodities_predicted)}
Key Risk Flagged: {pred.key_risk}
Tickers Mentioned: {', '.join(pred.recommended_tickers[:15])}

═══ ACTUAL RESULTS ═══
IHSG Close: {actual.get('ihsg_close', 'N/A')} ({actual.get('ihsg_change_pct', 0):+.2f}%, {actual.get('ihsg_change_pts', 0):+.1f} pts)
IHSG Open/High/Low: {actual.get('ihsg_open','?')} / {actual.get('ihsg_high','?')} / {actual.get('ihsg_low','?')}
IHSG Volume: {volume_str}
IHSG Signal: {actual.get('ihsg_signal', 'Unknown')}
USD/IDR: {actual.get('usdidr', 'N/A')} ({actual.get('usdidr_change_pct', 0):+.3f}%) — Rupiah {actual.get('rupiah_signal', '?')}
Foreign Flow Actual: {actual.get('foreign_flow_signal', 'Unknown')}
Foreign Flow Data: {actual.get('foreign_flow_raw', '')[:300]}
Commodity Actuals:
{commodity_str}
Top Movers:
{actual.get('top_movers', 'N/A')}

Sector Performance:
{actual.get('sector_performance', 'N/A')}

═══ TODAY'S UNEXPECTED NEWS ═══
{news[:1500]}

═══ MORNING BRIEF EXCERPT ═══
{morning_brief[:800]}

═══ TASK ═══
Perform the following analysis and return ONLY a valid JSON object (no markdown, no preamble):

{{
  "step4_evaluation": {{
    "ihsg_correct": true/false,
    "ihsg_predicted": "{pred.ihsg_signal}",
    "ihsg_actual": "{actual.get('ihsg_signal', '?')}",
    "ihsg_actual_pct": {actual.get('ihsg_change_pct', 0)},
    "foreign_flow_correct": true/false,
    "foreign_flow_predicted": "{pred.foreign_flow_signal}",
    "foreign_flow_actual": "{actual.get('foreign_flow_signal', '?')}",
    "sector_accuracy": {{
      "SectorName": true/false/null
    }}
  }},
  "step5_rca": {{
    "unanticipated_factors": ["factor that happened but wasn't in brief"],
    "overestimated_factors": ["factor brief thought was important but had small actual impact"],
    "underestimated_factors": ["factor brief dismissed but had big actual impact"],
    "information_delay_factors": ["news that only appeared after 08:30 so brief couldn't catch it"],
    "inverse_correlation_cases": ["brief assumed X causes Y but today X happened and Z happened instead — explain why"]
  }},
  "step6_lessons": [
    "Ketika [morning condition], tetapi [unexpected factor] terjadi, maka [actual market impact with numbers].",
    "Ketika [morning condition], tetapi [unexpected factor] terjadi, maka [actual market impact with numbers]."
  ],
  "summary_sentence": "One-sentence summary of what happened vs what was predicted."
}}

CRITICAL RULES:
- sector_accuracy: use true/false ONLY if you have actual sector data from "Sector Performance" or "Top Movers". If data insufficient to verify, use null — DO NOT guess.
- Do NOT include ticker_accuracy — it causes scoring errors when data is unavailable.
- error_rate_pct is calculated by the system, not by you — do not include it.
- lessons must follow exactly: "Ketika [kondisi pagi], tetapi [faktor tak terduga] terjadi, maka [dampak dengan angka]."
- Be specific with numbers (e.g. "IHSG turun 3.35%" not "IHSG fell").
"""

    try:
        response = llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = get_content(response)
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            raw = match.group(0)
        analysis = json.loads(raw)
        if not isinstance(analysis, dict):
            raise ValueError("LLM evaluation must be a JSON object")
        return _normalize_and_enrich_analysis(analysis, pred, actual, date_id)
    except Exception as e:
        print(f"  [step4-6] [WARN] LLM evaluation attempt 1 failed: {e}. Retrying with fallback...")
        try:
            retry_prompt = prompt + "\n\nCRITICAL: Provide non-empty step5_rca and step6_lessons in JSON format."
            retry_resp = llm_chat(
                messages=[{"role": "user", "content": retry_prompt}],
                max_tokens=8192,
                temperature=0.2,
            )
            raw2 = get_content(retry_resp)
            match2 = re.search(r'\{[\s\S]*\}', raw2)
            if match2:
                raw2 = match2.group(0)
            analysis2 = json.loads(raw2)
            if isinstance(analysis2, dict):
                return _normalize_and_enrich_analysis(analysis2, pred, actual, date_id)
        except Exception as retry_err:
            print(f"  [step4-6] [WARN] LLM retry also failed: {retry_err}. Using deterministic ground-truth synthesis.")

        return _normalize_and_enrich_analysis({}, pred, actual, date_id)




# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_evening_review(date_key: str = None) -> dict | None:
    """
    Full 7-step evening review pipeline.
    Returns learning dict, or None if morning brief not found.
    """
    now = jakarta_now()
    if not date_key:
        from scheduler import resolve_evening_review_date
        date_key = resolve_evening_review_date()

    try:
        target_dt = datetime.strptime(date_key, "%Y-%m-%d")
        date_str  = target_dt.strftime("%B %d, %Y")
        date_id   = target_dt.strftime("%d %B %Y")
    except Exception:
        date_str = now.strftime("%B %d, %Y")
        date_id  = now.strftime("%d %B %Y")

    print(f"\n{'='*60}")
    print(f"[evening_reviewer] Starting review for session {date_key} at {now.strftime('%H:%M WIB')}")
    print(f"{'='*60}")

    # ── Step 1: Load morning brief ──────────────────────────────
    pred, morning_brief = load_morning_brief(date_key)
    if pred is None:
        return None

    # ── Step 2: Collect actuals ─────────────────────────────────
    print("\n[Step 2] Collecting actual market data...")
    actual = collect_actual_data(date_id, target_date=date_key)
    try:
        save_json_artifact(date_key, "evening_actuals.json", actual)
    except Exception as e:
        print(f"  [evening_reviewer] actuals artifact save failed: {e}")

    # ── Step 3: Unexpected news ─────────────────────────────────
    print("\n[Step 3] Searching unexpected news...")
    news = collect_unexpected_news(date_str, date_id)

    # ── Steps 4-6: LLM evaluation ───────────────────────────────
    print("\n[Step 4-6] Running LLM evaluation + RCA + lesson generation...")
    analysis = run_llm_analysis(pred, actual, news, morning_brief, date_str, date_id)

    # ── Step 7: Compute accuracy + save ─────────────────────────
    print("\n[Step 7] Saving learning and updating performance stats...")
    accuracy = _accuracy_from_analysis(analysis)
    ev = analysis.get("step4_evaluation", {})
    ev = ev if isinstance(ev, dict) else {}

    rca = analysis.get("step5_rca", {})
    rca = rca if isinstance(rca, dict) else {}
    sector_accuracy = ev.get("sector_accuracy", {})
    sector_accuracy = sector_accuracy if isinstance(sector_accuracy, dict) else {}

    learning = {
        "date":                    date_key,
        "ihsg_predicted":          pred.ihsg_signal,
        "ihsg_confidence":         pred.ihsg_confidence,
        "ihsg_actual":             ev.get("ihsg_actual", actual.get("ihsg_signal", "?")),
        "ihsg_actual_pct":         _number(ev.get("ihsg_actual_pct", actual.get("ihsg_change_pct", 0))),
        "ihsg_correct":            _boolean(ev.get("ihsg_correct")),
        "foreign_flow_predicted":  pred.foreign_flow_signal,
        "foreign_flow_actual":     ev.get("foreign_flow_actual", actual.get("foreign_flow_signal", "?")),
        "foreign_flow_correct":    _boolean(ev.get("foreign_flow_correct")),
        "sector_accuracy":         sector_accuracy,
        "error_rate_pct":          100 - accuracy,
        "accuracy_score":          accuracy,
        "rca_unanticipated":       _string_list(rca.get("unanticipated_factors")),
        "rca_overestimated":       _string_list(rca.get("overestimated_factors")),
        "rca_underestimated":      _string_list(rca.get("underestimated_factors")),
        "rca_info_delay":          _string_list(rca.get("information_delay_factors")),
        "rca_inverse_correlation": _string_list(rca.get("inverse_correlation_cases")),
        "lessons":                 _string_list(analysis.get("step6_lessons")),
        "summary":                 analysis.get("summary_sentence", "") if isinstance(analysis.get("summary_sentence", ""), str) else "",
        "actual_usdidr":           actual.get("usdidr", "N/A"),
        "actual_commodities":      {k: v for k, v in actual.get("commodities", {}).items()},
    }

    # Save structured learning note
    save_learning(date_key, learning)
    try:
        save_json_artifact(date_key, "evening_review.json", learning)
    except Exception as e:
        print(f"  [evening_reviewer] review artifact save failed: {e}")

    # Update rolling performance stats
    update_performance_stats(learning)

    # Print summary
    print(f"\n{'─'*50}")
    print(f"  IHSG: {pred.ihsg_signal} → {learning['ihsg_actual']} ({learning['ihsg_actual_pct']:+.2f}%) {'✅' if learning['ihsg_correct'] else '❌'}")
    print(f"  Foreign Flow: {pred.foreign_flow_signal} → {learning['foreign_flow_actual']} {'✅' if learning['foreign_flow_correct'] else '❌'}")
    print(f"  Accuracy: {accuracy}% | Error Rate: {learning['error_rate_pct']}%")
    if learning["lessons"]:
        print(f"  Lessons learned: {len(learning['lessons'])}")
    print(f"{'─'*50}")

    return learning
