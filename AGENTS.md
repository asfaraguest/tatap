# AGENTS.md — Tatap Engineering & Collaboration Workflow (Master Directives)

> [!CAUTION]
> **DIREKTIF MUTLAK & PATEN UNTUK SEMUA AI AGENTIC TOOLS (ANTIGRAVITY / GEMINI / CURSOR / COPILOT / CLAUDE):**
> 1. **APLIKASI ANDROID-BASED WAJIB SELALU DITANDATANGANI (SIGNED APK ONLY):** Seluruh file Android APK (`tatap-release-v<VERSION>.apk` dan `tatap-tv-release-v<VERSION>.apk`) **MUTLAK WAJIB DITANDATANGANI** dengan keystore resmi produksi (`android/keystore/release.jks`) via skema signature `v1SigningEnabled true` dan `v2SigningEnabled true`. DILARANG KERAS merilis APK unsigned, debug, atau mentah!
> 2. **STRICT 4 OFFICIAL ASSETS ON GITHUB RELEASE:** Rilis GitHub publik HANYA boleh memuat 4 aset resmi berikut:
>    - `tatap-release-v<VERSION>.apk` (Signed Official Mobile APK)
>    - `tatap-tv-release-v<VERSION>.apk` (Signed Official Android TV / Google TV APK)
>    - `tatap-windows-x64-portable.zip` (Official Windows Portable)
>    - `Tatap-x86_64.AppImage` (Official Linux AppImage)
>    Jika terdapat berkas mentah (`app-release.apk`, `app-debug.apk`), agent WAJIB segera menghapusnya (`gh release delete-asset`).
> 3. **WORKFLOW PATEN SEMVER 2.0.0 & DOKUMENTASI CHANGELOG.md:** Setiap patch/fitur/rilis WAJIB mengikuti SemVer 2.0.0 atomik melalui `python3 tools/bump_version.py <patch|minor|major>` dan lulus seluruh test suite `pytest tests/test_semver.py`. **SETIAP ADA PERUBAHAN** (penambahan fitur, perbaikan bug, maupun refaktor), agent **MUTLAK WAJIB** mencatatkannya ke dalam berkas `CHANGELOG.md` sesuai format *Keep a Changelog* beserta penjelasan alasan kenaikan nomor versinya (`PATCH`, `MINOR`, atau `MAJOR`).
> 4. **ZERO-TOLERANCE BLACKLIST HENTAI:** Dilarang membypass filter hentai di semua level backend, scraper, maupun UI.
> 5. **URUTAN BACAAN WAJIB SEBELUM PLANNING/ITERASI (AGENTS.MD LALU PROJECT_MAP.MD):** Sebelum memulai perencanaan (*planning*), investigasi, maupun iterasi perubahan kode/fitur/bugfix apa pun, setiap AI Agent **MUTLAK WAJIB** membaca `AGENTS.md` terlebih dahulu, lalu membaca `PROJECT_MAP.md` untuk memahami topologi berkas, aturan paritas Chaquopy Android, indeks simbol fungsi, dan matriks keputusan teknis (*zero search overhead*).
> 6. **DOWNLOAD BUTTONS DI README.MD WAJIB SELALU MENGARAH KE LATEST RELEASE YANG SUDAH PUBLIK (BUKAN DRAFT):** Seluruh tautan/tombol download pada `README.md` (Android Mobile, Android TV, Windows Portable, Linux AppImage) **MUTLAK WAJIB DIPASTIKAN** selalu mengarah ke versi rilis publik yang sudah aktif (*published/public latest release*), **BUKAN rilis yang masih berstatus DRAFT**. Selama rilis baru masih berstatus draft atau dalam pengerjaan, tautan unduhan publik di `README.md` wajib tetap mengarah ke rilis publik stabil terakhir yang asetnya dapat diunduh tanpa error 404. Hanya setelah rilis dipublikasikan resmi ke publik (`isDraft: false`), tautan download di `README.md` disinkronkan ke versi baru tersebut via `python3 tools/bump_version.py --sync-readme`. Jika suatu rilis ditarik kembali menjadi draft, tautan di `README.md` wajib segera dikembalikan ke versi publik aktif terakhir.
> 7. **ALUR IN-APP UPDATE MUTLAK SEAMLESS (DIRECT DOWNLOAD & INSTALL TANPA EXTERNAL BROWSER):** Kode implementasi pembaruan aplikasi (*in-app update*) pada Android (baik Mobile maupun Android TV) **MUTLAK WAJIB** memiliki tombol aksi aktif (misalnya *"Perbarui Sekarang"* / *"Update Now"*) yang berfungsi langsung mengunduh (*streaming download*) berkas APK resmi bertanda tangan ke penyimpanan lokal dan secara otomatis meluncurkan *PackageInstaller* resmi Android via `FileProvider`. **DILARANG KERAS** memaksa pengguna membuka web browser eksternal secara manual hanya untuk mencari dan mengunduh berkas APK! Apabila antarmuka modal/dialog menampilkan *Changelog* atau Catatan Rilis (*Release Notes*), antarmuka **MUTLAK WAJIB** menyediakan tombol perbarui/pasang aktif yang diletakkan tepat di bagian bawah (*bottom action button*) di bawah tampilan catatan rilis tersebut, sehingga pengguna dapat langsung mengeksekusi pembaruan di tempat tanpa berpindah aplikasi.

