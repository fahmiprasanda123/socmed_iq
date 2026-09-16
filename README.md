# ⚡ SocialIQ — Social Media Benchmarking & Intelligence Dashboard

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SQLite](https://img.shields.io/badge/SQLite-Local_Storage-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Support via Saweria](https://img.shields.io/badge/Saweria-Traktir_Kopi-FFA000?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white)](https://saweria.co/itsamilitarysecret)

**SocialIQ** adalah aplikasi analitik dan *benchmarking* media sosial (Instagram, Threads, TikTok) berbasis Python & Streamlit. Dirancang untuk membandingkan metrik performa beberapa akun sekaligus secara komprehensif, mulai dari tingkat pertumbuhan follower, *Engagement Rate* (ER), pola posting waktu terbaik, hingga efektivitas format konten dan hashtag.

Seluruh data ditarik secara langsung (*live scraping*) dari profil publik aktual tanpa data sintetis/palsu, serta dilengkapi penyimpanan lokal SQLite untuk melacak histori pertumbuhan dari hari ke hari.

---

## ✨ Fitur Utama

- ⚡ **Live Web Scraper**: Mengambil metrik aktual (follower, jumlah postingan, like, komentar, caption) langsung dari profil publik (Instagram, Threads, TikTok).
- 📊 **Head-to-Head Benchmarking Matrix**: Perbandingan metrik utama (Total Followers, Growth %, Estimated ER, Avg Interactions, Post Volume) antar akun secara berdampingan.
- 🎯 **Content Quadrant Analysis**: Matriks kuadran efektivitas konten (Volume Post vs Average Interactions) yang mengelompokkan akun ke dalam 4 kategori strategi (*High Efficiency Champions, Growth Grinders, Niche Specialists, Low Impact Risk*) beserta rekomendasi tindakan nyata.
- 🕒 **Best Posting Time Heatmap**: Peta panas (heatmap) 24x7 untuk mengidentifikasi hari dan jam dengan rata-rata interaksi tertinggi.
- 🏷️ **Hashtag Performance Analytics**: Deteksi otomatis tagar pada postingan dan analisis korelasi hashtag terhadap performa interaksi.
- 📁 **Historical Tracking & SQLite Persistence**: Penyimpanan snapshot metrik ke dalam database lokal (`data/socialiq.db`) untuk analisis tren jangka panjang.
- 🤖 **CLI Daily Tracker (`track_daily.py`)**: Script command-line yang siap dijadwalkan via `cron` (Linux/macOS) atau *Task Scheduler* (Windows) untuk otomatis merekam snapshot metrik setiap hari.
- 📥 **Export & Import Data**: Unduh laporan analitik ke format Excel (`.xlsx`) atau CSV, serta kemampuan mengimpor riwayat metrik eksternal.

---

## 🚀 Cara Menjalankan

### 1. Prasyarat
Pastikan Python 3.9 atau lebih baru telah terpasang di komputer Anda.

### 2. Clone Repository & Setup Virtual Environment
```bash
# Masuk ke direktori proyek
cd socmed_analysis

# Buat virtual environment
python3 -m venv .venv

# Aktifkan virtual environment
# Di macOS / Linux:
source .venv/bin/activate
# Di Windows:
# .venv\Scripts\activate

# Install dependensi
pip install -r requirements.txt
```

### 3. Jalankan Aplikasi Web Streamlit
```bash
streamlit run app.py
```
Aplikasi akan otomatis terbuka di browser Anda pada alamat `http://localhost:8501`.

---

## 🕒 Otomatisasi Snapshot Harian (CLI Tracker)

Untuk membangun data historis pertumbuhan akun secara otomatis tanpa perlu membuka dashboard setiap hari, jalankan script `track_daily.py`:

```bash
# Update semua akun yang sudah pernah disimpan di database:
python track_daily.py

# Atau lacak akun tertentu secara spesifik:
python track_daily.py --platform Instagram --handles akun_a akun_b akun_c
```

> **Tip**: Pasang script ini di `crontab` harian (misal setiap jam 23:59) untuk pencatatan otomatis yang konsisten:
> ```bash
> 59 23 * * * cd /path/to/socmed_analysis && .venv/bin/python track_daily.py >> tracker.log 2>&1
> ```

---

## ☕ Dukungan & Traktir Kopi

Jika Anda menyukai aplikasi ini, merasa terbantu, atau ingin mendukung pengembangan dan pemeliharaan *source code* SocialIQ agar terus bertambah fiturnya, Anda bisa mentraktir secangkir kopi! 

Dukungan sekecil apa pun sangat berarti untuk menjaga semangat *ngoding* dan *maintenance*:

<p align="center">
  <a href="https://saweria.co/itsamilitarysecret" target="_blank">
    <img src="https://img.shields.io/badge/Saweria-Traktir%20Kopi%20%E2%98%95-FFA000?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white" alt="Dukung via Saweria" />
  </a>
</p>

👉 **Saweria Link:** [https://saweria.co/itsamilitarysecret](https://saweria.co/itsamilitarysecret)

Terima kasih banyak atas apresiasi dan dukungannya! 🙏✨

---

## 🌐 Catatan Deployment ke Streamlit Cloud (Production)

> **Kenapa scraping berhasil di laptop lokal tapi gagal di Streamlit Cloud?**
>
> 1. **Pemblokiran IP Data Center (AWS/Cloud):** Server Streamlit Community Cloud berjalan di atas infrastruktur publik AWS. Meta (Instagram) secara otomatis memblokir atau me-redirect request dari IP data center ke halaman login (`HTTP 302/429/403`). Di laptop lokal, scraping berhasil lancar karena menggunakan IP residential (ISP rumahan/seluler).
> 2. **Solusi Praktis & Rekomendasi:**
>    - **Metode 1 (Export & Import Data Historis - Paling Praktis):** Jalankan scraping atau tracker harian di lokal (`track_daily.py`), buka menu **📁 Manajemen Data Historis** di dashboard lokal, unduh database (`.db`) atau export CSV, lalu upload ke dashboard Streamlit Cloud Anda.
>    - **Metode 2 (Gunakan Proxy):** Masukkan proxy residensial pada menu **Settings &rarr; Secrets** di Streamlit Cloud:
>      ```toml
>      PROXY_URL = "http://username:password@proxy-ip:port"
>      ```
>    - **Metode 3 (Self-Hosting dengan Cloudflare Tunnel / Ngrok):** Jalankan dashboard di komputer lokal Anda, lalu ekspos menggunakan Cloudflare Tunnel gratis untuk mendapatkan domain publik tanpa risiko blokir IP server.

---

## ⚠️ Catatan & Disclaimer

- Data yang diambil bersumber dari profil publik yang dapat diakses secara terbuka tanpa login akun pengguna.
- Gunakan aplikasi ini secara bijak dan wajar serta patuhi *Terms of Service* dari masing-masing platform media sosial terkait frekuensi permintaan scraping.

---

## 👤 Author & Kontak

Dibuat dengan ❤️ oleh [@itsamilitarysecret](https://threads.net/@itsamilitarysecret).
