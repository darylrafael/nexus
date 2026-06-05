from datetime import datetime, timedelta
import os
import time  # <--- TAMBAHAN: Import time
from agents.commodity_agent import get_commodity_prices
from agents.economics_engine import build_economics_context
from agents.validator import build_commodity_context, validate
# Import modul internal yang udah lo buat sebelumnya
from agents.web_agent import search_multiple, search_web
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from memory.learning_store import build_learning_context, load_recent_learnings
# <--- MODIFIKASI: Tambahkan log_session di akhir baris import ini
from memory.session import log_session
from openai import OpenAI
import yfinance as yf

# Inisialisasi Client OpenRouter/OpenAI
client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


def run_market_brief() -> str:
    """Fungsi utama untuk mengumpulkan data pasar riil kemarin, menyaring berita makro,

    menyuntikkan aturan logika ekonomi deterministik, dan menghasilkan laporan
    panduan harian (Daily Market Brief) sebelum pasar IDX dibuka.
    """
    start = time.time()  # <--- TAMBAHAN: Mulai hitung waktu di awal fungsi

    # 1. Setup format penanggalan dinamis
    now = datetime.now()
    current_date = now.strftime("%B %d, %Y")  # Contoh: June 03, 2026
    yesterday = (now - timedelta(days=1)).strftime("%B %d, %Y")  # Contoh: June 02, 2026
    yesterday_id = (now - timedelta(days=1)).strftime("%d %B %Y")  # Format Indonesia: 02 Juni 2026

    # 2. Setup query pencarian berita berdasarkan tanggal kemarin
    queries = {
        "Indonesian Economy": f"IHSG rupiah kurs BI rate inflasi ekonomi Indonesia {yesterday_id}",
        "Global Macro": f"The Fed suku bunga AS ekonomi China GDP inflasi {yesterday_id}",
        "Geopolitics": f"geopolitik perang dagang Asia tenggara pasar modal {yesterday_id}",
    }

    # 3. Ambil data komoditas dasar teks dan suntik aturan dasarnya
    print("  [market_agent] Fetching text commodity data...")
    commodity_text_data = get_commodity_prices()
    commodity_text_context = build_commodity_context(commodity_text_data)

    # 4. 🔥 Hitung persentase perubahan harga komoditas riil (DETERMINISTIC ENGINE via yfinance)
    print("  [market_agent] Calculating exact global commodity price changes via yfinance...")

    def _pct(ticker: str) -> float:
        try:
            t = yf.Ticker(ticker)
            p = t.fast_info.last_price
            prev = t.fast_info.previous_close
            return ((p - prev) / prev) * 100 if prev else 0.0
        except Exception as e:
            print(f"  [yfinance warning] failed to fetch {ticker}: {e}")
            return 0.0

    commodity_changes = {
        "Crude Oil": _pct("CL=F"),  # WTI Crude Futures
        "Natural Gas": _pct("NG=F"),  # Henry Hub Natural Gas
        # Lo bisa tambah ticker komoditas lain di sini jika dibutuhkan ke depan
    }

    # Bangun konteks aturan ekonomi baku berdasarkan perubahan persentase di atas
    economics_context = build_economics_context(
        commodity_changes=commodity_changes, current_date=current_date
    )

    # 5. Ambil data pergerakan pasar IDX (Top Movers, Volume, & Foreign Flow)
    print("  [market_agent] Fetching IDX market movers...")
    try:
        top_movers = search_web(
            f"saham naik turun terbesar IHSG top gainer loser {yesterday_id}", days=2
        )
        if len(top_movers.strip()) < 50:
            top_movers = "No fresh market mover data found."
    except Exception:
        top_movers = "Market movers data unavailable."

    print("  [market_agent] Fetching trending stocks...")
    try:
        trending_stocks = search_web(
            f"saham paling aktif volume terbesar IDX BEI {yesterday_id}", days=2
        )
        if len(trending_stocks.strip()) < 50:
            trending_stocks = "No fresh trending stock data found."
    except Exception:
        trending_stocks = "Trending stocks data unavailable."

    print("  [market_agent] Fetching foreign flow data...")
    try:
        foreign_flow = search_web(
            f"asing net buy sell IHSG investor asing {yesterday_id}", days=2
        )
        if len(foreign_flow.strip()) < 50:
            foreign_flow = "No fresh foreign flow data found."
    except Exception:
        foreign_flow = "Foreign flow data not available."

    # 6. Jalankan pencarian berita makro (Multi-Threaded Search)
    print("  [market_agent] Running targeted macroeconomic searches...")
    raw_news = search_multiple(queries, days=2)

    for category in raw_news:
        if not raw_news[category] or len(raw_news[category].strip()) < 50:
            raw_news[category] = f"No major developments reported on {yesterday_id}."

    recent_learnings = load_recent_learnings(days=14)
    learning_context = build_learning_context(recent_learnings)
    if learning_context:
        context = learning_context + "\n\n" + context

    # 7. ASSEMBLY CONTEXT: Satukan seluruh data mentah menjadi satu payload utuh untuk LLM
    context = "=== CORE MARKET DATA ===\n"
    context += f"{commodity_text_context}\n\n"
    context += f"## IDX Top Movers ({yesterday_id}):\n{top_movers}\n\n"
    context += f"## Trending IDX Stocks ({yesterday_id}):\n{trending_stocks}\n\n"
    context += f"## Foreign Flow ({yesterday_id}):\n{foreign_flow}\n\n"

    context += "=== GROUND TRUTH ECONOMIC LOGIC CONSTRAINTS ===\n"
    context += f"{economics_context}\n\n"

    context += "=== MACROECONOMIC & REGIONAL NEWS ===\n"
    for category, result in raw_news.items():
        context += f"\n## {category}:\n{result}\n"

    # 8. Setup prompt instruksi ketat untuk LLM Analyst
    prompt = f"""
You are an expert Indonesian Equity & Macroeconomic Research Analyst.
BRIEF DATE = "{current_date}" (This is a pre-market brief written before today's market open)
DATA WINDOW = "Yesterday {yesterday} — synthesize what happened yesterday to prepare traders for today."

STRICT RULES:
- This is a PRE-MARKET brief. Report what happened YESTERDAY ({yesterday}) to inform TODAY's trading session.
- Only report events and data points from yesterday ({yesterday}). If data is older, explicitly write "No major developments yesterday."
- Use EXACT prices, index points, and percentages from the DATA section. Do not approximate or invent numbers.
- Identify affected stocks dynamically from the provided data. Do not hallucinate tickers that don't exist in the context.
- Foreign flow significance rule: If the net foreign flow is below Rp1 trillion in either direction, classify it as "Stagnant/Sideways" in your signal. Do NOT call it accumulation or distribution.
- Market reaction takes precedence over textbook theory. Check actual stock price movements before assigning directions.
- Confidence Score Guide: 80-100% = direct, quantifiable, confirmed impact. 50-79% = likely but indirect transmission. Below 50% = speculative noise.

DATA PROVIDED:
{context}

OUTPUT FORMAT (Follow this markdown structure exactly for system parsing):

---
### 1. Indonesian Economic News: [Yesterday's Headline]
- **Summary**: 3-4 analytical sentences summarizing the domestic event with specific numbers.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Explain exactly HOW this development will influence today's IHSG opening session.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, yesterday's price change, and reason.
---

### 2. Global Macroeconomic Updates: [Yesterday's Headline]
- **Summary**: 3-4 analytical sentences capturing global movements with specific numbers.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Explain the transmission mechanism from global sentiment to today's IHSG.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, yesterday's price change, and reason.
---

### 3. Commodity Prices: [Actual Prices from Yesterday's Close]
- **Summary**: Present precise closing prices and percentage changes for Oil, Coal, CPO, and Nickel.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Map these commodity fluctuations directly to IDX sectors.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, yesterday's price change, and reason.
---

### 4. Geopolitical & Regional Developments: [Yesterday's Headline]
- **Summary**: 3-4 sentences outlining regional shifts or trade policies impacting ASEAN.
- **Market Impact**: [Bullish / Bearish / Neutral] | **Confidence**: [X%]
- **Rationale**: Explain the transmission mechanism to today's IHSG.
- **Affected Stocks**: Cite only stocks found in the data -> Ticker, yesterday's price change, and reason.
---

### 5. Foreign Flow Watch (Yesterday's Close)
- **Net Buy/Sell**: State the exact net figure in Rupiah (e.g., Net Sell Rp1.39 Triliun).
- **Top Accumulated Stocks**: Top stocks bought by foreign investors yesterday according to data.
- **Top Distributed Stocks**: Top stocks sold by foreign investors yesterday according to data.
- **Signal**: What does this positioning suggest for today's index direction?
---

### 6. Sector Outlook for Today
Categorize sectors dynamically based on yesterday's data:

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

    # 9. Panggil OpenRouter API untuk eksekusi sintesis analisis
    print("  [market_agent] Generating market brief using LLM...")
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b:free",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
        temperature=0.2,  # Diturunkan biar hasilnya patuh format dan gak "ngaco"
    )

    # 10. Loloskan hasil ke validator akhir untuk memastikan arah bahasa & kontradiksi bersih
    final_output = response.choices[0].message.content
    print("  [market_agent] Validating output rules...")
    final_output = validate(final_output)

    # <--- TAMBAHAN: Kirim log data ke memory session tepat sebelum fungsi selesai
    log_session(
        query="daily_brief",
        agent="market_agent",
        model="gpt-oss-120b",
        result=final_output,
        duration_ms=int((time.time() - start) * 1000),
    )

    return final_output