---

## 1. Identitas & Filosofi Proyek

**Tatap** adalah pemutar dan agregator anime multiplatform (Web Desktop, Windows Portable, Linux AppImage, dan Native Android) dengan fokus pada:
- **Zero-Bloat & Standalone Runtime:** Berjalan tanpa dependensi eksternal yang rumit (menggunakan embedded/standalone runtime di semua platform).
- **Resilient Networking:** Scraping sumber anime dengan proteksi TLS desync DPI-bypass untuk menjaga konektivitas stabil.
- **Smart Subtitle Fallback:** Sistem subtitle multi-tier (AIGTX Smart Lexicon, AI Fansub BYOK LLM, Google Translate GTX, dan Native WEBVTT sync).
- **Akurasi Klaim Teknis:** Jangan pernah mengklaim "100% Offline" karena aplikasi melakukan scraping stream online. Gunakan istilah yang akurat seperti *"Standalone Localhost Backend"* atau *"Aplikasi Mandiri Tanpa Server Publik"*.

---

## 2. Peta Arsitektur Codebase

```
tatap/
├── backend/                  # Server FastAPI & API Scraping
│   ├── main.py               # Entry point FastAPI, routing, API subtitle & stream
│   ├── config.py             # Konfigurasi port, path DB, dan environment
│   ├── database/             # SQLite database handler (history, bookmark, settings)
│   └── api/                  # Modul scraper: anilist, hianime, otakudesu, translate, desync
├── frontend/                 # Web UI (Zero-build vanilla JS & CSS)
│   ├── index.html            # Single-page UI structure & modals
│   ├── js/                   # app.js (state & playback), api.js, term.js, hls.min.js
│   └── css/                  # style.css (Dark cyber theme, responsive grids, fullscreen)
├── android/                  # Native Android App
│   ├── app/src/main/java/    # UI Native Java: MainActivity, DetailActivity, PlayerActivity (ExoPlayer)
│   ├── app/src/main/python/  # Backend FastAPI embedded via Chaquopy
│   └── app/build.gradle      # Konfigurasi build & signingConfigs release keystore
├── tools/                    # Automated Desktop Packaging Tools
│   ├── build_linux_appimage.py      # Builder AppImage (Python standalone + appimagetool)
│   └── build_windows_portable.py    # Builder Portable Windows (Python embed + Go launcher)
├── launcher/                 # Source Go untuk launcher native Windows (Tatap.exe)
├── dist/                     # Direktori output build binary rilis
└── agent.md                  # Standard Operating Procedure (file ini)
```

---

## 3. Standar UI/UX Pemutar Video & Subtitle

### Subtitle Dual-Layer Rendering
Player Tatap menggunakan pendekatan **Dual-Layer** untuk kompatibilitas maksimal:
1. **App-Level Custom Overlay (`#pm-subs-overlay`):** Digunakan saat pemutaran normal atau saat container `.ambient-stage` masuk mode fullscreen. Memungkinkan styling kustom (ukuran S/M/L, font shadow tebal, background translucent) dan live update translation.
2. **Native TextTrack Synchronization (`VTTCue`):** Subtitle yang diparsing wajib disinkronkan ke elemen `<video>` via `HTMLVideoElement.addTextTrack` atau `<track>`. Saat pengguna masuk fullscreen melalui tombol kontrol bawaan browser pada elemen `<video>`, browser mempromosikan elemen video ke top layer; native track otomatis aktif (`showing`) dan dirender melalui styling CSS `video::cue`.

