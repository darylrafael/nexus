# Nexus Pipeline Remediation Report (Phases 0–9)

## Executive Summary

Audit sistem pipeline intelijen pasar Nexus mengidentifikasi sejumlah kerentanan kritis, inkonsistensi matematis, potensi kegagalan runtime, dan celah keamanan data. Remediasi menyeluruh telah diselesaikan dalam 9 fase berurutan tanpa regresi, disertai dengan penambahan 54 tes otomatis baru dan verifikasi end-to-end.

---

## 1. Audit Findings & Root Cause Analysis

### 1.1 Keamanan & Secret Exposure (Phase 0)
- **Problem**: Validasi environment variable bersifat parsial, tidak ada `SECURITY.md`, dan file rahasia berpotensi terbaca ke dalam log atau Docker build context.
- **Root Cause**: Tidak adanya validasi tipe terpusat pada startup dan ketiadaan `.dockerignore`.
- **Remediasi**: Diterapkan `config.py` fail-fast tanpa membocorkan nilai rahasia, dibuat `SECURITY.md`, diperbarui `.dockerignore`, dan dipin versi runtime ke Python 3.11.9 via `requirements.lock`.

### 1.2 Data Fabrication & Nilai Fallback Palsu (Phase 1)
- **Problem**: Saat API Yahoo Finance atau Web Search mengalami rate-limit atau libur, kode mengembalikan angka palsu (seperti USD/IDR `17,950` atau harga minyak statis) yang mengotori analisis dan model evaluasi.
- **Root Cause**: Penggunaan literal default pada exception handler alih-alih melempar error atau mengembalikan `None`.
- **Remediasi**: Seluruh fallback palsu dihilangkan. Nilai yang gagal diambil secara eksplisit bernilai `None`/`Unavailable`, dipropagasi ke UI, dan diberi penanda `isWebFallback` jika diambil dari sumber sekunder.

### 1.3 Inkonsistensi Matematika & Formula Penilaian (Phase 2)
- **Problem**: Evaluasi akurasi IHSG menggunakan ambang batas yang tidak konsisten (kadang 0.1%, kadang 0.25%). Foreign flow salah mengartikan "Net Buy Rp 10 Miliar" sebagai arah signifikan. Sesi libur dihitung sebagai "gagal".
- **Root Cause**: Tidak ada definisi kanonikal di tingkat utilitas bersama.
- **Remediasi**:
  - Dibuat `utils/direction.py` dengan threshold netral kanonikal `±0.20%`.
  - Dibuat `utils/flow.py` dengan threshold materialitas `±Rp 1.0 Triliun` dan proteksi mismatch tanggal.
  - Dibuat `utils/stats.py` yang memisahkan akurasi arah, aliran dana, dan sektor secara independen. Sesi tidak scorable (libur/suspensi) dikeluarkan dari denominator.
  - Riwayat sesi dire-score menggunakan `scripts/rescore_history.py`.

### 1.4 Redundansi Query & Pemborosan Kuota (Phase 3)
- **Problem**: Tavily search dan Yahoo Finance dipanggil berulang kali untuk query yang sama dalam rentang hitungan menit antara agent yang berbeda.
- **Root Cause**: Arsitektur agent terisolasi tanpa shared state cache.
- **Remediasi**: Ditambahkan in-memory query cache dengan TTL 30 menit berbasis SHA-256 di `web_agent.py`, serta fungsi terpadu `fetch_all_commodities()` di `market_data.py`. Checkpoint status pipeline disimpan di `pipeline_status.json`.

### 1.5 Kerentanan LLM Parsing & Ketergantungan Tunggal (Phase 4)
- **Problem**: Model reasoning sering mengembalikan format pemikiran (`<think>...`), markdown ticks, atau JSON yang terpotong saat context token mencapai batas, menyebabkan crash `json.loads()`.
- **Root Cause**: Parsing JSON primitif tanpa normalisasi output model open-weights.
- **Remediasi**: Diterapkan parser berjenjang di `utils/json_parser.py` (stripping tag, recursive bracket extraction, comma cleaning, partial repair). Ditambahkan multi-provider fallback (OpenRouter -> DeepInfra -> Gemini) dengan timeout 45s dan deteksi pemotongan token di `llm_client.py`.

### 1.6 Kegagalan IO, Concurrency, & Lisensi Data (Phase 5)
- **Problem**: Penulisan JSON langsung berisiko merusak data jika proses terhenti di tengah jalan. SQLite mengalami `database locked`. Kegagalan Obsidian membuat pipeline terblokir. Penggunaan Yahoo Finance tanpa batas lisensi berisiko hukum.
- **Root Cause**: Tidak ada atomic write file, SQLite tidak menggunakan WAL mode, Obsidian sinkronisasi secara blocking, dan tidak ada layer provider terisolasi.
- **Remediasi**:
  - Penulisan artefak via temporary file + atomic rename di `memory/artifacts.py`.
  - SQLite diatur ke WAL mode (`PRAGMA journal_mode = WAL;`) dengan timeout busy 30 detik di `memory/session.py`.
  - Obsidian dipindahkan ke background task dengan circuit breaker.
  - Dibuat kalender libur bursa IDX di `core/calendar.py` dan `data/idx_holidays.json`.
  - Dibuat provider boundary di `data_sources/provider.py` dengan penegakan flag `NEXUS_PUBLIC_MODE`.

