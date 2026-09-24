"""
Evening Reviewer — runs at 19:00 WIB weekdays.
Full 7-step post-market evaluation and learning pipeline.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from llm_client import llm_chat
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

def collect_actual_data(date_id: str) -> dict:
    """Fetch IHSG, commodities, rupiah, top movers from yfinance + web search."""
    data = {}
    data["evidence_ids"] = []

    # IHSG
    print("  [step2] fetching IHSG actual...")
    try:
        data.update(fetch_ihsg_snapshot())
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
            max_tokens=1500,
            temperature=0.1,
        )
        raw = response.choices[0].message.content
        # Extract everything inside the outermost { } to ignore markdown/intro text
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            raw = match.group(0)
        analysis = json.loads(raw)
        if not isinstance(analysis, dict):
            raise ValueError("LLM evaluation must be a JSON object")
        return analysis
    except Exception as e:
        print(f"  [step4-6] LLM failed: {e}")
        return {
            "step4_evaluation": {
                "ihsg_correct": actual.get("ihsg_signal") == pred.ihsg_signal,
                "ihsg_predicted": pred.ihsg_signal,
                "ihsg_actual": actual.get("ihsg_signal", "Unknown"),
                "ihsg_actual_pct": actual.get("ihsg_change_pct", 0),
                "foreign_flow_correct": actual.get("foreign_flow_signal") == pred.foreign_flow_signal,
            },
            "step5_rca": {
                "unanticipated_factors": [],
                "overestimated_factors": [],
                "underestimated_factors": [],
                "information_delay_factors": [],
                "inverse_correlation_cases": []
            },
            "step6_lessons": [],
            "summary_sentence": "Evaluation unavailable due to LLM error."
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Update performance stats
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_evening_review() -> dict | None:
    """
    Full 7-step evening review pipeline.
    Returns learning dict, or None if morning brief not found.
    """
    now      = jakarta_now()
    date_key = now.strftime("%Y-%m-%d")
    date_str = now.strftime("%B %d, %Y")
    date_id  = now.strftime("%d %B %Y")

    print(f"\n{'='*60}")
    print(f"[evening_reviewer] Starting review for {date_key} at {now.strftime('%H:%M')}")
    print(f"{'='*60}")

    # ── Step 1: Load morning brief ──────────────────────────────
    pred, morning_brief = load_morning_brief(date_key)
    if pred is None:
        return None

    # ── Step 2: Collect actuals ─────────────────────────────────
    print("\n[Step 2] Collecting actual market data...")
    actual = collect_actual_data(date_id)
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