### Fullscreen Promotion Strategy
- **Container Level:** Shortcut `f` / `F`, double-click pada area video, atau tombol **`⛶ FULL`** memicu `requestFullscreen()` pada `.ambient-stage`, bukan langsung pada elemen `<video>`.
- **Interception:** Panggilan native `v.requestFullscreen()` di-intercept untuk memprioritaskan fullscreen pada container `.ambient-stage`.
- **Keyboard Shortcut Safety:** Tombol `Escape` saat berada dalam mode fullscreen hanya keluar dari fullscreen tanpa menutup modal pemutar.

---

## 4. Alur Kerja Build & Packaging (Release Pipeline)

Setiap rilis versi stabil mengikuti tahapan berikut:

### 1. Build Linux AppImage
```bash
python3 tools/build_linux_appimage.py
```
* **Output:** `dist/Tatap-x86_64.AppImage` (~58 MB)
* **Karakteristik:** Membungkus runtime CPython 3.11 standalone, dependensi pip, backend, frontend, icon, dan desktop launcher mandiri yang dapat langsung dijalankan (`chmod +x`).

### 2. Build Windows Portable
```bash
python3 tools/build_windows_portable.py
```
* **Output:** `dist/tatap-windows-x64-portable.zip` (~26 MB)
* **Karakteristik & Isolasi Dependensi:**
  - Mengunduh Python 3.11 Embeddable x64 resmi dan mengompilasi launcher native Go `Tatap.exe`.
  - **Pencegahan Konflik Dependensi (Pydantic / Pydantic-Core):** Selalu pasang wheel murni melalui `pip install --target ... --platform win_amd64 --python-version 311 --only-binary=:all:`. Jangan pernah mengekstrak wheel dari folder cache campuran via `glob.glob()`, karena versi pustaka lama dapat menimpa versi baru dan memicu crash `SystemError: The installed pydantic-core version is incompatible with current pydantic`.

### 3. Build & Sign Android Production APK (Mandatory Signed APK Only)
Setiap rilis publik Android (baik varian Mobile maupun Android TV) **MUTLAK WAJIB berstatus Signed APK resmi** (bukan APK debug, mentah, atau unsigned):
1. **Konfigurasi Signing Otomatis di Gradle:**
   - Di `android/app/build.gradle`, blok `signingConfigs.release` mengikat keystore produksi `android/keystore/release.jks`.
   - Skema tanda tangan diaktifkan penuh: `v1SigningEnabled true` dan `v2SigningEnabled true`.
   - Varian release (`mobileRelease` dan `tvRelease`) secara otomatis menghasilkan output file bertanda tangan:
     - `android/app/build/outputs/apk/mobile/release/tatap-release-v<VERSION>.apk`
     - `android/app/build/outputs/apk/tv/release/tatap-tv-release-v<VERSION>.apk`
2. **Kompilasi Mandiri / CI:**
   - CI (`.github/workflows/android.yml`) mendekode `KEYSTORE_BASE64` secret dan menjalankan `./gradlew assembleRelease`.
   - Atau build lokal: `cd android && ./gradlew assembleRelease`
3. **Penandatanganan Manual / Verifikasi dengan `apksigner`:**
   ```bash
   # Verifikasi tanda tangan APK Mobile & TV:
   apksigner verify --verbose --print-certs dist/android/tatap-release-v<VERSION>.apk
   apksigner verify --verbose --print-certs dist/android/tatap-tv-release-v<VERSION>.apk
   ```
   Pastikan verifikasi menampilkan:
   - `CN=Tatap, OU=TatapApp, O=Tatap`
   - `Verified using v1 scheme (JAR signing): true`
   - `Verified using v2 scheme (APK Signature Scheme v2): true`
4. **Larangan Keras:** Dilarang mengunggah file APK yang tidak ditandatangani atau membiarkan file unsigned/debug ke halaman rilis publik.

---

## 5. Protokol Git & GitHub Release

