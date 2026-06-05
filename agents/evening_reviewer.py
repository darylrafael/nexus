"""
Evening Reviewer — runs at 19:00 WIB weekdays.
Full 7-step post-market evaluation and learning pipeline.
"""
import json
import re
import yfinance as yf
from datetime import datetime
from openai import OpenAI
from dataclasses import asdict

from agents.web_agent import search_web, search_multiple
from agents.prediction_extractor import extract_predictions, MarketPrediction
from memory.obsidian import read_note, write_note
from memory.learning_store import save_learning, load_recent_learnings, update_performance_stats
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Read morning brief from Obsidian
# ═══════════════════════════════════════════════════════════════════════════════

def load_morning_brief(date_key: str) -> tuple:
    """
    Read morning brief note from Obsidian.
    Returns (MarketPrediction, raw_brief_text) or (None, None) if not found.
    """
    note_title = f"{date_key} - IHSG Market Brief"
    raw = read_note(note_title)
    if not raw or len(raw.strip()) < 100:
        print(f"  [step1] ❌ Morning brief not found for {date_key}. Stopping.")
        return None, None
    pred = extract_predictions(raw, date_key)
    print(f"  [step1] ✅ Brief loaded. IHSG pred={pred.ihsg_signal} ({pred.ihsg_confidence}%)")
    return pred, raw


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Collect actual market data
# ═══════════════════════════════════════════════════════════════════════════════

