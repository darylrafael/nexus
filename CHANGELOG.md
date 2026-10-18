# Changelog

All notable changes to the **Nexus Market Intelligence Pipeline** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), adhering to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.1] - 2026-10-18

### Final Release Package Verification, Mobile Performance & Contrast Remediation, & Live Smoke Validator (Phases A–D)

- **Phase A (Release Packager & Isolated Smoke Test)**:
  - Rewrote `core/packaging.py` so the package allowlist is `git ls-files` minus an explicit denylist (`*.db`, `*.sqlite*`, `*.bak`, `*.pyc`, `*.log`, `.env`, `.env.*`, `__pycache__`, `node_modules`, `.next`, `.ruff_cache`, `.pytest_cache`, `.git`, `%*` segments, `scripts/fix_dashboard_audit.py`, `scripts/package_deliverables.py`), failing hard on any untracked non-ignored file (`"untracked file X would be missing from the package: git add it or ignore it"`).
  - Tracked and verified `llm_client.py`, `LEGAL.md`, `RUNBOOK.md`, `demo_data/`, `requirements.lock`, `.python-version`, `register_tasks.ps1`, `.dockerignore`, and `pytest.ini` via `REQUIRED_FILES` and `REQUIRED_PACKAGES` manifests (`--verify-zip`).
  - Added `smoke_test_release_zip` (`--smoke-test-zip`, `--smoke-test-with-venv`, `--smoke-test-install-deps`) and wired `package-smoke-test` into `.github/workflows/ci.yml`.
  - Updated `tests/test_phase1_path_isolation.py` and `tests/test_phase6_hygiene_and_packaging.py` to fall back to filesystem walking when `.git` is absent so `pytest -q` passes inside an extracted release zip (`127 passed`).
- **Phase B (Lighthouse Mobile Performance, WCAG AA Contrast, Typography, & UI State Fixtures)**:
  - Slimmed `/api/stats` (`dashboard/src/app/api/stats/route.js`) by returning only `{ url, title }` for cited `src_*` IDs (reducing JSON payload from `269 KB` to `~25 KB`), dynamically imported secondary modals/drawers in `dashboard/src/app/page.js`, and rendered the initial verified scorecard & latest call card on SSR so mobile `FCP ~ 1.1s`, `LCP <= 2.5s`, and `Performance >= 85`.
  - Remediated `:root` (light) and `[data-theme="dark"]` color tokens in `dashboard/src/app/globals.css` (`--text-tertiary`, `--text-secondary`, `--matched-text`, `--warning-text`, `--warning-body`, `--missed-text`, `--accent-cyan`, `--accent-blue`), achieving `0` `axe-core` violations (`34 passes, 0 violations`) across both dark and light themes at 390px and `100` Lighthouse Accessibility score.
  - Enforced strict `>= 12px` font size on all essential text across all 6 viewports (`360, 390, 430, 768, 1024, 1440`) and kept both `.dir-badge` and `.calibrated-conf-badge` inside the first viewport (`bottom <= 551px` at `360x740`, `499px` at `390x844` and `430x932`).
  - Committed three explicit Playwright UI state fixtures (`tests/fixtures/stale_fixture.json`, `tests/fixtures/fresh_today_fixture.json`, `tests/fixtures/missing_field_fixture.json`) strictly outside `runs/`.
- **Phase C (Live Smoke Runner & Workflow Hardening)**:
  - Added `scripts/live_smoke.py` and `tests/test_live_smoke.py` validating all 7 live session invariants in an isolated temp directory while refusing to run if `NEXUS_RUNS_DIR` resolves inside the repository's real `runs/`.
  - Hardened `.github/workflows/morning_brief.yml` and `.github/workflows/evening_review.yml` with explicit holiday-aware trading-day checks, `actions/upload-artifact@v4`, clean `runs/` commits, and `if: failure()` Telegram alerts.
- **Phase D (Documentation & Evaluation Check)**:
  - Verified all metric blocks via `python scripts/evaluate.py --check` (wired into `.github/workflows/ci.yml`), added the Release Package guide to `README.md`, and confirmed prominent key-rotation notices in `SECURITY.md` and `FIX_REPORT.md`.