### Kaidah Mutlak Semantic Versioning (SemVer 2.0.0) Pada Setiap Patch & Rilis
> [!IMPORTANT]
> **STANDAR ATURAN VERSIONING TATAP (PATENT POLICY):**
> Setiap patch perbaikan (*bug fixes*), hotfix, rilis fitur (*features*), dan rilis publik aplikasi **WAJIB 100% MENGIKUTI KAIDAH SEMANTIC VERSIONING RESMI (SemVer 2.0.0)** dengan format `v<MAJOR>.<MINOR>.<PATCH>`:
> 
> 1. **MAJOR (`X.0.0`):**
>    - Dinaikkan ketika terjadi perombakan arsitektur besar yang tidak kompatibel ke belakang (*breaking changes*), restrukturisasi skema database SQLite tanpa migrasi otomatis, atau perubahan mendasar pada kontrak runtime eksternal.
> 2. **MINOR (`x.Y.0`):**
>    - Dinaikkan ketika menambahkan fungsionalitas atau antarmuka baru yang backward-compatible (misalnya: penambahan Drawer Navigation Panel, In-Player Resolution Selector, On-Demand Update Checker, dukungan Android TV 10-Foot UI, provider scraping baru, atau perombakan tata letak UI utama).
>    - Nilai PATCH wajib direset kembali ke `0`.
> 3. **PATCH (`x.y.Z`):**
>    - Dinaikkan untuk perbaikan bug (*bug fixes*), perbaikan kompatibilitas platform/perangkat spesifik (seperti perbaikan fullscreen iOS Safari / Android Chrome, display cutout/notch edge-to-edge, immersive mode), optimasi performa, dan pembaruan dependensi/security hardening tanpa penambahan modul arsitektur baru.
> 
> **Aturan Mutlak Patch & Rilis bagi Agent:**
> - **Dilarang Keras** merilis patch/bugfix tanpa menaikkan digit PATCH (`X.Y.Z` -> `X.Y.Z+1`).
> - **Dilarang Keras** merilis fitur baru tanpa menaikkan digit MINOR dan mereset PATCH ke `0` (`X.Y.0`).
> - **Dilarang Keras** menggunakan penomoran versi bebas, non-standar, atau format arbitrer (seperti `v2.3`, `v2.3-patch1`).
> - **Prosedur Sinkronisasi Versi Atomik:** Saat melakukan update versi (apakah Major, Minor, atau Patch), agent **WAJIB MENGGUNAKAN** utilitas resmi:
>   ```bash
>   python3 tools/bump_version.py patch   # atau minor / major
>   python3 tools/bump_version.py --check # verifikasi audit
>   pytest tests/test_semver.py           # verifikasi automated tests
>   ```
>   Tool ini secara atomik menyinkronkan seluruh berkas: `VERSION`, `backend/version.py`, `android/app/src/main/python/backend/version.py`, `android/app/build.gradle` (deterministik `versionCode` dan `versionName`), `launcher/winres/winres.json`, `tatap.manifest`, dan `frontend/index.html`.
>
> - [x] Verifikasi konsistensi: `python3 tools/bump_version.py --check` && `pytest tests/test_semver.py`
> - [x] Build ulang dan verifikasi ke-4 berkas rilis resmi (`dist/`)
> - [x] Buat git commit dan tag `v<VERSION>` serta rilis publik GitHub
>
### Standar Aset Release Publik (Protokol Ketat "Hanya 4 Aset Resmi")
> [!CAUTION]
> **ATURAN MUTLAK / PATENT RULES UNTUK SETIAP AGENT:**
> Halaman rilis publik GitHub **HANYA BOLEH MENAMPILKAN TEPAT 4 ASET RESMI**. DILARANG KERAS mengunggah atau membiarkan berkas APK mentah (`app-release.apk`, `app-debug.apk`, dsb.) berada di release publik GitHub:
> 1. 📱 **`tatap-release-v<VERSION>.apk`** (Official Signed Mobile APK via Keystore `release.jks`, Multi-Scheme v2/v3 verified)
> 2. 📺 **`tatap-tv-release-v<VERSION>.apk`** (Official Signed Android TV / Google TV APK 10-Foot UI via Keystore `release.jks`)
> 3. 🪟 **`tatap-windows-x64-portable.zip`** (Official Windows Portable)
> 4. 🐧 **`Tatap-x86_64.AppImage`** (Official Linux AppImage)
>
> Jika CI workflow atau proses otomatis sempat mengunggah `app-release.apk` atau `app-debug.apk`, agent **WAJIB SEGERA** menghapusnya dengan:
> `gh release delete-asset v<VERSION> app-release.apk -y`
> `gh release delete-asset v<VERSION> app-debug.apk -y`
> Jangan pernah menyelesaikan respon ke pengguna sebelum memverifikasi bahwa daftar aset rilis di GitHub HANYA berisi 4 berkas resmi di atas!

