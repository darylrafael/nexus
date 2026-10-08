# Legal, Regulatory & Licensing Disclosures

Dokumen ini memuat batas hukum, penafian regulasi, serta batasan lisensi data penyedia pihak ketiga untuk repositori dan sistem **Nexus**.

---

## 1. Penafian Regulasi & Pasar Modal (Regulatory Disclaimer)

### Status Operasional
Nexus adalah perangkat lunak sumber terbuka (open-source software) berbasis kecerdasan buatan otonom untuk penelitian kuantitatif, analisis data pasar, dan tujuan pendidikan komputasi finansial.

### Batas Regulasi OJK & Bappebti:
1. **Bukan Rekomendasi Investasi**:
   - Konten analitik, brief harian, ringkasan sektor, dan skor probabilitas yang dihasilkan oleh sistem ini **sama sekali bukan merupakan nasihat investasi, rekomendasi transaksi efek, analisis saham terdaftar, atau ajakan membeli/menjual instrumen keuangan apa pun** sebagaimana diatur dalam Undang-Undang Pasar Modal No. 8 Tahun 1995 dan peraturan perundang-undangan Otoritas Jasa Keuangan (OJK).
2. **Ketiadaan Izin Entitas Jasa Keuangan**:
   - Pengembang dan pengelola sistem Nexus tidak beroperasi sebagai Perusahaan Efek, Wakil Penasihat Investasi, Perantara Pedagang Efek (Broker-Dealer), Manajer Investasi, atau Lembaga Penasihat Keuangan Berizin OJK.
3. **Tanggung Jawab Pemodal (DYOR)**:
   - Keputusan investasi, pengelolaan portofolio, dan alokasi modal adalah tanggung jawab mutlak dan independen dari masing-masing individu pemodal. Pengguna diwajibkan melakukan *Due Diligence* mandiri (*Do Your Own Research* / DYOR) serta berkonsultasi dengan penasihat keuangan berlisensi resmi sebelum mengeksekusi transaksi pasar.
4. **Ketiadaan Garansi Kinerja Historis**:
   - Kinerja akurasi historis yang disajikan pada dashboard telemetri merupakan catatan uji coba komputasi dan tidak dapat diartikan sebagai jaminan hasil keuntungan di masa depan.

---

## 2. Batasan Lisensi Data & Penyedia Pihak Ketiga (Data Licensing Boundary)

### 2.1 Yahoo Finance Provider Boundary
- **Status Publik**: Sesuai dengan batasan Terms of Service penyedia pihak ketiga, library antarmuka Yahoo Finance (`yfinance`) dalam sistem ini diisolasi di balik lapisan abstraksi `MarketDataProvider`.
- **Mode Publik (`NEXUS_PUBLIC_MODE`)**:
  - Apabila flag lingkungan `NEXUS_PUBLIC_MODE=true` diaktifkan, modul secara otomatis membatasi frekuensi query, menerapkan caching yang ketat, dan menandai seluruh data yang diperoleh dengan atribusi eksplisit.
  - Untuk penggunaan komersial berskala institusi, modul dirancang untuk dapat dihubungkan langsung ke penyedia berlisensi resmi (*Licensed Enterprise Feed*) seperti Bloomberg API, Refinitiv Eikon, atau IDX Data Feed Resmi melalui implementasi class `LicensedMarketDataProvider`.

### 2.2 Tavily News Search API
- Pemanfaatan API Tavily dibatasi pada pencarian berita publik (*public news indexing*) dengan penyaringan domain, pencegahan scraping media sosial, dan caching in-memory berbasis waktu hidup (TTL 30 menit).

---

## 3. Kebijakan Privasi & Perlindungan Data (Privacy Policy)

1. **Nir-Penyimpanan Identitas Pribadi (Zero PII)**:
   - Nexus tidak menyimpan, memproses, atau mendistribusikan data identitas pribadi pengguna (*Personally Identifiable Information*).
2. **Sanitasi Log Publik**:
   - Seluruh berkas log telemetri yang diekspos ke antarmuka dashboard publik (`telemetry.json`) secara otomatis disaring dari isi prompt mentah maupun respon internal agen untuk melindungi kerahasiaan operasional.