---

## [2.2.0] - 2026-10-17

### Buy-Side Remediation: Data Contamination Purge, Provenance Guard, & Lock Ledger (Phases 1–8)

- **Phase 1 (Path Isolation & Repo Checksum Guard)**: Centralized all filesystem paths (`NEXUS_RUNS_DIR`, `NEXUS_DB_PATH`, `NEXUS_MEMORY_DIR`, `NEXUS_VAULT_DIR`, `NEXUS_DATA_DIR`) in `core/paths.py`. Added autouse `tmp_path` isolation and SHA-256 repo checksum guards in `tests/conftest.py` and CI.
- **Phase 2 (Provenance Guard)**: Implemented `core/provenance.py` (`is_mock_provenance`, `has_mock_provenance`, `check_run_dir_provenance`) and JS provenance guards across `learning_store`, `utils/stats`, `rescore_history.py`, `sync-runs.mjs`, and `/api/stats`. Added UI "Test data detected" error banner when mock artifacts are encountered.
- **Phase 3 (Data Cleaning & Null-Correctness Exclusion)**: Purged mock run directories and mock lessons, fixed `utils/stats.py` so `ihsg_correct = null` is excluded from directional $n$, and regenerated `runs/global/nexus_stats.json` and `runs/index.json` strictly from genuine sessions.
- **Phase 4 (FX Sign Convention & Unified Shrinkage Calibration)**: Rewrote `validate_lesson` in `memory/learning_store.py` to distinguish explicit `USD/IDR` vs `Rupiah` conventions and validate against stored session actuals (`unreliable_source_data` vs `sign_confusion`). Unified per-call and headline calibrated confidence in `utils/stats.py::compute_empirical_calibrated_confidence`. Enforced `data_quality` gating before prompt injection.
- **Phase 5 (Pre-Open Lock Ledger & Retroactive Disclosure)**: Marked historical sessions (`2026-09-22` to `2026-10-08`) as `lock_status = "retroactive"` (*Hash added retroactively; not proof of pre-open lock*). Added append-only hash-chained `runs/global/lock_ledger.jsonl` and `verify_prediction_lock` for tamper detection.
- **Phase 6 (Allowlist Packaging & Secret Hygiene)**: Replaced denylist packaging with `git ls-files` allowlist in `scripts/package_deliverables.py`, removed stray `%SystemDrive%` artifact, and added automated zip-hygiene and secret-scan tests.
- **Phase 7 (Mobile Budget, Self-Hosted Fonts, & Strict Viewport Audit)**: Self-hosted fonts via `next/font/local`, reduced mobile default height to $\le 2,900\text{px}$ across 360/390/430px, hardened `tests/audit_mobile_viewports.py` over all visible text and interactive nodes, and verified Telegram failure alerts and APScheduler job isolation.

#### Canonical Evaluation Metrics (`scripts/evaluate.py`)
<!-- METRICS:START -->
**Canonical Artifact Summary** (Scoring Engine `v2.2.0`, Rescored `2026-10-15`, Verified Runs: **13**, Scored Reviews: **n=12**, Unreviewed Pending: **1**)

### TABLE 1: HEADLINE DIRECTION TRACK RECORD & UNCERTAINTY
| Metric | Realized Value | Statistical Note / Wilson 95% CI |
| :--- | :--- | :--- |
| Scored Sessions (n) | **12** | ⚠️ Sample too small to conclude skill (n < 30) |
| Direction Hit Rate | **41.7%** (5/12) | 95% Wilson CI: [19.3%, 68.0%] |
| Rolling Accuracy | **34.3%** | Trailing dynamic 50/30/20 attribution average |

### TABLE 2: EMPIRICAL NAIVE BASELINES COMPARISON
| Strategy / Baseline | Accuracy (Hits/n) | Delta vs Nexus Model | Buy-Side Assessment |
| :--- | :--- | :--- | :--- |
| **Nexus Multi-Agent Model** | **41.7%** (5/12) | 0.0% | Active directional thesis |
| Always-Bearish (Down Only) | **66.7%** (8/12) | +25.0% | Outperforms model due to prevailing market downtrend |
| Persistence (Repeat T-1) | **63.6%** (7/11) | +21.9% | Exploits directional momentum across consecutive sessions |
| Always-Bullish (Up Only) | **33.3%** (4/12) | -8.4% | Model outperforms permanent long bias |

