# Nexus Quantitative & Analytical Methodology

Dokumen ini mendefinisikan formula, ambang batas matematis (*thresholds*), dan metodologi evaluasi yang digunakan oleh Nexus dalam memprediksi serta menilai kinerja harian Indeks Harga Saham Gabungan (IHSG).

---

## 1. Klasifikasi Arah Indeks (Directional Classification)

Untuk mencegah subjektivitas dalam menentukan apakah pergerakan pasar sesuai prediksi, Nexus menggunakan ambang batas kanonikal sebesar **±0.20% (20 basis poin)**.

| Persentase Perubahan Penutupan ($P$) | Klasifikasi Resmi | Penjelasan |
|---|---|---|
| $P \ge +0.20\%$ | **BULLISH** | Penguatan indeks signifikan |
| $-0.20\% < P < +0.20\%$ | **NEUTRAL** | Pergerakan mendatar / fluktuasi minor |
| $P \le -0.20\%$ | **BEARISH** | Pelemahan indeks signifikan |

### Aturan Evaluasi Arah:
- Sebuah prediksi dinyatakan **HIT (Berhasil)** jika dan hanya jika:
  $$\text{Klasifikasi Prediksi} = \text{Klasifikasi Aktual}$$
- Jika prediksi menyatakan `BULLISH` dan IHSG hanya naik $+0.05\%$, penutupan aktual diklasifikasikan sebagai `NEUTRAL`, sehingga hasil evaluasi adalah **MISS (Meleset)**.

---

## 2. Klasifikasi Aliran Dana Asing (Foreign Flow Classification)

Aliran dana asing (Foreign Net Buy / Net Sell) di pasar reguler Bursa Efek Indonesia merupakan indikator likuiditas institusional utama. Fluktuasi kecil harian tidak mencerminkan arah arus modal terencana.

Nexus menetapkan ambang batas materialitas sebesar **±Rp 1.0 Triliun**:

| Nilai Bersih Aliran Dana ($F$) | Klasifikasi Resmi |
|---|---|
| $F \ge +\text{Rp } 1.0 \text{ Triliun}$ | **NET BUY** |
| $-\text{Rp } 1.0 \text{ Triliun} < F < +\text{Rp } 1.0 \text{ Triliun}$ | **NEUTRAL** |
| $F \le -\text{Rp } 1.0 \text{ Triliun}$ | **NET SELL** |

### Validasi Tanggal:
Data aliran dana asing divalidasi terhadap tanggal penutupan sesi. Jika data yang diperoleh memiliki cap waktu di luar rentang tanggal sesi bersangkutan, data ditolak sebagai *date mismatch* untuk mencegah bias *stale data*.

---

## 3. Evaluasi Sektor Deterministik (Deterministic Sector Attribution)

Evaluasi kinerja sektor saham dihitung secara terpisah dari indeks gabungan:
- Transmisi harga komoditas global dihitung oleh mesin deterministik:
  - Lonjakan CPO $\rightarrow$ Sektor Perkebunan / CPO (`BULLISH`)
  - Lonjakan Batubara / Minyak $\rightarrow$ Sektor Energi (`BULLISH`)
  - Lonjakan Emas $\rightarrow$ Sektor Logam Mulia (`BULLISH`)
- Di sore hari, performa aktual indeks sektoral IDX dibandingkan terhadap tesis deterministik:
  $$\text{Sector Hit Rate} = \frac{\sum \text{Sektor Cocok}}{\text{Total Sektor Ditracking}} \times 100\%$$

---

## 4. Formula Akurasi Komposit & Sesi Terhitung (Scorable Sessions)

### 4.1 Definisi Sesi Terhitung (Scorable Session)
Sesi perdagangan dikategorikan sebagai **Scorable** jika:
1. Hari tersebut merupakan hari bursa resmi (bukan libur nasional atau cuti bersama).
2. Perdagangan IDX berlangsung penuh tanpa suspensi darurat.
3. Terdapat data penutupan resmi dan brief pagi yang tercatat.

Sesi libur atau sesi yang berstatus `UNSCORABLE` **dikecualikan dari denominator statistik**, sehingga tidak menurunkan rasio kemenangan (*win rate*) sistem secara semena-mena.

### 4.2 Pemisahan Matriks Akurasi
Nexus tidak menggabungkan metrik ke dalam satu angka agregat yang ambigu, melainkan menyajikan 3 dimensi terpisah:
1. **Directional Accuracy**: Persentase ketepatan arah indeks gabungan IHSG.
2. **Foreign Flow Accuracy**: Persentase ketepatan kategori aliran dana institusi asing.
3. **Sectoral Attribution Rate**: Rata-rata ketepatan dampak sektoral.

---

## 5. Mekanisme Root Cause Analysis (RCA) & Injeksi Pembelajaran

Setiap kali terjadi *divergence* (prediksi meleset):
1. **Kategori Diagnostik**:
   - `UNANTICIPATED`: Sentimen mendadak yang tidak ada dalam feed pagi (misal eskalasi geopolitik siang hari).
   - `UNDERESTIMATED`: Faktor yang dianalisis pagi hari namun dampaknya jauh lebih besar daripada ekspektasi.
   - `OVERWEIGHTED`: Faktor yang dibesar-besarkan dalam tesis pagi hari namun diabaikan pasar.
2. **Penyimpanan Aturan (Heuristics)**:
   - Pelajaran diekstraksi ke dalam pernyataan formal (*heuristik*).
   - Heuristik disimpan ke dalam memori pengetahuan dan diinjeksikan sebagai referensi konteks pada penyusunan brief di sesi-sesi berikutnya.
