# Nexus — Claude Project Context

## What This Is
A Python multi-agent AI pipeline for IHSG (Indonesian Stock Exchange) market intelligence.
Runs automatically every weekday: morning brief at 06:55 WIB, evening review at 20:00 WIB.

## Project Structure
```
nexus/
├── .github/
│   └── workflows/
│       ├── morning_brief.yml      # 06:55 WIB cloud scheduled morning brief
│       └── evening_review.yml     # 20:00 WIB cloud scheduled evening review
├── main.py                        # CLI entry point
├── config.py                      # API keys via dotenv
├── scheduler.py                   # APScheduler / local cron (06:55 and 20:00 WIB)
├── orchestrator/
│   └── gemini.py                  # Tool-calling orchestrator (OpenRouter + Gemini fallback)
├── agents/
│   ├── web_agent.py               # Tavily search wrapper
│   ├── code_agent.py              # Code generation (OpenRouter)
│   ├── commodity_agent.py         # yfinance + web for commodity prices
│   ├── market_agent.py            # Main IHSG daily brief orchestrator
│   ├── economics_engine.py        # Deterministic commodity→sector impact logic (Single Source of Truth)
│   ├── validator.py               # Post-LLM output validator (imports COMMODITY_LOGIC from economics_engine)
│   ├── prediction_extractor.py    # Parse morning brief → structured predictions (ticker universe filtered)
│   └── evening_reviewer.py        # Post-market evaluation + RCA + lessons
├── core/
│   ├── sectors.py                 # Deterministic 11 IDX-IC sector scorer (+-0.20% band, close data only)
│   └── schedule.py                # Schedule configuration
├── memory/
│   ├── obsidian.py                # Optional local note storage
│   ├── learning_store.py          # Save/load learning entries + performance stats
│   └── session.py                 # SQLite session tracking
├── utils/
│   ├── flow.py                    # Strict Indonesian D/M/Y foreign flow parser (Rp1T threshold)
│   ├── stats.py                   # Dynamic 50/30/20 scoring blend, Wilson 95% CI, baselines, calibration
│   └── direction.py               # IHSG +-0.20% Neutral band evaluation
├── delivery/
│   └── telegram.py                # Telegram bot delivery
└── dashboard/                     # Next.js 16 telemetry & performance dashboard
```

## How to Run
```bash
# Cloud automated:
# GitHub Actions runs morning brief at 06:55 WIB and evening review at 20:00 WIB.
# Manual trigger available via GitHub Actions Web UI (workflow_dispatch).

# One-off local query
python main.py "your query here"

# Manual morning brief
python -c "from scheduler import daily_brief; daily_brief()"

# Manual evening review
python -c "from scheduler import evening_review; evening_review()"

# Start local scheduler
python scheduler.py

# Check session stats
python -c "from memory.session import print_summary; print_summary()"
```

