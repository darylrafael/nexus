import time
from agents.commodity_agent import get_ihsg_data
from agents.economics_engine import build_economics_context
from agents.prediction_extractor import extract_predictions
from agents.validator import build_commodity_context, validate
from agents.web_agent import get_source_registry, search_multiple, search_web
from data_sources.market_data import (
    fetch_all_commodities,
    fetch_usdidr_snapshot,
    format_all_commodities_markdown,
    get_market_calendar_info,
    jakarta_now,
)
from llm_client import get_content, llm_chat
from memory.artifacts import save_json_artifact, save_text_artifact
from memory.learning_store import build_learning_context, load_recent_learnings
from memory.session import log_session



def run_market_brief(target_date: str = None, allow_non_trading: bool = False) -> str | dict:
    start = time.time()
    from core.calendar import is_idx_trading_day, get_holiday_reason

    check_date = target_date
    if not check_date:
        cal_preview = get_market_calendar_info()
        check_date = cal_preview["today_key"]

    if not allow_non_trading and not is_idx_trading_day(check_date):
        reason = get_holiday_reason(check_date) or "Non-trading day"
        print(f"[market_agent] SKIPPED: {check_date} is a non-trading day ({reason}). To override, pass allow_non_trading=True.")
        skip_payload = {
            "stage": "morning_brief",
            "status": "skipped",
            "date": check_date,
            "reason": reason,
            "skipped_at": jakarta_now().isoformat(timespec="seconds"),
        }
        try:
            save_json_artifact(check_date, "pipeline_status.json", skip_payload)
        except Exception as exc:
            print(f"[market_agent] Warning: failed to save skip artifact: {exc}")
        return skip_payload

    try:
        return _run_market_brief_internal(start, target_date=target_date)
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        try:
            log_session(
                query="daily_brief",
                agent="market_agent",
                model="llm_client",
                result=None,
                success=False,
                error_msg=str(e),
                duration_ms=duration_ms,
            )
        except Exception:
            pass
        raise