### TABLE 3: PIPELINE SUB-COMPONENT SCORING BREAKDOWN
| Component | Nominal Weight | Scorable (n) | Realized Hit Rate | Institutional Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| IHSG Direction | 50% | n = 12 | 41.7% (5/12) | Primary directional bias (Bullish/Bearish/Neutral ±0.20% band) |
| Sector Breakdown | 30% | n = 36 | 27.8% (10/36) | Evaluated across 11 IDX-IC closing returns; midday snapshots rejected |
| Foreign Flow | 20% | n = 1 | Insufficient data | Suppressed from scoring when scorable n < 5; treated as institutional context |

### TABLE 4: PROBABILISTIC CONFIDENCE CALIBRATION & BRIER SCORE
| Calibration Metric | Measured Value | Plain Language Buy-Side Interpretation |
| :--- | :--- | :--- |
| Model Stated Confidence (Uncalibrated) | **79.6%** | Raw uncalibrated LLM confidence output across n=12 scored sessions |
| Realized Direction Hit Rate | **41.7%** | Actual empirical accuracy (5/12 scored sessions) |
| Calibrated Confidence (Shrinkage) | **49.7%** (n=12, illustrative shrinkage estimate) | Bayesian shrinkage with prior strength N0=30 and prior cap 55.0% |
| Brier Score | **0.3996** | Probabilistic error (0.00 = perfect, 0.25 = random coin toss, >0.25 = overconfident) |

### TABLE 5: ECONOMIC PAYOFF STRUCTURE (BASIS POINTS)
| Strategy Portfolio | Realized Payoff (bps) | Trade Count | Tradability / Practical Feasibility |
| :--- | :--- | :--- | :--- |
| **Long-Only (Headline Payoff)** | **-176.0 bps** | 4 calls | Realizable long exposure on retail Indonesian brokerage accounts |
| Short-Side Payoff | **+244.0 bps** | 6 calls | **Theoretical only; not retail-tradable on IDX cash index** |
| Combined Theoretical Long/Short | **+68.0 bps** | 10 calls | Pure hypothetical synthetic index return before borrow fees and slippage |

### TABLE 6: SELF-LEARNING LOOP HYGIENE & QUARANTINE AUDIT
- Valid Injected Lessons: **20** (sanitized, validated against stored actuals, genuine data_quality-passing sessions only)
- Quarantined / Rejected Lessons: **9** (prevented from corrupting future pre-market intelligence)

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
<!-- METRICS:END -->

---

## [2.1.0] - 2026-10-15

### Final Buy-Side Institutional Remediation (Phases A–G)

#### Phase A: CI & Pipeline Regressions
- **Restored Flow Import (A1)**: Restored `from utils.flow import classify_foreign_flow` in `agents/evening_reviewer.py`, verified via `tests/test_phase_a1_data_authenticity.py`.
- **Zero Linter Warnings (A2)**: Fixed all pyflakes issues across `agents`, `data_sources`, `utils`, `memory`, `core`, and `scheduler.py` (`pyflakes` exits 0 with zero output).
- **Unified Environment Configuration (A3)**: Harmonized `NEXUS_SKIP_ENV_VALIDATION` and `SKIP_ENV_VALIDATION` in `config.py` and `tests/conftest.py`.
- **Isolated SQLite Session Database (A4)**: Replaced shared SQLite database in tests with an isolated test fixture in `conftest.py`, stabilizing Obsidian circuit breaker tests across consecutive runs.
- **End-to-End Smoke Testing (A5)**: Added mocked pipeline execution in `tests/test_smoke_pipeline_mocked.py` asserting zero internal error keys.
- **Structured Error Diagnostics (A6)**: Implemented structured JSON error telemetry (`status`, `error_type`, `message`, `timestamp`) across pipeline exceptions.