**Langkah Penyelarasan Rilis Resmi:**
1. Update git tag:
   ```bash
   git tag -a v<VERSION> -m "Release v<VERSION>"
   git push origin v<VERSION>
   ```
2. Upload signed APK dan paket binary portable:
   ```bash
   gh release upload v<VERSION> \
     dist/android/tatap-release-v<VERSION>.apk \
     dist/android/tatap-tv-release-v<VERSION>.apk \
     dist/tatap-windows-x64-portable.zip \
     dist/Tatap-x86_64.AppImage \
     --clobber
   ```
3. **Verifikasi & Pembersihan Aset Tak Resmi:**
   Periksa aset rilis dengan `gh release view v<VERSION>`. Pastikan tidak ada file selain 4 file resmi di atas.
4. **Perbarui Release Notes:**
   Tulis catatan rilis berbahasa Indonesia yang terstruktur rapi, mencantumkan perbaikan bug, penambahan fitur, dan panduan download untuk seluruh platform.
5. **Sinkronisasi Tautan Unduhan README.md:**
   Setelah rilis dipublikasikan resmi ke publik (`--draft=false`), jalankan `python3 tools/bump_version.py --sync-readme` untuk memperbarui tautan download di `README.md` ke versi baru tersebut. Selama rilis masih berstatus DRAFT, tautan di `README.md` dilarang diarahkan ke versi draft agar pengguna publik tidak mengalami error 404.


---

## 6. Protokol Triage & Feedback GitHub Issues

Saat menangani issue dari pengguna/komunitas di GitHub:
1. **Inspeksi Isu:**
   * Gunakan REST API via `gh api repos/:owner/:repo/issues/:id` untuk menghindari kegagalan GraphQL pada versi CLI lama.
   * Pahami sistem operasi, browser/perangkat, dan bukti tangkapan layar dari pelapor.
2. **Diagnosis & Solusi:**
   * Cari akar penyebab di kode dasar (bukan sekadar penambal sementara).
   * Verifikasi solusi di lingkungan lokal sebelum melakukan commit.
3. **Bahasa Komunikasi:**
   * **Commit & Internal Repo:** Bahasa Inggris standar industri (Conventional Commits).
   * **Balasan / Feedback ke Pelapor di GitHub:** **Wajib menggunakan Bahasa Inggris** yang sopan, jelas, ramah, dan profesional.
   * Format balasan:
     - Ucapan terima kasih atas laporan.
     - Penjelasan singkat akar masalah (*Root Cause*).
     - Rincian perbaikan teknis yang dilakukan (*Fix Implemented*).
     - Informasi versi rilis / commit tempat perbaikan tersedia beserta tautan langsung.
     - Undangan untuk memverifikasi atau memberikan feedback balik.

---

## 7. Standar Pemutar Video Android & Katalog Metadata

### 1. Akurasi Gesture Swipe & Audio
- **Gesture Volume Tanpa Lag:** Pada `PlayerActivity.java`, gunakan **continuous float accumulator** (`currentVolumeFraction`) yang diinisialisasi dari rasio `currentVolume / maxVolume` pada saat `ACTION_DOWN`. Hindari *integer truncation* dari perhitungan jarak per-event (`(int)(distanceY * maxVol)`) yang menyebabkan swipe pelan/halus macet atau "nyangkut" di perangkat modern (Android 14, 15, dan 16).
- **Brightness Float Accumulator:** Nilai brightness layar disimpan dalam float `0.01f - 1.0f` dan diperbarui ke `WindowManager.LayoutParams.screenBrightness`.

### 2. Standar Tipografi & Penempatan Subtitle Mobile
- **Posisi Default Ergonomis:** Margin bawah default subtitle Android disetel ke `22dp` (bukan 50dp+) agar tidak menutupi ekspresi wajah karakter atau adegan sentral dalam rasio lanskap layar HP/tablet.
- **Kustomisasi Subtitle (`Style Dialog`):** Sediakan menu pengaturan subtitle dengan opsi kustomisasi:
  - Posisi: *Bawah (22dp)*, *Sangat Bawah (10dp)*, *Sedang (40dp)*, *Tinggi (58dp)*.
  - Background Opacity: *Transparan Sedang (30%)*, *Tipis (15%)*, *Gelap (70%)*, atau *Tanpa Kotak (Text Shadow murni)*.
  - Ukuran Teks: *14sp*, *16sp*, *19sp*, dan *22sp*.
  - Semua preferensi disimpan secara persisten di `SharedPreferences` (`tatap_player_prefs`).

