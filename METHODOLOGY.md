# Nexus Quantitative & Analytical Methodology (v2.2.0)

Dokumen ini mendefinisikan formula, bobot matematis, ambang batas (*thresholds*), dan protokol evaluasi yang digunakan oleh Nexus dalam memprediksi serta menguji kinerja harian Indeks Harga Saham Gabungan (IHSG). Seluruh angka realisasi pada bagian akhir dokumen ini dihasilkan secara otomatis dari artefak kanonikal (`runs/global/nexus_stats.json` dan `runs/index.json`) oleh `scripts/evaluate.py`.

---

## 1. Komposit Penilaian Harian (Composite Accuracy Score)

Nexus mengevaluasi prediksi harian secara deterministik tanpa campur tangan LLM (*post-market evaluation*). Skor komposit harian (`accuracy_score`) dihitung menggunakan bobot kanonikal berikut:

$$\text{Accuracy Score} = \sum_{c \in \text{Scorable}} \left( \frac{W_c}{\sum_{k \in \text{Scorable}} W_k} \times \text{Score}_c \right)$$

| Komponen | Bobot Nominal ($W_c$) | Deskripsi Komponen | Kondisi Scorable |
| :--- | :--- | :--- | :--- |
| **IHSG Direction** | **50%** ($0.50$) | Prediksi arah indeks (Bullish / Bearish / Neutral) | `ihsg_correct` bernilai boolean (`True` atau `False`), penutupan resmi IHSG tersedia, dan validasi OHLC lolos. Nilai `null` dikeluarkan dari denominator $n$. |
| **Sector Allocation** | **30%** ($0.30$) | Hit rate prediksi terhadap 11 indeks sektoral IDX-IC | Data sektoral merupakan harga penutupan resmi (sesi I / intraday ditolak). |
| **Foreign Flow** | **20%** ($0.20$) | Arah aliran dana institusional asing pasar reguler | Tanggal berita cocok ketat (D/M/Y) dengan tanggal sesi dan scorable $n \ge 5$. |

> **Dynamic Renormalization Rule:**  
> Jika suatu komponen tidak dapat dinilai (*unscorable*, misalnya data aliran dana asing tidak memiliki kecocokan tanggal yang valid, atau `ihsg_correct` bernilai `null`), bobot komponen tersebut dikecualikan dan bobot komponen tersisa direnormalisasi ke 100%. Jika seluruh komponen tidak memiliki data yang scorable, sesi dinyatakan *Unscorable* (`null`).

---

## 2. Aturan Sampel Kecil & Humilitas Statistik (Small-Sample Rules)

Sesuai standar verifikasi buy-side institusional, Nexus menerapkan aturan perlindungan ukuran sampel ($n$):

1. **Ambang Batas Minimum ($n < 5$):**
   - Jika jumlah sesi yang scorable $n < 5$, metrik persentase **tidak ditampilkan ke publik** (`null`) dan digantikan oleh label `"Insufficient data"`.
   - Mencegah representasi keliru dari sampel ekstrem kecil.
2. **Peringatan Sampel Terbatas ($5 \le n < 30$):**
   - Jika $5 \le n < 30$, persentase ditampilkan namun wajib disertai label transparan `"Sample too small to conclude skill (n < 30)"`.
   - Interval kepercayaan Wilson 95% (*Wilson Score Confidence Interval*) wajib disertakan untuk menunjukkan rentang ketidakpastian statistik.
3. **Sampel Memadai ($n \ge 30$):**
   - Diperlukan minimal 30 sesi independen sebelum klaim keahlian prediktif (*predictive skill*) dapat diuji secara parametrik.

---

## 3. Klasifikasi Arah Indeks (Directional Classification)

Ambang batas materialitas pergerakan harian IHSG ditetapkan sebesar **±0.20% (20 basis poin)**:

| Persentase Perubahan Penutupan ($P$) | Klasifikasi Resmi | Penjelasan |
| :--- | :--- | :--- |
| $P \ge +0.20\%$ | **BULLISH** | Penguatan indeks material |
| $-0.20\% < P < +0.20\%$ | **NEUTRAL** | Fluktuasi mendatar / konsolidasi sempit |
| $P \le -0.20\%$ | **BEARISH** | Pelemahan indeks material |

- **Hit:** $\text{Klasifikasi Prediksi} = \text{Klasifikasi Aktual}$ (`ihsg_correct = True`).
- **Miss:** Klasifikasi arah prediksi berbeda dari klasifikasi aktual penutupan (`ihsg_correct = False`).
- **Unscorable:** Jika `ihsg_correct = null` (pasar tutup/data tidak valid), sesi tidak dihitung sebagai Hit maupun Miss dan dikeluarkan dari denominator $n$.

---

## 4. Aliran Dana Asing (Foreign Flow Protocol)

1. **Fokus Pasar Reguler:**
   - Nexus memprioritaskan angka aliran dana asing **pasar reguler** (*regular market*) dengan ambang materialitas $\pm\text{Rp 1.0 Triliun}$. Transaksi pasar negosiasi dan *crossing* dipantau untuk mendeteksi *divergence alert*, namun tidak dimasukkan ke dalam metrik utama guna menghindari distorsi aksi korporasi non-pasar.
