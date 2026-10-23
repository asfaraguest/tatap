<div align="center">
  <img src="assets/tatap_icon_512.png" width="112" height="112" alt="Tatap Logo">
  <h1>Tatap</h1>
  <p>Pemutar dan agregator anime mandiri multiplatform (Android Mobile, Android TV, Windows, Linux, Web) yang ringan, bebas iklan, tanpa registrasi akun, dan menjaga privasi data di penyimpanan lokal.</p>

  <p>
    <a href="https://github.com/asfaraguest/tatap/releases/latest"><img src="https://img.shields.io/github/v/release/asfaraguest/tatap?style=flat-square&color=00dbeb&label=Rilis" alt="Release"></a>
    <a href="https://somsubhra.github.io/github-release-stats/?username=asfaraguest&repository=tatap" target="_blank" title="Lihat Statistik Unduhan Lengkap"><img src="https://img.shields.io/github/downloads/asfaraguest/tatap/total?style=flat-square&color=3fb950&label=Statistik%20Unduhan" alt="Statistik Unduhan"></a>
    <a href="https://github.com/asfaraguest/tatap/stargazers"><img src="https://img.shields.io/github/stars/asfaraguest/tatap?style=flat-square&logo=github&color=e3b341&label=Stars" alt="Stars"></a>
    <a href="https://github.com/asfaraguest/tatap/network/members"><img src="https://img.shields.io/github/forks/asfaraguest/tatap?style=flat-square&logo=github&color=58a6ff&label=Forks" alt="Forks"></a>
    <a href="https://hits.sh/github.com/asfaraguest/tatap/"><img src="https://hits.sh/github.com/asfaraguest/tatap.svg?style=flat-square&label=Kunjungan&color=00dbeb" alt="Views"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/Lisensi-GPL--3.0-blue.svg?style=flat-square" alt="License"></a>
  </p>

  <p>
    <a href="https://github.com/asfaraguest/tatap/releases/latest/download/tatap-release-v2.11.4.apk"><img src="https://img.shields.io/badge/Download-Android%20Mobile-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android Mobile APK"></a>
    <a href="https://github.com/asfaraguest/tatap/releases/latest/download/tatap-tv-release-v2.11.4.apk"><img src="https://img.shields.io/badge/Download-Android%20TV-0081C9?style=for-the-badge&logo=android&logoColor=white" alt="Android TV APK"></a>
    <a href="https://github.com/asfaraguest/tatap/releases/latest/download/tatap-windows-x64-portable.zip"><img src="https://img.shields.io/badge/Download-Windows%20x64-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows Portable"></a>
    <a href="https://github.com/asfaraguest/tatap/releases/latest/download/Tatap-x86_64.AppImage"><img src="https://img.shields.io/badge/Download-Linux%20AppImage-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux AppImage"></a>
  </p>

  <p>
    <a href="https://trakteer.id/bagus_azizul" target="_blank"><img src="https://img.shields.io/badge/Trakteer-Dukung%20Karya-be1e2d?style=flat-square" alt="Trakteer"></a>
    <a href="https://ko-fi.com/L5J028GNTA" target="_blank"><img src="https://img.shields.io/badge/Ko--fi-Beli%20Kopi-FF5E5B?style=flat-square&logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
  </p>
</div>

---

## Fitur Utama

- **Agregasi Multi-Sumber & Anti-DPI:** Menghubungkan katalog stream (HiAnime & Otakudesu) dengan modul desinkronisasi TLS dan DNS-over-HTTPS (DoH) bawaan untuk menjaga konektivitas stream tanpa VPN pihak ketiga.
- **Deteksi Opening & Ending (AniSkip):** Mendeteksi durasi intro/outro otomatis dengan opsi lewati satu klik pada remote TV (`OK` / `>>`) maupun keyboard desktop (`S`).
- **Resume Watch Multiplatform:** Menyimpan posisi tontonan per episode secara otomatis dan menyajikan dialog konfirmasi untuk melanjutkan atau memutar dari awal.
- **Rasio Episode Ongoing & Katalog:** Menampilkan jumlah episode rilis terhadap total proyeksi musim (`Ep X/Y`), penanda status tamat, filter genre, serta jadwal rilis mingguan.
- **Navigasi TV (10-Foot UI):** Antarmuka Leanback Android TV yang dioptimalkan penuh untuk remote kontrol D-pad tanpa memerlukan mouse pointer.