### 3. Validasi Pencocokan Katalog Anime (AniList ke HiAnime)
- **Konsistensi Musim (Season Consistency):** Skrip pencocokan di `backend/main.py` (`_match_slug_one`) **wajib memverifikasi nomor musim** (`_extract_season_num`) dan token kemiripan judul (`_is_title_match`).
- **Pencegahan Fallback Keliru:** Dilarang menggunakan fallback buta ke hasil pertama (`res[0]`) ketika nama tidak cocok. Fallback keliru akan mencemari database cache permanen (`slug_map`), membuat anime Season baru/on-going tertukar dengan Season 1 atau judul yang sama sekali berbeda.
- **Tab On-going / Airing:** Tab anime yang sedang tayang harus selalu mengueri data status penayangan aktif langsung dari katalog stream (`/api/seasonal?which=airing`).

### 4. Kompatibilitas Packaging & Instalasi Android (16KB Page Alignment & Android 15/16)
- **Ekstraksi Pustaka Native:** Wajib menyetel `packaging.jniLibs.useLegacyPackaging = true` di `build.gradle` dan `android:extractNativeLibs="true"` di `AndroidManifest.xml`.
- **Akar Masalah Kegagalan Instal:** Pada Android 15, Android 16, dan perangkat 64-bit modern (seperti seri Infinix Note 40 / MediaTek / Transsion XOS), pustaka native uncompressed yang tidak ter-align pada batas 16KB akan langsung ditolak oleh PackageInstaller OS (`INSTALL_FAILED_INVALID_APK`). Dengan `useLegacyPackaging = true`, file `.so` dikompresi di APK dan diekstrak secara otomatis ke penyimpanan privat saat dipasang, menjamin 100% kompatibilitas dan menghemat ukuran unduhan APK dari ~54MB menjadi ~35MB.

### 5. Standar Alur In-App Update (Seamless APK Download & Install)
- **Tombol Aksi Unduh & Pasang Otomatis (In-App Direct Flow):** Setiap komponen antarmuka atau dialog update pembaruan (`AppUpdateManager.java` / `dialog_app_update.xml`) **wajib memiliki tombol aksi utama** (seperti `btn_update_now` "Perbarui Sekarang") yang langsung mengeksekusi pengunduhan APK secara streaming (`startDownload`) dan otomatis meluncurkan `PackageInstaller` (`installApk`) via `FileProvider`.
- **Zero Reliance pada Browser Eksternal:** Pengguna dilarang keras dipaksa membuka manual browser eksternal (`ACTION_VIEW` URL GitHub) hanya untuk mencari atau mendapatkan file update APK. Tautan browser hanya boleh hadir sebagai opsi sekunder/fallback darurat (`tv_update_fallback_browser`), bukan tombol aksi utama.
- **Penempatan Tombol Wajib di Bawah Changelog:** Apabila dialog menampilkan rincian *Changelog* / Catatan Rilis (`tv_update_notes`), tombol aksi perbarui (`btn_update_now`) **wajib diletakkan tepat di bagian bawah** wadah teks changelog/catatan rilis tersebut (didampingi tombol dismiss "Nanti"). Pengguna harus dapat membaca catatan rilis lalu langsung mengeklik tombol pembaruan tepat di bawahnya.
- **Dukungan Remote D-Pad Android TV:** Pada Android TV, tombol aksi perbarui di bawah changelog harus dapat menerima fokus remote D-Pad secara instan (`TvFocusHelper.attachFocusScale` dan `btnNow.requestFocus()`).
- **Penanganan Izin Paket Tidak Dikenal:** Jika OS Android 8.0+ memerlukan izin `REQUEST_INSTALL_PACKAGES`, aplikasi harus membimbing pengguna ke pengaturan via `Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES` dan otomatis melanjutkan instalasi saat kembali (`onActivityResult`).

---

## 8. Prinsip Rekayasa Agen AI (Agent Guardrails)

