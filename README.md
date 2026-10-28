# Nexus — Multi-Agent IHSG Market Intelligence Pipeline

A Python multi-agent pipeline that autonomously generates pre-market intelligence briefs for the Indonesian Stock Exchange (IHSG / ^JKSE), delivers them via Telegram, evaluates prediction accuracy against official market close data, and **learns from its own mistakes** through an auditable self-learning feedback loop.

Designed with buy-side quantitative rigor: deterministic economic rules prevent LLM hallucination, evaluations are scored strictly against official exchange settle data, and metrics are honestly benchmarked against persistent market baselines with Wilson 95% confidence intervals.

---

## System Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │          SCHEDULING & EXECUTION LAYER                  │
                  │  GitHub Actions (Cloud Cron)  │  APScheduler (Local)   │
                  │  06:55 WIB Morning Brief      │  20:00 WIB Review      │
                  └────────────┬───────────────────────────┬───────────────┘
                               │                           │
              ┌────────────────▼───────┐          ┌────────▼──────────────┐
              │     MARKET AGENT        │          │   EVENING REVIEWER    │
              │  (Morning Brief)        │          │  (Post-Market Eval)   │
              └──┬──────────┬──────┬───┘          └──┬────────────┬───────┘
                       │          │      │           │            │
              ┌────────▼─┐ ┌──────▼─┐ ┌─▼────────┐ │     ┌──────▼──────┐
              │ WEB AGENT │ │COMMODITY│ │ECONOMICS │ │     │  PREDICTION │
              │ (Tavily)  │ │ AGENT   │ │ ENGINE   │ │     │  EXTRACTOR  │
              └────────┬──┘ │(yfinance│ │(rules)   │ │     │ (IDX Filter)│
                       │    └────────┘ └──────────┘ │     └─────────────┘
                       │                            │
              ┌────────▼────────────────────────────▼────┐
              │                  LLM                      │
              │         OpenRouter (GPT-OSS-120B)         │
              │         Gemini 2.5 Pro (Fallback)         │
              └────────────────────┬──────────────────────┘
                                   │
              ┌────────────────────▼──────────────────────┐
              │              VALIDATOR                     │
              │  Direction language fixer + ticker check  │
              │  (imports COMMODITY_LOGIC from economics) │
              └────────────────────┬──────────────────────┘
                                   │
              ┌─────────────┬──────▼──────┬───────────────┐
              │             │             │               │
     ┌────────▼──────┐ ┌────▼────┐ ┌─────▼──────┐ ┌──────▼──────┐
     │   OBSIDIAN    │ │ TELEGRAM│ │  LEARNING  │ │   SESSION   │
     │ (Memory/Notes)│ │(Delivery│ │   STORE    │ │  (SQLite)   │
     └───────────────┘ └─────────┘ └────────────┘ └─────────────┘
```

---

## How It Works

### Morning Brief (06:55 WIB, Weekdays)
1. **Macro & Commodity Ingestion**: Fetches snapshot prices for Brent Crude, WTI, and Natural Gas via `yfinance`. Coal, CPO, and Nickel web search estimates are parsed with strict keyword proximity and sign resolution; unverified items are marked "Unavailable".
2. **Deterministic Economics Engine (`agents/economics_engine.py`)**: Canonical commodity-to-sector rules directly map price shocks to the 11 IDX-IC sectors (e.g. CPO firm $\to$ Agri/CPO positive; Brent surge $\to$ Energy positive, Transport/Consumer defensive) without probabilistic LLM guessing.
3. **News & Factor Synthesis**: Web agent searches for domestic macroeconomic catalysts, Bank Indonesia statements, and Wall Street overnight closes with SHA-256 deduplication.
4. **Context Injection**: Loads recent prediction accuracy and validated heuristic rules from `memory/learning_store.py` to prompt the LLM against recurring blind spots.
5. **Output Validation (`agents/validator.py`)**: Synchronizes with the economics engine to verify that directional language aligns with underlying commodity logic.
6. **Delivery & Archiving**: Formats and broadcasts structured briefing notes to Telegram and archives them in `runs/YYYY-MM-DD/`.

### Evening Review & Scoring (20:00 WIB, Weekdays)
1. **Authoritative Close Ingestion**: Pulls official IDX settlement data for IHSG (^JKSE), consecutive-candle USD/IDR exchange rates, and closing returns for the 11 IDX-IC parent sectors.
2. **Strict Foreign Flow Evaluation**: Parses institutional net foreign flow using Indonesian D/M/Y date verification. Applies a $\pm\text{Rp 1.0 Triliun}$ threshold (under Rp 1T is classified as Stagnant/Sideways).
3. **Deterministic 11 IDX-IC Sector Scoring (`core/sectors.py`)**: Evaluates predicted sectors against official close data with a $\pm 0.20\%$ Neutral band. Subsectors with conflicting calls on the same parent index are flagged as unverifiable and excluded.
4. **Dynamic 50/30/20 Scorable Blend (`utils/stats.py`)**:
   $$\text{Composite Score} = 0.50 \times \text{Index Direction} + 0.30 \times \text{Sector Accuracy} + 0.20 \times \text{Foreign Flow}$$
   Weights automatically rescale across scorable components only. Unscorable sessions (half-day or missing feeds) record `null` rather than a penalty score.
5. **Root Cause Analysis (RCA)**: Identifies unanticipated drivers, underestimated factors, and policy surprises.
6. **Heuristic Rule Extraction**: Derives structured market rules (*"Ketika [trigger], tetapi [divergence], maka [impact]"*), verifies consistency against stored numbers, and saves to the persistent knowledge store.

---

## Statistical Performance & Benchmark Baselines

All performance figures, baselines, confidence intervals, calibration metrics, payoff structures, and self-learning hygiene counts are generated deterministically from `runs/global/nexus_stats.json` and `runs/index.json` via `python scripts/evaluate.py`:

<!-- METRICS:START -->
**Canonical Artifact Summary** (Scoring Engine `v2.2.0`, Rescored `2026-10-28`, Verified Runs: **27**, Scored Reviews: **n=27**, Unreviewed Pending: **0**)

### TABLE 1: HEADLINE DIRECTION TRACK RECORD & UNCERTAINTY
| Metric | Realized Value | Statistical Note / Wilson 95% CI |
| :--- | :--- | :--- |
| Scored Sessions (n) | **27** | ⚠️ Sample too small to conclude skill (n < 30) |
| Direction Hit Rate | **40.7%** (11/27) | 95% Wilson CI: [24.5%, 59.3%] |
| Rolling Accuracy | **34.3%** | Trailing dynamic 50/30/20 attribution average |

### TABLE 2: EMPIRICAL NAIVE BASELINES COMPARISON
| Strategy / Baseline | Accuracy (Hits/n) | Delta vs Nexus Model | Buy-Side Assessment |
| :--- | :--- | :--- | :--- |
| **Nexus Multi-Agent Model** | **40.7%** (11/27) | 0.0% | Active directional thesis |
| Always-Bearish (Down Only) | **55.6%** (15/27) | +14.9% | Outperforms model due to prevailing market downtrend |
| Persistence (Repeat T-1) | **53.8%** (14/26) | +13.1% | Exploits directional momentum across consecutive sessions |
| Always-Bullish (Up Only) | **40.7%** (11/27) | +0.0% | Model outperforms permanent long bias |

### TABLE 3: PIPELINE SUB-COMPONENT SCORING BREAKDOWN
| Component | Nominal Weight | Scorable (n) | Realized Hit Rate | Institutional Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| IHSG Direction | 50% | n = 27 | 40.7% (11/27) | Primary directional bias (Bullish/Bearish/Neutral ±0.20% band) |
| Sector Breakdown | 30% | n = 67 | 34.3% (23/67) | Evaluated across 11 IDX-IC closing returns; midday snapshots rejected |
| Foreign Flow | 20% | n = 3 | Insufficient data | Suppressed from scoring when scorable n < 5; treated as institutional context |

### TABLE 4: PROBABILISTIC CONFIDENCE CALIBRATION & BRIER SCORE
| Calibration Metric | Measured Value | Plain Language Buy-Side Interpretation |
| :--- | :--- | :--- |
| Model Stated Confidence (Uncalibrated) | **78.2%** | Raw uncalibrated LLM confidence output across n=27 scored sessions |
| Realized Direction Hit Rate | **40.7%** | Actual empirical accuracy (11/27 scored sessions) |
| Calibrated Confidence (Shrinkage) | **42.2%** (n=27, illustrative shrinkage estimate) | Bayesian shrinkage with prior strength N0=30 and prior cap 55.0% |
| Brier Score | **0.3923** | Probabilistic error (0.00 = perfect, 0.25 = random coin toss, >0.25 = overconfident) |

### TABLE 5: ECONOMIC PAYOFF STRUCTURE (BASIS POINTS)
| Strategy Portfolio | Realized Payoff (bps) | Trade Count | Tradability / Practical Feasibility |
| :--- | :--- | :--- | :--- |
| **Long-Only (Headline Payoff)** | **-364.0 bps** | 5 calls | Realizable long exposure on retail Indonesian brokerage accounts |
| Short-Side Payoff | **+1465.0 bps** | 20 calls | **Theoretical only; not retail-tradable on IDX cash index** |
| Combined Theoretical Long/Short | **+1101.0 bps** | 25 calls | Pure hypothetical synthetic index return before borrow fees and slippage |

### TABLE 6: SELF-LEARNING LOOP HYGIENE & QUARANTINE AUDIT
- Valid Injected Lessons: **44** (sanitized, validated against stored actuals, genuine data_quality-passing sessions only)
- Quarantined / Rejected Lessons: **20** (prevented from corrupting future pre-market intelligence)

| Session Date | Quarantine Reason | Sample Quarantined Content |
| :--- | :--- | :--- |
| 2026-09-28 | `unreliable_source_data: stored usdidr_change_pct (0.871%) diverges from consecutive spot close (0.268%)` | Ketika IHSG diprediksi Bearish dengan risiko pelemahan Rupiah, te... |
| 2026-09-29 | `session_limit_exceeded: max 2 lessons per session` | Ketika brief tidak mencatat risiko geopolitik dan guncangan pasar... |
| 2026-09-30 | `duplicate_tail: maka ihsg ditutup bearish (-0` | Ketika foreign flow diprediksi Stagnant/Sideways, tetapi terjadi ... |
| 2026-09-30 | `duplicate_tail: maka ihsg ditutup bearish (-0` | Ketika sektor Properti diprediksi Bearish, tetapi sektor properti... |
| 2026-09-30 | `duplicate_tail: maka ihsg ditutup bearish (-0` | Ketika sektor Banking diprediksi Neutral, tetapi sektor keuangan ... |
| 2026-10-01 | `unreliable_source_data: stored usdidr_change_pct (2.195%) diverges from consecutive spot close (0.476%)` | Ketika IHSG diprediksi Bullish, tetapi terjadi pelemahan Rupiah s... |
| 2026-10-02 | `unreliable_source_data: cites unverified foreign flow from date_mismatch_rejected source` | Ketika IHSG diprediksi Bearish dengan confidence 67% dan foreign ... |
| 2026-10-02 | `invalid_unit: +17K style notation` | Ketika sektor Kesehatan diprediksi Bearish, tetapi sektor tersebu... |
| 2026-10-07 | `unreliable_source_data: cites unverified foreign flow from date_mismatch_rejected source` | Ketika aliran dana asing diprediksi stagnan/sideways, tetapi terj... |
| 2026-10-08 | `numeric_contradiction: stated IHSG 82.0% vs actual -1.88%` | Ketika IHSG diprediksi bullish dengan keyakinan 82% didukung peng... |
| 2026-10-09 | `session_limit_exceeded: max 2 lessons per session` | Ketika komoditas Coal diprediksi 'bearish', tetapi harga Batu Bar... |
| 2026-10-12 | `session_limit_exceeded: max 2 lessons per session` | Ketika sektor Industrials dan Energi diprediksi Bullish, tetapi I... |
| 2026-10-12 | `session_limit_exceeded: max 2 lessons per session` | Ketika sektor Infrastruktur dan Barang Konsumen Non-Primer dipred... |
| 2026-10-13 | `boilerplate_generic: matches pattern 'perlu memperketat stop-loss'` | Ketika proyeksi pagi mengantisipasi IHSG Bearish (confidence 82%)... |
| 2026-10-14 | `boilerplate_generic: matches pattern 'perlu memperketat stop-loss'` | Ketika proyeksi pagi mengantisipasi IHSG Bearish (confidence 82%)... |
| 2026-10-16 | `numeric_contradiction: stated IHSG 11.57% vs actual -11.57%` | Ketika [tidak ada risiko besar yang teridentifikasi di pagi hari]... |
| 2026-10-19 | `numeric_contradiction: stated IHSG 3.64% vs actual -3.64%` | Ketika IHSG diproyeksikan bearish dengan harapan penopang pada se... |
| 2026-10-22 | `unreliable_source_data: stored usdidr_change_pct (-0.017%) diverges from consecutive spot close (0.596%)` | Ketika morning brief memprediksi IHSG 'Bearish' dengan 80% confid... |
| 2026-10-23 | `session_limit_exceeded: max 2 lessons per session` | Ketika Foreign Flow diprediksi Distribusi (Net Sell), dan memang ... |
| 2026-10-27 | `session_limit_exceeded: max 2 lessons per session` | Ketika tidak ada prediksi mengenai aksi unjuk rasa, tetapi unjuk ... |
<!-- METRICS:END -->

---

## Tech Stack & Data Sources

| Component | Tool / Provider | Role |
|---|---|---|
| **Primary LLM** | OpenRouter (`gpt-oss-120b`) | Morning thesis generation, attribution RCA |
| **Failover LLM** | Google Gemini 2.5 Pro | Automated high-availability fallback |
| **Market Data** | Yahoo Finance (`yfinance`) | IHSG OHLC, USD/IDR, energy futures |
| **News Search** | Tavily Search API | Macro, regulatory, and corporate news |
| **Sector Scorer** | Deterministic Engine (`core/sectors.py`) | 11 IDX-IC parent index verification |
| **Delivery** | Telegram Bot API | Pre-market mobile broadcast |
| **Dashboard** | Next.js 16 (App Router + React 19) | Transparent public audit interface |

---

## Known Limitations

1. **Small Sample Size ($n < 30$)**: Statistical power is insufficient to demonstrate an edge over random variation until at least 30 independent scored trading sessions are accumulated (see generated Table 1 above for current $n$ and Wilson 95% CI).
2. **Research-Tier Data Feeds**: Feeds are aggregated from public web endpoints (`yfinance`, Tavily) without a direct, licensed IDX binary exchange feed.
3. **Retail Trading Constraints**: Positive theoretical short-side capture on Bearish calls is not directly executable by Indonesian retail accounts on the cash IHSG index; long-only performance on Bullish calls is reported separately in Table 5 above.
4. **Retroactive vs Pre-Open Locks**: Historical predictions (`2026-09-22` through `2026-10-08`) were hashed during post-hoc rescoring and are explicitly marked `lock_status = "retroactive"` (*Hash added retroactively; not proof of pre-open lock*). Only new predictions hashed at creation time before 09:00 WIB and appended to `runs/global/lock_ledger.jsonl` carry `locked_pre_open` status.
5. **Stale Pipeline Safeguard**: When no new genuine pipeline runs occur within 1 trading day, the dashboard displays a prominent stale pipeline warning (`No new call generated today`) and marks past unreviewed sessions as `Not reviewed`.

---

## How to Run

### 1. Installation
```bash
git clone <REPO_URL>
cd nexus
python -m venv venv
venv\Scripts\activate  # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest -v
```

### 3. Launch Dashboard
```bash
cd dashboard
npm install
npm run build
npm run start -- -p 3002
```
Open [http://127.0.0.1:3002](http://127.0.0.1:3002).

### 4. Optional Windows Automation Helpers
The repository ships with optional Windows automation helpers configured relative to the repository root:
- `run_brief.bat` / `run_review.bat`: Executes morning brief or evening review using the local virtual environment.
- `run_scheduler.bat` / `start_hidden.vbs`: Starts the local background scheduler (visible or silent).
- `register_tasks.ps1`: Registers Windows Task Scheduler tasks aligned with `schedule.yaml` (06:55 and 20:00 WIB).
- All paths are relative (`%~dp0` / `$PSScriptRoot`), contain no hardcoded personal paths or credentials, and write logs to `*.log` (excluded from git and release packages).

---

## Release Package

The release archive is built deterministically from git-tracked files (`git ls-files`) minus an explicit denylist enforced in `core/packaging.py`. Any untracked, non-ignored file in the working tree causes a hard failure so required modules are never silently omitted.

### Build the Release Zip
```bash
python -m core.packaging --verify-hygiene --build-zip nexus_remediated.zip
```

### Verify and Smoke-Test the Release Zip
```bash
# Verify allowlist/denylist rules, REQUIRED_FILES manifest, and secret scan:
python -m core.packaging --verify-zip nexus_remediated.zip

# Extract into an isolated temp directory (no .git, no .env) and run import + pytest smoke checks:
python -m core.packaging --smoke-test-zip nexus_remediated.zip
```

### Excluded Patterns (Denylist)
- **Secrets & Environment**: `.env`, `.env.*` (except `.env.example`)
- **Databases & Backups**: `*.db`, `*.sqlite*`, `*.bak`, `*.log`, `*.pyc`
- **Build & Cache Directories**: `__pycache__/`, `.ruff_cache/`, `.pytest_cache/`, `node_modules/`, `.next/`, `out/`, `.git/`, `venv/`, `.venv/`
- **OS / Shell Artifacts**: Any path segment starting with `%` (e.g. `%SystemDrive%`)
- **One-Off Local Maintenance Scripts**: `scripts/fix_dashboard_audit.py`, `scripts/package_deliverables.py`

---

*Educational and architectural demonstration project. Not investment advice. DYOR.*