#### Phase B: Data Integrity & Exchange Standards
- **Strict Indonesian Date Resolution (B1)**: Enforced strict D/M/Y date matching in foreign flow extraction. Unmatched dates return `Unknown` (`date_mismatch_rejected`). Foreign flow treated as institutional context and unscored when scorable $n < 5$.
- **Data Quality Audit Block (B2)**: Every evening review generates an auditable `data_quality` dictionary (`ohlc_valid`, `fx_consistent`, `flow_date_matched`, `sector_data_is_close`).
- **Geometric OHLC Verification (B3)**: Implemented `validate_ohlc` in `data_sources/market_data.py` enforcing candle invariants and rejecting stale identical candles.
- **Commodity Source Disclosure (B4)**: Commodities lacking structured public APIs (Coal, CPO, Nickel) labeled `"Price unavailable (no structured source)"`.
- **Post-Close Sector Ingestion (B5)**: `core/sectors.py` enforces post-16:00 WIB close data, rejecting midday or Sesi I snapshots.
- **Holiday & Clock Alignment (B6)**: `getIdxMarketStatus` cross-references `data/idx_holidays.json` with client clock to prevent spurious scheduling.

#### Phase C: Scoring & Learning Hygiene
- **Explicit Scorable Weights (C1)**: Enforced canonical 50% Index Direction, 30% Sector Allocation, 20% Foreign Flow in `utils/stats.py`.
- **Small-Sample Guardrails (C1)**: Suppressed percentage displays when $n < 5$ (`null` + `"Insufficient data"`); affixed sample size warning when $n < 30$.
- **Bayesian Confidence Calibration (C2)**: Model stated confidence calibrated via empirical shrinkage towards realized hit rate; computed Brier score (see generated metrics block above).
- **Quarantine of Garbled Lessons (C3)**: Sanitized self-learning store, moving corrupted entries (`+17K` notation, unreliable source data, sign confusion, duplicates) to `rejected_lessons`.
- **Payoff Segregation (C4)**: Segregated realizable Long-Only payoff from theoretical Short-Side payoff (`"theoretical, not retail-tradable"`).
- **Rescored Historical Corpus (C5)**: Rescored genuine historical sessions via `scripts/rescore_history.py`.
- **Tamper-Evident Prediction Hash (C6)**: Morning brief stamped with a SHA-256 prediction lock hash.

#### Phase D: Prediction Quality & Sanitization
- **Ticker Universe Filtering (D1)**: Filtered hallucinated tickers (`DATE`, `XRPL`) using canonical IDX list, capped at 10 items.
- **Watchlist Polish (D2)**: Stripped markdown artifacts (`**Bullish**:`) and raw trade directives from watchlist summaries.

#### Phase E: Dashboard Logic & Label Honesty
- **Session Chip Accuracy (E1)**: Restricted `⏳ Live` status strictly to `session.date === todayTradingKey && marketStatus?.isOpen`.
- **Label Honesty (E2)**: Audited and removed inaccurate "Deterministic" labels from probabilistic components.
- **Layout Optimization (E4 & E5)**: Stale pipeline alert collapsed by default; Section 5 (Active Workbench) and Section 6 (Archive) wrapped in collapsible containers.
- **Sliding-Window Rate Limiting (E8 & G1)**: Implemented sliding-window rate limiting (60 req/min) with `Retry-After` headers and constant-time token comparison.

#### Phase F: Mobile-First Accessibility Audit
- **Comprehensive Viewport Audit**: Tested 12 combinations (360px, 390px, 430px, 768px, 1024px, 1440px across Dark/Light themes).
- **0 Horizontal Overflow**: Zero horizontal scroll across all screen sizes.
- **Touch Target & Typography Compliance**: Zero touch targets < 44x44px; zero body text < 12px.
- **Mobile Height Budget**: Default mobile page height kept within target budget, with Today's Call card positioned above the fold.

#### Phase G: Documentation & Evaluation Scripts
- **Deterministic Scripted Reporting (G5)**: Implemented `scripts/evaluate.py` generating markdown metric tables directly from `nexus_stats.json`.
- **Methodology Documentation (G6)**: Published comprehensive `METHODOLOGY.md` documenting exact mathematical formulations and institutional buy-side limitations.

