# Nexus Operational Runbook

Dokumen ini memuat panduan operasional lengkap untuk menjalankan, memonitor, mengaudit, dan memulihkan sistem Nexus baik di lingkungan lokal (Windows/Linux) maupun di cloud (GitHub Actions).

---

## 1. Persiapan Lingkungan (Setup & Installation)

### Prasyarat
- Python 3.11.x (versi target: `3.11.9`)
- Node.js 18+ (untuk dashboard Next.js)
- Git

### Instalasi Dependensi Python
```bash
# Clone repositori
git clone <repo-url>
cd nexus

# Buat virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

# Instal dependensi terkunci
pip install -r requirements.lock
```

### Konfigurasi Environment (`.env`)
Salin template konfigurasi dan isi kunci yang diperlukan:
```bash
cp .env.example .env
```
Variabel minimal yang dibutuhkan:
```env
OPENROUTER_API_KEY=your_openrouter_key
TAVILY_API_KEY=your_tavily_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

---

## 2. Cara Menjalankan Pipeline (Execution Modes)

### 2.1 Standard CLI Entry Points (Rekomendasi)
Nexus menyediakan entry point terpadu via package `nexus`:

```bash
# Menjalankan Morning Brief pre-market
python -m nexus brief

# Menjalankan Evening Review post-market
python -m nexus review

# Menjalankan background scheduler
python -m nexus serve
```

### 2.2 Menjalankan Scheduler Lokal
```bash
# Menjalankan scheduler berbasis schedule.yaml (06:55 WIB & 20:00 WIB)
python scheduler.py
```

### 2.3 Menjalankan Dashboard Telemetri
```bash
cd dashboard
npm install
npm run build
npm start
# Dashboard dapat diakses di http://localhost:3000
```

---

## 3. Otomatisasi Cloud (GitHub Actions)

Nexus dikonfigurasi untuk berjalan secara otomatis di GitHub Actions tanpa server mandiri:

1. **Morning Brief (`.github/workflows/morning_brief.yml`)**:
   - Berjalan terjadwal pada **23:55 UTC** (ekuivalen dengan **06:55 WIB**).
   - Mempublikasikan brief harian langsung ke kanal Telegram yang ditentukan.
   - Menyimpan artefak sesi ke repositori secara atomik.

2. **Evening Review (`.github/workflows/evening_review.yml`)**:
   - Berjalan terjadwal pada **13:00 UTC** (ekuivalen dengan **20:00 WIB**).
   - Mengambil data penutupan sesi bursa, mengevaluasi prediksi pagi hari, dan memperbarui heuristik.

3. **Manual Trigger (Workflow Dispatch)**:
   - Kedua workflow dapat dipicu kapan saja secara manual melalui Web UI GitHub Actions atau GitHub Mobile app jika diperlukan rilis ad-hoc.

---

## 4. Prosedur Pemulihan Insiden (Incident Recovery)

### Insiden 1: Lock File Tertinggal (`RunLockError`)
- **Gejala**: Log menunjukkan pesan `Cannot acquire lock for <job>: another process is running`.
- **Penyebab**: Proses sebelumnya terhenti mendadak (misal pemadaman listrik atau kill sinyal keras) sebelum lock dilepas.
- **Solusi**:
  1. Pastikan tidak ada proses python yang sedang aktif:
     ```powershell
     Get-Process python*
     ```
  2. Hapus file lock yang tertinggal di folder `runs/`:
     ```powershell
     Remove-Item runs\*.lock -Force
     ```

### Insiden 2: Kegagalan Rate-Limit Penyedia LLM
- **Gejala**: OpenRouter mengembalikan HTTP 429 atau kuota habis.
- **Tindakan Otomatis**: Sistem secara otomatis mencoba fallback tier: OpenRouter -> DeepInfra -> Gemini.
- **Tindakan Manual**: Jika semua provider gagal, tambahkan token cadangan ke `.env` atau perbarui saldo OpenRouter.

### Insiden 3: Inkonsistensi Riwayat Statistik
- **Gejala**: File `nexus_stats.json` rusak atau menunjukkan angka yang tidak cocok dengan riwayat sesi.
- **Solusi**: Jalankan script rescoring deterministik:
  ```bash
  python scripts/rescore_history.py
  ```
  Script akan memindai seluruh folder sesi historis, memverifikasi parameter scorable, dan membangun ulang `nexus_stats.json`.

---

## 5. Prosedur Pengujian & Verifikasi Kualitas

Sebelum melakukan rilis atau commit ke branch produksi, selalu jalankan test suite lengkap:
```bash
python -m pytest tests/
```
Seluruh unit test harus berstatus hijau (`PASSED`).