## Environment Variables (.env)
```
OPENROUTER_API_KEY=
GEMINI_API_KEY=
DEEPINFRA_TOKEN=
TAVILY_API_KEY=
OBSIDIAN_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Key Design Decisions & Ground Rules
- **Single Source of Truth for Economics**: `agents/economics_engine.py` defines the canonical `COMMODITY_LOGIC`. `agents/validator.py` imports directly from it to prevent duplicate hardcoded ticker divergence.
- **Deterministic Evaluation**: Sector accuracy is scored strictly by rule against 11 IDX-IC closing returns (+-0.20% Neutral band) in `core/sectors.py`. Direction hit rate is evaluated with a +-0.20% Neutral band. Foreign flow requires strict Indonesian D/M/Y date verification with a Rp1T threshold.
- **Dynamic Scorable Blend (50/30/20)**: Composite accuracy blends 50% Index Direction + 30% Sector + 20% Flow dynamically normalized across scorable components only. Unscorable sessions (holiday/half-day) record null and are excluded from benchmarks.
- **Honest Statistical Metrics**: Exposes 95% Wilson Confidence Intervals, comparative baselines (Always-Bearish, Persistence, Always-Bullish), probability calibration (Brier score), and separate Long-Only vs Short-Only payoff in basis points. Any sample $n < 30$ is prominently labeled "Insufficient sample".
- **Zero Fabrication**: Missing data is marked "Unavailable" or "—", never defaulted to 0, 0.0%, 50%, or previous closes.

## Models Used
| Task | Model | Provider |
|------|-------|----------|
| Market brief / orchestration | gpt-oss-120b | OpenRouter (Gemini fallback) |
| Code generation | gpt-oss-120b | OpenRouter |
| Evening review / RCA | gpt-oss-120b | OpenRouter (Gemini fallback) |

## Known Limitations
- **Sample Size**: When the historical record has $n < 30$ scorable sessions, statistical power is insufficient to draw conclusions regarding predictive edge.
- **Research-Tier Data**: Uses public endpoints (`yfinance`, Tavily search) without a direct licensed IDX exchange feed.
- **Retail Shorting Constraint**: Synthetic basis point payoff separates realizable Long-Only capture on Bullish calls from theoretical Short-Side index capture on Bearish calls (not directly accessible to Indonesian retail investors).

## Generated Evaluation Metrics (`scripts/evaluate.py`)
<!-- METRICS:START -->
**Canonical Artifact Summary** (Scoring Engine `v2.2.0`, Rescored `2026-10-15`, Verified Runs: **23**, Scored Reviews: **n=22**, Unreviewed Pending: **1**)

### TABLE 1: HEADLINE DIRECTION TRACK RECORD & UNCERTAINTY
| Metric | Realized Value | Statistical Note / Wilson 95% CI |
| :--- | :--- | :--- |
| Scored Sessions (n) | **22** | ⚠️ Sample too small to conclude skill (n < 30) |
| Direction Hit Rate | **40.9%** (9/22) | 95% Wilson CI: [23.3%, 61.3%] |
| Rolling Accuracy | **33.7%** | Trailing dynamic 50/30/20 attribution average |

### TABLE 2: EMPIRICAL NAIVE BASELINES COMPARISON
| Strategy / Baseline | Accuracy (Hits/n) | Delta vs Nexus Model | Buy-Side Assessment |
| :--- | :--- | :--- | :--- |
| **Nexus Multi-Agent Model** | **40.9%** (9/22) | 0.0% | Active directional thesis |
| Always-Bearish (Down Only) | **59.1%** (13/22) | +18.2% | Outperforms model due to prevailing market downtrend |
| Persistence (Repeat T-1) | **52.4%** (11/21) | +11.5% | Exploits directional momentum across consecutive sessions |
| Always-Bullish (Up Only) | **36.4%** (8/22) | -4.5% | Model outperforms permanent long bias |

### TABLE 3: PIPELINE SUB-COMPONENT SCORING BREAKDOWN
| Component | Nominal Weight | Scorable (n) | Realized Hit Rate | Institutional Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| IHSG Direction | 50% | n = 22 | 40.9% (9/22) | Primary directional bias (Bullish/Bearish/Neutral ±0.20% band) |
| Sector Breakdown | 30% | n = 59 | 33.9% (20/59) | Evaluated across 11 IDX-IC closing returns; midday snapshots rejected |
| Foreign Flow | 20% | n = 3 | Insufficient data | Suppressed from scoring when scorable n < 5; treated as institutional context |

### TABLE 4: PROBABILISTIC CONFIDENCE CALIBRATION & BRIER SCORE
| Calibration Metric | Measured Value | Plain Language Buy-Side Interpretation |
| :--- | :--- | :--- |
| Model Stated Confidence (Uncalibrated) | **80.8%** | Raw uncalibrated LLM confidence output across n=22 scored sessions |
| Realized Direction Hit Rate | **40.9%** | Actual empirical accuracy (9/22 scored sessions) |
| Calibrated Confidence (Shrinkage) | **44.7%** (n=22, illustrative shrinkage estimate) | Bayesian shrinkage with prior strength N0=30 and prior cap 55.0% |
| Brier Score | **0.4079** | Probabilistic error (0.00 = perfect, 0.25 = random coin toss, >0.25 = overconfident) |

### TABLE 5: ECONOMIC PAYOFF STRUCTURE (BASIS POINTS)
| Strategy Portfolio | Realized Payoff (bps) | Trade Count | Tradability / Practical Feasibility |
| :--- | :--- | :--- | :--- |
| **Long-Only (Headline Payoff)** | **-364.0 bps** | 5 calls | Realizable long exposure on retail Indonesian brokerage accounts |
| Short-Side Payoff | **+1382.0 bps** | 15 calls | **Theoretical only; not retail-tradable on IDX cash index** |
| Combined Theoretical Long/Short | **+1018.0 bps** | 20 calls | Pure hypothetical synthetic index return before borrow fees and slippage |

### TABLE 6: SELF-LEARNING LOOP HYGIENE & QUARANTINE AUDIT
- Valid Injected Lessons: **34** (sanitized, validated against stored actuals, genuine data_quality-passing sessions only)
- Quarantined / Rejected Lessons: **17** (prevented from corrupting future pre-market intelligence)

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
<!-- METRICS:END -->