---

## [2.1.0] - 2026-10-14

### Complete Buy-Side Audit & Pipeline Remediation (Phases 0–7)

#### Security & Hygiene (Phase 0)
- **Scrubbed & Purged**: Removed `.env` with unrotated API keys from deliverable archives; instructed owner to rotate keys across OpenRouter, DeepInfra, Tavily, Obsidian, Telegram, and Gemini.
- **Middleware Hardening**: Enforced constant-time comparison (`constantTimeEqual`) on `/api/*` routes, stripped query-string `?access_key=` authentication to avoid log leaks, removed fake `X-RateLimit` headers, and kept public dashboard pages accessible.
- **Sanitized Public UI**: Removed internal infrastructure references (`:27124`, `vault/nexus/learning_store.md`, `v2.4 Core Online`).
- **Legal & Data Disclaimers**: Elevated prominent disclaimers regarding research-tier data, no licensed exchange feed, and non-investment advice.

#### Pipeline Crash Bugs Fixed (Phase 1)
- **Fixed `agents/market_agent.py`**: Defined `rupiah_change = -(usdidr_change_pct)` from `fetch_usdidr_snapshot()` (economics engine treats negative as rupiah weakened) and replaced unsafe dict defaults with `comm_res.get("changes") or {}`.
- **Fixed `agents/evening_reviewer.py`**: Eliminated `NameError: name 'learning' is not defined` by setting `learning["market_regime"] = detect_market_regime(learning)` after dictionary initialization; renamed duplicate `ihsg_confidence` key to `ihsg_data_confidence`; added None-safe checks for `ihsg_actual_pct`.
- **Pipeline Alerts**: Added explicit exception raising in `scheduler.py` to trigger immediate failure notifications via GitHub Actions / Telegram.
- **Smoke Tests**: Added mocked end-to-end smoke tests in `tests/test_smoke_pipeline_mocked.py`.

#### Data Integrity & Ground Truth (Phase 2)
- **Indonesian D/M/Y Strict Dates**: Implemented date parsing in `utils/flow.py` ensuring Indonesian dates like `10/6/2026` are parsed strictly as 10 June (not October 6); added `strict=True` requiring explicit target date verification in news text.
- **Foreign Flow Rp1T Threshold**: Implemented canonical $\pm\text{Rp 1.0T}$ threshold (e.g. Rp 252.65B is classified as Stagnant/Sideways, not Distribution).
- **OHLC Invariant Validation**: Added `validate_ohlc` in `data_sources/market_data.py` enforcing geometric invariants (`low <= min(o,c)`, `high >= max(o,c)`, etc.). On failure, sets open/high/low to `None` instead of fabricating to close. Removed zero volume defaults.
- **USD/IDR Consecutive Candle %**: Computed exchange rate % change strictly from consecutive daily candles rather than stale multi-day previous closes.
- **Commodity Sign Resolution**: Required percentages in commodity snippets to be keyword-proximate and bilingually sign-resolved (`turun`/`melemah` vs `naik`/`menguat`) with confidence scoring.

#### Scoring & Self-Learning Loop (Phase 3)
- **Deterministic 11 IDX-IC Sector Scorer**: Built `core/sectors.py` scoring predicted sectors against official close data with a $\pm 0.20\%$ Neutral band; subsectors with conflicting parent calls are marked unverifiable and excluded.
- **Dynamic 50/30/20 Scorable Blend**: Composite session accuracy blends 50% Index Direction + 30% Sector + 20% Flow, dynamically normalized across scorable components only. Returns `null` for unscorable sessions.
- **Honest Statistical Metrics**: Added Wilson 95% Confidence Intervals, comparative baselines, Brier calibration score, and separate Long-Only vs Short-Only payoff (see generated metrics block above).
- **Ticker Universe Validation**: Built `data/idx_tickers.json` to filter hallucinated acronyms (`DATE`, `XRPL`), ordered by mention frequency and capped at 8-10.
- **Unified Economics Engine**: Harmonized `agents/validator.py` with `agents/economics_engine.py` (eliminated duplicate hardcoded tickers).
- **Historical Rescoring**: Rescored genuine historical sessions via `scripts/rescore_history.py --apply`.