2. **Pencocokan Tanggal Ketat (*Strict D/M/Y Matching*):**
   - Teks berita asing wajib mencantumkan tanggal hari-H perdagangan (format tanggal Indonesia D/M/Y). Jika artikel bertanggal lain atau tidak spesifik, sinyal dinyatakan `"Unknown"` dengan alasan `date_mismatch_rejected` dan dikecualikan dari penilaian.
3. **Status Saat Ini:**
   - Selama scorable $n < 5$, metrik aliran dana asing disembunyikan sebagai `"Insufficient data"` dan disajikan semata-mata sebagai konteks deskriptif institusional.

---

## 5. Validasi Integritas Data, Provenance Guard, & Konvensi Kurs Rupiah

1. **Provenance Guard (`core/provenance.py`):**
   - Artefak yang memiliki sumber berawalan `mock` (`data_quality.fields.*.source = "mock_*"` atau ID sumber `mock_*`) atau penanda sintetis (`is_mock`, `synthetic`) ditolak secara otomatis oleh `learning_store`, `utils/stats`, `rescore_history`, `sync-runs.mjs`, dan `/api/stats`.
2. **Validasi Geometris & Kualitas Data (`data_quality`):**
   - **`ohlc_valid`:** Memverifikasi $\text{Low} \le \min(\text{Open}, \text{Close})$ dan $\text{High} \ge \max(\text{Open}, \text{Close})$, serta menolak lilin statis yang identik dengan hari sebelumnya.
   - **`fx_consistent`:** Memverifikasi perubahan persentase kurs dari candle harian berurutan.
   - **`sector_data_is_close`:** Menolak snapshot sektoral intraday/Sesi I.
3. **Aturan Konvensi Tanda Kurs (`USD/IDR` vs `Rupiah`) di `learning_store.validate_lesson`:**
   - Data persentase perubahan kurs yang disimpan dalam pipeline (`spot_usdidr_change_pct`) menggunakan **konvensi kutipan pasangan `USD/IDR`**:
     - Perubahan positif ($+\Delta\%$) berarti `USD/IDR` naik $\implies$ **Rupiah melemah (terdepresiasi)**.
     - Perubahan negatif ($-\Delta\%$) berarti `USD/IDR` turun $\implies$ **Rupiah menguat (terapresiasi)**.
   - Oleh karena itu, pernyataan seperti *"Rupiah menguat -0.318%"* atau *"Rupiah melemah +0.476%"* adalah **valid secara matematis** dalam konvensi `USD/IDR`.
   - Validator mendeteksi apakah pelajaran menyebut eksplisit pasangan `USD/IDR` atau menyebut nilai `Rupiah`, memvalidasi kecocokan angka dan arah terhadap data aktual sesi (`spot_usdidr_change_pct` dalam toleransi $0.15$ poin persentase), dan membedakan secara tegas antara:
     - `sign_confusion`: Kontradiksi tanda internal (misal *"USD/IDR naik -0.50%"* atau *"Rupiah menguat dari Rp17.800 ke Rp17.950"*) atau arah yang berlawanan dengan realisasi aktual.
     - `unreliable_source_data`: Arah tanda konsisten dengan konvensi `USD/IDR`, tetapi besaran persentase yang dikutip LLM menyimpang jauh dari kurs aktual yang terverifikasi pada sesi tersebut.
   - Pelajaran hanya diinjeksi ke prompt pagi apabila berasal dari sesi asli (*genuine*) yang lolos pemeriksaan `data_quality` (`overall_valid = True`).

---

## 6. Kalibrasi Probabilitas (Bayesian Shrinkage) & Brier Score

### 6.1 Definisi Presisi Calibrated Confidence
Untuk mengeliminasi *overconfidence* dari output mentah LLM ($C_{\text{stated}}$, dalam persen $0\text{--}100$), Nexus menerapkan penyusutan empiris (*Bayesian shrinkage*) di `utils/stats.py` (`compute_empirical_calibrated_confidence`):

- **Input:**
  - $k$: Jumlah prediksi arah IHSG yang benar (*hits*) pada korpus terverifikasi.
  - $n$: Jumlah total sesi arah IHSG yang *scorable* ($n > 0$).
  - $C_{\text{stated}}$: Tingkat keyakinan mentah yang dinyatakan oleh model (atau rata-rata keyakinan mentah pada level headline).
- **Parameter Prior:**
  - **Prior Cap ($P_{\text{cap}}$):** $55.0\%$ (`CALIBRATION_PRIOR_CAP_PCT = 55.0`). Membatasi keyakinan prior maksimum sebesar $55.0\%$ sebelum bukti empiris terkumpul.
  - **Prior Strength ($N_0$):** $30$ sesi (`CALIBRATION_PRIOR_STRENGTH = 30`). Setara dengan 30 sesi pseudo-observasi pada tingkat prior $\min(C_{\text{stated}}, P_{\text{cap}})$.