- **Kepatuhan Mutlak Terhadap Dokumen Ini (`AGENTS.md`) & Peta Proyek (`PROJECT_MAP.md`):** Setiap agen AI yang beroperasi pada repositori ini WAJIB membaca dan menaati seluruh instruksi di `AGENTS.md` lalu membaca `PROJECT_MAP.md` sebelum memulai pekerjaan. Dilarang menebak atau mencari-cari berkas secara acak sebelum memahami topologi dan matriks aksi pada `PROJECT_MAP.md`.
- **Mandatori Seamless In-App Update (Zero Forced External Browser):** Dilarang keras merombak atau mengganti mekanisme in-app update menjadi sekadar pengalihan tautan browser eksternal. Tombol aksi untuk streaming download dan auto-install APK via `FileProvider` wajib selalu ada dan berfungsi. Jika antarmuka memunculkan changelog/catatan rilis, tombol perbarui wajib selalu hadir di bawah tampilan changelog tersebut.
- **Kepatuhan Mutlak SemVer 2.0.0 & Wajib Dokumentasi CHANGELOG.md:** Setiap bugfix, patch, fitur baru, dan rilis publik WAJIB 100% mengikuti kaidah Semantic Versioning 2.0.0 (`v<MAJOR>.<MINOR>.<PATCH>`). Gunakan selalu `python3 tools/bump_version.py <patch|minor|major>` untuk sinkronisasi atomik, verifikasi audit via `python3 tools/bump_version.py --check`, dan pastikan test suite `pytest tests/test_semver.py` lulus sebelum commit & tag. Dilarang menggunakan tag arbitrer atau melompati kaidah SemVer. **Setiap ada perubahan kode, perbaikan bug, atau penambahan fitur, agent WAJIB mencatatkannya ke dalam berkas `CHANGELOG.md`** secara rapi (format Keep a Changelog) lengkap dengan alasan dan justifikasi penomoran versinya. Dilarang melakukan commit/release tanpa memperbarui `CHANGELOG.md`.
- **Aturan Rilis Publik GitHub (Zero Raw APK / Strict 4 Official Assets):** Dilarang keras mengunggah atau membiarkan `app-release.apk` atau `app-debug.apk` berada di rilis GitHub. Release HANYA boleh berisi:
  1. `tatap-release-v<VERSION>.apk` (Signed resmi mobile via keystore `release.jks`)
  2. `tatap-tv-release-v<VERSION>.apk` (Signed resmi Android TV / Google TV via keystore `release.jks`)
  3. `tatap-windows-x64-portable.zip` (Official Windows Portable)
  4. `Tatap-x86_64.AppImage` (Official Linux AppImage)
- **Zero-Tolerance Konten Dewasa / Hentai:** Blacklist total konten bergenre Hentai pada semua layer (backend scraping, browse, search, stream resolver, TUI console). Jangan izinkan fallback stream maupun metadata untuk judul bergenre hentai.
- **Pencocokan Stream & Anti-Regresi:** Selalu validasi judul (`_is_title_match`) dan season (`_extract_season_num`) saat fallback ke Otakudesu. Dilarang fallback buta ke `res[0]`.
- **Tombol Unduhan README.md Selalu Merujuk ke Rilis Publik (Bukan Draft):** Seluruh tombol dan tautan unduhan pada `README.md` wajib selalu merujuk ke rilis resmi yang sudah aktif/publik di GitHub (misal `releases/latest/download/tatap-release-v<LATEST_PUBLIC_VERSION>.apk`), bukan ke versi rilis yang masih berstatus Draft. Endpoint GitHub `/releases/latest/download/` tidak menyajikan aset rilis Draft dan akan melempar 404 jika diakses publik. Tautan baru boleh diarahkan ke nomor versi rilis baru HANYA setelah rilis tersebut dipublikasikan secara resmi ke publik.
- **Dokumentasi & Integritas Kode:** Jangan pernah menghapus komentar atau docstring yang ada kecuali diminta secara eksplisit atau sudah tidak relevan karena perubahan kode.
- **Verifikasi Sebelum Klaim Sukses:** Selalu jalankan uji sintaksis (`node --check`, linting, build test) dan verifikasi release (`gh release view`) sebelum mendeklarasikan tugas selesai.
- **Transparansi Kerja:** Laporkan langkah kerja secara ringkas, jelas, dan sertakan tautan ke file atau artefak terkait.