def collect_actual_data(date_id: str) -> dict:
    """Fetch IHSG, commodities, rupiah, top movers from yfinance + web search."""
    data = {}

    # IHSG
    print("  [step2] fetching IHSG actual...")
    try:
        ihsg = yf.Ticker("^JKSE")
        hist = ihsg.history(period="2d")
        if len(hist) >= 2:
            close = hist.iloc[-1]["Close"]
            prev  = hist.iloc[-2]["Close"]
            pct   = (close - prev) / prev * 100
            pts   = close - prev
            data["ihsg_close"]    = round(close, 2)
            data["ihsg_prev"]     = round(prev, 2)
            data["ihsg_change_pct"] = round(pct, 2)
            data["ihsg_change_pts"] = round(pts, 2)
            data["ihsg_signal"]   = "Bullish" if pct > 0.2 else ("Bearish" if pct < -0.2 else "Neutral")
            data["ihsg_open"]     = round(hist.iloc[-1]["Open"], 2)
            data["ihsg_high"]     = round(hist.iloc[-1]["High"], 2)
            data["ihsg_low"]      = round(hist.iloc[-1]["Low"], 2)
            data["ihsg_volume"]   = int(hist.iloc[-1]["Volume"])
        else:
            data["ihsg_signal"] = "Unknown"
    except Exception as e:
        print(f"  [step2] IHSG error: {e}")
        data["ihsg_signal"] = "Unknown"

    # Rupiah (USD/IDR)
    print("  [step2] fetching USD/IDR...")
    try:
        idr = yf.Ticker("USDIDR=X")
        fi  = idr.fast_info
        rate = fi.last_price
        prev_rate = fi.previous_close
        pct_idr = (rate - prev_rate) / prev_rate * 100 if prev_rate else 0
        data["usdidr"]         = round(rate, 0)
        data["usdidr_change_pct"] = round(pct_idr, 3)
        data["rupiah_signal"]  = "Weakened" if pct_idr > 0 else "Strengthened"
    except Exception as e:
        print(f"  [step2] USD/IDR error: {e}")
        data["usdidr"] = "N/A"

    # Commodities via yfinance
    print("  [step2] fetching commodity prices...")
    commodity_tickers = {
        "Crude Oil (WTI)": "CL=F",
        "Natural Gas":     "NG=F",
        "Brent Crude":     "BZ=F",
    }
    data["commodities"] = {}
    for name, ticker in commodity_tickers.items():
        try:
            t     = yf.Ticker(ticker)
            price = t.fast_info.last_price
            prev  = t.fast_info.previous_close
            pct   = (price - prev) / prev * 100 if prev else 0
            data["commodities"][name] = {
                "price": round(price, 2),
                "change_pct": round(pct, 2),
                "signal": "Up" if pct > 0 else "Down"
            }
        except:
            data["commodities"][name] = {"price": "N/A", "change_pct": 0, "signal": "Unknown"}

    # Coal, CPO, Nickel — web search (no free yfinance ticker)
    print("  [step2] fetching Coal/CPO/Nickel via web...")
    for name, query in {
        "Coal (Newcastle)": f"harga batu bara Newcastle hari ini {date_id}",
        "CPO":               f"harga CPO crude palm oil hari ini {date_id}",
        "Nickel (LME)":      f"harga nikel LME hari ini {date_id}",
    }.items():
        try:
            result = search_web(query, days=1)
            data["commodities"][name] = {"raw": result[:200]}
        except:
            data["commodities"][name] = {"raw": "N/A"}

    # Top gainers / losers
    print("  [step2] fetching top movers...")
    try:
        data["top_movers"] = search_web(
            f"saham naik turun terbesar IHSG top gainer loser {date_id}", days=1
        )[:600]
    except:
        data["top_movers"] = "N/A"

    # Sector performance (crucial for sector accuracy evaluation)
    print("  [step2] fetching sector performance...")
    try:
        data["sector_performance"] = search_web(
            f"performa sektor IHSG hari ini {date_id} sektor naik turun terbesar", days=1
        )[:600]
    except:
        data["sector_performance"] = "N/A"

    # Foreign flow
    print("  [step2] fetching foreign flow...")
    try:
        ff_raw = search_web(f"asing net buy sell IHSG investor asing {date_id}", days=1)
        data["foreign_flow_raw"] = ff_raw[:500]
        t = ff_raw.lower()
        if "net buy" in t or "beli asing" in t:
            data["foreign_flow_signal"] = "Accumulation"
        elif "net sell" in t or "jual asing" in t:
            data["foreign_flow_signal"] = "Distribution"
        else:
            data["foreign_flow_signal"] = "Stagnant/Sideways"
    except:
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
IHSG Volume: {actual.get('ihsg_volume', 'N/A'):,}
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
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.1
        )
        raw = response.choices[0].message.content
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  [step4-6] LLM failed: {e}")
        return {
            "step4_evaluation": {
                "ihsg_correct": actual.get("ihsg_signal") == pred.ihsg_signal,
                "ihsg_predicted": pred.ihsg_signal,
                "ihsg_actual": actual.get("ihsg_signal", "Unknown"),
                "ihsg_actual_pct": actual.get("ihsg_change_pct", 0),
                "foreign_flow_correct": actual.get("foreign_flow_signal") == pred.foreign_flow_signal,
                "error_rate_pct": 50
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
    correct = 0
    total   = 0

    for key in ["ihsg_correct", "foreign_flow_correct"]:
        val = ev.get(key)
        if isinstance(val, bool):
            correct += int(val)
            total   += 1

    # Only count sectors where LLM had actual data (true/false), skip null
    for val in ev.get("sector_accuracy", {}).values():
        if isinstance(val, bool):
            correct += int(val)
            total   += 1

    return int(correct / total * 100) if total > 0 else 0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_evening_review() -> dict | None:
    """
    Full 7-step evening review pipeline.
    Returns learning dict, or None if morning brief not found.
    """
    now      = datetime.now()
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

    learning = {
        "date":                    date_key,
        "ihsg_predicted":          pred.ihsg_signal,
        "ihsg_confidence":         pred.ihsg_confidence,
        "ihsg_actual":             ev.get("ihsg_actual", actual.get("ihsg_signal", "?")),
        "ihsg_actual_pct":         ev.get("ihsg_actual_pct", actual.get("ihsg_change_pct", 0)),
        "ihsg_correct":            ev.get("ihsg_correct", False),
        "foreign_flow_predicted":  pred.foreign_flow_signal,
        "foreign_flow_actual":     ev.get("foreign_flow_actual", actual.get("foreign_flow_signal", "?")),
        "foreign_flow_correct":    ev.get("foreign_flow_correct", False),
        "sector_accuracy":         ev.get("sector_accuracy", {}),
        "ticker_accuracy":         ev.get("ticker_accuracy", {}),
        "error_rate_pct":          ev.get("error_rate_pct", 100 - accuracy),
        "accuracy_score":          accuracy,
        "rca_unanticipated":       analysis.get("step5_rca", {}).get("unanticipated_factors", []),
        "rca_overestimated":       analysis.get("step5_rca", {}).get("overestimated_factors", []),
        "rca_underestimated":      analysis.get("step5_rca", {}).get("underestimated_factors", []),
        "rca_info_delay":          analysis.get("step5_rca", {}).get("information_delay_factors", []),
        "rca_inverse_correlation": analysis.get("step5_rca", {}).get("inverse_correlation_cases", []),
        "lessons":                 analysis.get("step6_lessons", []),
        "summary":                 analysis.get("summary_sentence", ""),
        "actual_usdidr":           actual.get("usdidr", "N/A"),
        "actual_commodities":      {k: v for k, v in actual.get("commodities", {}).items()},
    }

    # Save structured learning note
    save_learning(date_key, learning)

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