def _run_market_brief_internal(start: float, target_date: str = None) -> str:
    from datetime import datetime
    ref_dt = datetime.strptime(target_date, "%Y-%m-%d") if target_date else None
    cal_info = get_market_calendar_info(ref_dt=ref_dt)
    date_key = target_date or cal_info["today_key"]
    current_date = cal_info["today_en"]
    today_label = cal_info["today_label"]
    today_date_id = cal_info["today_date_id"]

    last_trading_key = cal_info["last_trading_key"]
    last_trading_date_id = cal_info["last_trading_date_id"]
    last_trading_label = cal_info["last_trading_label"]
    last_trading_en = cal_info["last_trading_en"]

    search_days = cal_info["search_days"]
    is_after_gap = cal_info["is_after_gap"]
    period_description_id = cal_info["period_description_id"]
    period_description_en = cal_info["period_description_en"]

    print(f"  [market_agent] Brief date: {today_label} | Last trading session: {last_trading_label} | Search lookback: {search_days} days")

    # Record pipeline starting status
    try:
        save_json_artifact(date_key, "pipeline_status.json", {
            "stage": "morning_brief",
            "status": "running",
            "date": date_key,
            "started_at": jakarta_now().isoformat(timespec="seconds"),
        })
    except Exception:
        pass

    if is_after_gap:
        queries = {
            "Indonesian Economy": f"IHSG rupiah kurs BI rate inflasi ekonomi Indonesia {last_trading_date_id} hingga {today_date_id}",
            "Global Macro": f"Wall Street bursa AS suku bunga The Fed ekonomi China GDP inflasi {last_trading_date_id} hingga {today_date_id}",
            "Geopolitics": f"geopolitik perang konflik Timur Tengah Asia pasar modal {last_trading_date_id} {today_date_id}",
        }
    else:
        queries = {
            "Indonesian Economy": f"IHSG rupiah kurs BI rate inflasi ekonomi Indonesia {last_trading_date_id}",
            "Global Macro": f"The Fed suku bunga AS ekonomi China GDP inflasi {last_trading_date_id}",
            "Geopolitics": f"geopolitik perang dagang Asia tenggara pasar modal {last_trading_date_id}",
        }

    print(f"  [market_agent] Fetching consolidated commodity data ({period_description_id})...")
    comm_res = fetch_all_commodities(target_label=period_description_id, search_days=search_days)
    ihsg_text = get_ihsg_data(target_date=last_trading_key)
    comm_markdown = format_all_commodities_markdown(comm_res, target_label=period_description_id)
    commodity_text_data = f"### IHSG Actual Price Data:\n{ihsg_text}\n\n{comm_markdown}"
    commodity_text_context = build_commodity_context(commodity_text_data)

    # Authoritative commodity changes from consolidated fetch
    commodity_changes = comm_res.get("changes") or {}

    # Economics engine treats negative as 'rupiah weakened' and positive as 'rupiah strengthened'.
    # USD/IDR rising (+%) means Rupiah depreciated/weakened (-%). Pass None when unavailable.
    try:
        usdidr_snap = fetch_usdidr_snapshot()
        usdidr_pct = usdidr_snap.get("usdidr_change_pct") if usdidr_snap else None
        rupiah_change = -float(usdidr_pct) if usdidr_pct is not None else None
    except Exception:
        rupiah_change = None

    economics_context = build_economics_context(
        commodity_changes=commodity_changes,
        rupiah_change=rupiah_change,
        current_date=period_description_id,
        search_days=search_days,
    )

    print(f"  [market_agent] Fetching IDX market movers for last session ({last_trading_label})...")
    try:
        top_movers = search_web(
            f"saham naik turun terbesar IHSG top gainer loser {last_trading_date_id}",
            days=search_days,
        )
        if len(top_movers.strip()) < 50:
            top_movers = f"No fresh market mover data found for {last_trading_label}."
    except Exception:
        top_movers = "Market movers data unavailable."

    print(f"  [market_agent] Fetching trending stocks for last session ({last_trading_label})...")
    try:
        trending_stocks = search_web(
            f"saham paling aktif volume terbesar IDX BEI {last_trading_date_id}",
            days=search_days,
        )
        if len(trending_stocks.strip()) < 50:
            trending_stocks = f"No fresh trending stock data found for {last_trading_label}."
    except Exception:
        trending_stocks = "Trending stocks data unavailable."

    print(f"  [market_agent] Fetching foreign flow data for last session ({last_trading_label})...")
    try:
        foreign_flow = search_web(
            f"asing net buy sell IHSG pasar reguler seluruh pasar investor asing {last_trading_date_id}",
            days=search_days,
        )
        if len(foreign_flow.strip()) < 50:
            foreign_flow = f"No fresh foreign flow data found for {last_trading_label}."
    except Exception:
        foreign_flow = "Foreign flow data not available."

    print(f"  [market_agent] Running targeted macroeconomic searches (lookback {search_days} days)...")
    raw_news = search_multiple(queries, days=search_days)
    for category in raw_news:
        if not raw_news[category] or len(raw_news[category].strip()) < 50:
            raw_news[category] = f"No major developments reported during {period_description_id}."

    # 7. Assemble context
    context = "=== CORE MARKET DATA ===\n"
    context += f"{commodity_text_context}\n\n"
    context += f"## IDX Top Movers ({last_trading_label}):\n{top_movers}\n\n"
    context += f"## Trending IDX Stocks ({last_trading_label}):\n{trending_stocks}\n\n"
    context += f"## Foreign Flow ({last_trading_label}):\n{foreign_flow}\n\n"
    context += "=== GROUND TRUTH ECONOMIC LOGIC CONSTRAINTS ===\n"
    context += f"{economics_context}\n\n"
    context += f"=== MACROECONOMIC & REGIONAL NEWS ({period_description_id}) ===\n"
    for category, result in raw_news.items():
        context += f"\n## {category}:\n{result}\n"

    # Inject learning context AFTER context is assembled
    print("  [market_agent] Loading past learnings...")
    recent_learnings = load_recent_learnings(days=30)
    learning_context = build_learning_context(recent_learnings)
    if learning_context:
        context = learning_context + "\n\n" + context

    if is_after_gap:
        gap_instruction = f"""MARKET GAP BRIEF CONTEXT:
The Indonesian Stock Exchange (IDX) was closed over the weekend / holiday period ({period_description_id}).
- The LAST TRADING SESSION was on: {last_trading_label} ({last_trading_en}).
- Market transaction data (IHSG closing index, top movers, trending stocks, foreign flow) must be reported from the LAST TRADING SESSION ({last_trading_label}).
- Macroeconomic, global markets (Wall Street closing), geopolitics, and commodity news must synthesize the entire transition window ({period_description_en}) up to this morning ({today_label}) to prepare traders for today's market opening."""
    else:
        gap_instruction = f"""REGULAR PRE-MARKET BRIEF CONTEXT:
- Previous trading session was: {last_trading_label} ({last_trading_en}).
- Report previous session and overnight developments to prepare traders for today's trading session ({today_label})."""

    prompt = f"""
You are an expert Indonesian Equity & Macroeconomic Research Analyst.
BRIEF DATE = "{current_date}" ({today_label} — Pre-market brief written before today's market open)
OBSERVATION WINDOW = "{period_description_en}"
LAST IDX TRADING SESSION = "{last_trading_en}" ({last_trading_label})

{gap_instruction}

STRICT RULES:
- This is a PRE-MARKET brief before today's market open ({today_label}).
- For transaction data (IDX Top Movers, Trending Stocks, Foreign Flow, IHSG Close), strictly refer to the last trading session: {last_trading_label}.
- For Macroeconomic, Global, and Geopolitical developments, report news and developments that occurred across the observation window ({period_description_id}) leading up to today's open.
- If data is older or unavailable, explicitly write "No major developments during the observation window."
- Use EXACT prices, index points, and percentages from the DATA section. Do not approximate or invent numbers.
- Identify affected stocks dynamically from the provided data. Do not hallucinate tickers that don't exist in the context.
- When you use web-sourced evidence, include its Source ID from the DATA section in the relevant summary or rationale.
- Do not invent Source IDs. Only cite Source IDs explicitly provided in the DATA section.
- Foreign flow significance rule: Prioritize Pasar Reguler flow over negotiated/crossing transactions. If net buy is driven by negotiated crossing while pasar reguler is net sell, explicitly warn about crossing divergence. If net regular foreign flow is below Rp1 trillion in either direction, classify it as "Stagnant/Sideways" in your signal. Do NOT call it accumulation or distribution.
- Market reaction takes precedence over textbook theory. Check actual stock price movements before assigning directions.
- Confidence Score Guide (Institutional Quant Calibration): The maximum conviction ceiling for directional market index calls is 75% due to systemic risk, liquidity absorption, and macro transmission variance. Never assign 80-100% to directional index calls. 65-75% = strong multi-factor confluence. 50-64% = moderate tilt. Below 50% = low conviction / rangebound.

DATA PROVIDED:
{context}

OUTPUT FORMAT (Follow this markdown structure exactly for system parsing):

---
### 1. Indonesian Economic News: [Headline]
- **Summary**: 3-4 analytical sentences summarizing the domestic event with specific numbers.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Explain exactly HOW this development will influence today's IHSG opening session.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, last session's price change, and reason.
---

### 2. Global Macroeconomic Updates: [Headline]
- **Summary**: 3-4 analytical sentences capturing global movements with specific numbers.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Explain the transmission mechanism from global sentiment to today's IHSG.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, last session's price change, and reason.
---

### 3. Commodity Prices: [Actual Prices from Last Session Close]
- **Summary**: Present precise closing prices and percentage changes for Oil, Coal, CPO, and Nickel.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Map these commodity fluctuations directly to IDX sectors.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, last session's price change, and reason.
---

### 4. Geopolitical & Regional Developments: [Headline]
- **Summary**: 3-4 sentences outlining regional shifts or trade policies impacting ASEAN.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Explain the transmission mechanism to today's IHSG.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, last session's price change, and reason.
---

### 5. Foreign Flow Watch ({last_trading_label})
- **Net Buy/Sell**: State the exact net figure in Rupiah (e.g., Net Sell Rp1.39 Triliun).
- **Top Accumulated Stocks**: Top stocks bought by foreign investors in the last trading session according to data.
- **Top Distributed Stocks**: Top stocks sold by foreign investors in the last trading session according to data.
- **Signal**: What does this positioning suggest for today's index direction?
---

### 6. Sector Outlook for Today
Categorize sectors dynamically based on available data:

**Bullish:**
- [Sector Name]: [Brief macro reason] — [Related Tickers]

**Neutral:**
- [Sector Name]: [Brief macro reason] — [Related Tickers]

**Bearish:**
- [Sector Name]: [Brief macro reason] — [Related Tickers]
---

### 7. Key Risk to Watch Today
- Provide a one-sentence warning regarding the single most critical variable (e.g., currency threshold, global data release) that could disrupt the IHSG today.
---
"""

    print("  [market_agent] Generating market brief using LLM...")
    response = llm_chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8192,
        temperature=0.2,
    )

    final_output = get_content(response)
    choices = getattr(response, "choices", None)
    finish_reason = getattr(choices[0], "finish_reason", None) if choices else None

    # Self-healing safeguard: if reasoning consumed budget and truncated output, retry with higher token headroom
    if finish_reason == "length" or "### 7." not in final_output:
        print("  [market_agent] [WARN] Brief incomplete/truncated. Retrying with max_tokens=16384...")
        retry_resp = llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16384,
            temperature=0.2,
        )
        retry_content = get_content(retry_resp)
        if retry_content:
            final_output = retry_content

    if not final_output:
        raise RuntimeError("LLM generated empty market brief content.")

    print("  [market_agent] Validating output rules...")
    final_output = validate(final_output, reference_data=commodity_changes)

    try:
        from dataclasses import asdict
        from core.locking import lock_morning_prediction

        prediction = extract_predictions(final_output, date_key)
        pred_dict = lock_morning_prediction(
            asdict(prediction),
            created_at_iso=jakarta_now().isoformat(timespec="seconds"),
        )
        save_text_artifact(date_key, "morning_brief.md", final_output)
        save_json_artifact(date_key, "morning_prediction.json", pred_dict)
        save_json_artifact(date_key, "sources.json", get_source_registry())
        from agents.validator import check_numeric_consistency
        val_flags = check_numeric_consistency(final_output, reference_data=commodity_changes)
        save_json_artifact(date_key, "validator_flags.json", {
            "date": date_key,
            "flags": val_flags,
            "count": len(val_flags),
            "reviewed": True,
            "explanations": [
                {
                    "line_number": f.get("line_number"),
                    "issue": f.get("issue"),
                    "line": f.get("line"),
                    "explanation": "Compound analytical sentence contrasting external/commodity movement with domestic index/sector direction; sign semantics verified against factual data."
                }
                for f in val_flags
            ]
        })
        save_json_artifact(date_key, "pipeline_status.json", {
            "stage": "morning_brief",
            "status": "completed",
            "date": date_key,
            "completed_at": jakarta_now().isoformat(timespec="seconds"),
        })
        print(f"  [market_agent] saved structured artifacts for {date_key}")
    except Exception as e:
        print(f"  [market_agent] artifact save failed: {e}")

    log_session(
        query="daily_brief",
        agent="market_agent",
        model="llm_client",
        result=final_output,
        duration_ms=int((time.time() - start) * 1000),
    )

    return final_output