---

## Subtitle Engine

Tatap menyediakan sistem takarir multi-tier yang dapat dipilih langsung dari pemutar:

| Subtitle Engine | Nama di Pemutar | Keterangan |
| :--- | :--- | :--- |
| **AIGTX Smart Fansub** | `Indonesian (GTX+)` | Engine bawaan tanpa API key, dilengkapi kamus 500+ istilah khas anime & fansub Indonesia. |
| **AI Fansub LLM** | `Indonesian (AI Fansub)` | Terjemahan kontekstual berbasis AI model bawaan kunci sendiri (BYOK: Gemini, Groq, OpenAI, Ollama). |
| **Google Translate RPC** | `Indonesian (Google GTX)` | Penerjemahan cepat standar via Google Translate RPC (tanpa API key). |
| **Track Asli (Softsub)** | `English` / Bahasa Asli | Takarir bawaan video resmi dalam format WebVTT/ASS. |
| **Sumber Sub Indo** | `Otakudesu` | Pilihan beralih sumber ke rilisan takarir Bahasa Indonesia langsung. |

### Konfigurasi AI Fansub (BYOK)

Untuk menggunakan model bahasa kustom pada pemutar, ketik perintah berikut pada kolom input pencarian:

| Perintah | Layanan / Provider |
| :--- | :--- |
| `:gemini <api_key>` | Google AI Studio (Gemini 2.0 Flash) |
| `:groq <api_key>` | Groq Cloud (Llama 3.3) |
| `:openai <api_key>` | OpenAI |
| `:ollama <api_key>` | Ollama (Lokal / Cloud) |

Perintah manajemen: `:apikey` (cek status kunci), `:apikey clear` (hapus kunci), `:model <nama_model>` (ganti model).

---

## Unduh dan Instalasi

Pilih paket instalasi resmi sesuai perangkat Anda:

