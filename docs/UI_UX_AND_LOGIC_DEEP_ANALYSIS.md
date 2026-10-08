# Nexus: Deep Analysis & Architectural Audit Report
**Focus: UI/UX Intelligence, System Logics, Self-Learning Loop, and Market Authenticity**
*Status: Institutional Engineering Audit*
*Target Audience: Lead Quantitative Engineers, System Architects, & UI/UX Product Designers*

---

## Executive Summary

Audit ini dilakukan berdasarkan evaluasi komprehensif terhadap seluruh basis kode **Nexus** (pipeline multi-agen IHSG Python dan dashboard Next.js 14).

### Penilaian Kualitas (Brutally Honest Assessment):
Nexus saat ini adalah **prototipe fungsional berkecepatan tinggi yang solid secara runtime**, namun **belum memenuhi standar sistem intelijen pasar institusi riil**.
- **Kelebihan Utama**: Pipeline berjalan deterministik, memiliki fallback model LLM multi-tier yang tangguh, sistem penulisan atomik dan SQLite WAL yang aman, penanganan zona waktu Jakarta yang konsisten, dan 54 unit test yang lulus 100%.
- **Kelemahan Fatal**:
  1. *UI/UX Disconnect*: Terdapat inkonsistensi antara representasi data di tabel UI dengan payload API (khususnya metrik heuristik yang menampilkan status "Unresolved" dan kolom kosong).
  2. *Data Blind Spots*: Komoditas domestik paling krusial bagi IHSG (Batubara Newcastle dan Kelapa Sawit CPO) tidak dapat dirender secara numerik di UI karena format data scraper web tidak terstruktur, menyisakan kekosongan pada kartu telemetri.
  3. *Residu Nilai Fallback*: Masih ditemukan hardcode visual seperti `'Rp 15,385'` di layer komponen React ketika data kurs gagal ditarik.
  4. *Pseudo-Learning Loop*: Sistem memori saat ini belum memiliki mekanisme *empirical hypothesis testing*, *regime filtering*, atau *time-decay weighting*, melainkan hanya menyimpan string catatan dan menginjeksi potongan teks secara linier ke prompt pagi.

---

## 1. Audit Mendalam UI / UX & Desain Antarmuka

### 1.1 Evaluasi Desain Visual & Kesesuaian Sistem (Fintech Terminal Standard)
Berdasarkan standar perancangan antarmuka finansial kuantitatif (*Institutional Trading Terminal*):