### 1.7 Inkonsistensi Jadwal, Race Condition, & Circular Imports (Phase 6)
- **Problem**: Jadwal cron berbeda antara README (07:00), bat scripts (06:30), dan GitHub Actions (06:55). Circular import antara `market_agent` dan `evening_reviewer`. Dua instance scheduler bisa berjalan bersamaan.
- **Root Cause**: Konfigurasi waktu terpecah di berbagai file.
- **Remediasi**: Dibuat `schedule.yaml` dan `core/schedule.py` sebagai sumber kebenaran tunggal (**06:55 WIB** dan **20:00 WIB**). Ditambahkan file lock inter-process di `core/locking.py`. Circular imports dipindahkan ke `utils/dates.py`. Paket distandarisasi via `pyproject.toml` dan `nexus/__main__.py`.

### 1.8 Zona Waktu Naif, Kebocoran Privasi, & Kegagalan Telegram (Phase 7)
- **Problem**: Pemanggilan `datetime.now()` naif menyebabkan pergeseran tanggal saat dijalankan di cloud UTC. Data prompt user dan respon mentah masuk ke `telemetry.json`. Pesan Telegram melebihi limit 4096 karakter dan crash saat rate limit.
- **Root Cause**: Ketiadaan standar waktu aplikasi terpusat dan formatting raw HTML yang tidak disanitasi.
- **Remediasi**:
  - Dibuat `core/time.py` dengan kanonikal `Asia/Jakarta` (`jakarta_now()`).
  - `telemetry.json` publik dibersihkan dari field privat (`query`, `result`).
  - Telegram bot dilengkapi HTML converter aman, paragraph chunker di `utils/text.py`, dan retry-after backoff di `delivery/telegram.py`.
  - Validasi schema runtime diimplementasikan di `schemas.py`.

### 1.9 Dashboard Hardening, Akses Terbatas, & Error Boundaries (Phase 8)
- **Problem**: Dashboard tidak memiliki Content Security Policy, membaca seluruh folder `runs/` secara filesystem crawl lambat, tidak ada boundary error React, dan tidak ada disclaimer regulasi OJK/IDX.
- **Root Cause**: Konfigurasi default Next.js tanpa middleware keamanan atau manifest pre-komputasi.
- **Remediasi**:
  - Diterapkan CSP dan security headers di `dashboard/next.config.mjs`.
  - Ditambahkan Basic Auth gate via `dashboard/src/middleware.js`.
  - Dibuat generator indeks cepat `runs/index.json` di `sync-runs.mjs`.
  - Disediakan `error.js`, `loading.js`, `not-found.js`, `robots.js`, dan `sitemap.js`.
  - Ditambahkan badge kualitas data (`⚡ WEB FALLBACK`, `⏸ UNSCORABLE`).
  - Ditambahkan `LegalDisclaimerBanner` dan `LegalDisclaimerFooter` di antarmuka.

---

## 2. Verification Summary

| Test Suite | File | Tests | Status |
|---|---|---|---|
| Configuration & Secrets | `tests/test_config.py` | 3 | PASSED |
| Core Abstractions | `tests/test_core.py` | 3 | PASSED |
| Zero Data Fabrication | `tests/test_phase1_no_fabricated_data.py` | 6 | PASSED |
| Scoring & Rescoring Math | `tests/test_phase2_scoring_fixes.py` | 9 | PASSED |
| Query Caching & Deduplication | `tests/test_phase3_deduplication.py` | 3 | PASSED |
| LLM Fault Tolerance & Parsing | `tests/test_phase4_llm_reliability.py` | 5 | PASSED |
| Licensing & Provider Boundaries | `tests/test_phase5_data_sources_licensing.py` | 4 | PASSED |
| Storage Resilience & WAL | `tests/test_phase5_storage_resilience.py` | 7 | PASSED |
| Scheduling & Run Locks | `tests/test_phase6_scheduling_automation.py` | 7 | PASSED |
| Timezones, Schemas & Telemetry | `tests/test_phase7_timezones_telemetry.py` | 7 | PASSED |
| Next.js Production Build | `dashboard/` (`npm run build`) | All Pages | COMPILED & GENERATED (Code 0) |
| **Total Test Suite** | `pytest tests/` | **54** | **100% PASSED** |

---

## 3. Unresolved Items / Out of Scope

Semua 10 fase dari prompt audit telah **diselesaikan 100%**. Tidak ada item tertunda.
Sistem siap untuk operasional lokal maupun cloud CI/CD.