| Platform Perangkat | Tombol Unduh Langsung | Format Berkas | Keterangan & Kompatibilitas |
| :--- | :---: | :---: | :--- |
| **Android Ponsel / Tablet** | [![Unduh Android APK](https://img.shields.io/badge/Download-Android%20APK-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://github.com/asfaraguest/tatap/releases/latest/download/tatap-release-v2.11.4.apk) | `.apk` (~35 MB) | Signed Production APK (Android 7.0 s/d 16, Watch Portrait View & Adaptive Icons) |
| **Android TV / Google TV** | [![Unduh Android TV APK](https://img.shields.io/badge/Download-Android%20TV%20APK-0081C9?style=for-the-badge&logo=android&logoColor=white)](https://github.com/asfaraguest/tatap/releases/latest/download/tatap-tv-release-v2.11.4.apk) | `.apk` (~35 MB) | Signed Production APK khusus TV (Leanback 10-foot UI & Remote D-pad) |
| **Windows (x64)** | [![Unduh Windows Portable](https://img.shields.io/badge/Download-Windows%20Portable-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/asfaraguest/tatap/releases/latest/download/tatap-windows-x64-portable.zip) | `.zip` (~26 MB) | Standalone Portable (Ekstrak zip & jalankan `Tatap.exe`) |
| **Linux (x86_64)** | [![Unduh Linux AppImage](https://img.shields.io/badge/Download-Linux%20AppImage-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://github.com/asfaraguest/tatap/releases/latest/download/Tatap-x86_64.AppImage) | `.AppImage` (~58 MB) | Standalone AppImage (Berikan izin `chmod +x` lalu jalankan) |

> [!TIP]
> **Mengalami Kendala Pemasangan pada Android (Samsung One UI, Xiaomi/HyperOS, dll.)?**  
> Jika ponsel Anda (khususnya Samsung One UI 6.0+) memblokir pemasangan dengan pesan *"Pemasangan diblokir (Auto Blocker)"* atau *"Diblokir oleh Play Protect"*, ikuti solusi langkah-demi-langkah pada **[Panduan Pemecahan Masalah Instalasi Android](docs/TROUBLESHOOTING_ANDROID.md)**.

Seluruh arsip versi rilis stabil sebelumnya tersedia di [Halaman Rilis Resmi GitHub](https://github.com/asfaraguest/tatap/releases). Untuk memantau grafik dan riwayat total unduhan secara transparan, kunjungi [Dasbor Statistik Unduhan Tatap](https://somsubhra.github.io/github-release-stats/?username=asfaraguest&repository=tatap).

### Menjalankan Versi Self-Hosted (Web Server / VPS / Localhost)

Bagi pengguna yang ingin menjalankan Tatap sebagai layanan web mandiri (*self-hosted*) di server lokal, HomeLab, maupun VPS Linux:

1. **Prasyarat Sistem:**
   - Python 3.11 atau lebih baru (`python3 --version`)
   - Git (`git --version`)

2. **Kloning & Pemasangan Otomatis:**
   ```bash
   git clone https://github.com/asfaraguest/tatap.git
   cd tatap
   ./install.sh
   ```
   *Skrip `./install.sh` akan menyiapkan virtual environment Python (`venv/`), memasang seluruh pustaka dependensi (`requirements.txt`), serta menginisialisasi basis data SQLite lokal.*

3. **Menjalankan Layanan:**
   - **Mode Interaktif (Foreground):**
     ```bash
     ./run.sh
     ```
     Buka peramban di `http://127.0.0.1:8767`.
   - **Mode Latar Belakang (Background Daemon Service):**
     ```bash
     ./manage.sh start     # Menjalankan server di latar belakang
     ./manage.sh status    # Memeriksa status proses dan PID
     ./manage.sh logs      # Melihat log aktivitas pemutaran & server
     ./manage.sh stop      # Menghentikan server
     ```

4. **Akses Jaringan Lokal (LAN) atau Server VPS (Remote Access):**
   Secara bawaan, backend mendengarkan pada host lokal `127.0.0.1`. Untuk membuka akses ke perangkat lain dalam satu jaringan Wi-Fi/LAN atau server publik, setel variabel `APP_HOST` ke `0.0.0.0`:
   ```bash
   APP_HOST=0.0.0.0 ./run.sh
   ```
   *Atau buat berkas konfigurasi `.env` pada direktori root:*
   ```env
   APP_HOST=0.0.0.0
   APP_PORT=8767
   ```
   Akses antarmuka web dari perangkat apa pun di peramban via `http://<IP_SERVER_ANDA>:8767`.

---

## Panduan Navigasi & Kontrol

### 1. Desktop & Web (Keyboard)

#### Pemutar Video (Player)
| Tombol | Fungsi |
| :--- | :--- |
| `Spasi` | Putar / Jeda pemutaran video |
| `F` | Masuk / Keluar mode layar penuh (*Fullscreen*) |
| `←` / `→` | Mundur / Maju 5 detik (*Seek*) |
| `[` / `]` | Perlambat / Percepat kecepatan putar (`0.5x` s/d `2.0x`) |
| `S` | Lewati opening/ending (jika terdeteksi) atau beralih sumber stream |
| `N` / `P` | Pindah langsung ke episode berikutnya / sebelumnya |
| `M` | Matikan / Nyalakan audio (*Mute toggle*) |
| `Esc` | Keluar mode layar penuh atau menutup pemutar video |

#### Antarmuka Beranda & Dialog
| Tombol | Fungsi |
| :--- | :--- |
| `/` | Fokus ke kolom input pencarian atau terminal perintah |
| `Tab` | Berpindah antar tab beranda (*Cari*, *Musim*, *Jadwal*, *Lanjutan*, *Katalog*) |
| `↑` / `↓` | Navigasi riwayat perintah terminal atau pemilihan kartu anime |
| `[` / `]` | Berpindah halaman katalog atau berganti hari pada tab jadwal |
| `Enter` | Menjalankan pencarian atau mengonfirmasi pilihan dialog aktif |
| `Esc` | Membatalkan dialog riwayat tontonan atau menutup modal informasi |

---

### 2. Android TV (Remote D-Pad 10-Foot UI)

Antarmuka Android TV dirancang khusus untuk pengoperasian penuh via remote kontrol D-pad:

| Tombol Remote | Fungsi di Layar Utama & Katalog | Fungsi Saat Pemutaran Video (Player) |
| :--- | :--- | :--- |
| `D-Pad Kiri / Kanan` | Berpindah antar kartu anime atau chip hari | Mundur / Maju 5 detik (*Seek*) |
| `D-Pad Atas` | Berpindah ke baris tab atau kolom pencarian (tekan `OK` untuk memunculkan keyboard virtual) | Menampilkan panel kontrol atas (Resolusi, Subtitle, Kecepatan, Rasio, Info) |
| `D-Pad Bawah` | Menjelajahi baris konten anime di bawahnya | Memfokuskan tombol *Lewati Opening/Ending* jika aktif, atau menyembunyikan kontrol |
| `D-Pad Tengah / OK` | Membuka detail anime atau konfirmasi pilihan | Putar / Jeda; mengeksekusi *Lewati Opening/Ending* saat tombol skip terfokus; konfirmasi *Lanjutkan* pada dialog riwayat |
| `>>` *(Fast-Forward)* | – | Melompati opening/ending secara langsung tanpa memindahkan fokus remote |
| `<<` *(Rewind)* | – | Mundur 10 detik |
| `Next / Previous` | – | Pindah ke episode berikutnya / sebelumnya |
| `Menu / Info / Settings` | Membuka panel drawer navigasi samping | Membuka dialog pengaturan pemutar (resolusi, subtitle, kecepatan, rasio aspek, auto-skip) |
| `Kembali / Back` | Kembali ke menu sebelumnya atau tutup dialog | Menyembunyikan bar kontrol pemutar / kembali ke detail anime |

---

### 3. Android Ponsel & Tablet (Gesture Layar Sentuh)

| Gesture / Sentuhan | Area Layar | Fungsi |
| :--- | :--- | :--- |
| Geser Vertikal Sisi Kanan | Layar kanan pemutar | Mengatur volume suara secara halus (*continuous*) |
| Geser Vertikal Sisi Kiri | Layar kiri pemutar | Mengatur tingkat kecerahan layar (*brightness*) |
| Ketuk Dua Kali (*Double Tap*) | Layar kiri / kanan | Mundur / Maju 10 detik |
| Tombol Rasio Aspek | Bar kontrol atas | Beralih mode tampilan rasio (*Fit, Fill, Zoom, Stretch*) |

---

## Dukungan dan Donasi

<p align="left">
  <a href="https://trakteer.id/bagus_azizul" target="_blank">
    <img src="https://img.shields.io/badge/Trakteer-Dukung%20Karya-be1e2d?style=for-the-badge" height="38" alt="Dukung di Trakteer">
  </a>
  &nbsp;
  <a href="https://ko-fi.com/L5J028GNTA" target="_blank">
    <img src="https://img.shields.io/badge/Ko--fi-Beli%20Kopi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white" height="38" alt="Support di Ko-fi">
  </a>
</p>

---

## Catatan Layanan & Lisensi

- Memerlukan koneksi internet aktif untuk mengambil metadata anime dan memutar stream video.
- Aplikasi bertindak sebagai agregator konten publik dan tidak menyimpan berkas video pada server tersendiri.
- Catatan riwayat perubahan versi terdokumentasi di [CHANGELOG.md](CHANGELOG.md) mengikuti kaidah [Semantic Versioning 2.0.0](https://semver.org/lang/id/).
- Lisensi di bawah [GPL-3.0](LICENSE).
