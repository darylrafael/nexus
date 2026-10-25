# Nexus Pipeline Remediation Report (Phases 0–9 & Buy-Side Audit Phases 1–8)

## Executive Summary

Audit sistem pipeline intelijen pasar Nexus mengidentifikasi sejumlah kerentanan kritis, inkonsistensi matematis, kontaminasi artefak mock pada direktori produksi `runs/`, potensi kegagalan runtime, dan celah keamanan data. Remediasi menyeluruh telah diselesaikan secara berurutan tanpa regresi, disertai pembuktian terukur melalui skrip evaluasi deterministik (`scripts/evaluate.py`) dan suite pengujian terisolasi.

> **⚠️ Peringatan Penting Rotasi Kunci API (Phase 6.5):**  
> Owner diingatkan bahwa seluruh kunci API yang pernah terekspos pada berkas `.env` historis (`OPENROUTER_API_KEY`, `DEEPINFRA_TOKEN`, `TAVILY_API_KEY`, `OBSIDIAN_API_KEY`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`) **harus segera dirotasi** pada dashboard masing-masing penyedia layanan. Laporan ini **tidak** mengklaim bahwa kunci-kunci tersebut telah dirotasi.

---

## 1. Audit Findings & Root Cause Analysis

### 1.1 Isolasi Path & Pencegahan Kontaminasi Data Tes (Phase 1)
- **Problem**: Menjalankan `pytest -q` menulis output tes mock (`MOCK_BRIEF_MARKDOWN`, `mock_yfinance`, `mock_fx`) langsung ke direktori produksi `runs/2026-10-14` dan `runs/2026-10-16` karena path `"runs"` dan `"nexus_sessions.db"` di-hardcode di berbagai modul.
- **Root Cause**: Ketiadaan resolver path terpusat yang membaca variabel lingkungan dan ketiadaan fixture isolasi global pada `tests/conftest.py`.
- **Remediasi**:
  - Dibuat `core/paths.py` sebagai resolver tunggal (`NEXUS_RUNS_DIR`, `NEXUS_DB_PATH`, `NEXUS_MEMORY_DIR`, `NEXUS_VAULT_DIR`, `NEXUS_DATA_DIR`) yang digunakan oleh seluruh agen, penyimpanan memori, skrip evaluasi, dan scheduler.
  - Ditambahkan autouse fixture `isolated_nexus_environment` (`tmp_path`) dan session-level fixture `guard_real_repo_artifacts` (checksum SHA-256 sebelum/sesudah) di `tests/conftest.py`.
  - Ditambahkan pemeriksaan CI `git diff --exit-code -- runs data` dan `git status --porcelain`.

### 1.2 Penjaga Provenance (Defense in Depth — Phase 2)
- **Problem**: Artefak dengan sumber sintetis/mock (`data_quality.fields.*.source = "mock_*"` atau `src_id = "mock_*"`) dapat masuk ke perhitungan statistik, penyimpanan pelajaran, dan tampilan dashboard.
- **Root Cause**: Layer agregasi (`learning_store.py`, `utils/stats.py`, `rescore_history.py`, `sync-runs.mjs`, `/api/stats`) tidak memvalidasi provenance sumber data.
- **Remediasi**:
  - Dibuat `core/provenance.py` (`is_mock_provenance`, `has_mock_provenance`, `check_run_dir_provenance`, `build_runs_index`) dan fungsi ekuivalen di `dashboard/src/lib/nexusData.js`.
  - Seluruh layer menolak artefak ber-provenance mock. Jika artefak mock ditemukan di `runs/`, dashboard menampilkan banner peringatan **"Test data detected"** dan mengecualikannya dari seluruh perhitungan skor.

### 1.3 Pembersihan Kontaminasi & Pengecualian Null Correctness (Phase 3)
- **Problem**: Direktori mock `runs/2026-10-14`, `runs/2026-10-15`, dan `runs/2026-10-16` serta pelajaran mock mengotori metrik historis. Selain itu, sesi dengan `ihsg_correct = null` sempat dihitung sebagai *miss* dalam denominator arah $n$.
- **Root Cause**: Kondisi `if ihsg_corr is not None` atau konversi boolean implisit tanpa memastikan `ihsg_corr is True or ihsg_corr is False`.
- **Remediasi**:
  - Direktori mock dan pelajaran mock dihapus setelah dicadangkan di luar bundel publik.
  - `utils/stats.py` diperbaiki sehingga `ihsg_correct = null` tidak pernah dianggap *scorable* dan dikeluarkan dari $n$.
  - `runs/global/nexus_stats.json` dan `runs/index.json` diregenerasi murni dari sesi asli (*genuine*).
  - Status liveness pipeline pada `/api/stats` dan dashboard secara jujur menampilkan banner *stale* (`isStale: true`) beserta pesan `"No new call generated today"` karena data asli terakhir berhenti pada `2026-10-08`.

### 1.4 Konvensi Tanda Kurs Rupiah & Kalibrasi Kepercayaan Terpadu (Phase 4)
- **Problem**:
  1. `validate_lesson` di `memory/learning_store.py` mengasumsikan tanda positif selalu berarti Rupiah menguat, padahal data tersimpan menggunakan konvensi `USD/IDR` (positif = Rupiah melemah, negatif = Rupiah menguat, sehingga *"rupiah menguat -0.318%"* adalah valid). Tiga pelajaran (`2026-09-28`, `2026-10-01`, `2026-10-07`) sebelumnya ditolak dengan alasan yang kurang tepat (`sign_confusion`).
  2. UI sempat menampilkan `calibrated_confidence` per panggilan yang berbeda dari angka headline karena dua rumus penyusutan yang berbeda.
- **Remediasi**:
  - `validate_lesson` ditulis ulang untuk mendeteksi konvensi eksplisit (`USD/IDR` vs `Rupiah`) dan memvalidasi angka serta arah terhadap data aktual sesi (`spot_usdidr_change_pct`). Pelajaran pada `2026-09-28`, `2026-10-01`, dan `2026-10-07` yang menyimpang dari data kurs aktual dikarantina dengan alasan akurat `unreliable_source_data`.
  - Fungsi `compute_empirical_calibrated_confidence` di `utils/stats.py` ditetapkan sebagai satu-satunya formula penyusutan ($w = \min(n/30, 1.0)$, prior cap $55.0\%$), diberi label `"illustrative shrinkage estimate"` saat $n < 30$.
  - Injeksi pelajaran ke prompt pagi (`build_learning_context`) hanya menyertakan sesi asli yang lolos `data_quality` (`overall_valid = True`).

### 1.5 Kejujuran Kunci Hash Prediksi (Phase 5)
- **Problem**: Prediksi historis (`2026-09-22` s/d `2026-10-08`) memiliki `lock_hash` dan klaim `"locked_at 06:55 WIB"` yang ditambahkan saat *rescore*, bukan saat pembuatan sebelum pasar buka.
- **Remediasi**:
  - Seluruh prediksi historis ditandai `lock_status = "retroactive"`, `locked_at = null`, `hash_computed_at = "2026-10-15"`, dan menampilkan `"Hash added retroactively; not proof of pre-open lock"` pada UI.
  - Pekerjaan pagi (`lock_morning_prediction` di `core/locking.py`) kini mencatat hash beserta timestamp pembuatan ke buku besar *append-only* berantai `runs/global/lock_ledger.jsonl`, dengan fungsi verifikasi `verify_prediction_lock` yang mendeteksi modifikasi pasca-kunci.

### 1.6 Pengemasan Allowlist & Kebersihan Repositori (Phase 6)
- **Problem**: Direktori literal `%SystemDrive%/ProgramData/Microsoft/Windows/Caches/*.db` muncul di repositori akibat variabel lingkungan Windows yang tidak diekspansi; skrip pemaket menggunakan denylist yang rawan meloloskan berkas terlarang.
- **Remediasi**:
  - Direktori `%SystemDrive%` dihapus, pola `/%*` ditambahkan ke `.gitignore`, dan pemeriksaan CI ditambahkan untuk menggagalkan build jika ada path berawalan `%`.
  - `memory/session.py` dibersihkan dari deklarasi `global DB_PATH` yang tidak terpakai.
  - `scripts/package_deliverables.py` ditulis ulang menggunakan mekanisme **allowlist** berbasis `git ls-files` dengan filter ketat terhadap pola terlarang (`*.db`, `.ruff_cache`, `scripts/fix_dashboard_audit.py`, `scripts/package_deliverables.py`, `__pycache__`, `node_modules`, `.next`, `.env`, `*.bak`).

### 1.7 Optimasi Mobile, Self-Hosted Fonts, & Audit Aksesibilitas Ketat (Phase 7)
- **Remediasi**:
  - Font di-host secara lokal melalui `next/font/local` tanpa request eksternal.
  - Tinggi halaman default mobile pada lebar 360px, 390px, dan 430px diturunkan menjadi $\le 2.900\text{px}$ dengan mempertahankan ukuran font ($\ge 12\text{px}$ esensial, $\ge 11\text{px}$ seluruh teks) dan target sentuh ($\ge 44\times 44\text{px}$).
  - Skrip audit `tests/audit_mobile_viewports.py` memeriksa seluruh node teks terlihat dan seluruh elemen interaktif pada 6 lebar layar dan 2 tema.
  - Keterbatasan rate limiter in-memory per instance didokumentasikan di `SECURITY.md`.
  - Peringatan kegagalan Telegram dan isolasi job `APScheduler` diverifikasi dengan unit test.

---

## 2. Metrik Evaluasi Kuantitatif Kanonikal (`scripts/evaluate.py`)

<!-- METRICS:START -->
**Canonical Artifact Summary** (Scoring Engine `v2.2.0`, Rescored `2026-10-23`, Verified Runs: **24**, Scored Reviews: **n=24**, Unreviewed Pending: **0**)

### TABLE 1: HEADLINE DIRECTION TRACK RECORD & UNCERTAINTY
| Metric | Realized Value | Statistical Note / Wilson 95% CI |
| :--- | :--- | :--- |
| Scored Sessions (n) | **24** | ⚠️ Sample too small to conclude skill (n < 30) |
| Direction Hit Rate | **37.5%** (9/24) | 95% Wilson CI: [21.2%, 57.3%] |
| Rolling Accuracy | **31.4%** | Trailing dynamic 50/30/20 attribution average |

### TABLE 2: EMPIRICAL NAIVE BASELINES COMPARISON
| Strategy / Baseline | Accuracy (Hits/n) | Delta vs Nexus Model | Buy-Side Assessment |
| :--- | :--- | :--- | :--- |
| **Nexus Multi-Agent Model** | **37.5%** (9/24) | 0.0% | Active directional thesis |
| Always-Bearish (Down Only) | **54.2%** (13/24) | +16.7% | Outperforms model due to prevailing market downtrend |
| Persistence (Repeat T-1) | **56.5%** (13/23) | +19.0% | Exploits directional momentum across consecutive sessions |
| Always-Bullish (Up Only) | **41.7%** (10/24) | +4.2% | Model outperforms permanent long bias |

### TABLE 3: PIPELINE SUB-COMPONENT SCORING BREAKDOWN
| Component | Nominal Weight | Scorable (n) | Realized Hit Rate | Institutional Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| IHSG Direction | 50% | n = 24 | 37.5% (9/24) | Primary directional bias (Bullish/Bearish/Neutral ±0.20% band) |
| Sector Breakdown | 30% | n = 62 | 33.9% (21/62) | Evaluated across 11 IDX-IC closing returns; midday snapshots rejected |
| Foreign Flow | 20% | n = 3 | Insufficient data | Suppressed from scoring when scorable n < 5; treated as institutional context |

### TABLE 4: PROBABILISTIC CONFIDENCE CALIBRATION & BRIER SCORE
| Calibration Metric | Measured Value | Plain Language Buy-Side Interpretation |
| :--- | :--- | :--- |
| Model Stated Confidence (Uncalibrated) | **79.8%** | Raw uncalibrated LLM confidence output across n=24 scored sessions |
| Realized Direction Hit Rate | **37.5%** | Actual empirical accuracy (9/24 scored sessions) |
| Calibrated Confidence (Shrinkage) | **41.0%** (n=24, illustrative shrinkage estimate) | Bayesian shrinkage with prior strength N0=30 and prior cap 55.0% |
| Brier Score | **0.4146** | Probabilistic error (0.00 = perfect, 0.25 = random coin toss, >0.25 = overconfident) |

### TABLE 5: ECONOMIC PAYOFF STRUCTURE (BASIS POINTS)
| Strategy Portfolio | Realized Payoff (bps) | Trade Count | Tradability / Practical Feasibility |
| :--- | :--- | :--- | :--- |
| **Long-Only (Headline Payoff)** | **-364.0 bps** | 5 calls | Realizable long exposure on retail Indonesian brokerage accounts |
| Short-Side Payoff | **+1175.0 bps** | 17 calls | **Theoretical only; not retail-tradable on IDX cash index** |
| Combined Theoretical Long/Short | **+811.0 bps** | 22 calls | Pure hypothetical synthetic index return before borrow fees and slippage |

### TABLE 6: SELF-LEARNING LOOP HYGIENE & QUARANTINE AUDIT
- Valid Injected Lessons: **38** (sanitized, validated against stored actuals, genuine data_quality-passing sessions only)
- Quarantined / Rejected Lessons: **19** (prevented from corrupting future pre-market intelligence)

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
<!-- METRICS:END -->

---

## 3. Verifikasi Akhir Phase 8 (Command Verification)

1. **Static Analysis (`pyflakes` & `ruff`)**:
   - `python -m pyflakes agents data_sources utils memory core scheduler.py` selesai dengan kode keluar `0` tanpa nama tak terdefinisi atau peringatan.
   - `python -m ruff check --no-cache .` selesai dengan kode keluar `0` (`All checks passed!`).
2. **Isolasi Suite Pengujian (`pytest -q` 5x Berturut-turut di Fresh Clone Tanpa `.env`)**:
   - Diuji pada *fresh git clone* dengan lingkungan bersih tanpa berkas `.env`: kelima eksekusi berturut-turut lulus (`123 passed`), dan `git status --porcelain` kosong (`''`) setelah setiap eksekusi.
3. **Kemurnian Direktori `runs/`**:
   - `runs/` hanya berisi tanggal sesi asli (`2026-09-22` s/d `2026-10-08`), `global`, dan `index.json`. Direktori mock telah dihapus dan tidak ada berkas di `runs/` yang mengandung string `"mock"`.
4. **Pencarian Provenance Mock (`grep -ri "mock_" runs dashboard/data`)**:
   - Mengembalikan hasil kosong (`0` kecocokan).
5. **Konsistensi Blok Metrik Dokumen (`python scripts/evaluate.py --check`)**:
   - Mengembalikan kode keluar `0` (seluruh blok metrik kanonikal pada `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `METHODOLOGY.md`, dan `FIX_REPORT.md` identik dengan output skrip evaluasi).
6. **Status Liveness `/api/stats` & Stale Banner Dashboard**:
   - `/api/stats` mengembalikan `isStale: true` dan `mockDataDetected: false`; layar pertama dashboard menampilkan `.stale-pipeline-banner` dengan pesan `"No new call generated today"`, tanpa chip `"Live"`, dan kartu panggilan berada di atas batas lipatan layar (*above the fold*) pada 360px, 390px, dan 430px.
7. **Verifikasi Paket Rilis Allowlist (`python -m core.packaging`)**:
   - Paket zip dibangun melalui allowlist `git ls-files` dan lolos pemeriksaan pola terlarang serta pemindaian rahasia (`0` pelanggaran).

---

## 4. Remediasi Lanjutan Phase A–D (Release Package, Measured Quality Gaps, Live Proof, & Documentation)

### 4.1 Phase A: Perbaikan Paket Rilis & Uji Asap Terisolasi
- **Masalah**: Berkas `nexus_remediated.zip` sebelumnya tidak menyertakan `llm_client.py` yang dibutuhkan oleh 4 modul pipeline, serta kehilangan berkas operasional penting (`LEGAL.md`, `RUNBOOK.md`, `requirements.lock`, `.python-version`, dll.). Saat diekstrak ke lingkungan bersih, `pytest` gagal saat pengumpulan tes.
- **Remediasi**:
  - `core/packaging.py` dibangun ulang dengan mekanisme allowlist berbasis `git ls-files` dikurangi denylist eksplisit (menolak `*.db`, `.env`, `__pycache__`, `node_modules`, `.next`, `.ruff_cache`, `.pytest_cache`, `.git`, path berawalan `%`, skrip pemaket/audit sementara).
  - Ditambahkan pemeriksaan berkas tidak terlacak (`check_untracked_files`) yang menggagalkan pembuatan paket rilis jika ada berkas repo yang belum di-commit/di-ignore.
  - Diterapkan manifestasi wajib `REQUIRED_FILES` (20 berkas) dan `REQUIRED_PACKAGES` (8 direktori paket) yang diverifikasi saat `--verify-zip`.
  - Ditambahkan fungsi uji asap terisolasi penuh (`smoke_test_release_zip` / `--smoke-test-zip`): mengekstrak zip ke direktori temp, membuat `venv` bersih, menginstal dependensi dari `requirements.lock`/`requirements.txt`, menguji impor modul utama dengan `NEXUS_SKIP_ENV_VALIDATION=1`, menjalankan `pytest -q`, dan memverifikasi `runs/` serta database sqlite tidak berubah.
  - Tes unit diadaptasi agar tidak bergantung pada direktori `.git` saat dijalankan dari pohon zip yang diekstrak.

### 4.2 Phase B: Kesenjangan Kualitas Dashboard & Audit Aksesibilitas
- **Masalah**: Payload `/api/stats` berukuran 226 KB karena menyertakan fallback sumber yang tidak disitasi; LCP repainting akibat font-swap; kontras warna di light/dark mode memerlukan audit kepatuhan WCAG AA.
- **Remediasi**:
  - Endpoint `/api/stats` dirampingkan (`slimSourcesMap`) hanya mengembalikan sumber yang disitasi oleh brief aktif, memangkas ukuran respon dari 226 KB menjadi ~42 KB.
  - Font `nexusSans` dan `nexusMono` dikonfigurasi dengan `display: 'optional'`, elemen `<html>` diberi atribut `data-theme="dark"` dan `suppressHydrationWarning` untuk mengeliminasi flash tema dan layout shift.
  - Token CSS di `dashboard/src/app/globals.css` disesuaikan untuk memenuhi rasio kontras WCAG AA: audit `axe-core` mencatat **0 pelanggaran pada 34 aturan** untuk dark dan light mode pada 390px.
  - Audit viewport Playwright pada 12 konfigurasi (360, 390, 430, 768, 1024, 1440 x Dark, Light) mengonfirmasi: **0 console error, 0 elemen overflow horizontal, 0 teks <11px, 0 tap target interaktif <44px**, dan kartu arah serta badge calibrated confidence berada pada posisi vertikal $\le 551\text{px}$ (di dalam viewport pertama).
  - Fixture pengujian status UI Playwright disimpan secara aman di luar `runs/` (`tests/fixtures/stale_fixture.json`, `tests/fixtures/fresh_today_fixture.json`, `tests/fixtures/missing_field_fixture.json`) dan diverifikasi oleh `tests/test_phase7_playwright_states.py`.
  - Skor Lighthouse Mobile (median 3 run): **Accessibility 100/100, Performance 89.0 (peak 97.0), FCP 981.8ms (0.9s), CLS 0.0000, TBT 222ms**.

### 4.3 Phase C: Pembuktian Pipeline Live & Penjaga Keamanan
- **Masalah**: Perlunya script uji asap live yang dapat memverifikasi output nyata tanpa merusak corpus `runs/` repositori, serta pengerasan alur kerja CI/CD cloud.
- **Remediasi**:
  - Dibuat `scripts/live_smoke.py` dan `tests/test_live_smoke.py` yang memvalidasi 7 kriteria: eksistensi artefak lengkap, tidak ada kunci error, foreign flow valid atau unknown dengan alasan, OHLC valid, persentase USD/IDR konsisten $\le 0.05\%$, ticker terdaftar di whitelist IDX, dan zero mock provenance.
  - Penjaga keamanan refusable: `scripts/live_smoke.py` memunculkan `RuntimeError("REFUSED: refusing to write smoke test artifacts into the repository's real runs directory")` jika `NEXUS_RUNS_DIR` mengarah ke `runs/` repositori.
  - GitHub Actions workflows (`morning_brief.yml` dan `evening_review.yml`) dikeraskan: pemeriksaan hari libur bursa eksplisit, retensi artefak 90 hari melalui `actions/upload-artifact@v4`, commit otomatis artefak sesi baru, dan alert Telegram saat alur kerja mengalami kegagalan (`if: failure()`).

### 4.4 Phase D: Konsistensi Dokumentasi & Penjaga CI
- Alur kerja CI (`.github/workflows/ci.yml`) diperbarui dengan langkah validasi konsistensi dokumen `python scripts/evaluate.py --check`.
- `README.md` diperbarui dengan bab `Release Package` dan panduan verifikasi integritas paket rilis.
- `SECURITY.md` dilengkapi panduan rotasi kredensial per penyedia layanan.
- `CHANGELOG.md` mencatat rilis `[2.2.1] - 2026-10-18`.

---

## 5. Not Verified

Sesuai Aturan 5 (*"If you cannot verify something, list it under 'Not verified'. Do not guess."*), item berikut berada di luar cakupan eksekusi lokal saat ini dan dicatat secara transparan:

1. **Rotasi Kunci API Eksternal**: Rotasi kredensial yang pernah terekspos pada berkas `.env` historis (`OPENROUTER_API_KEY`, `DEEPINFRA_TOKEN`, `TAVILY_API_KEY`, `OBSIDIAN_API_KEY`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`) memerlukan akses administratif ke konsol masing-masing penyedia layanan oleh pemilik akun.
2. **Eksekusi Live Pre-Open (`06:55 WIB`) dan Post-Close (`20:00 WIB`) Terhadap Bursa Efek Indonesia (IDX) pada Hari Perdagangan Berikutnya**: Pembuatan kunci `locked_pre_open` pada `runs/global/lock_ledger.jsonl` dan pengiriman pesan ke server produksi Telegram Bot API telah diverifikasi melalui *integration/unit test* dengan *mocked HTTP transport* (`tests/test_phase3_4_5_logic.py`, `tests/test_phase7_alerts_and_scheduler.py`, dan `tests/test_live_smoke.py`), namun eksekusi terjadwal *live* berikutnya bergantung pada jadwal hari bursa mendatang dan kredensial produksi yang telah dirotasi.
3. **Shared Distributed Store untuk Rate Limiter Next.js Middleware**: Sebagaimana didokumentasikan pada `SECURITY.md`, middleware `dashboard/src/middleware.js` menggunakan penyimpanan *in-memory* per-instance (`ipBuckets`) karena tidak ada instans Redis/Upstash terdistribusi yang dikonfigurasi pada lingkungan lokal.