#### Dashboard Logic & Stale Pipeline Alert (Phase 4)
- **Stale Pipeline Safeguard**: Added `pipelineHealth` detecting sessions older than 1 trading day (`isStale: true`), rendering a prominent alert banner and marking older pending sessions as "Not reviewed".
- **Zero Fabrication**: Replaced fabricated fallbacks (`"0.0%"`, `50.0%`, `totalRuns = reviews.length * 2`) with `null` and `"—"`.
- **True Volatility Band**: Labeled pre-market support/resistance as `Prev-Day Range Ref` unless verified 14-day ATR is available.
- **Watchlist Cleanliness**: Replaced `"BUY ON WEAK"` with `"MONITORED"` / `"POSITIVE TILT"`.

#### Outside Viewer UI/UX (Phase 5)
- **Information Hierarchy**: Restructured top-to-bottom: Product Header $\to$ Today's Call Card $\to$ Track Record Scorecard $\to$ Last 5 Sessions Ledger $\to$ Detailed Audit Workbench $\to$ Full Archive.
- **Methodology & Audit Guide**: Created comprehensive `MethodologyView` explaining predictions, scoring rules, baselines, and buy-side caveats.

#### Mobile-First Optimization (Phase 6)
- **Responsive Viewport Auditing**: Verified viewports across 360px, 390px, 430px, 768px, 1024px, and 1440px in both Dark and Light modes using automated Playwright tests.
- **Zero Horizontal Overflow & Zero Console Errors**: All 12 viewport/theme combinations pass with 0 overflow and 0 console errors.
- **Touch Target & Font Floors**: Enforced minimum 44x44px touch targets on buttons/nav and minimum 11-12px font sizes.

---

## [2.0.0] - 2026-10-08

### Full Architecture & Security Remediation (Phases 0–8)

#### Security & Configuration (Phase 0)
- **Added**: `SECURITY.md` establishing disclosure protocols, secret governance, and environment policy.
- **Added**: Strict fail-fast `.env` validation in `config.py` with zero secret value leakage.
- **Added**: Explicit `.dockerignore` preventing secret, database, and credential exfiltration.
- **Added**: Dependency lockfile `requirements.lock` and Python version pin `.python-version` (`3.11.9`).
- **Added**: Comprehensive test suite `tests/test_config.py` validating configuration boundary rules.

#### Data Integrity & Zero Fabrication (Phase 1)
- **Removed**: All hardcoded fallback prices, exchange rates, tickers, and demo constants across the pipeline.
- **Fixed**: Explicit propagation of `None` / `Unavailable` throughout `data_sources`, `agents`, Next.js API routes, and UI components.
- **Added**: `tests/test_phase1_no_fabricated_data.py` verifying that no unvalidated values can contaminate analysis.

#### Mathematical Consistency & Scoring Alignment (Phase 2)
- **Added**: `utils/direction.py` standardizing IHSG directional classification with canonical ±0.20% neutral threshold.
- **Added**: `utils/flow.py` standardizing Indonesian foreign flow parsing (`Rp Triliun` / `Rp Miliar`) with canonical ±Rp 1.0T threshold and date mismatch rejection.
- **Added**: `utils/stats.py` calculating separated Direction, Flow, and Sector hit rates over strictly scorable trading sessions.
- **Added**: `scripts/rescore_history.py` auditing historical sessions, fixing flawed percentages, and generating verified `nexus_stats.json`.
- **Added**: `tests/test_phase2_scoring_fixes.py` providing 9 unit test proofs of mathematical correctness.

#### Deduplication & Cache Architecture (Phase 3)
- **Added**: In-memory SHA-256 query cache with 30-minute TTL and metrics logging in `agents/web_agent.py`.
- **Added**: Centralized `fetch_all_commodities()` and formatting in `data_sources/market_data.py`.
- **Refactored**: `commodity_agent.py`, `market_agent.py`, and `evening_reviewer.py` to reuse unified market data fetches.
- **Added**: Pipeline stage tracking (`pipeline_status.json`) allowing resilient checkpointing and partial recoveries.
- **Added**: `tests/test_phase3_deduplication.py`.

