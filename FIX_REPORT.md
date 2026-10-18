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
   - Mengembalikan kode keluar `0` (seluruh blok `<!-- METRICS:START -->
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
<!-- METRICS:END -->` pada `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `METHODOLOGY.md`, dan `FIX_REPORT.md` identik dengan output skrip).
6. **Status Liveness `/api/stats` & Stale Banner Dashboard**:
   - `/api/stats` mengembalikan `isStale: true` dan `mockDataDetected: false`; layar pertama dashboard menampilkan `.stale-pipeline-banner` dengan pesan `"No new call generated today"`, tanpa chip `"Live"`, dan kartu panggilan berada di atas batas lipatan layar (*above the fold*) pada 360px, 390px, dan 430px.
7. **Verifikasi Paket Rilis Allowlist (`python -m core.packaging`)**:
   - Paket zip dibangun melalui allowlist `git ls-files` dan lolos pemeriksaan pola terlarang serta pemindaian rahasia (`0` pelanggaran).

---

## 4. Not Verified

Sesuai Aturan 5 (*"If you cannot verify something, list it under 'Not verified'. Do not guess."*), item berikut berada di luar cakupan eksekusi lokal saat ini dan dicatat secara transparan:

1. **Rotasi Kunci API Eksternal**: Rotasi kredensial yang pernah terekspos pada berkas `.env` historis (`OPENROUTER_API_KEY`, `DEEPINFRA_TOKEN`, `TAVILY_API_KEY`, `OBSIDIAN_API_KEY`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`) memerlukan akses administratif ke konsol masing-masing penyedia layanan oleh pemilik akun.
2. **Eksekusi Live Pre-Open (`06:55 WIB`) dan Post-Close (`20:00 WIB`) Terhadap Bursa Efek Indonesia (IDX) pada Hari Perdagangan Berikutnya**: Pembuatan kunci `locked_pre_open` pada `runs/global/lock_ledger.jsonl` dan pengiriman pesan ke server produksi Telegram Bot API telah diverifikasi melalui *integration/unit test* dengan *mocked HTTP transport* (`tests/test_phase3_4_5_logic.py` dan `tests/test_phase7_alerts_and_scheduler.py`), namun eksekusi terjadwal *live* berikutnya bergantung pada jadwal hari bursa mendatang dan kredensial produksi yang telah dirotasi.
3. **Shared Distributed Store untuk Rate Limiter Next.js Middleware**: Sebagaimana didokumentasikan pada `SECURITY.md`, middleware `dashboard/src/middleware.js` menggunakan penyimpanan *in-memory* per-instance (`ipBuckets`) karena tidak ada instans Redis/Upstash terdistribusi yang dikonfigurasi pada lingkungan lokal.