- **Formula Matematis (`utils/stats.py::compute_empirical_calibrated_confidence`):**
  $$w = \min\left(\frac{n}{N_0}, 1.0\right)$$
  $$P_{\text{realized}} = 100 \times \frac{k}{n}, \qquad P_{\text{prior}} = \min\left(C_{\text{stated}}, 55.0\right)$$
  $$C_{\text{calibrated}} = \text{round}\Big(w \cdot P_{\text{realized}} + (1 - w) \cdot P_{\text{prior}},\ 1\Big)$$
- **Contoh Perhitungan Tangan (*Hand-Computed Example*):**
  Untuk korpus saat ini dengan $k = 5$, $n = 12$, $N_0 = 30$, dan $C_{\text{stated}} = 79.6\%$ (atau panggilan tunggal dengan $C_{\text{stated}} = 75\% \ge 55.0\%$):
  $$w = \min\left(\frac{12}{30}, 1.0\right) = 0.40$$
  $$P_{\text{realized}} = 100 \times \frac{5}{12} = 41.6667\%, \qquad P_{\text{prior}} = \min(79.6, 55.0) = 55.0\%$$
  $$C_{\text{calibrated}} = \text{round}\big(0.40 \times 41.6667 + 0.60 \times 55.0,\ 1\big) = \text{round}\big(16.6667 + 33.0,\ 1\big) = \text{round}(49.6667, 1) = \mathbf{49.7\%}$$
- **Penjelasan Diskrepansi Historis (Mengapa UI Sebelumnya Menampilkan 59% vs Headline):**
  Pada versi sebelumnya, `agents/prediction_extractor.py` menghitung `calibrated_confidence` per panggilan menggunakan rumus heuristik terpisah ($0.50 \times C_{\text{stated}} + 0.50 \times P_{\text{realized}}$ tanpa prior cap $55.0\%$, yang menghasilkan $\approx 59\%$ untuk $C_{\text{stated}} = 75\%$), sedangkan `utils/stats.py` menghitung angka headline dengan `prior_cap_pct = 55.0%` dan `N0 = 30`. Diskrepansi tersebut telah **dihapus sepenuhnya**: baik `prediction_extractor.py`, `rescore_history.py`, maupun `/api/stats` kini memanggil fungsi tunggal `compute_empirical_calibrated_confidence` di `utils/stats.py`.
- **Label Sampel Kecil ($n < 30$):**
  Selama $n < 30$, nilai `calibrated_confidence` wajib diberi label **`"illustrative shrinkage estimate"`** beserta ukuran sampelnya `(n=12, illustrative shrinkage estimate)`.

### 6.2 Brier Score
Mengukur akurasi probabilitas kuadratik atas prediksi arah yang *scorable*:
$$\text{Brier} = \frac{1}{n} \sum_{t=1}^{n} \left(\frac{C_{\text{stated}, t}}{100} - o_t\right)^2, \quad o_t \in \{0, 1\}$$
- Skor $0.00$: Kalibrasi probabilitas sempurna.
- Skor $0.25$: Setara tebakan acak 50/50 (*coin toss*).
- Skor $> 0.25$: Model mengalami *overconfidence* terhadap ketidakpastian pasar.

---

## 7. Kejujuran Kunci Prediksi (Lock Hash Honesty — Phase 5)

1. **Prediksi Historis (`2026-09-22` s/d `2026-10-08`):**
   - Prediksi pada rentang tanggal ini diberi hash saat proses *rescoring* historis, bukan sebelum pembukaan pasar pada hari-H.
   - Oleh sebab itu, artefak tersebut ditandai `lock_status = "retroactive"`, `locked_at = null`, `hash_computed_at = "2026-10-15"`, dan `out_of_sample_verified = false`.
   - Pada UI, sesi ini menampilkan peringatan eksplisit: **`"Hash added retroactively; not proof of pre-open lock"`**.
2. **Prediksi Baru (*Going Forward*):**
   - Pekerjaan pagi (`market_agent.py` $\to$ `lock_morning_prediction` di `core/locking.py`) menghitung SHA-256 atas payload prediksi kanonikal pada saat pembuatan, merekam `created_at` (WIB), dan menulis catatan *append-only* berantai (*hash-chained*) ke `runs/global/lock_ledger.jsonl` (`date`, `lock_hash`, `prev_ledger_hash`, `created_at`).
   - Hanya prediksi yang memiliki entri valid di `lock_ledger.jsonl` dengan timestamp `created_at` sebelum pukul 09:00 WIB pada tanggal sesi yang berhak menyandang `lock_status = "locked_pre_open"` dan menampilkan **`"Locked at 06:55 WIB"`** di UI.
   - Fungsi `verify_prediction_lock` memverifikasi ulang hash payload terhadap `lock_ledger.jsonl` dan langsung mendeteksi jika ada pengeditan pasca-kunci (`tampered_after_lock`).

---

## 8. Tabel Evaluasi Kuantitatif Kanonikal (`scripts/evaluate.py`)

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