#### LLM Fault Tolerance & Robust Parsing (Phase 4)
- **Added**: Multi-stage resilient JSON parser in `utils/json_parser.py` (strips `<think>` tags, markdown fences, balances brackets, trims commas, and repairs partial output).
- **Added**: Dual-tier fallback (OpenRouter -> DeepInfra -> Gemini) with strict 45s timeouts in `llm_client.py`.
- **Added**: Truncation detection flagging incomplete model generation (`finish_reason == 'length'`).
- **Added**: `tests/test_phase4_llm_reliability.py`.

#### Storage Resilience & Data Licensing (Phase 5)
- **Added**: Atomic file write routines (`tmp_file -> os.replace`) in `memory/artifacts.py`.
- **Added**: SQLite WAL mode (`PRAGMA journal_mode = WAL;`) and 30s busy timeout in `memory/session.py`.
- **Added**: Non-blocking background worker and circuit breaker for Obsidian Local REST API synchronization.
- **Added**: Indonesian Exchange (IDX) holiday calendar `data/idx_holidays.json` and utility functions in `core/calendar.py`.
- **Added**: `MarketDataProvider` abstraction in `data_sources/provider.py` with licensing boundary check (`NEXUS_PUBLIC_MODE`).
- **Added**: Domain denylist, `topic="news"` parameter, and recency verification in `agents/web_agent.py`.
- **Added**: `tests/test_phase5_storage_resilience.py` and `tests/test_phase5_data_sources_licensing.py`.

#### Scheduling, Idempotency & Packaging (Phase 6)
- **Added**: Single source of truth configuration `schedule.yaml` and `core/schedule.py`. Aligned schedules to **06:55 WIB** (Morning Brief) and **20:00 WIB** (Evening Review).
- **Added**: Inter-process file locking in `core/locking.py` (`acquire_run_lock`) preventing overlapping executions.
- **Added**: `utils/dates.py` eliminating circular dependencies between agents and schedulers.
- **Added**: Python standard package layout `pyproject.toml`, `nexus/__init__.py`, `nexus/__main__.py` with CLI verbs (`brief`, `review`, `serve`).
- **Added**: `tests/test_phase6_scheduling_automation.py`.

#### Timezone Governance & Telemetry Privacy (Phase 7)
- **Added**: Canonical timezone utility `core/time.py` (`jakarta_now()`, `Asia/Jakarta`, UTC+07:00), replacing naive datetime calls across all modules.
- **Added**: Structured session error logging `log_session(success=False, error_msg=...)` on all failure branches.
- **Added**: Sensitive data scrubbing (`query`, `result` removed) for public telemetry JSON exports.
- **Added**: Safe HTML parser (`markdown_to_safe_html`), message chunking on paragraph boundaries, and Telegram rate-limit backoff in `delivery/telegram.py`.
- **Added**: `schemas.py` defining JSON schemas for brief, review, and telemetry artifacts.
- **Added**: `tests/test_phase7_timezones_telemetry.py`.

#### Dashboard Security & Production Hardening (Phase 8)
- **Added**: Strict security headers (CSP, HSTS, X-Content-Type-Options, Frame-Options) in `dashboard/next.config.mjs`.
- **Added**: Basic Auth access gate middleware `dashboard/src/middleware.js`.
- **Added**: Pre-computed session index generator `runs/index.json` in `sync-runs.mjs`.
- **Added**: Data quality indicators (`isWebFallback`, `isUnscorable`, `confidence`) across API routes and UI badges.
- **Added**: Evidence-based heuristic validation in `api/memory/route.js`.
- **Added**: Next.js App Router error boundary (`error.js`), skeleton (`loading.js`), 404 (`not-found.js`), `robots.js`, and `sitemap.js`.
- **Added**: Regulatory and legal disclaimer footer and morning brief disclaimer banner (`Disclaimer.js`).