| Komponen Desain | Kondisi Saat Ini di Nexus | Masalah / Evaluasi Kritis | Rekomendasi Solusi Top-Tier |
|---|---|---|---|
| **Palet Warna & Tema** | Dark Mode OLED (`--canvas: #06080d`, `--surface: #0c1017`) dan Light Mode Swiss. | Pada Light Mode, rasio kontras beberapa badge status berada di bawah standar WCAG AA (4.5:1), seperti `--warning-text` di atas `--warning-bg`. | Perketat rasio kontras minimal 4.5:1 untuk semua teks status. Gunakan palet Slate Finansial (#0F172A). |
| **Tipografi Angka** | Menggunakan Google Fonts *JetBrains Mono* untuk sebagian angka. | Masih ada komponen yang menggunakan font sans-serif proporsional untuk harga, menyebabkan *layout shifting* saat angka berubah. | Terapkan atribut CSS `font-variant-numeric: tabular-nums` atau class `.font-mono` secara universal untuk semua angka finansial, bps, dan persentase. |
| **Aksesibilitas Warna (Color Blindness)** | Arah pasar mengandalkan warna hijau (`--matched-text`) dan merah (`--missed-text`). | Analis dengan Deuteranopia/Protanopia tidak dapat membedakan status arah secara cepat tanpa simbol glif yang kontras. | Wajibkan penyertaan glif arah permanen (`▲` untuk Bullish/Hit, `▼` untuk Bearish/Miss, `—` untuk Neutral/Flat) di setiap indikator visual. |
| **Information Hierarchy** | Layar *Market Intelligence* menampilkan KPI, Variance Bridge, Sector Tape, RCA Panel, dan Historical Ledger sekaligus. | Beban kognitif terlalu padat (*cognitive overload*). Tidak ada pemisahan tegas antara "Apa yang harus saya perhatikan hari ini" dan "Audit sesi masa lalu". | Pisahkan menjadi struktur 2 tingkat: **Hero View** (Active Trading Session & Live Thesis) dan **Collapsible Audit Drawer** untuk riwayat masa lalu. |
| **Status Jam Bursa** | Teks sederhana `MARKET OPEN / CLOSED` dengan interval timer 15 detik. | Trader institusi tidak mendapatkan informasi mengenai fase spesifik sesi IDX. | Tambahkan **IDX Market Session Progress Bar**: Pre-Opening (08:45–08:59), Sesi I (09:00–11:30), Istirahat (11:30–13:30), Sesi II (13:30–15:49), Pre-Closing (15:50–16:00), dan Post-Trading (16:05–16:15 WIB). |

---

### 1.2 Audit Komponen-ke-Komponen Dashboard

#### A. `LessonsDatabaseView.js` (Tabel Basis Pengetahuan & Aturan)
- **Problem**: Kolom `Validated`, `Contradicted`, dan `Validation Rate` menampilkan data kosong dan badge merah "Unresolved".
- **Akar Masalah**: File `api/memory/route.js` tidak menghitung agregasi matematis berapa kali aturan tersebut diuji dan terbukti berhasil memitigasi kesalahan pada sesi-sesi setelahnya.
- **Rekomendasi**: Ubah skema payload API memori untuk menyertakan `validated_count`, `contradicted_count`, dan `success_rate_pct` berbasis pengujian historis riil.

#### B. `SectorAssetTape.js` (Pita Sektor & Indikator Komoditas)
- **Problem**:
  1. Batubara (Coal), Kelapa Sawit (CPO), dan Nikel (Nickel) hilang dari tampilan visual.
  2. Fallback hardcoded `'Rp 15,385'` muncul jika USD/IDR tidak berupa angka.
- **Akar Masalah**:
  - Filter hanya mengizinkan objek dengan `Number.isFinite(item.change_pct)`. Karena Coal & CPO disimpan dalam bentuk string mentah pencarian web (`"raw": "[no date] ICE Newcastle..."`), komponen membuangnya dari render array.
- **Rekomendasi**:
  - Buat parser numerik deterministik di `data_sources/market_data.py` untuk mengekstrak angka penutupan dan perubahan harian dari teks mentah komoditas web, atau integrasikan ticker Yahoo Finance/Barchart yang valid (`NCF=F` untuk Newcastle Coal, `FCPO.KL` untuk CPO).
  - Ganti fallback `'Rp 15,385'` dengan state visual `Unavailable` berbalut tooltip penjelasan.

#### C. `VarianceBridge.js` (Jembatan Variansi Prediksi vs Realisasi)
- **Kondisi**: Sangat baik secara konsep (Pre-Market Thesis $\rightarrow$ Session Close $\rightarrow$ Spread & Delta $\rightarrow$ Attribution Verdict).
- **Peningkatan UX**: Tambahkan visualisasi **Confidence Interval** (misal bar deviasi standar) untuk mendampingi `Accuracy Score`.

#### D. `HistoricalLedger.js` & `page.js` (Tabel Histori Audit)
- **Problem**: Tabel riwayat memiliki 8 kolom yang sangat lebar. Pada layar laptop 13-14 inci atau tablet, terjadi *horizontal cut-off* tanpa indikator scroll horizontal yang jelas.
- **Rekomendasi**: Tambahkan pembungkus `overflow-x-auto` dengan shadow gradient di sisi kanan tabel sebagai petunjuk visual bahwa tabel dapat digulir secara horizontal.

---

## 2. Audit Logika Pasar Modal & Integritas Data

### 2.1 Ketergantungan Data Bursa: Yahoo Finance (`^JKSE`) vs Feed Resmi IDX
- **Kondisi Riil Pasar**:
  Yahoo Finance menarik data bursa Indonesia dengan jeda (*delay*) 15–20 menit. Lebih krusial lagi, kalkulasi penutupan resmi (*Official Settlement Price*) IDX baru selesai dibentuk pada sesi *Pre-Closing & Post-Trading* (15:50–16:15 WIB).
- **Risiko Logika**:
  Jika `evening_reviewer` dieksekusi sebelum settlement terkonsolidasi, data candle bisa mencerminkan harga menit ke-15:49 dan bukan harga penutupan resmi.
- **Solusi Top-Tier**:
  Tambahkan validasi timestamp snapshot: `evening_reviewer` hanya memproses data jika cap waktu candle menunjukkan perdagangan telah melewati 16:15 WIB. Jika belum, jadwalkan retry dengan exponential backoff.

---

### 2.2 Distorsi Likuiditas: Pasar Reguler vs Pasar Negosiasi (Crossing)
- **Realitas Transaksi IDX**:
  Pergerakan IHSG digerakkan oleh *Pasar Reguler*. Transaksi di *Pasar Negosiasi* (tukar-menukar saham antar pemegang saham mayoritas/institusi) sering bernilai fantastis (misal transaksi crossing Rp 5 Triliun di saham tertentu) namun dilakukan dengan harga kesepakatan tetap yang tidak menggerakkan grafik IHSG.
- **Kelemahan Logika Saat Ini**:
  Fungsi `utils/flow.py` mengekstrak angka foreign flow dari teks berita tanpa memisahkan apakah angka tersebut terjadi di Pasar Reguler atau Seluruh Pasar (All Market).
- **Solusi Top-Tier**:
  Perbaiki regex dan prompt ekstraksi untuk memprioritaskan frasa `"Pasar Reguler"` / `"Regular Market"`. Jika berita hanya menyebutkan angka kumulatif, tandai data tersebut dengan badge `ALL_MARKET_INCLUSIVE`.

---

### 2.3 Logika Deterministik Ekonomi (`economics_engine.py`)
- **Evaluasi**:
  Pendekatan hardcoded commodity-to-sector adalah keputusan arsitektur yang brilian karena mengeliminasi halusinasi model AI. Namun, formulanya saat ini mengabaikan **Kondisi Makro Makroekonomi Ganda**:
  1. *Net Oil Importer Vulnerability*: Kenaikan harga minyak mentah global (WTI naik tajam) di-mapping positif ke sektor energi, namun dampaknya terhadap defisit neraca dagang dan inflasi menekan sektor perbankan dan konsumer. Mengingat perbankan memiliki bobot kapitalisasi pasar terbesar di IHSG (>35%), lonjakan minyak sering kali menghasilkan penutupan IHSG yang merah pekat.
  2. *Transmisi Kurs Valas*: Kenaikan USD/IDR (Rupiah melemah) saat ini belum dimodelkan secara otomatis terhadap sektor yang memiliki utang berdenominasi valas tinggi atau bahan baku impor 90% (seperti Farmasi dan Pakan Ternak).
- **Rekomendasi**:
  Tingkatkan mesin ekonomi deterministik menjadi **Multi-Factor Transmission Matrix** yang memperhitungkan interaksi antara Komoditas, Kurs Valas, dan Yield Obligasi Negara (FR).

---

## 3. Audit Sistem Belajar Mandiri (Self-Learning Loop)

### 3.1 Skema Pembelajaran Saat Ini vs Ideal

```
KONDISI SAAT INI (LINEAR CONTEXT INJECTION):
[Prediksi Meleset] ──► [LLM Buat Lesson Text] ──► [Simpan ke JSON] ──► [Tempel 5 Lesson Terakhir ke Prompt Pagi]

SKEMA IDEAL INSTITUSIONAL (CLOSED-LOOP EMPIRICAL HYPOTHESIS TESTING):
[Prediksi Meleset] ──► [Formulasikan Hipotesis Terstruktur] ──► [Tag Market Regime]
                             │
                             ▼
[Uji Konsistensi di Sesi Berikutnya] ──► [Lacak Tingkat Akurasi Setelah Injeksi]
                             │
       ┌─────────────────────┴─────────────────────┐
       ▼                                           ▼
[Sukses >= 3x: PROMOTED]                  [Gagal >= 3x: DEPRECATED / DECAYED]
```

### 3.2 Tiga Kelemahan Utama Sistem Pembelajaran Saat Ini:
1. **Tidak Ada Decay Waktu (Time-Decay)**:
   Aturan yang tercipta saat pasar berada dalam kondisi krisis geopolitik tetap diinjeksi dengan bobot yang sama saat pasar kembali ke kondisi normal. Sistem membutuhkan bobot *Exponential Moving Average (EMA)* yang menurunkan signifikansi aturan seiring berjalannya waktu jika aturan tersebut tidak terpicu kembali.
2. **Tidak Ada Pemisahan Rezim Pasar (Regime Tagging)**:
   Pasar modal memiliki 3 fase utama: *Trending Bullish*, *Trending Bearish*, dan *Ranging/Sideways Churn*. Heuristik yang valid di fase bullish (misal: "Buy on weakness sektor teknologi") adalah bencana di fase bearish. Heuristik wajib diberi label regim pasar asal.
3. **Prompt Dilution (Pengaburan Konteks LLM)**:
   Menginjeksi potongan teks pelajaran panjang ke prompt pagi menyebabkan fenomena *attention sink* pada model open-weights. Prompt pagi harus menerima instruksi terstruktur berupa parameter bobot (misal: `SECTOR_WEIGHT_ADJUSTMENT: Energy -15%`), bukan narasi panjang yang membingungkan model.

---

## 4. Audit Ketahanan Sistem & Penanganan Kasus Ekstrem (Edge Cases)

| Skenario Ekstrem | Dampak pada Sistem Saat Ini | Perilaku yang Diharapkan (Target Institusi) |
|---|---|---|
| **Trading Halt (IDX Anjlok $\ge 5\%$)** | Sistem mencatat penutupan pada harga halt tanpa mengetahui sesi terhenti darurat. | Sistem mendeteksi volume anomali / status halt; membekukan evaluasi akurasi normal dan memberi label `TRADING_HALT_SUSPENDED`. |
| **Pembalikan Arah Intraday (Whipsaw)** | Prediksi pagi bullish (Wall Street +2%). IHSG dibuka loncat +1%, lalu siang hari anjlok -1.5%. Review malam mencatat prediksi salah 100%. | Sistem memisahkan evaluasi menjadi dua metrik: **Opening Gap Accuracy** (mengukur ketepatan reaksi pembukaan) dan **Closing Trend Accuracy** (mengukur dinamika intraday). |
| **Keterlambatan Eksekusi Scheduler** | Jika server macet dan pipeline baru berjalan pukul 08:40 WIB (5 menit sebelum pre-opening), sistem tetap memproses data berita malam seolah-olah waktu masih dini hari. | Guardrail waktu mutlak: Jika eksekusi terjadi melewati pukul 08:30 WIB, sistem beralih ke mode `EMERGENCY_PRE_OPENING_UPDATE` dengan pembatasan pencarian web hanya pada berita 1 jam terakhir. |

---

## 5. Master Roadmap & Spesifikasi Teknis Perbaikan

Untuk menyelesaikan seluruh temuan di atas tanpa mengotori basis kode sebelum perancangan matang, berikut adalah tahapan implementasi yang direkomendasikan:

### Tahap A: Penyempurnaan UI/UX & Data Authenticity (Frontend)
1. **Perbaikan API Memory (`dashboard/src/app/api/memory/route.js`)**:
   Lakukan kalkulasi nyata terhadap relasi aturan dan performa sesi sesudahnya, sehingga kolom `Validated`, `Contradicted`, dan `Validation Rate` memiliki angka riil dan tidak lagi berstatus "Unresolved".
2. **Integrasi Komoditas Terstruktur (Coal & CPO)**:
   Ubah pemrosesan data komoditas agar harga dan persentase perubahan Batubara dan CPO selalu terekstraksi ke dalam format numerik dan muncul di kartu *Cross-Asset Telemetry*.
3. **Pembersihan Residu Fallback**:
   Gantikan string `'Rp 15,385'` di `SectorAssetTape.js` dan `page.js` dengan komponen visual `DataUnavailableBadge` yang informatif.
4. **Institutional Trading Bar**:
   Lengkapi antarmuka dengan indikator fase sesi bursa aktif (Pre-Opening, Sesi I, Sesi II, Pre-Closing) dan countdown timer menuju rilis brief berikutnya.

### Tahap B: Penguatan Logika Pasar & Sistem Belajar (Backend)
1. **Multi-Factor Transmission Matrix (`economics_engine.py`)**:
   Integrasikan transmisi suku bunga Bank Indonesia dan depresiasi Rupiah secara deterministik terhadap sektor-sektor berisiko tinggi.
2. **Lifecycle Aturan Heuristik (`learning_store.py`)**:
   Implementasikan status formal: `HYPOTHESIS` $\rightarrow$ `ACTIVE` $\rightarrow$ `DEPRECATED`, lengkap dengan pelacakan akurasi empiris.
3. **Regime-Aware Context Filtering**:
   Hanya injeksikan aturan yang sesuai dengan regim pasar aktif untuk menjaga kebersihan context window model LLM.

---
*Laporan ini disimpan secara persisten sebagai cetak biru resmi untuk eksekusi penyempurnaan Nexus.*
