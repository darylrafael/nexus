# Changelog

All notable changes to the **Nexus Market Intelligence Pipeline** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), adhering to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
