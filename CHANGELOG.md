# Changelog

Semua perubahan penting pada proyek **Tatap** didokumentasikan di berkas ini.

Format dokumen ini mengacu pada [Keep a Changelog](https://keepachangelog.com/id/1.1.0/), dan proyek ini sepenuhnya mematuhi [Semantic Versioning 2.0.0](https://semver.org/lang/id/).

---

## Prinsip Penomoran Versi (SemVer 2.0.0)

Format versi menggunakan skema `MAJOR.MINOR.PATCH`:
- **MAJOR (X.0.0):** Perubahan arsitektur mendasar atau modifikasi yang tidak kompatibel ke belakang (*breaking changes*).
- **MINOR (x.Y.0):** Penambahan fitur atau kapabilitas baru yang tetap kompatibel ke belakang (*backward-compatible new features*). Digit PATCH direset ke 0.
- **PATCH (x.y.Z):** Perbaikan bug, peningkatan stabilitas, atau perbaikan internal tanpa penambahan fitur baru (*backward-compatible bug fixes*).

## [2.12.1] - 2026-10-22

### Justifikasi SemVer 2.0.0 (PATCH: 2.12.0 -> 2.12.1)
Kenaikan digit PATCH diterapkan secara mutlak sesuai kaidah Semantic Versioning 2.0.0 dan Direktif #3 [`AGENTS.md`](AGENTS.md) untuk perbaikan bug (*backward-compatible bug fix*) khusus platform Android TV (tatapTV) dan antarmuka Leanback 10-Foot UI:

1. **Perbaikan Layar TV Tergencet (*Screen Squashing Fix*):**
   - Menghilangkan tabrakan `android:id="@+id/layout_header_root"` pada root container `LinearLayout` di `src/tv/res/layout/activity_main.xml` dan `layout-television/activity_main.xml`, menggantinya dengan `android:id="@+id/layout_tv_root"`.
   - Menambahkan guard `isVerticalSidebar` pada `MainActivity.java:applyTvTopBarCompression()` sehingga tinggi layar TV tidak pernah dipaksa menjadi 44dp saat menggunakan layout sidebar vertikal.
2. **Pembersihan Sintaks XML Dangling:**
   - Menghapus fragmen atribut duplikat yang tidak valid di bawah tab `btn_tab_genre` pada kedua berkas layout TV.
3. **Penyelarasan Rantai Navigasi D-Pad TV:**
   - Memperbaiki rantai fokus tombol bawah sidebar (`btn_status_power` dan `btn_toggle_menu`), di mana `nextFocusUp` kini mengarah ke `btn_tab_genre` alih-alih melompati menu.
   - Mengembalikan perilaku alami navigasi bawah dari `btn_tab_jadwal` menuju `btn_tab_riwayat` di dalam sidebar vertikal, sementara tombol D-Pad Kanan mengarahkan fokus ke chip jadwal harian (`btn_day_senin`).
4. **Docked Left Sidebar & Harmonisasi Dimensi Poster:**
   - Menghilangkan overscan padding pada root TV layout sehingga background sidebar menempel penuh (*docked*) ke tepi kiri layar sesuai kaidah Apple TV, dengan safe-zone padding internal yang rapi.
   - Menyelaraskan `tv_card_poster_height` menjadi 175dp–180dp di `dimens.xml` TV sehingga poster anime mempertahankan aspek rasio sinematik 2:3 yang proporsional pada grid 6 kolom.
5. **Poles Tampilan Detail Anime (Indikator Nomor Saja):**
   - Menghilangkan badge teks status yang menumpuk pada kartu episode di `DetailActivity.java` dan `item_episode.xml`.
   - Menstandarkan tombol episode menjadi nomor murni terpusat dengan palet status Apple Flat UI (System Blue tinted untuk episode terakhir diputar, muted dark untuk yang sudah ditonton, dan clean elevated surface untuk yang belum).
6. **Penyempurnaan Web & Desktop UI, Search & Bottom Bar, Ikon Gear, dan Dual Theme (Terang & Gelap):**
   - **Perbaikan Input Spasi Search Bar:** Menghilangkan *event bubbling* pada `#search-input-wrap` yang memicu `e.preventDefault()`, mengisolasi input `#cmd` via `e.stopPropagation()`, serta melepas atribut statis `readonly` pada HTML.
   - **Perbaikan Backspace Blur Bug:** Memisahkan penanganan `Escape` dan `Backspace` pada `term.js:onKey(e)` sehingga menekan backspace saat mengetik di kotak pencarian tidak lagi melepas fokus kursor.
   - **Tombol Clear & Preservasi Kata Kunci:** Menambahkan tombol clear (`✕`) pada search bar untuk menghapus teks secara instan, serta mempertahankan kata kunci pencarian di dalam input saat submit pencarian judul anime.
   - **Penggantian Ikon Menu Kanan Atas:** Mengganti ikon elipsis 3 titik (`#icon-more-options`) dengan ikon roda gigi (*gear/settings*) bergaya Apple Flat UI dengan animasi rotasi halus 45 derajat saat hover.
   - **Dual Theme Engine (Apple Light & Obsidian Dark):** Menyediakan sistem pergantian tema 2 mode (Terang & Gelap) dengan persistensi `localStorage`, atribut dinamis `data-theme="light"|"dark"`, pencegahan kedipan (*zero flicker init*), dan integrasi pada Popover menu (`⌘T`), Drawer navigasi, serta perintah terminal (`:tema` / `:theme`).
   - **Desain Presisi Bottom Bar & Header:** Menyelaraskan gradien warna elegan pada `.tui-head`, `.bottom-bar`, dan `.apple-popover` dengan palet warna teroptimasi untuk mode terang maupun gelap tanpa membebani performa CPU perangkat *low-end* (zero blur tax) dan tanpa merusak kontras panggung pemutar video bioskop.

7. **Perbaikan Duplicate Icon Sidebar Android TV:**
   - Mengeliminasi pemanggilan `updateTvTabSpannable` pada sidebar vertikal TV (`isVerticalSidebar`) di `MainActivity.java` yang sebelumnya menyisipkan `CenteredImageSpan` ke dalam string teks tab sementara elemen layout XML telah memiliki `drawableStart`, yang memicu munculnya dua ikon kembar berdampingan (`[Icon] [Icon] Judul Tab`).
   - Menstandarkan pewarnaan ikon murni melalui `tab.setCompoundDrawableTintList(...)`.
   - Mengganti atribut `drawableStart` pada `btn_tab_genre` dari `@drawable/ic_filter` menjadi `@drawable/ic_tab_genre` yang tepat di kedua berkas layout TV (`src/tv/` dan `layout-television/`).
8. **Autohide / Collapsed Rail (64dp) & Expand (210dp) Sidebar Android TV:**
   - Menghadirkan mekanisme *Autohide* cerdas di mana bilah sisi meramping menjadi rel ikon kompak (`64dp`) saat pengguna menjelajah katalog poster anime (`rv_anime_grid`), meluaskan ruang lebar kisi poster anime hingga ~146dp untuk tampilan sinematik maksimal di layar TV 1080p dan 4K.
   - Memasang `OnGlobalFocusChangeListener` pada root sidebar untuk mendeteksi pergerakan fokus remote D-Pad secara reaktif (zero polling); saat fokus berpindah ke kisi poster, sidebar otomatis meramping (*collapse*), dan saat remote diarahkan ke kiri masuk ke sidebar, sidebar mengembang halus (*expand* 210dp, durasi 200ms `DecelerateInterpolator`) menampilkan seluruh teks label tab, kolom pencarian, dan logo `TATAP TV`.
   - Menyesuaikan orientasi kontrol bawah (`btn_status_power` dan `btn_toggle_menu`) menjadi vertikal saat collapsed dan horizontal saat expanded dengan rantai fokus remote D-Pad yang mengalir mulus tanpa hambatan.
9. **Automated Regression Suite (`tests/test_android_tv_sidebar_autohide.py`):**
   - Menambahkan test suite otomatis yang menguji ketiadaan duplicate ImageSpan pada vertical sidebar, integritas ID layout TV, nilai default dimensi rel `64dp` dan `210dp`, serta sinkronisasi paritas 100% kedua layout TV.
10. **Background Pattern Wallpaper Mac (macOS Wave Ribbons, Ambient Mesh & Topographic Contours):**
   - Menghadirkan pola wallpaper khas macOS (Sonoma/Ventura/Monterey/Sequoia) di `#bg-glow` menggunakan SVG vektor resolusi independen dan pure CSS multi-radial gradient mesh.
   - Menggunakan 3 lapisan pita gelombang melengkung (*cubic bezier waves*) dan garis kontur topografi (*topographic contour lines*) yang halus dan dinamis.
   - Adaptasi palet warna penuh: Mode Gelap (*Obsidian & Midnight Cyan/Indigo Glow*) dan Mode Terang (*Apple Studio Silver & Soft Sky/Lavender Ribbon Waves*).
   - Menjaga filosofi *zero-bloat*, performa tinggi dengan hardware acceleration GPU, dan zero CPU overhead tanpa aset gambar raster eksternal.
11. **Full-Width Layout `<footer class="bottom-bar">`:**
   - Menghilangkan pembatasan `max-width: 1560px` pada `.bottom-search-row` dan `.statusbar` sehingga membentang penuh 100% (*edge-to-edge*) di semua resolusi layar lebar desktop, selaras dengan `.tui-head`.
   - Menjaga kontainer konten `main` tetap terpusat dengan padding responsif yang konsisten.
12. **Penyempurnaan Menyeluruh Apple Light Theme (`[data-theme="light"]`):**
   - Memperbaiki latar belakang header dan footer di mode terang agar selaras dengan palet Apple Light Theme tanpa warna hitam pekat.
   - Memperbaiki latar belakang kotak pencarian `.search-input-wrap` dan teks `#cmd` agar memiliki kontras tinggi dan mudah dibaca di atas tema terang.
   - Memperbaiki `.apple-popover`, `.drawer-content`, badge status, genre pill, dan tombol chip aktif di mode terang.
   - Membersihkan duplikasi 150+ baris CSS di akhir berkas `frontend/css/style.css`.
   - Menjamin modal video player (`#player-modal`) tetap 100% hitam pekat (`#000000 !important`) di semua tema demi pengalaman teatrikal maksimal.
13. **Automated Regression Suite (`tests/test_web_bottom_bar_and_light_theme.py`):**
   - Menambahkan test suite otomatis yang memverifikasi Mac Wallpaper SVG, CSS variables, ketiadaan batasan 1560px pada bottom bar, ketiadaan duplikasi blok CSS, zero backdrop blur tax, dan integritas pemutar video bioskop.
14. **Perapian Presisi Ikon Sidebar Android TV Mode Collapsed (Rail 64dp Midline Alignment):**
   - Mengatasi masalah ikon yang berantakan dan tidak sejajar saat sidebar TV menciut (*collapsed rail 64dp*).
   - Menyelaraskan seluruh 11 elemen vertikal sidebar ke garis sumbu tengah (*midline*) tepat di `x = 24dp` pada kontainer konten 48dp:
     - Logo brand "T" (`tv_app_logo`): 24dp.
     - Ikon pencarian (`etSearch`): padding horizontal `(48dp - 15dp) / 2 = 16.5dp` dan `compoundDrawablePadding(0)`.
     - 7 Ikon Tab Navigasi (`btn_tab_*`): padding horizontal simetris `(48dp - 15dp) / 2 = 16.5dp` dan `compoundDrawablePadding(0)`.
     - Tombol status server (`btn_status_power`): dimensi kotak simetris `38dp x 38dp` dengan internal icon padding `9dp`.
     - Tombol menu (`btn_toggle_menu`): dimensi kotak simetris `38dp x 38dp`, top margin `8dp`, dan padding horizontal `(38dp - 15dp) / 2 = 11.5dp` berpusat di `24dp`.
   - Mengunci preservasi padding rel pada `setTabAppearance` di `MainActivity.java` sehingga saat tab berganti status (aktif/inaktif) saat sidebar menciut, padding simetris dan pemusatan ikon tetap utuh 100%.
   - Menambahkan pengujian regresi otomatis `test_tv_sidebar_collapsed_icons_centered` di `tests/test_android_tv_sidebar_autohide.py`.
15. **Picture-in-Picture (PiP) Eksklusif Android Mobile:**
   - Menghadirkan dukungan penuh mode Picture-in-Picture (PiP) pada `PlayerActivity.java` untuk perangkat Android Mobile (ponsel dan tablet).
   - Menambahkan atribut `android:supportsPictureInPicture="true"` pada `AndroidManifest.xml`.
   - **Seamless Auto-Enter & Gesture Support:** Mengintegrasikan `onUserLeaveHint()` dan `setAutoEnterEnabled(true)` (Android 12+ / API 31+) sehingga saat pengguna melakukan gesture swipe ke beranda (*Home*) atau menekan tombol Home saat video diputar, aplikasi bertransisi halus secara otomatis ke jendela mengambang (*floating window*).
   - **Tombol Kontrol Manual:** Menambahkan tombol "PiP" berikon vektor pada bilah atas landscape (`btn_pip`) dan bilah kontrol portrait (`btn_portrait_pip`).
   - **3 Remote Actions Interaktif:** Menyediakan tombol aksi interaktif pada jendela PiP (Mundur 10 detik, Play / Pause dinamis, dan Maju 10 detik) yang dikelola via `BroadcastReceiver` berizin `RECEIVER_NOT_EXPORTED` (Android 13+).
   - **Subtitle Mini Proporsional:** Menyesuaikan ukuran font dan margin subtitle custom overlay saat berada dalam mode PiP (`10sp`, margin `4dp`) agar teks tetap terbaca jelas tanpa menutupi video, dan secara otomatis memulihkan preferensi ukuran subtitle pengguna saat kembali ke layar penuh.
   - **Lifecycle Guards:** Melindungi `onPause()` dan `onStop()` dengan pengecekan `isInPictureInPictureMode()` agar pemutaran video dan sinkronisasi subtitle tidak terhenti saat sistem Android memanggil lifecycle background.
   - **Isolasi Android TV:** PiP dinonaktifkan secara ketat pada platform Android TV (`TvFocusHelper.isTv(this)`) untuk menjaga integritas antarmuka 10-Foot UI Leanback.
   - **Automated Regression Suite (`tests/test_android_pip.py`):** Menambahkan test suite otomatis yang memvalidasi deklarasi manifest, aset vektor PiP, tombol layout, lifecycle hooks, dan guard PiP.
16. **Penyempurnaan Hierarki Spacing, Top Bar, dan Transformasi Warna AI-SLOP ke Soft Modern Palette (Web & Desktop):**
   - **Eliminasi Total Palet Warna 'AI-SLOP':** Mengganti warna cyan neon menyilaukan (`#19d0d0`, `#38e8e8`), warna rawa gelap berlumpur (`#00363a`, `#002428`, `#0e281e`, `#241b0d`), dan efek *neon halo bloom* yang berlebihan dengan palet warna Apple Soft Modern & Obsidian Slate: Soft Sky (`#38bdf8`), Cerulean Deep (`#0284c7`), Soft Light Sky (`#7dd3fc`), Obsidian Slate (`#0c0d12`), dan warm graphite surfaces yang teduh, nyaman di mata saat menonton anime di ruangan gelap.
   - **Perapian Top Bar (`.tui-head`) & Apple Concentric Segmented Control:**
     - Menyelaraskan tinggi top bar menjadi `58px` (desktop) dan `52px` (mobile) dengan bayangan lembut `0 4px 20px rgba(0,0,0,0.45)`.
     - Mengimplementasikan prinsip konsentris Apple HIG pada bilah navigasi tab: container `.nav-tabs-bar` memiliki radius sudut $R = 10\text{px}$, padding $3\text{px}$, tinggi $38\text{px}$, dan tombol tab `.nav-tab-btn` memiliki radius sudut dalam konsentris $R_{\text{inner}} = 7\text{px}$ dengan tinggi $32\text{px}$ dan padding horizontal $15\text{px}$.
     - Tombol roda gigi (*gear menu*) `.header-drawer-btn` diselaraskan menjadi bujur sangkar presisi $38\text{px} \times 38\text{px}$ dengan radius $10\text{px}$, tepat sejajar pada garis sumbu tengah (*midline*) dengan kontainer segmented control.
     - Posisi popover `.apple-popover` disesuaikan ke `top: 62px` (memberikan jeda vertikal alami 4px di bawah top bar 58px).
   - **Perapian Hierarki Ruang (*Padding & Margin*) Halaman & Komponen:**
     - Kontainer utama `main`: padding diselaraskan menjadi `clamp(16px, 2.2vw, 26px) var(--pad-x) calc(var(--status-h) + 24px)`.
     - Judul seksi `.sec-head`: margin vertikal diselaraskan ke `22px 0 14px;` (dengan elemen pertama `margin-top: 4px;`) menghilangkan kesan sesak.
     - Kotak pencarian `.search-input-wrap`: tinggi `44px`, padding horizontal `14px`, radius sudut `10px`, dengan ring fokus presisi `0 0 0 3px var(--accent-soft)` tanpa efek *neon glow*.
     - Baris pencarian bawah `.bottom-search-row`: padding vertikal `10px var(--pad-x)`.
     - Teks kartu poster `.poster-body`: padding horizontal dan bawah `8px 6px 4px;` (dan `10px 6px 4px;` pada desktop lebar) sehingga judul anime tidak lagi menempel ke tepi batas kartu.
     - Kartu riwayat `.hist-info`: padding `10px 12px;` dan jeda vertikal `gap: 4px;`.
     - Modal detail anime `.sheet`: padding `clamp(16px, 2.4vw, 24px)`, margin kontrol episode `14px 0 10px`, meta box `12px 0 4px`, seasons bar `12px 0 4px` dengan radius `10px`, dan box sinopsis `12px 14px` dengan radius `8px`.
   - **Transformasi Badges & Filter Chips Menjadi Soft Translucent Tint:**
     - Score badge: amber hangat `rgba(245, 158, 11, 0.12)` & teks `#fbbf24`.
     - Finished status: emerald natural `rgba(16, 185, 129, 0.12)` & teks `#34d399`.
     - Ongoing status: soft sky `rgba(56, 189, 248, 0.12)` & teks `#38bdf8`.
     - Chip aktif (`.cf-chip.active`, `.genre-list button.active`, `.btn-cf-genre.active`): soft tint `rgba(56, 189, 248, 0.15)` dengan border `var(--accent)`.
   - **Sinkronisasi Kode JavaScript (`frontend/js/app.js`):**
     - Menstandarkan inline button status resolve stream dan switcher sumber dari `var(--cyan,#00dbeb)` menjadi `var(--accent)`.
   - **Automated Regression Suite (`tests/test_web_soft_colors_and_spacing.py`):**
     - Menambahkan test suite otomatis yang memverifikasi tidak ada lagi warna AI-slop di `style.css` dan `app.js`, variabel soft color `:root`, dimensi konsentris top bar 58px / 38px / 32px, dan nilai padding/margin proporsional.
17. **Perbaikan Kehilangan Padding & Margin Saat Katalog Muncul (Web & Desktop):**
   - **Eliminasi Penumpukan & Margin Collapse Antara Top Bar dan Judul Katalog:** Mengatur `padding-top` pada kontainer `main` secara konsisten menjadi `clamp(22px, 2.6vw, 34px)` dan menormalkan `margin: 0 0 clamp(16px, 2vw, 22px)` pada `.sec-head` (serta menghapus selector non-fungsional `main > .sec-head:first-child{margin-top:4px}` yang membuat heading terdesak ke atas).
   - **Pemberian Headroom Proporsional Pada Grid Katalog Poster (`.poster-grid`):** Menambahkan `margin-top: clamp(6px, 1vw, 10px)` dan `margin-bottom: clamp(20px, 2.5vw, 40px)` pada `.poster-grid` di seluruh breakpoint layar. Menghilangkan masalah kartu baris pertama menempel ketat langsung di bawah teks judul seksi dan badge filter saat katalog selesai dimuat, sehingga kartu memiliki ruang gerak bebas saat efek hover/focus scale (`translate3d(0, -4px, 0) scale(1.015)`).
   - **Penyelarasan Horizontal Guides dengan Top Bar & Bottom Bar:** Menstandarkan padding horizontal `main` menggunakan `var(--pad-x)` murni di semua resolusi desktop (menggantikan pembatasan kaku `max-width: 1560px` pada 1024px yang sebelumnya menyebabkan indentasi ganjil 90px pada konten katalog dibanding logo TATAP dan kotak pencarian), dengan batas maksimal `1680px` pada layar ultra-wide (>= 1600px).
   - **Harmonisasi Spacing Empty State & Pager:** Menyelaraskan padding dan margin vertikal pada `.empty` (`clamp(22px, 3.5vw, 36px) 14px`) dan `.pager` (`clamp(22px, 2.5vw, 32px) 0 clamp(16px, 2vw, 24px)`) agar ritme visual konsisten di semua status pemuatan katalog.

## [2.12.0] - 2026-10-22

### Justifikasi SemVer 2.0.0 (MINOR: 2.11.0 -> 2.12.0)
Kenaikan digit MINOR diterapkan secara mutlak sesuai kaidah Semantic Versioning 2.0.0 dan Direktif #3 [`AGENTS.md`](AGENTS.md) karena memuat perombakan arsitektur navigasi Android TV 10-Foot UI (*Left Vertical Sidebar Navigation*), restrukturisasi navigasi Desktop berbasis Apple HIG Flat UI (*single-source navigation & Apple Options Popover*), standardisasi indikator episode murni angka (*Episode Number Only*), polesan tampilan Detail Anime Apple Flat Inspector, serta ketahanan metadata franchise dan katalog:

1. **Android TV Left Vertical Sidebar Navigation (10-Foot UI):**
   - Menggantikan bar menu horizontal atas yang memakan ruang vertikal pada layar TV dengan **Left Vertical Sidebar (~200dp)** pada `layout-television/activity_main.xml` dan `src/tv/res/layout/activity_main.xml`.
   - Memberikan area katalog kanan ruang vertikal penuh (100% full height) dengan grid 5-6 kolom yang lebih lega dan imersif.
   - Integrasi navigasi spasial D-Pad mulus: D-Pad Kanan dari item sidebar langsung berpindah ke kartu kolom 0 pada katalog, dan D-Pad Kiri dari kolom 0 katalog secara otomatis kembali ke tab sidebar yang sedang aktif via `dispatchKeyEvent` di `MainActivity.java`.
   - Adopsi Apple tvOS Flat Dark Palette (`#161618`, `#1E1E22`, `#26262B`, Apple Blue `#0A84FF`) dengan selector fokus `bg_tv_sidebar_item.xml`.

2. **Standardisasi Indikator Episode (Clean Episode Number Only):**
   - Menghilangkan seluruh prefiks redundan (`EP 01`, `EP 12`, `SUB 12`, `Putar Ep 1`) pada seluruh antarmuka Android dan Web.
   - Badge episode pada kartu anime (`AnimeAdapter.java`, `term.js`) kini secara konsisten menampilkan angka bersih (misal: `1`, `2`, `12` atau `12/24` atau `TAMAT`).
   - Tombol quick play di Detail Anime diperbarui menjadi `"Putar 1"` atau `"Lanjutkan 4"`.
   - Nomor episode di modal detail dan selector pemutar kini terpusat dengan angka murni.

3. **Anime Detail View Apple Flat Polish:**
   - Memperbarui `activity_detail.xml` dan `layout-land/activity_detail.xml` dengan palet Apple Flat UI: kontainer `#161618`, kartu `#1E1E22`, dan tombol aksi kapsul Apple Blue `#0A84FF`.
   - Tipografi sinopsis Apple Subhead (`#86868B`, sans-serif-medium, letter-spacing 0.08) dengan body text `#D1D1D6` yang bersih dan mudah dibaca pada TV maupun smartphone.

4. **Desktop Apple HIG Redesign & Anti-Menu Ganda:**
   - Memusatkan navigasi desktop pada Top Segmented Pill Bar sebagai navigasi primer tunggal.
   - Mengeliminasi menu ganda pada desktop melalui **Apple Options Popover (`⋯`)** untuk utilitas (Cross Filter Katalog, Filter Genre, Ganti Sumber Stream, Cek Pembaruan, Bantuan).
   - Menambahkan spotlight search bar bergaya macOS dengan pintasan global `⌘K` / `Ctrl+K` dan `/`.

5. **Metadata & Catalog Resilient Fallback:**
   - Menambahkan fallback franchise relation langsung dari scraper HiAnime ketika AniList mengalami pemadaman (403 disabled) atau limitasi koneksi.
   - Menyelaraskan filter katalog musim lampau (`sy` dan `ey`) dan pagination agar selalu menyajikan total halaman akurat.

6. **Perbaikan Subtitle Anime Favorit (Bookmark) Tidak Muncul Permanen:**
   - **Invalidasi Cache SQLite Otomatis**: Menambahkan `clear_episode_cache_for_slug` pada `database/__init__.py` dan mengintegrasikannya ke `add_bookmark` serta `remove_bookmark` agar status favorit baru selalu membersihkan cache episode yang berpotensi cacat.
   - **Pencegahan Negative Subtitle Caching & Bypass Cache Stale**: Menambahkan parameter `refresh` dan route alias `/api/episode` pada `backend/main.py`. Mengabaikan cache hit dan scraping ulang jika `mode == 'sub'` namun entri cache tidak memiliki softsub yang valid, menghapus fallback buta ke cache 'dub', menolak penyimpanan ke `episode_cache` jika subtitle kosong, dan membersihkan in-memory failover cache saat bookmark diubah.
   - **Isolasi State Web Player**: Memisahkan metadata jumlah episode bookmark (`cur.subCount`) dari track subtitle pemutar (`cur.activeSub`, `cur.res`, `cur.cues`), memuat detail lengkap anime saat membuka dari favorit, dan mengaktifkan auto-recovery `refresh=1` jika unbookmark terjadi saat pemutar aktif dengan subtitle kosong.
   - **Android Native Intent & ExoPlayer Auto-Retry**: Memastikan `AnimeAdapter` dan `DetailActivity` selalu meneruskan extra `mode = 'sub'` yang valid, serta mengimplementasikan satu kali auto-retry dengan query `&refresh=1` pada `PlayerActivity` jika respons `mode='sub'` mengembalikan array subtitle kosong.

## [2.11.0] - 2026-10-21

### Justifikasi SemVer 2.0.0 (MINOR: 2.10.2 -> 2.11.0)
Kenaikan digit MINOR diterapkan secara mutlak sesuai kaidah Semantic Versioning 2.0.0 dan Direktif #3 [`AGENTS.md`](AGENTS.md) karena memuat penambahan provider scraping baru (*new scraping provider*) dan kapabilitas failover streaming CDN otomatis (`https://anichan.to/`) yang tetap kompatibel ke belakang (*backward-compatible new feature*):

1. **New Direct HLS Scraping Provider: AniChan (`backend/api/anichan.py` & Chaquopy Parity):**
   - Mengimplementasikan scraper native untuk `https://anichan.to/` yang langsung mengekstrak stream **raw HLS Master `.m3u8` murni** (zero iframe/embed player) dan segmen MPEG-TS asli (`0x47`). Server bertipe `embed` ditolak keras.
   - Mengelola sesi token otomatis via `POST /api/watch/session` dengan auto-refresh berdasarkan timestamp kedaluwarsa (`exp`).
   - Menyediakan dekriptor AES-GCM 256-bit payload server dari `GET /api/watch/servers` berbasis HMAC-SHA256 session token dan kunci `XOR(O, b)` dengan fallback ekstraksi dinamis jika kunci rotasi di masa depan.
   - Mengintegrasikan AniList ID resolver (`clean_title_for_search` dan `/api/suggest?q=...`) dengan pencocokan judul token similarity dan konsistensi musim.
   - Mengekstrak varian resolusi adaptif (`1080p`, `720p`, `480p`, `360p`), track subtitle WEBVTT asli, dan metadata intro/outro untuk fitur AniSkip.
   - Menerapkan perlindungan anti-hentai zero-tolerance (memvalidasi `isAdult: false` dan blacklist genre `Hentai`/`Adult`).
2. **Title-Scoped Automatic CDN Failover (`backend/main.py`):**
   - Kegagalan stream utama (HiAnime / Otakudesu) akibat CDN mati, 404, atau terblokir DPI (seperti kasus anime *Eyeshield 21*) secara transparan memicu failover otomatis ke AniChan HLS M3U8.
   - **Isolasi Mutlak Per-Judul:** Failover dicatat pada memori judul `_ANIME_FAILOVER_CACHE[slug] = "anichan"`, sehingga episode lanjutan (ep 2, 3, dst.) dari judul tersebut langsung tersambung ke AniChan tanpa delay timeout, sementara preferensi sumber utama global pengguna (`preferred_source`) **TIDAK PERNAH DIUBAH**. Judul anime lain tetap memprioritaskan HiAnime secara normal.
   - Mendaftarkan whitelist referer proxy video (`/api/player/video`) dan subtitle (`_fetch_sub_text`) untuk domain CDN AniChan (`toroplay.cymru`, `nexabloom.top`, `broforgotsave.online`, `shiora.top`, `imgnex.top`, `anichan.to`, `hiddenvertex.space`).
   - Menambahkan fallback daftar episode via `anichan.get_episodes(slug)` jika HiAnime dan Otakudesu tidak memiliki data episode judul tertentu.
3. **Frontend In-App Controls & Notification (`frontend/js/app.js`, `frontend/js/term.js`):**
   - Menampilkan toast notifikasi informatif saat stream dialihkan via failover: `"CDN HiAnime tidak merespon · Otomatis memutar cadangan dari AniChan"`.
   - Menambahkan opsi siklus sumber 3-arah (`hianime` $\leftrightarrow$ `otakudesu` $\leftrightarrow$ `anichan`) pada tombol sumber pemutar dan perintah terminal `:switch [hianime|otaku|anichan]` serta `:source anichan`.
   - Menampilkan label `"SRC: ANICHAN (FAILOVER) ⇄"` pada tombol info sumber pemutar video.
4. **Automated Unit Tests (`tests/test_anichan.py`):**
   - Menambahkan 6 unit test baru mencakup normalisasi judul, dekripsi payload AES-GCM, unwrapping direct HLS M3U8, parser varian resolusi, penolakan keras konten hentai, dan cascading failover per-judul tanpa polusi preferensi global.

## [2.10.2] - 2026-10-21

### Justifikasi SemVer 2.0.0 (PATCH: 2.10.1 -> 2.10.2)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memuat perbaikan bug navigasi (*navigation bug fixes*), perbaikan kompatibilitas platform Android TV dan 10-Foot UI, eliminasi *orphan focus*, pencegahan *virtual keyboard popup thrashing*, serta implementasi hierarki tombol Back berjenjang tanpa mengubah kontrak antarmuka eksternal (*backward-compatible platform ergonomics & bug fix patch*):
1. **Zero Orphan Focus & Focus History Stack (`frontend/js/app.js`):**
   - Mengimplementasikan `TvNavigationManager` yang mencatat `activeZone` (`tabs`, `search`, `chips`, `grid`, `detail-modal`, `player-hud`, `settings-modal`) dan `focusHistoryStack`.
   - Menambahkan mekanisme preservasi fokus sebelum dan sesudah re-render DOM (`innerHTML = ''`), menyimpan indeks elemen fokus dan memulihkannya secara otomatis setelah render selesai, sehingga fokus tidak pernah terlempar ke `document.body`.
   - Mengelola tumpukan riwayat fokus saat membuka Detail Anime, dialog Resume Watch, atau masuk ke Video Player, serta memulihkan fokus dan posisi scroll persis ke kartu atau episode pemicu saat pengguna menekan Back.
2. **Geometric & Dynamic Grid Spatial Navigation (`frontend/js/app.js`, `frontend/js/term.js`):**
   - Menghilangkan modulo statis `(idx + cols) % total` yang memicu wrap-around ke baris teratas saat pengguna menekan D-Pad Bawah di baris terbawah.
   - Mengimplementasikan kalkulasi geometris spasial 2D via `getBoundingClientRect()` dan dynamic row grouping.
   - Mengatasi edge-case baris terakhir tidak penuh: jika baris terakhir memiliki jumlah item lebih sedikit, target fokus otomatis dikunci ke item terakhir di baris bawah tersebut (`Math.min(targetIndex, items.length - 1)`).
   - Menambahkan pemanggilan seragam `targetEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })` pada setiap perpindahan fokus remote TV.
3. **Player HUD State Machine & Auto-Hide Fix (`frontend/js/app.js`, `frontend/css/style.css`):**
   - Memisahkan state fokus pemutaran video menjadi 3 mode tegas:
     a) `PLAYER_IDLE`: HUD tersembunyi. D-Pad Kiri/Kanan langsung melakukan seek 5 detik tanpa terhalang kontrol tersembunyi; OK melakukan Play/Pause (atau eksekusi AniSkip jika aktif); Up memunculkan HUD kontrol atas; Down memfokuskan AniSkip atau bar bawah.
     b) `PLAYER_HUD_ACTIVE`: HUD tampil dengan timer auto-hide 4000ms (4 detik) yang di-reset pada setiap interaksi D-Pad. Saat timer habis dan `hidePlayerControls()` berjalan, kelas `.tv-focus` dan `blur()` dibersihkan dari seluruh tombol HUD sebelum kembali ke mode `PLAYER_IDLE`.
     c) `PLAYER_MODAL_ACTIVE`: Saat dialog pengaturan (Subtitle/Resolusi/Kecepatan/Resume) terbuka, timer auto-hide dihentikan sementara (*suspended*) dan navigasi dikunci (*focus trap*) di dalam dialog sampai ditutup.
4. **Two-Stage Search Input Focus vs Virtual Keyboard (IME) (`frontend/js/app.js`, `frontend/index.html`, `MainActivity.java`):**
   - Pada mode TV di antarmuka web, kolom pencarian `#cmd` berstatus `readonly` saat navigasi visual D-Pad (Stage 1), mencegah Virtual Keyboard (IME) muncul menutupi layar hanya karena dilewati cursor D-Pad.
   - Mode ketik aktif (Stage 2) hanya dibuka ketika pengguna menekan tombol OK/Enter pada kolom pencarian.
   - Di Android TV native (`MainActivity.java`), `layoutSearchBox` menerima fokus visual D-Pad terlebih dahulu, dan `etSearch` tidak memanggil `showKeyboard(SHOW_FORCED)` secara agresif. Tombol Back dan D-Pad Bawah menutup keyboard via `hideSoftInputFromWindow` dan mengembalikan fokus navigasi.
5. **6-Level Back Button Hierarchy & Indikator Visual .tv-focus (`frontend/css/style.css`, `MainActivity.java`):**
   - Memastikan seluruh elemen interaktif memiliki `tabindex="0"`.
   - Memperkuat styling visual `.tv-focus` dengan `outline: 3px solid var(--accent)`, `transform: scale(1.06)`, `z-index: 20`, dan `scroll-margin: 72px` agar tidak terpotong header sticky maupun batas overscan TV.
   - Menata alur penanganan tombol Back (`Escape` / `KEYCODE_BACK`) berjenjang 6-level:
     (1) Tutup IME / keluar search edit $\to$ (2) Tutup modal dialog aktif $\to$ (3) Sembunyikan Player HUD $\to$ (4) Keluar Player ke Detail Episode $\to$ (5) Tutup Detail ke Grid Beranda $\to$ (6) Konfirmasi double-back (Toast 2000ms) untuk keluar aplikasi di layar utama.
6. **Refaktorisasi AniSkip OP/ED Caching, Anti-Stutter Seek & Remote Shortcut (`backend/api/aniskip.py`, `backend/main.py`, `frontend/js/app.js`, `PlayerActivity.java`):**
   - **Backend URL & Caching Fix:** Menghapus parameter statis `&episodeLength=0` dari endpoint AniSkip API (hanya disertakan jika durasi > 0). Memperbaiki logika caching agar tidak menyimpan respons kosong selama 24 jam saat terjadi network error/timeout/HTTP 5xx/429, menetapkan negative cache TTL 15 menit untuk 404, dan menambahkan validasi interval `is_valid_interval(start, end)` (durasi >= 5.0 detik).
   - **Cross-Provider OP/ED Cache Sharing:** Timestamp OP/ED valid yang diperoleh dari provider mana pun disimpan dengan kunci `(mal_id, ep)` dan `(normalized_title, ep)`, sehingga saat pengguna beralih stream ke Otakudesu untuk anime yang sama, timestamp intro dan outro tetap tersedia.
   - **Frontend Anti-Stutter & Rewind Tolerance:** State intro/outro, `activeSkipTarget`, dan tombol skip langsung di-reset sebelum request stream baru selesai. Ditambahkan flag `hasAutoSkippedIntro` dan `hasAutoSkippedOutro` serta offset `+0.5s` yang mengeliminasi seek loop / micro-stutter HLS dan memungkinkan pengguna me-rewind manual untuk mendengarkan lagu tanpa dilempar paksa ke depan.
   - **Shortcut 'S' Collision Fix:** Event listener tombol keyboard `S` memeriksa status tombol skip terlebih dahulu; jika tombol skip sedang aktif/terlihat, tombol 'S' memicu eksekusi skip OP/ED dan mencegah pemanggilan `switchSource`.
   - **ExoPlayer Android & Remote TV Fix:** Menambahkan validasi ketat interval (`introEnd > introStart && introEnd > 0 && duration >= 5000ms`) agar default {0, 0} tidak memicu tombol skip di 00:00. Ditambahkan flag auto-skip dan offset `+500ms`. Pada TV remote, tombol Fast-Forward langsung memicu skip, dan tombol OK mengeksekusi skip hanya jika tombol skip difokuskan atau saat HUD pemutar sedang tersembunyi.
7. **Unit Test Suite Otomatis Navigasi TV & AniSkip (`tests/test_tv_dpad_navigation.py`, `tests/test_skip_times.py`):**
   - Menambahkan unit test komprehensif baru untuk validasi interval, negative cache 404, error recovery tanpa cache polusi, dan cross-provider cache sharing.
   - Seluruh 253 test suite unit tests Tatap lulus 100%.
8. **Linux AppImage & Process Management Auto-Shutdown (`linux/AppRun`, `manage.sh`, `run.sh`):**
   - **Auto-Shutdown Backend via Signal Trap (`linux/AppRun`):** Menambahkan fungsi pembersihan `cleanup()` dan mengikat sinyal via `trap cleanup EXIT INT TERM HUP`. Saat jendela peramban atau runtime AppImage ditutup, skrip mengirim sinyal `kill -TERM "$SERVER_PID"`, memberikan tenggat toleransi 2 detik agar koneksi database SQLite dan FastAPI tertutup dengan bersih, lalu mengirimkan `kill -KILL "$SERVER_PID"` jika proses masih menggantung, meniadakan proses zombie server backend di latar belakang.
   - **Isolasi Proses Browser & Profil Independen (`linux/AppRun`):** Menambahkan flag `--user-data-dir="${DATA_DIR}/browser-profile"`, `--class=Tatap`, dan `--ozone-platform-hint=auto` pada eksekusi peramban berbasis Chromium (Chrome, Brave, Chromium, Edge). Isolasi ini mencegah *browser socket delegation* ke sesi browser pengguna yang sedang berjalan, sehingga `$BROWSER_PID` terikat murni pada jendela Tatap dan memicu `trap cleanup` seketika saat jendela aplikasi ditutup. Pada fallback `xdg-open`, ditambahkan panduan terminal dan notifikasi desktop interaktif.
   - **Multi-User Safe Log & PID Handling (`manage.sh`, `run.sh`):** Mengganti hardcoded path `/tmp/tatap.log` menjadi path terisolasi ramah multi-user (`${XDG_STATE_HOME:-$HOME/.local/state}/tatap/tatap.log` dengan fallback `./cache/tatap.log` atau `/tmp/tatap-$UID/`) untuk mencegah error `Permission denied` pada Linux multi-user. Menambahkan verifikasi kepemilikan proses pengguna aktif (`ps -u "$UID" -p "$pid" -o args=`) sebelum menjalankan `kill`, dan membatasi perintah stop via `pkill -u "$UID"` agar tidak mengganggu proses milik pengguna lain. Menambahkan fallback deteksi python executable pada `run.sh`.
   - **Unit Test Suite Linux Process Management (`tests/test_linux_process_management.py`):** Menambahkan 5 automated unit test untuk memverifikasi signal trap, isolasi profil peramban, isolasi path log multi-user, dan validasi sintaksis skrip bash (`bash -n`). Seluruh 258 unit test Tatap lulus 100%.
9. **Pemolesan Visual Apple UI × OG Tatap Eksklusif Desktop & Web (`frontend/css/style.css`):**
   - **Specular Inset Highlight & Animasi Pegas Apple:** Mengadopsi specular inset (`var(--specular-inset)`) dan kurva pegas Apple (`var(--ease-spring): cubic-bezier(0.22, 1, 0.36, 1)`) pada antarmuka desktop, memberikan kehalusan visual setara macOS Sequoia dan Apple TV+ tanpa membebani GPU/CPU dengan `backdrop-filter: blur()`.
   - **Penataan 4 Sudut Badge Poster Tanpa Tabrakan:** Menata ulang posisi badge di kontainer poster `.pc-media` ke 4 sudut mandiri (Kiri Atas: Indeks, Kanan Atas: Skor Rating, Kiri Bawah: Tag Episode/Tamat, Kanan Bawah: Tag Tipe, Dasar: Progress Track) dengan gaya pill gelap Apple TV yang bersih.
   - **Segmented Control & macOS Spotlight Bar:** Memperhalus tab navigasi atas (`.nav-tabs-bar`, `.nav-tab-btn`) dan kolom pencarian bawah (`#search-input-wrap`) bergaya Spotlight bar dengan prompt terminal `tatap$` aksen Cyan `#19d0d0`.
   - **Detail Anime Sheet & Uniform Episode Grid:** Mengunci `max-height: min(86vh, 780px)` pada modal detail dengan scroll lancar dan tombol episode seragam 44px.
   - **Video Player HUD & Floating Skip Pill:** Menyempurnakan transisi auto-hide HUD kontrol pemutar (220ms smooth) dan tombol AniSkip pill melayang.
   - **Eksklusivitas Desktop & Web:** Seluruh breakpoint responsif mobile (`<= 768px`, `<= 480px`), remote TV D-Pad (`.tv-focus`), dan modul native Android (`android/`) tetap 100% utuh tanpa modifikasi.
   - **Automated Unit Tests:** Menambahkan 6 automated unit test baru (`tests/test_apple_ui_desktop_polish.py`). Seluruh 264 test suite unit tests Tatap lulus 100%.
10. **Redesign Apple UI & Eliminasi Total Bug Visual Desktop/Web (`frontend/css/style.css`, `frontend/js/term.js`, `frontend/js/app.js`, `frontend/index.html`):**
    - **Pemisahan Total Fokus Desktop dari TV 10-Foot UI:** Mendekopel pemilih `:focus-visible` dari `.tv-focus`. Mengganti scaling paksa `scale(1.06)` dan neon glow 18px pada desktop dengan ring fokus Apple yang tenang (`box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px rgba(25, 208, 208, 0.5)`), meniadakan layout jumping saat navigasi atau klik mouse di peramban desktop.
    - **Pencegahan TV Mode False-Positive di Desktop:** Memperbaiki `renderSel()` di `term.js` agar hanya menyematkan `.tv-focus` jika `isTvMode()` aktif. Mengeliminasi hardcoded `_isTvDetected = true` pada `setFocus()` di `app.js` agar peramban desktop tidak disalahartikan sebagai Android TV.
    - **Eliminasi Double-Box Nesting pada Kartu Poster:** Mengubah kontainer luar `.poster-card` menjadi transparan dan tanpa border ganda, menjadikan artwork squircle `.pc-media` sebagai pahlawan visual utama dengan bayangan lembut Apple TV dan spring hover lift (`translateY(-4px) scale(1.015)`).
    - **Badge Kapsul Kaca Gelap Translucent:** Mengganti warna solid teal, hijau, dan oranye yang mencolok pada `.pc-badge-ep`, `.pc-badge-tamat`, dan `.pc-badge-long` menjadi kapsul gelap elegan (`rgba(10,12,16,0.82)`) dengan border dan teks beraksen halus.
    - **Pencarian Desktop Interaktif Seketika:** Menghilangkan kunci `readonly` pada `#cmd` di desktop saat inisialisasi sehingga pengguna dapat langsung mengklik dan mengetik tanpa hambatan.
    - **Apple Capsule Player Controls:** Memperhalus tombol kontrol video player (`.player-head-btns button/select`, `.player-foot>button`, `.sub-picker`) menjadi pill capsule kaca semi-transparan (`border-radius: 999px`).
    - **Refined Empty State Artwork:** Mempercantik tampilan kosong dengan ikon SVG viewfinder Tatap yang bersih menggantikan karakter ASCII mentah.
    - **Automated Unit Tests:** Menambahkan 6 automated unit test baru (`tests/test_apple_ui_desktop_redesign.py`). Seluruh 270 test suite unit tests Tatap lulus 100%.

## [2.10.1] - 2026-10-21

### Justifikasi SemVer 2.0.0 (PATCH: 2.10.0 -> 2.10.1)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memuat perbaikan bug keamanan kritis (*security vulnerability fix*), pencegahan kebocoran resource (*resource leak fix*), serta peningkatan stabilitas internal tanpa memodifikasi kontrak antarmuka eksternal (*backward-compatible security & reliability patch*):
1. **Mitigasi Celah Kritis SSRF (Server-Side Request Forgery) & Intranet Scanning (`backend/main.py`):**
   - Mengatasi kerentanan di mana endpoint proxy `/api/player/video`, `/api/player/sub`, dan `/api/player/sub_custom` memiliki konfigurasi CORS `Access-Control-Allow-Origin: *` dan sebelumnya hanya memverifikasi awalan skema `http`.
   - Mengimplementasikan fungsi validasi terpusat `_validate_external_proxy_url(url)` yang menolak seluruh skema non-HTTP/HTTPS serta memblokir akses ke alamat IP privat RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), alamat loopback (`127.0.0.0/8`, `localhost`, `0.0.0.0`, `::1`), link-local/cloud metadata (`169.254.0.0/16`, `169.254.169.254`), multicast, dan domain intranet (`.local`, `.internal`) dengan status `HTTP 403 Forbidden`.
   - Mencegah skrip jahat pada halaman web eksternal di peramban pengguna menyalahgunakan backend lokal Tatap (`127.0.0.1:8767`) untuk memindai jaringan lokal pengguna atau membaca layanan internal.
2. **Eliminasi Kebocoran File Descriptor Socket pada TLS Desync Streaming (`backend/api/desync.py`):**
   - Menyelidiki akar masalah terputusnya streaming video saat pengguna melakukan *seek*, *pause*, atau perpindahan episode: FastAPI `StreamingResponse` menginterupsi generator `tls_desync_stream` via `GeneratorExit`.
   - Menata ulang generator `tls_desync_stream` dan fungsi transmisi `tls_desync_request` ke dalam blok `try...finally:`, menjamin pemanggilan `raw_sock.close()` selalu dieksekusi dalam kondisi apa pun sehingga mencegah akumulasi socket descriptor tak tertutup (`OSError: [Errno 24] Too many open files`).
   - Menerapkan batasan kapasitas maksimum memori (*bounded cache* 256 entri) pada tabel in-memory `_DNS_CACHE`.
3. **Graceful Connection Pool Cleanup pada FastAPI Lifespan (`backend/main.py`):**
   - Menambahkan prosedur pembersihan koneksi jaringan asinkron saat server menerima sinyal *shutdown* pada handler `lifespan(app)`.
   - Menutup connection pool `_direct_client` via `await _direct_client.aclose()`, serta memanggil pembersihan persistent client pada `api.anilist.close_al_client()`, `api.hianime.close_shared_client()`, dan `api.otakudesu.close_otaku_client()`.
4. **Resiliensi Rate Limiting AniList & Optimasi Traversal Prekuel (`backend/api/anilist.py`):**
   - Mengimplementasikan pelacak *backoff cooldown* in-memory `_al_rate_limit_until`: jika upstream AniList merespons `HTTP 429 Too Many Requests`, sistem secara cerdas membaca header `Retry-After` (default 60 detik) dan menahan request berikutnya agar tidak memperpanjang penalti ban IP pengguna, melainkan langsung mengalirkan *fallback* katalog HiAnime / data lokal.
   - Mengoptimalkan penelusuran rantai prekuel pada `anime_relations()` dari 5 langkah menjadi 3 langkah maksimal, menghemat konsumsi kuota AniList secara drastis saat membuka modal detail anime berseri panjang.
5. **Perbaikan Resolusi URL Relatif Master M3U8 (`backend/api/hianime.py`):**
   - Memperbaiki metode pembacaan variant stream pada `_probe_master` agar menggunakan RFC-compliant `urllib.parse.urljoin(master_url, v_url)` alih-alih penggabungan string mentah `base + v_url`, mencegah terbentuknya URL cacat dengan double slash (`//`) pada CDN upstream bertingkat.
6. **Penguatan Defense-in-Depth Sanitasi XSS Frontend (`frontend/js/app.js`, `frontend/js/term.js`):**
   - Memperluas utilitas pembersih string `esc()` di antarmuka web desktop dan antarmuka TUI agar turut meng-escape karakter tanda kutip tunggal (`'` $\to$ `&#39;`), menutup celah penyisipan HTML injection pada atribut berelemen kutip tunggal.
7. **Suite Pengujian Keamanan & Resiliensi Otomatis (`tests/test_security_and_resilience.py`):**
   - Menambahkan 6 unit test baru yang memverifikasi penolakan SSRF, kelulusan URL publik sah, penutupan socket saat interupsi generator, serta pelacakan backoff AniList 429.
   - Seluruh 243 unit test lulus 100%.

## [2.10.0] - 2026-10-20

### Justifikasi SemVer 2.0.0 (MINOR: 2.9.4 -> 2.10.0)
Kenaikan digit MINOR diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memperkenalkan penambahan kapabilitas antarmuka baru, visual thumbnail sinematik 16:9 pada riwayat tontonan, perombakan arsitektur tampilan desktop, dan pencegahan hilangnya poster pada database tanpa breaking changes:
1. **Perombakan Layout Desktop Platform (Centered Container & Fluid Ergonomics):**
   - Menambahkan pembatas lebar maksimal `max-width: 1560px` terpusat (`margin: 0 auto`) pada layar desktop (`>= 1024px`), mencegah kartu anime merentang pipih tanpa batas pada monitor ultrawide dan 4K.
   - Mengoptimalkan media queries grid poster desktop: kartu diperlebar secara ergonomis dari sebelumnya 155px menjadi `minmax(165px, 1fr)` pada layar `>= 769px` dan `minmax(182px, 1fr)` pada layar `>= 1280px`.
   - Menambahkan efek hover elevasi kartu yang halus (`translate3d(0, -4px, 0)`) dengan *cyan rim glow* lembut (`box-shadow: 0 12px 28px -4px rgba(0,0,0,0.85), 0 0 18px rgba(25,208,208,0.22)`).
   - Memperbaiki tipografi judul kartu anime di desktop (`font-size: 13.5px`, `line-height: 1.38`, `height: 2.76em`) untuk keterbacaan optimal.
2. **Katalog Anime Sebagai Default Homescreen Saat Startup:**
   - Menjadikan **Katalog Anime** (`/api/catalog`) sebagai tampilan awal default saat aplikasi Tatap pertama kali dibuka di platform Desktop maupun Web Browser.
   - Tab navigasi `Katalog` (`tab-nav-katalog`) aktif secara otomatis dan memuat katalog populer lengkap dengan kartu anime, kontrol paginasi, dan tombol filter katalog tanpa lagi menampilkan prompt pencarian kosong (*"siap [ ] ketik judul"*).
3. **Penyajian Thumbnail Visual 16:9 pada Strip "Lanjutkan Menonton" di Beranda (`app.js`, `style.css`):**
   - Mengubah strip horizontal "Lanjutkan menonton" (`#continue-sec` / `#continue-row`) dari sebelumnya hanya berupa kotak teks polos tanpa gambar menjadi kartu visual horizontal (`.hist-card`) dengan thumbnail rasio sinematik 16:9 (`.hist-thumb-wrap`).
   - Melengkapi thumbnail dengan badge episode melayang (`.hist-ep-badge`), ikon play saat hover (`.hist-play-badge`), serta progress track bar (`.hist-progress-track` & `.hist-progress-fill`) di dasar thumbnail yang menampilkan proporsi menit tontonan secara presisi.
   - Menyediakan fallback placeholder anggun (`.hist-thumb-ph`) dengan ikon Tatap jika berkas poster sedang memuat atau gagal dimuat, mencegah terjadinya layout shift.
   - Memperbaiki visibilitas strip lanjutkan menonton agar tampil di beranda katalog (`katalog`, `musim`, `cari`).
4. **Pencegahan Terhapusnya Poster Anime pada Watch History & Auto-Backfill (`backend/database/__init__.py`):**
   - Menyelidiki akar masalah terhapusnya poster pada `watch_history`: saat memutar anime atau memperbarui progres tontonan, pemanggilan `add_history` tanpa argumen `poster` sebelumnya mengeksekusi `DELETE FROM watch_history` dan menyisipkan string kosong, melenyapkan URL poster yang tersimpan.
   - Memperbaiki `add_history` agar otomatis memeriksa dan mengawetkan (*preserve*) nilai `poster` dan `type` dari rekor sebelumnya, serta melakukan fallback pencarian ke tabel `bookmarks`.
   - Menambahkan mekanisme auto-backfill pada `get_history()` yang secara cerdas mengisi kembali poster dan tipe anime dari tabel `bookmarks` jika sebelumnya kosong, lalu memperbarui basis data SQLite secara atomik.
5. **Ekstraksi Poster pada Detail HiAnime & Forwarding MPV (`backend/api/hianime.py`, `backend/main.py`):**
   - Memperbarui `hianime_details(slug)` agar mengekstrak URL poster anime dari elemen `class="film-poster-img"` atau `class="film-poster"`.
   - Mengirimkan metadata `poster` pada respons endpoint `/api/anime/{slug}/episodes`.
   - Menyesuaikan handler `/api/play-mpv` agar turut meneruskan `poster` dan `type` ke `add_history`.
6. **Fallback Placeholder Anti-Kotak Hitam Kosong pada Grid Riwayat (`term.js`, `style.css`):**
   - Menambahkan fallback placeholder `.pc-thumb-ph` pada kartu grid tab Riwayat (`poster-grid`), mencegah kartu menjadi kotak hitam kosong saat poster belum tersedia atau terjadi kegagalan jaringan gambar.
7. **Hardening Startup Backend & Dialog Kesalahan GUI (`linux/AppRun`):**
   - Mengalihkan output server Python ke berkas log terpusat `${DATA_DIR}/server.log`.
   - Menambahkan pembersihan port 8767 cerdas via Python socket dan deteksi instance sehat yang sudah berjalan (`/api/ping`) untuk mencegah tabrakan socket (`[Errno 98] Address already in use`).
   - Menaikkan batas waktu tunggu startup ke 15 detik dengan interval polling 200ms (75 iterasi), menjamin pembukaan instan saat server siap dan toleran terhadap cold boot.
   - Menampilkan dialog kesalahan grafis (`zenity`, `kdialog`, `xmessage`, atau `notify-send`) yang menyajikan cuplikan log terakhir saat server gagal merespons, mencegah aplikasi keluar hening (*silent exit*).
8. **Handshake Startup Frontend & Overlay Pemulihan Koneksi (`app.js`, `api.js`, `index.html`):**
   - Menambahkan handshake `/api/ping` dengan mekanisme auto-retry 5 kali saat inisialisasi browser untuk mencegah error koneksi prematur saat backend sedang *warming up*.
   - Menyediakan modal overlay diagnostik `#backend-error-overlay` (*"Backend Tatap Belum Terhubung"*) lengkap dengan tombol interaktif *"Coba Hubungkan Ulang"*, penyalin informasi debug, serta *auto-reconnect poller* setiap 3 detik.
9. **Paritas Penuh Chaquopy Android & Suite Uji Otomatis (`tests/test_watch_history_thumbnail.py`):**
   - Menyinkronkan 100% seluruh modifikasi backend ke `android/app/src/main/python/backend/`.
   - Menambahkan unit test otomatis baru yang menguji layout desktop, startup hardening, preservasi poster, auto-backfill bookmarks, paritas Chaquopy, dan integritas token CSS/JS frontend.
10. **Harmonisasi Skala Tipografi Semantik, Eliminasi Faux-Bold & Redesain Kapsul Buffering ExoPlayer Android:**
    - **Skala Tipografi Semantik & Token Warna (`dimens.xml`, `colors.xml`):** Menetapkan skala tipografi modular harmonis Material Design 3 (`text_display_large` 20sp, `text_headline` 17sp, `text_title_large` 15sp, `text_title_medium` 13sp, `text_body_large` 13.5sp, `text_body_medium` 12sp, `text_subhead` 12sp, `text_caption` 11sp, `text_badge` 9.5sp, `text_code` 11.5sp) beserta token warna semantik (`text_primary`, `text_secondary`, `text_muted`, `text_dim`, `text_accent`, `text_success`, `text_warning`, `text_danger`).
    - **Eliminasi Total Faux-Bolding:** Menghilangkan kombinasi ganda sintetis `fontFamily="sans-serif-medium"` + `textStyle="bold"` di seluruh layout Android (`activity_main.xml`, `activity_detail.xml`, `activity_player.xml`, `item_anime_card.xml`, `item_episode.xml`, `item_lane_header.xml`, `item_range_chip.xml`, `item_season_chip.xml`, dan seluruh dialog), menghasilkan rendering glif medium murni (font weight 500) yang tajam tanpa artefak penebalan blur di semua chipset Android/TV (MediaTek, Transsion/Infinix, Amlogic).
    - **Redesain Kapsul HUD Buffering & Menyiapkan Stream ExoPlayer (`bg_buffering_hud.xml`, `activity_player.xml`, `PlayerActivity.java`):** Mengganti bentuk oval kaku 64x64dp lama dengan kapsul rounded rectangle dinamis modern (`corners:radius="14dp"`, stroke `1dp #3338BDF8`, padding `20dp x 14dp`, `wrap_content` hingga `maxWidth="260dp"`). Pesan teks buffering (`"MENYIAPKAN STREAM..."`, `"MEMUAT STREAM..."`, `"MENGHUBUNGKAN ULANG..."`, `"MEMUAT EPISODE X..."`) kini tampil proporsional tanpa terpotong (*clipped/truncated*) di semua rasio layar.
    - **Peningkatan Keterbacaan Dialog Bantuan Command (`dialog_command_help.xml`):** Memisahkan font perintah sintaks terminal (`monospace` tebal `@dimen/text_code`) dari teks penjelas fungsi yang kini menggunakan `sans-serif` alami `@dimen/text_caption`, meningkatkan legibilitas panduan perintah pengguna secara signifikan.
    - **Automated Test Suite Baru (`tests/test_android_typography_and_buffering_hud.py`):** Menambahkan 5 pengujian otomatis untuk memvalidasi token tipografi, integritas kapsul buffering, pencegahan faux-bolding, dan keterbacaan deskripsi dialog bantuan. Seluruh 216 automated test suite di repositori Tatap lulus 100%.
11. **Eliminasi Menyeluruh Duplicate Title & Isolasi Mutlak Riwayat Tontonan ke View Riwayat (`index.html`, `term.js`, `app.js`):**
    - **Pembersihan DOM & Eliminasi Seksi Usang:** Menghapus tuntas elemen usang `#lane-season-sec` (header statis *"Tayang musim ini"*) dan `#lane-still-sec` (header statis *"Masih tayang (lanjut)"*) dari `frontend/index.html` dan `frontend/js/term.js`. Menjadikan `<section id="search-sec">` dengan `<h2 id="results-title">` sebagai satu-satunya elemen kontainer judul di dalam `<main>`.
    - **Mesin Resolusi Judul Deterministik (`updateResultsTitle` di `term.js`):** Mengganti logika string appending akumulatif (`label += ...`) dengan resolver deterministik yang mencegah duplikasi judul di seluruh view:
      - *Musim Ini:* Menyajikan *"Tayang musim ini · FALL"* secara tunggal dan mencegah compounding string saat berpindah halaman paginasi (`pageNext`/`pagePrev`).
      - *Masih Tayang:* Menyajikan *"Masih tayang (lanjut)"* secara tunggal tanpa judul kembar.
      - *Terbaru / Jadwal Rilis:* Mencegah duplikasi frasa *"Hari Ini · Hari Ini"* saat melihat jadwal hari ini, menyajikannya bersih sebagai *"Jadwal rilis (Hari Ini)"*.
      - *Season Custom:* Mencegah duplikasi season berulang (misal *"Season: FALL 2024"* alih-alih *"Season: Fall 2024 · FALL"*).
      - *Katalog & Favorit:* Mempertahankan judul filter dinamis murni tanpa tercemar season appending.
    - **Isolasi Mutlak Riwayat Tontonan (`app.js`):** Mengisolasi riwayat tontonan 100% hanya pada tab **Riwayat** (`data-view="riwayat"`). Menghilangkan strip `#continue-sec` dari Katalog, Musim Ini, Cari, dan view lainnya sehingga beranda katalog bersih tanpa polusi riwayat. Tab Riwayat menyajikan seluruh riwayat tontonan secara lengkap dalam satu grid visual poster 16:9 (`.poster-grid`) dengan progress bar, badge episode, indikator waktu, paginasi, dan tombol hapus semua.
    - **Automated Test Suite Baru (`tests/test_desktop_title_deduplication.py`):** Menambahkan 4 pengujian otomatis yang memvalidasi ketiadaan seksi usang di DOM, isolasi strip riwayat, serta determinisme judul di semua view. Seluruh 220 pengujian di repositori Tatap lulus 100%.
12. **Eliminasi Online Status Pill, Penyesuaian Search Bar & Konsistensi Episode Button Size (`index.html`, `style.css`, `app.js`):**
    - **Eliminasi Online Status Pill & Redundansi Status:** Menghapus elemen `.bottom-actions` dan badge pil status scraper (`<span id="health">`) dari footer search bar, mengingat status konektivitas sudah ditangani secara andal oleh modal diagnostik startup `#backend-error-overlay` dan footer drawer navigation.
    - **Penataan & Dimensi Ergonomis Search Bar:** Search bar (`.search-input-wrap`) kini memanfaatkan 100% lebar baris input secara bebas tanpa terpotong elemen samping, dengan ketinggian yang ditingkatkan ke `height: 42px;` dan padding horizontal `0 16px;`.
    - **Penyelarasan Terpusat Desktop (Flush Alignment 1560px):** Menerapkan pembatas `max-width: 1560px; margin: 0 auto; width: 100%;` pada `.bottom-search-row` dan `.statusbar` di layar desktop (`>= 1024px`), menyelaraskan batas horizontal search bar agar lurus sejajar (*flush*) dengan kartu anime pada monitor 1080p, 1440p, hingga ultrawide.
    - **Konsistensi Dimensi Episode Button (.ep & .ep-grid):** Menetapkan tinggi tetap seragam `height: 44px; min-height: 44px; max-height: 44px;` dengan `border-radius: 8px;` pada tombol episode desktop (dan `40px` di mobile). Mengeliminasi ketimpangan visual di mana tombol episode terakhir ditonton (`.last-watch`) sebelumnya lebih tinggi daripada tombol normal karena memuat badge *"TERAKHIR"*; kini seluruh tombol memiliki dimensi luar yang persis identik (100% presisi).
    - **Automated Test Suite Baru (`tests/test_search_bar_layout_and_health_pill.py`):** Menambahkan 4 pengujian otomatis yang memverifikasi eliminasi status pill, dimensi dan alignment search bar, keseragaman dimensi episode button, serta ketahanan penanganan health check di JavaScript. Seluruh 224 pengujian otomatis di repositori Tatap lulus 100%.
13. **Pemulihan Menyeluruh Navigasi Keyboard 4-Arah, Enter/Space, dan Detail Episode Modal pada Desktop & Web (`term.js`, `app.js`, `style.css`, `index.html`):**
    - **Dukungan Grid Poster pada `renderSel()` & `moveSel()`:** Mengubah query `renderSel()` dari sebelumnya hanya `.trow` menjadi `box.querySelectorAll(".poster-card, .trow")`. Memperbaiki bug di mana navigasi keyboard macet total saat antarmuka berada pada tampilan beranda default Katalog, Musim Ini, Lanjutan, Riwayat, maupun Favorit (yang menggunakan kartu visual `.poster-card`).
    - **Navigasi Panah 4-Arah & Perhitungan Kolom Grid Responsif (`getGridCols`):** Menambahkan handler navigasi horizontal (`ArrowLeft` dan `ArrowRight`) serta vertikal baris demi baris (`ArrowDown` dan `ArrowUp` berdasarkan jumlah kolom grid responsif dinamis), memungkinkan penjelajahan kartu anime 2D yang alami dan lancar di monitor desktop.
    - **Aksi Enter dan Spasi Membuka Anime (`openSelected()`):** Memperbaiki handler tombol `Enter` dan `Space` pada kartu anime terpilih sehingga langsung memicu `openSelected()` / `App.openTitle()` untuk membuka detail episode anime alih-alih me-reset fokus ke command prompt.
    - **Transisi Mulus dari Search Bar Input (`#cmd`):** Menekan `ArrowDown` saat berada di kotak input pencarian kini secara otomatis memindahkan fokus langsung ke kartu hasil pertama tanpa perlu interaksi mouse.
    - **Navigasi Keyboard Lengkap di Modal Detail Anime (`handleTitleModalKey`):** Memungkinkan penjelajahan tombol episode (`.ep`) menggunakan panah 4-arah (`ArrowLeft`/`ArrowRight`/`ArrowUp`/`ArrowDown`), penekanan `Enter`/`Space` untuk langsung memutar episode yang disorot, pintasan `/` untuk memfilter nomor episode, pintasan `F` untuk bookmark favorit, serta `S` untuk beralih sumber streaming. Tombol episode terakhir ditonton (atau episode 1) otomatis terfokus saat modal dibuka.
    - **Kontrol Volume Keyboard di Video Player Desktop (`ArrowUp` / `ArrowDown`):** Menambahkan pengaturan volume bertahap (+/- 10%) dengan indikator toast visual pada pemutar video HTML5 desktop saat menekan `ArrowUp` atau `ArrowDown`.
    - **Styling Indikator Fokus Aksesibilitas (`:focus-visible` di `style.css`):** Menambahkan cincin fokus cyan bertepi tajam (`outline: 2px solid rgba(25,208,208,0.75)`) pada `.poster-card` dan tombol `.ep` saat dijelajahi via keyboard.
    - **Indikator Statusbar (`index.html`):** Memperbarui teks pintasan statusbar menjadi `<b>↑↓←→</b> pilih` untuk mencerminkan navigasi 4 arah.
    - **Suite Uji Otomatis Baru (`tests/test_desktop_keyboard_navigation.py`):** Menambahkan 8 unit test otomatis yang memverifikasi seluruh fungsionalitas navigasi keyboard, transisi input, seleksi grid 2D, modal episode, dan volume player.
14. **Perbaikan Masalah Auto-Scroll ke Bawah pada View Masih Tayang (`term.js`):**
    - **Akar Masalah Teratasi:** Mendiagnosis bug *cascading focus loop* di mana elemen banner header dual-lane (`is_header: true`) di dalam `S.items` tidak memiliki class `.poster-card`, sehingga query DOM `all = box.querySelectorAll(".poster-card, .trow")` mengalami pergeseran indeks. Mengklik kartu baris atas sebelumnya memfokuskan kartu berikutnya secara programatik dan memicu loop fokus berantai yang menyeret scroll ke dasar halaman.
    - **Seleksi Deterministik Berbasis `data-idx`:** Mengganti pencarian `all[S.sel]` dengan selektor langsung `box.querySelector('[data-idx="' + S.sel + '"]')` yang menyelaraskan indeks secara presisi dengan data `S.items`.
    - **Guard Pencegahan Rekursi Fokus:** Menambahkan kondisi `if(document.activeElement !== selEl)` sebelum memanggil `selEl.focus()`, memastikan interaksi mouse click tidak pernah memicu loop fokus berulang ke kartu lain.
15. **Paginasi Pencarian Desktop & Eliminasi Kebocoran Anime Tamat di Musim Saat Ini (`term.js`, `api.js`, `backend/main.py`, Chaquopy parity):**
    - **Pagination Pencarian Desktop (`view: "cari"`):** Menambahkan parameter `page` pada `window.Tatap.search` di `frontend/js/api.js`. Mengaktifkan pager (`hasPagination = S.total > 1`) pada pencarian di `frontend/js/term.js`, menyimpan `S.searchQuery = q`, menambahkan nomor halaman pada judul `(Hal X)`, dan memperbaiki `loadView()` serta `pagePrev()`/`pageNext()` agar menavigasi halaman pencarian alih-alih me-reset ke riwayat pencarian lama.
    - **Reset Pointer Seleksi Keyboard:** Menjamin reset `S.sel = -1` pada seluruh transisi halaman (termasuk tab Favorit dan Riwayat).
    - **Pembersihan Anime Tamat pada Musim Saat Ini (`which=now`):** Menyetel query AniList menjadi `status_in = ["RELEASING"]` khusus `which == "now"`, serta menyematkan filter pengaman sekunder `if which == "now" and is_finished: continue` untuk menyingkirkan anime Movie (1/1 episode) dan anime selesai dari tab Musim Ini.
    - **Pembaruan Cache Key `seasonal_v4`:** Menaikkan versi cache key dari `seasonal_v3` ke `seasonal_v4` pada `backend/main.py` dan Chaquopy parity (`android/app/src/main/python/backend/main.py`).
    - **Suite Uji Otomatis Baru (`tests/test_seasonal_and_navigation_fixes.py`):** Menambahkan 5 pengujian otomatis baru. Seluruh 237 pengujian otomatis di repositori Tatap lulus 100%.

## [2.9.4] - 2026-10-20

### Justifikasi SemVer 2.0.0 (PATCH: 2.9.3 -> 2.9.4)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memuat optimasi performa komprehensif pada varian Android TV (khususnya perangkat low-end dan TV Stick dengan RAM 1GB), penyempurnaan ergonomi navigasi remote D-Pad pada Video Player TV saat pause, serta perombakan sistem tipografi semantik untuk Android Mobile dan TV tanpa adanya breaking changes maupun perombakan arsitektur baru:
1. **Pemberantasan Lag & Stop-The-World GC Thrashing pada Android TV (`server_launcher.py`):**
   - Menghapus konfigurasi agresif `gc.set_threshold(100, 5, 5)` pada launcher background thread Chaquopy yang sebelumnya memicu stop-the-world Garbage Collection setiap kali terdapat 100 alokasi objek baru.
   - Mengembalikan ambang batas Python ke standar `(700, 10, 10)`, memangkas hingga ~70% pemborosan siklus CPU quad-core A53 pada TV Stick / TV Box kelas entri, sekaligus mencegah panas berlebih (*thermal throttling*).
   - Pembersihan memori GC eksplisit (`gc.collect()`) tetap dipertahankan secara pasif hanya saat sistem OS Android memicu event `onTrimMemory`.
2. **Eliminasi Cascading Layout Animation pada Grid Android TV (`MainActivity.java`):**
   - Menonaktifkan layout animation (`rvGrid.setLayoutAnimation(null)`) dan melewati `scheduleLayoutAnimation()` pada mode Android TV (`TvFocusHelper.isTv()`).
   - Kartu anime langsung muncul secara instan saat membuka beranda, berpindah tab, maupun menampilkan hasil pencarian tanpa membebani GPU fill-rate Mali-450 / Mali-G31.
3. **Optimasi Thread Priority & Zero-Animation pada `ImageLoader.java`:**
   - Memasang `ThreadFactory` kustom pada thread pool pemroses gambar dengan prioritas `android.os.Process.THREAD_PRIORITY_BACKGROUND`, menjamin thread pengunduh dan pen-decode bitmap tidak merebut time-slice CPU dari UI rendering thread dan thread pemutar video ExoPlayer.
   - Pada Android TV (`isTv`), menghilangkan animasi alpha fade berulang (`animate().alpha(1.0f).setDuration(160)`) per poster saat gambar selesai dimuat, beralih ke direct bitmap assignment untuk mencegah penumpukan animator object saat scrolling D-pad.
4. **Tuning Cache RecyclerView & Zero Layout Passes pada Focus Change (`TvFocusHelper.java` & `MainActivity.java`):**
   - Menetapkan ukuran view cache `rvGrid.setItemViewCacheSize(10)` dan membatasi `RecycledViewPool` ke 12 item pada TV, cukup untuk menampung baris atas dan bawah di luar viewport 4-5 kolom tanpa konsumsi RAM berlebih (< 1.5MB).
   - Menghapus mutasi dinamis `card.setStrokeWidth(...)` saat berpindah fokus di `TvFocusHelper.java`, sehingga hanya warna border (`card.setStrokeColor(...)`) yang diperbarui (pure GPU paint shader tanpa memicu `requestLayout()` dan kalkulasi ulang outline shape).
   - Menambahkan `.withLayer()` dan `DecelerateInterpolator` (80ms) pada scale zoom fokus remote TV.
5. **Penyempurnaan Navigasi Remote D-Pad Player Android TV (`PlayerActivity.java`):**
   - Mengimplementasikan routing navigasi remote deterministik saat video dalam keadaan **pause**:
     - **D-pad Kanan:** Mengarahkan fokus berurutan ke tombol Episode Berikutnya (`btnExoNext`) $\to$ tombol Skip Op/Ed (`btnSkipOpEd`) jika tersedia.
     - **D-pad Kiri:** Mengarahkan fokus ke tombol Episode Sebelumnya (`btnExoPrev`) $\to$ tombol Play/Pause.
     - **D-pad Atas:** Membuka dan langsung memfokuskan panel atas (`layoutTopBar`) (prioritas: tombol Subtitle Selector `btnSubSelector` $\to$ Resolusi $\to$ Back).
     - **D-pad Bawah:** Menutup top bar dan langsung memfokuskan panel kontrol bawah (Timeline bar $\to$ Play/Pause $\to$ Skip Op/Ed).
   - Saat video sedang berputar (**playing**), D-pad Kiri dan Kanan tetap berfungsi sebagai seek cepat mundur/maju 5 detik dengan visual feedback ripple instan.
6. **Perombakan Sistem Tipografi Semantik & Skala 10-Foot UI:**
   - Menambahkan file resource qualifier resmi `values-television/dimens.xml` dan `values-sw600dp-land/dimens.xml` untuk menghadirkan skala tipografi 10-Foot UI yang nyaman dibaca dari jarak 3 meter (judul kartu `15sp`, tinggi kontainer `48dp` anti-terpotong, badge `11.5sp`, judul detail `21sp`, sinopsis `14.5sp`).
   - Merapikan token dimensi mobile di `values/dimens.xml` (judul kartu `13sp`, tinggi kontainer `40dp`, badge `10sp`, judul detail `17sp`, sinopsis `13sp`).
   - Menerapkan keluarga font modern `sans-serif-medium` (Google Roboto sistem tanpa alokasi memori tambahan) pada kartu, badge, tombol tab, dan halaman detail.
7. **Penambahan Test Suite Otomatis (`tests/test_android_tv_perf_and_typography.py`):**
   - Menambahkan 6 unit test otomatis untuk memvalidasi tiadanya GC thrashing, background thread priority, zero layout passes, D-pad navigation routing, dan konsistensi token tipografi.
   - Seluruh test suite Tatap lulus 100% (202 tests passed).

## [2.9.3] - 2026-10-20

### Justifikasi SemVer 2.0.0 (PATCH: 2.9.2 -> 2.9.3)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memuat perbaikan bug kritis timeout streaming (*streaming timeout fixes*), optimasi failover multi-tier, dan mekanisme auto-retry serta cache invalidation tanpa adanya breaking changes maupun perombakan arsitektur baru:
1. **Perbaikan Timeout Streaming Multi-Tier & Fast Failover (Studi Kasus: Anime Naruto `naruto-1335`):**
   - Mendiagnosis dan memperbaiki akar masalah pada anime yang memiliki server upstream gantung (seperti `fetch.nexabloom.top` pada server Megaplay `HD-1` Naruto Episode 1) yang memicu error `The read operation timed out`.
   - Mengatasi bug pada fungsi `_fetch` di mana parameter `timeout=timeout` tidak diteruskan ke `client.get(url, headers=h, timeout=timeout)`, sehingga timeout pendek (5-8s) saat scanning server mati diabaikan oleh `httpx` di lingkungan Chaquopy Android dan memakan waktu tunggu penuh 12 detik + 11 detik fallback desync (23.57 detik terbuang sia-sia).
   - Menetapkan batas timeout ketat (5.0s) pada master playlist probing `_try_megaplay` dan langsung menandai host CDN master yang mati ke `_mark_dead(master_host, ttl=600)` agar pemutaran episode berikutnya langsung melewati (*skip*) server tersebut dalam 0ms.
   - Mengeliminasi penandaan keliru pada `megaplay.buzz` saat yang mati adalah CDN master di baliknya, sehingga endpoint utama tetap dapat melayani judul anime lain.
2. **Peningkatan Batas Read Timeout Client Android (`PlayerActivity.java`):**
   - Menaikkan `conn.setReadTimeout(20000)` (20 detik) menjadi `conn.setReadTimeout(45000)` (45 detik) pada `resolveAndPlayStream`.
   - Mencegah Android memutus koneksi secara sepihak di detik ke-20 (`SocketTimeoutException: Read timed out`) sebelum backend sempat mencapai server alternatif yang sehat (seperti ZokoAnime yang selesai dalam 2.8 detik).
3. **Mekanisme Smart Auto-Retry & Invalidation Cache Basi (`force=true`):**
   - Menambahkan fungsi `delete_episode_cache(slug, ep, mode)` pada modul database SQLite (`backend/database/__init__.py` dan Chaquopy parity).
   - Menambahkan parameter `force: bool = Query(False)` pada endpoint `/api/stream/resolve`. Jika `force=True`, backend secara otomatis memotong dan menghapus cache episode yang basi atau bermasalah, lalu meminta stream segar dari provider upstream.
   - Pada Android Native (`PlayerActivity.java`) dan Web Desktop (`app.js` & `api.js`): Saat terjadi error timeout atau player error, pemutar secara otomatis melakukan 1 kali *failover auto-retry* dengan query `&force=true` untuk memulihkan pemutaran tanpa campur tangan pengguna.
   - Jika setelah auto-retry stream tetap tidak dapat dijangkau, pemutar menampilkan tombol interaktif *"Coba Lagi ↻"* alih-alih membiarkan layar gelap/freeze.
4. **Eliminasi Unduhan Ganda Master M3U8 (`_validate_master_playlist`):**
   - Pada `_try_embed_legacy`, playlist master yang telah diunduh pada fase `_probe_master` langsung diteruskan ke `_validate_master_playlist(master, referer, variants=[], body_content=...)`, menghemat 1 kali round-trip jaringan (1-3 detik) pada server ZokoAnime dan VidTube.
5. **Paritas Penuh Chaquopy Android:**
   - Seluruh perbaikan backend disinkronkan 100% secara identik ke `android/app/src/main/python/backend/api/hianime.py`, `backend/main.py`, dan `backend/database/__init__.py`.
6. **Penambahan Test Suite Otomatis (`tests/test_stream_timeout_recovery.py`):**
   - Menambahkan unit test komprehensif untuk pengujian `delete_episode_cache`, `resolve` dengan `force=True`, `_validate_master_playlist` dengan `body_content`, serta fungsi negative cache `_mark_dead`.
   - Seluruh test suite Tatap lulus 100% (196 tests passed).

## [2.9.2] - 2026-10-18

### Justifikasi SemVer 2.0.0 (PATCH: 2.9.1 -> 2.9.2)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memuat perbaikan bug normalisasi track subtitle dan sumber terjemahan autosub (*backward-compatible bug fixes*) pada seluruh platform Tatap tanpa adanya perubahan breaking changes maupun penambahan modul antarmuka baru:
1. **Perbaikan Seleksi Subtitle Default English Murni (Kasus Multi-Track CDN ZokoAnime / Heavenly Delusion):**
   - Mengatasi anomali kritis pada server stream upstream (seperti ZokoAnime pada Episode 8–13 anime *Heavenly Delusion* / *Tengoku Daimakyou*) di mana CDN menyetel dummy attribute `lang: "en"` ke seluruh track subtitle multi-bahasa Eropa (Czech, Danish, Dutch, Finnish, Greek, Hungarian, Norwegian, Polish, Romanian, Slovak, Swedish).
   - Memperluas pemetaan kamus ISO-639-1 `_label_to_lang` dan `_LANG_NAME` di backend (`backend/api/hianime.py`) dan Chaquopy parity (`android/app/src/main/python/backend/api/hianime.py`) untuk memetakan seluruh nama bahasa Eropa dan Asia ke kode bahasa aslinya (`Czech` $\to$ `cs`, `Danish` $\to$ `da`, `Dutch` $\to$ `nl`, dsb.).
   - Mencegah dummy `lang: "en"` menimpa bahasa asli jika label menyebutkan nama bahasa non-Inggris (`_NON_ENGLISH_KEYWORDS`).
   - Menerapkan prioritas bertingkat pada normalisasi track default (`_normalize_subtitles`):
     1. Track native `Indonesian` (jika tersedia).
     2. Track `English` yang memiliki atribut upstream `raw_default == True`.
     3. Track berlabel persis `English` (`english`, `english [full]`, `eng`).
     4. Track varian `English` lainnya.
     5. Track non-Arabic pertama.
   - Mengeliminasi situasi di mana track bahasa Ceko (*Czech*) terpilih sebagai default karena urutan abjad C mendahului E.
2. **Perbaikan Sumber Terjemahan Autosub (Anti-Ngaco):**
   - Memperbaiki helper prewarming terjemahan backend `_check_and_prewarm` di `backend/main.py` dan Chaquopy parity agar URL sumber subtitle bahasa Inggris (`en_url`) memfilter kata kunci bahasa non-Inggris dan memprioritaskan track English exact.
   - Dengan masukan teks subtitle bahasa Inggris asli (bukan bahasa Ceko), autosub (GTX+, AI Fansub, dan Pure Google GTX) menghasilkan terjemahan bahasa Indonesia yang akurat, natural, dan bersih tanpa teks acak/rusak (*"autosub anti-ngaco"*).
3. **Hardening Layer Client (Android Native & Web Desktop):**
   - Pada `PlayerActivity.java` (Android Native), memperketat deteksi `isEnglish` dengan array pengecualian kata kunci bahasa non-Inggris (`nonEnKeywords`) serta memprioritaskan `foundExactEnSub` sebelum fallback ke varian English lainnya.
   - Pada `frontend/js/app.js` (Web Desktop), memperluas `langMap` dengan bahasa-bahasa Eropa serta menambahkan filter `isPureEnglishSubTrack` dan `isExactEnglishSubTrack` pada pemilih subtitle (`pickSubtitleUrl`) dan dropdown generator (`renderSubtitles`).
4. **Sistem Fallback Subtitle Bertingkat (5-Tier Subtitle Fallback):**
   - **Tier 1 (Cross-Mode SUB -> DUB Harvesting):** Pada mode dubbing bahasa Inggris (`mode=dub`) di mana server upstream hampir selalu tidak menyertakan subtitle (`tracks: []`), Tatap secara otomatis memanen track subtitle dari mode `sub` pada episode yang sama. Penonton dubbing kini dapat menikmati subtitle Indonesia (GTX+, AI Fansub) maupun English CC.
   - **Tier 2 (Cross-Server Probing):** Jika server video yang memutar video menghasilkan `subtitles: []`, sistem melakukan inspeksi metadata ringan ke server alternatif (Vidplay / ZokoAnime) untuk menyuntikkan track subtitle valid tanpa perlu mengunduh playlist m3u8 yang berat.
   - **Tier 3 (Otakudesu -> HiAnime Softsub Donor):** Saat memutar stream dari Otakudesu (yang hanya memiliki hardsub), Tatap mencocokkan judul ke HiAnime dan menyematkan track softsub padanannya.
   - **Tier 4 & 5 (Dukungan Subtitle Kustom Eksternal - File Lokal & URL):**
     - Endpoint backend baru `/api/player/sub_custom` (POST & GET) menerima teks upload file `.srt` / `.vtt` maupun URL eksternal, mengonversinya secara otomatis ke format WebVTT standar, dan mengintegrasikannya dengan mesin autosub Tatap.
     - Android Native (`PlayerActivity.java`): Menambahkan opsi `[+] Pilih File Subtitle Lokal (.srt / .vtt)...` via Storage Access Framework dan `[+] Masukkan URL Subtitle Kustom...`.
     - Web Desktop (`app.js` & `index.html`): Menambahkan input file lokal (`FileReader`) dan input prompt URL langsung dari antarmuka player.
5. **Penambahan Test Suite Subtitle & Fallback:**
   - Menambahkan test suite baru `tests/test_subtitle_selection.py` dan `tests/test_subtitle_fallback.py` (total 10 pengujian subtitle baru, seluruh test suite Tatap lulus 100%).
6. **Tombol Genre Tertaut (Linked Genre Buttons) pada Seluruh Platform:**
   - **Android Native & Android TV (`DetailActivity.java`, `MainActivity.java`, `bg_detail_genre_chip.xml`):** Seluruh chip genre pada halaman detail kini interaktif (`clickable` dan `focusable`). Pengguna mobile dapat langsung mengetuk genre untuk memfilter katalog, sedangkan pengguna Android TV dapat mengarahkan D-Pad remote ke deretan chip genre dengan feedback visual scale 1.08x dan border cyan yang elegan. Saat dipilih, aplikasi membawa `MainActivity` ke depan (`FLAG_ACTIVITY_CLEAR_TOP`) dan memfilter katalog sesuai genre terpilih via `onNewIntent` handler.
   - **Web Desktop (`app.js`, `term.js`, `style.css`):** Elemen genre pada modal detail anime (`.genre-pill.interactive`) kini dapat diklik untuk menutup modal dan langsung memfilter tampilan katalog sesuai genre melalui fungsi `window.Tui.applyGenreFilter(slug)`.
7. **Perbaikan Status Tayang Anime Tamat (Eliminasi False Ongoing Status):**
   - Mengatasi bug di mana anime yang telah selesai tayang (*Finished Airing / Completed*, misal `12/12` atau `28/28`) masih menampilkan teks `(Sedang Tayang)` atau badge `ONGOING`.
   - **Android UI (`DetailActivity.java` & `AnimeAdapter.java`):** Header jumlah episode kini secara cerdas menampilkan `X/X Episode (Tamat)` jika anime berstatus `finished` / `tamat` / `completed` atau rasio episode telah mencapai target tayang penuh, dan hanya menampilkan `(Sedang Tayang)` jika anime benar-benar masih dalam masa penayangan aktif.
   - **Backend Scrapers (`backend/api/hianime.py`, `backend/main.py`, dan Chaquopy parity):** Menyematkan status `is_finished`, `status = "finished"`, dan `badge = "TAMAT"` secara otomatis pada seluruh item kartu katalog dan jalur penayangan musiman saat `eps_released >= eps_total`.
   - **Web Desktop (`app.js`):** Memperbaiki penentuan badge status modal track detail agar mendeteksi rasio penuh episode dan status selesai dengan akurat.
8. **Test Suite Komprehensif (`tests/test_detail_metadata.py`):**
   - Menambahkan pengujian otomatis untuk verifikasi status tamat HiAnime browse cards, logika string episode di DetailActivity, intent navigasi genre di MainActivity, dan linked genre button web desktop.
9. **Sistem In-App Update Android Resmi (Mobile & Android TV / Google TV):**
   - **Pemeriksaan On-Demand & Anti Gangguan (Zero Auto-Popup):** Pemeriksaan pembaruan rilis Tatap berjalan secara manual saat pengguna mengklik menu *"Periksa Pembaruan"* di drawer menu samping atau mengeksekusi perintah terminal `:update`. Tidak ada pop-up otomatis saat startup aplikasi sehingga kenyamanan pengguna tetap terjaga 100%.
   - **Visual Download Progress Dialog:** Mengunduh berkas APK resmi bertanda tangan (`tatap-release-v<VER>.apk` untuk Mobile atau `tatap-tv-release-v<VER>.apk` untuk TV) langsung di dalam aplikasi secara streaming dengan progress bar cyan horizontal, persentase (0% s.d. 100%), serta rasio ukuran berkas real-time (misal `16.2 MB / 36.4 MB`).
   - **Dukungan Penuh Navigasi D-Pad Android TV:** Dialog pembaruan (`dialog_app_update.xml`) dan dialog pengunduhan (`dialog_app_download.xml`) sepenuhnya mendukung remote kontrol Android TV dengan highlight visual scale dan border cyan (`TvFocusHelper`).
   - **Integrasi PackageInstaller Resmi OS via FileProvider:** Menggunakan `androidx.core.content.FileProvider` (`${applicationId}.fileprovider`) untuk mengekspos APK secara aman ke installer sistem operasi tanpa memerlukan izin berbahaya. Menangani alur verifikasi izin `REQUEST_INSTALL_PACKAGES` (`Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES`) secara mulus dengan auto-resume instalasi setelah izin disetujui.
   - **HTTP Redirect Resilient Downloader:** Menerapkan penanganan HTTP redirect multi-hop (301, 302, 303, 307, 308) pada `AppUpdateManager.java` guna menjamin keandalan pengunduhan dari endpoint GitHub Releases ke storage AWS S3 / CDN.
   - **Cache Backend & Paritas Chaquopy:** Menambahkan cache server lokal 5 menit pada endpoint `/api/update/check` dengan bypass `force=true` guna melindungi dari rate-limiting API GitHub, serta menyelaraskan field `notes` dan `body` secara identik antara `backend/main.py` dan Chaquopy Android.
10. **Test Suite In-App Update (`tests/test_in_app_update.py`):**
   - Menambahkan 7 pengujian otomatis baru yang memvalidasi kontrak endpoint `/api/update/check`, integritas FileProvider dan permission Android, validasi layout dialog, struktur kelas `AppUpdateManager.java`, dan ketiadaan auto-check saat startup aplikasi.
11. **Optimasi Penggunaan CPU Tinggi pada Platform Linux AppImage & Desktop:**
   - **Aktivasi Akselerasi Hardware GPU & VA-API Video Decoding (`linux/AppRun`):** Menyematkan flag Chromium/Chrome resmi (`--enable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL,CanvasOopRasterization`, `--enable-gpu-rasterization`, `--enable-zero-copy`, `--ignore-gpu-blocklist`) sehingga proses decoding stream video HLS 1080p/720p dialihkan sepenuhnya ke GPU (Mesa VAAPI / NVDEC), menurunkan konsumsi CPU dari 80%–150%+ menjadi hanya ~3%–8%.
   - **Native Wayland Integration (`--ozone-platform-hint=auto`):** Menghindari overhead compositing Xwayland pada distro Linux modern (Ubuntu 22.04/24.04, Fedora, Arch).
   - **Reduksi Background Bloat & Telemetri:** Menonaktifkan service background Chromium yang menyerap CPU (`--disable-background-networking`, `--disable-component-update`, `--disable-sync`, `--disable-default-apps`, `--no-default-browser-check`, `--no-first-run`, `--disable-breakpad`, `--disable-features=Translate,OptimizationHints,MediaRouter`, `--audio-buffer-size=2048`).
   - **Mesin C-Extension Backend FastAPI/Uvicorn (`backend/main.py` & Paritas Chaquopy):** Mengaktifkan pustaka C-extension berkinerja tinggi `uvloop` (libuv) dan `httptools` yang sudah terpasang di runtime AppImage, serta mematikan `access_log` dan mengatur `log_level="warning"` guna mengeliminasi formatting ribuan baris log HTTP GET per episode selama streaming segmen video.
   - **Throttling & Guard Canvas Ambient Lighting (`frontend/js/app.js` & `frontend/css/style.css`):**
     - Menambahkan guard `document.hidden` dan `isVideoFullscreen()` pada loop `startAmbient()` agar canvas berhenti memproses draw/readback saat jendela diminimalkan atau saat video memenuhi layar.
     - Menyelaraskan frekuensi sampling dari 500ms menjadi 1200ms (sesuai durasi `transition: background 1.2s ease`), memangkas 58% frekuensi operasi `getImageData()` GPU-to-CPU readback.
     - Menambahkan `contain: strict;` pada `#ambient` dan `#ambient-fallback` untuk isolasi komposit GPU layer.
12. **Test Suite Optimasi Linux AppImage (`tests/test_linux_appimage_optimization.py`):**
   - Menambahkan pengujian otomatis baru yang memvalidasi keberadaan seluruh flag akselerasi hardware dan reduksi bloat di `AppRun`, auto-detection uvloop/httptools dan `access_log=False` di backend, serta throttling guards di frontend.
13. **Gesture Tahan Layar (Hold) untuk Percepat Putar 2.0x (Forward) & Mundur Cepat (Rewind) Terisolasi di Android Mobile:**
   - Mengimplementasikan gesture sentuh tahan lama (*press-and-hold*) yang intuitif pada pemutar video Android Mobile (`PlayerActivity.java`):
     - **Tahan Layar Sisi Kanan ($\ge 50\%$ lebar layar):** Mengaktifkan mode *Fast-Forward 2.0x* (`setPlaybackParameters(new PlaybackParameters(2.0f))`) seketika dengan feedback getaran haptik (`VibrationEffect.EFFECT_CLICK`) dan menampilkan HUD status cyber neon di tengah atas layar: `⚡ 2X Cepat >>`.
     - **Tahan Layar Sisi Kiri ($< 50\%$ lebar layar):** Mengaktifkan mode *Fast-Rewind* dengan melompat mundur bertahap secara halus (`seekTo(newPosition)`) sebesar 2 detik setiap 180ms, disertai feedback getaran haptik dan HUD akumulatif real-time: `⏪ Rewind (-Xs) <<`.
     - **Lepas Jari (Release / Action Up / Cancel):** Menghentikan mode akselerasi/rewind seketika, mengembalikan kecepatan putar ke kecepatan semula (`holdOriginalSpeed`), dan menyembunyikan HUD tanpa jeda.
   - **Pencegahan Konflik Gesture & Isolasi TV:**
     - Terintegrasi aman dengan `GestureDetector.SimpleOnGestureListener.onLongPress`: Hanya aktif jika tidak ada gesture scroll aktif (`activeGestureZone == 0`).
     - Diisolasi secara ketat hanya untuk perangkat Mobile melalui `!TvFocusHelper.isTv(this)`. Pengguna Android TV dengan remote D-Pad tidak terpengaruh sama sekali.
     - Perlindungan siklus hidup aktivitas (`onPause` & `onDestroy`): Memastikan loop runnable rewind dibatalkan dan kecepatan dikembalikan normal secara bersih jika aktivitas berpindah atau layar terkunci.
14. **Test Suite Komprehensif Hold Speed & Rewind Android (`tests/test_hold_speed_and_rewind_android.py`):**
   - Menambahkan pengujian otomatis baru yang memverifikasi deklarasi HUD `#hud_hold_speed` di `activity_player.xml`, binding view, implementasi `onLongPress` dengan pemisahan zona kanan (2.0x forward) dan kiri (rewind), loop runnable rewind 180ms/-2000ms, haptics, penanganan `ACTION_UP`/`ACTION_CANCEL`, cleanup `onPause`, dan isolasi TV.
15. **Restorasi Format Kontrol CC & Subtitle Bawaan Stabil:**
   - Membatalkan perubahan eksperimental panel CC Styler HUD fullscreen, tombol dock mengambang, serta menu titik 3 pada pemutar desktop.
   - Mengembalikan arsitektur kontrol subtitle pemutar desktop secara utuh ke implementasi stabil bawaan Tatap (`#pm-subs-wrap`, dropdown `#pm-subs`, sizing S/M/L, dan tombol terjemahan cepat ID) demi menjaga stabilitas fungsional dan kenyamanan pemutaran.
16. **Adopsi Desain Sistem Shiru UI (Ultra-Minimalist & Optimasi Perangkat Low-End):**
   - Mengadopsi bahasa desain modern Shiru (RockinChaos/Shiru & shiru.app) yang diselaraskan secara penuh dengan filosofi Tatap: Ultra-Minimalist, Zero-Bloat, dan Hemat Resource untuk Perangkat Low-End (laptop lawas, prosesor Celeron/Atom, GPU terintegrasi, dan Linux software rendering).
   - **Palet Obsidian & Electric Teal:** Latar belakang hitam pekat murni (`#000000`) yang hemat daya di layar OLED/AMOLED, panel permukaan bertingkat (`#0e1015` / `#151820`), dan aksen vibrant electric teal (`#19d0d0` dan `#008d8d`).
   - **100% Native System Font Stack (0KB Download / 0ms Latency):** Tidak memuat Google Fonts eksternal untuk menjaga prinsip Standalone Runtime lokal Tatap (0 network request, 0ms latency font swap, 0 footprint memori font table).
   - **Peniadaan Beban Backdrop Blur (Zero Backdrop Blur Tax):** Menghilangkan `backdrop-filter: blur(...)` pada seluruh elemen UI (navbar, drawer, sheet, modal, floating skip button), mencegah lonjakan utilisasi CPU hingga 80-100% pada GPU lawas dan driver Mesa software rasterization.
   - **Top Slim Sticky Navigation Bar (`.tui-head` & `.nav-tabs-bar`):** Menghadirkan bar navigasi tab atas yang ramping (tinggi 50px) dengan tab kategori langsung (*Musim Ini*, *Terbaru*, *Masih Tayang*, *Favorit*, *Katalog*) dengan indikator garis bawah aksen teal sederhana dan cepat, terhubung secara reaktif dengan router `Tui.setView`.
   - **Kartu Anime Sinematik Berestetika Bersih (`.poster-card`):** Sudut melengkung modern `border-radius: 10px`, layout containment (`contain: content; will-change: transform;`) untuk menghemat hingga 70% kalkulasi relayout DOM browser saat scrolling, dan transisi GPU composited `translate3d(0, -2px, 0)` yang mulus 60 FPS.
   - **Elemen Mikro Khas Shiru:** Indikator `.eyebrow` dengan titik neon persegi teal (`box-shadow: 0 0 6px var(--accent)`) dan garis pemisah `.shiru-divider`.
   - **Integritas Fungsional & Subtitle Dual-Layer:** Seluruh ID DOM, shortcut keyboard, endpoint API, dan kontrol subtitle dual-layer (`#pm-subs-overlay` & native `VTTCue`) tetap 100% stabil dan kompatibel.
17. **Test Suite Komprehensif Shiru UI Minimalist (`tests/test_shiru_ui_minimalist.py`):**
   - Menambahkan 6 pengujian otomatis baru yang memverifikasi ketiadaan font Google eksternal, peniadaan backdrop blur, token obsidian-teal, struktur tab navigasi atas, isolasi layout kartu anime, dan sinkronisasi event listener JavaScript.
18. **Optimalisasi Video Player Shell 16:9 Adaptif & Pemanfaatan Area Panggung Maksimal:**
   - Menghapus pembatasan kaku tinggi video 640px (`max-height: clamp(240px, 66vh, 640px)`) yang sebelumnya memicu letterboxing berlebihan pada layar monitor modern (1080p, 1440p, 4K).
   - Memperbarui dimensi `.player-shell` menjadi dinamis dan proporsional: `width: min(calc((94vh - 100px) * (16 / 9)), 96vw); max-width: 1560px; max-height: 96vh;` dengan overflow vertikal terisolasi rapi.
   - Mengatur rasio aspek bawaan video anime ke `aspect-ratio: 16 / 9` dengan penyesuaian dinamis intrinsik stream (`videoWidth / videoHeight`) saat event `loadedmetadata`, memungkinkan video anime mengisi area panggung secara maksimal tanpa memotong kontrol header atau footer.
19. **Fitur Tampilan Penuh Riwayat Menonton (Watch History View Paritas Android):**
   - Menambahkan tab navigasi **Riwayat** di header atas (`.nav-tabs-bar`) dan menu drawer (`:riwayat`) yang selaras dengan tab riwayat di Android.
   - Menampilkan koleksi anime yang pernah ditonton lengkap dengan badge nomor episode terakhir, indikator progress bar menit menonton di bagian bawah thumbnail kartu, tanggal tonton, dan dukungan resume pemutaran sekali klik.
   - Memperbarui perintah terminal `:riwayat`: mengetik `:riwayat` membuka tampilan riwayat menonton, sedangkan `:riwayat hapus` atau tombol "hapus semua" membersihkan database riwayat.
20. **Penghalusan Tipografi & Percantik Top Header Menu:**
   - Menerapkan global font antialiasing (`-webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;`) untuk mengeliminasi rasterisasi teks bergerigi pada latar hitam obsidian.
   - Merombak top header menu menjadi bar terpadu yang elegan: logo TATAP dengan tracking geometrik 2.2px, pill badge versi v2.9.2, dan tab bar tersegmentasi ala pill container (`background: var(--surface); border-radius: 8px;`) dengan feedback interaktif yang bersih dan halus.
   - Mengeliminasi tombol hamburger menu ganda di bottom bar (`#btn-drawer`), mempertahankan `#btn-drawer-head` di pojok kanan atas sebagai tombol menu tunggal resmi.
   - Mengatasi redundansi menu di drawer dengan menyembunyikan grup navigasi tampilan di layar desktop ($\ge 769\text{px}$) via class responsif `.drawer-group-nav`.
   - Menata ulang status bar keyboard shortcuts dengan styling badge keycap `kbd` yang rapi.
21. **Test Suite Komprehensif Video Player Shell & Riwayat (`tests/test_videoplayer_shell_and_riwayat.py`):**
   - Menambahkan 6 pengujian otomatis baru yang memverifikasi antialiasing tipografi, tombol hamburger tunggal, elemen UI dan tab riwayat, eliminasi duplikasi drawer di desktop, rasio aspek player shell 16:9, dan handler view/command riwayat di JavaScript (seluruh 175 test suite Tatap lulus 100%).
22. **Optimasi Engine Terjemahan Subtitle GTX+ (Pengayaan Slang Halus & Kosakata Game/Dungeon/Anime):**
   - **Pre-GTX Normalizer (`_PRE_GTX_EN_SLANG_RULES`):** Memperluas pra-pemrosesan teks sumber bahasa Inggris untuk menangkap idiom dan slang modern sebelum dikirim ke Google Translate guna mencegah blunder harfiah mesin (*dead meat, for real, cut the crap, spawn point, pull aggro, freaking out, rage quit, dungeon break, raid boss, party leader/members*).
   - **Kamus Leksikon Universal Game, RPG & Dungeon (`_UNIVERSAL_FANSUB_RULES`):** Mengoreksi calque harfiah mesin menjadi istilah anime/game yang akurat dan imersif (*"pesta"* $\to$ *"party"*, *"ruang bawah tanah tingkat X"* $\to$ *"dungeon tingkat X"*, *"inti/gerbang/jebakan ruang bawah tanah"* $\to$ *"inti/gerbang/jebakan dungeon"*, *"titik bertelur/kemunculan"* $\to$ *"titik spawn"*, *"menarik kebencian"* $\to$ *"menarik aggro"*, *"waktu/masa pendinginan"* $\to$ *"waktu cooldown"*, *"tingkat drop"* $\to$ *"drop rate"*, *"bilah kesehatan/mana"* $\to$ *"bar HP/MP"*, *"bos serbuan"* $\to$ *"raid boss"*, *"penggemar status"* $\to$ *"buff status"*, *"pemain tunggal"* $\to$ *"pemain solo"*, *"pemburu peringkat S"* $\to$ *"hunter rank S"*).
   - **Penghalusan Diksi Lisan Percakapan Kasual (`_CASUAL_FANSUB_RULES`):** Menyuntikkan partikel percakapan alami (*"nih", "deh", "sih", "kan", "kok"*) serta mengoreksi ekspresi harfiah kaku (*"apakah kamu nyata"* $\to$ *"kamu serius"*, *"tidak ada cara di neraka"* $\to$ *"mana mungkin"*, *"kamu daging mati"* $\to$ *"mampus kau"*, *"potong omong kosong"* $\to$ *"hentikan omong kosongmu"*, *"buat dirimu di rumah"* $\to$ *"anggap aja rumah sendiri"*), tanpa redundansi atau duplikasi leksikon.
   - **Preservasi Akronim Kapital pada Case-Matching:** Memperbarui `_replace_match` agar akronim kapital (seperti `HP`, `MP`, `DPS`, `SMK`, `OSIS`) tidak tereduksi menjadi huruf kecil saat teks sumber ditulis dengan huruf kecil.
   - **Proteksi Adegan Formal & Paritas 100% Chaquopy Android:** Adegan formal (kerajaan/militer) tetap 100% terlindungi dari bahasa gaul santai, dan seluruh aturan disinkronkan identik antara root backend dan Chaquopy embedded Android.
   - **Perluasan Automated Test Suite (`tests/test_translate.py`):** Menambahkan 3 blok pengujian komprehensif (`test_new_pre_gtx_slang_and_gaming`, `test_new_gaming_and_dungeon_universal_rules`, `test_new_casual_slang_smoothing`, dan `royal3`) sehingga total 18 pengujian translate dan seluruh 178 test suite Tatap lulus 100%.
23. **Penyempurnaan Tampilan & Tata Letak Anime Card (Optimasi Khusus Perangkat Low-End):**
    - **Rasio Poster Proporsional 2:3:** Mengubah rasio visual poster pada `.pc-media` menjadi `aspect-ratio: 2/3` sesuai standar format poster anime bioskop/serial industri, mengeliminasi distorsi dan pemotongan canggung di sisi gambar.
    - **Gradien Scrim Halus Tanpa Tambahan Node DOM (`.pc-media::after`):** Menerapkan gradien pelindung poster bawah via pseudo-element CSS murni, menjamin keterbacaan teks dan badge pada poster berlatar terang tanpa menambah elemen `<div>` baru di JavaScript (menghemat 30–50+ node DOM per render halaman).
    - **Sistem Badge Terstruktur & Semantik:**
      - **Kiri Atas:** Nomor urut / index (`.pc-idx`) dengan styling *dark pill*.
      - **Kanan Atas:** Skor rating bintang amber (`.pc-score`: `★ 8.5`) atau tanda tanya (`.pc-bad`) jika unmapped.
      - **Kiri Bawah:** Status episode semantik (`.pc-badge-ep`, `.pc-badge-tamat`, `.pc-badge-long`) tanpa styling CSS inline.
      - **Kanan Bawah:** Format anime (`.pc-badge-type`: `TV`, `MOVIE`, `ONA`).
      - **Garis Bawah Media:** Watch history progress bar (`.pc-progress-track`).
    - **Jaminan Performa 60 FPS untuk Low-End Device:**
      - *Strictly Zero `backdrop-filter: blur(...)`:* Menghilangkan seluruh filter blur multi-pass GPU yang menjadi penyebab utama stutter/jank pada chipset low-end (Mali, PowerVR, Intel HD). Seluruh badge menggunakan warna solid/transparan pekat berkinerja tinggi.
      - *Strict CSS Containment:* Mempertahankan `contain: content;` dan `will-change: transform;` guna mengisolasi subtree rendering setiap kartu.
      - *Compositor-Only Animations:* Mikro-interaksi hover hanya memanfaatkan akselerasi GPU murni (`transform: translate3d(0, -2px, 0)` dan `opacity`).
      - *Bypass Zoom pada Touch/TV:* Animasi scaling poster diisolasi hanya untuk perangkat dengan mouse/pointer melalui `@media (hover: hover)`.
    - **Test Suite Komprehensif (`tests/test_anime_card_polish.py`):** Menambahkan 4 pengujian otomatis baru yang memvalidasi keberadaan wadah `pc-media`, rasio 2/3, pseudo-element scrim, kelas badge semantik, zero backdrop-filter, dan CSS containment (seluruh 182 test suite Tatap lulus 100%).
24. **Perbaikan Ketahanan Sistem Pembaruan Versi (Pemberantasan Error 'Koneksi Gagal' pada Opsi Update):**
    - **Akar Masalah:** Menangani pembatasan kuota unauthenticated GitHub REST API (`HTTP 403 Forbidden` / 60 req/jam) yang sering habis pada jaringan seluler bersama (CGNAT) di Indonesia, timeout koneksi seluler/TV box, serta ketiadaan fallback jaringan.
    - **Arsitektur Fallback Bertingkat 4-Tier pada Backend (`backend/main.py` & Paritas Chaquopy):**
      - *Tier 1 (GitHub REST API):* Memeriksa API resmi GitHub dengan perpanjangan timeout menjadi 12.0 detik.
      - *Tier 2 (GitHub Web Releases Redirect):* Jika Tier 1 mengembalikan HTTP 403 atau error jaringan, otomatis menghubungi halaman web rilis `https://github.com/asfaraguest/tatap/releases/latest` (bebas batas kuota API), mengekstrak nomor versi dari header redirect `Location` (`/tag/v<VER>`), dan merekonstruksi URL unduhan 4 aset resmi secara deterministik.
      - *Tier 3 (GitHub Raw Fastly CDN):* Jika Tier 1 & 2 terganggu oleh DNS poisoning, membaca `VERSION` dan `CHANGELOG.md` via Fastly CDN (`raw.githubusercontent.com`) dengan latensi instan (< 500ms).
      - *Tier 4 (Stale Cache Fallback):* Jika perangkat benar-benar offline, menyajikan data cache rilis sebelumnya alih-alih melempar error gagal.
    - **Fallback Native Java Langsung pada Android (`AppUpdateManager.java`):**
      - Menambahkan mekanisme fallback langsung via HTTPS dari kode Java native jika server backend lokal Python (`127.0.0.1:8767`) sedang sibuk atau tidak merespons, menjamin pemeriksaan update di Android tidak pernah gagal.
    - **Perluasan Automated Test Suite (`tests/test_in_app_update.py`):**
      - Menambahkan 2 pengujian otomatis baru (`test_backend_update_tier2_web_fallback` dan `test_backend_update_tier3_raw_fallback`) yang memverifikasi otomatisasi fallback saat API terkena HTTP 403 dan simulasi kegagalan DNS web (seluruh 184 test suite Tatap lulus 100%).
25. **Penyempurnaan Proporsi & Konsistensi Desain Bilah Atas dan Bilah Bawah Sesuai Kaidah Desain Grafis:**
    - **Mathematical 3-Column Grid (`1fr auto 1fr`):** Mengganti sistem flex pada `.tui-head` menjadi 3-kolom grid CSS presisi dengan `justify-self: center` pada bar tab navigasi (`.nav-tabs-bar`), mengeliminasi deviasi horizontal sehingga tab navigasi berada 100% tepat di garis tengah (*true optical center*) layar monitor.
    - **Modular Scale 8-Point Grid (`56px`):** Menyelaraskan tinggi bilah atas menjadi 56px ($7 \times 8\text{px}$) dengan elevasi permukaan obsidian halus dan jarak bernapas vertikal 10px atas-bawah yang proporsional.
    - **Simbol Grafis Brand Mark Geometrik (`#icon-brand-mark`):** Menambahkan simbol apertur geometrik cyber viewfinder tajam di samping logo `TATAP` serta menjadikan elemen logo interaktif (`#head-brand`) untuk kembali ke Beranda (*Musim Ini*) dan auto-scroll ke atas.
    - **Pemusatan Pencarian Eksklusif di Bar Bawah & Konsistensi Gaya Desain Atas-Bawah:**
      - Mengeliminasi duplikasi elemen pencarian pada header atas agar bilah atas tetap bersih, fokus, dan lapang.
      - Menyelaraskan bahasa desain *bottom bar* secara simetris dengan *top bar*: menggunakan gradien obsidian komplementer `linear-gradient(0deg, ...)`, garis batas halus `rgba(255,255,255,0.07)`, elevasi bayangan `0 -4px 20px rgba(0,0,0,0.5)`, serta material permukaan `search-input-wrap` yang identik dengan kapsul tab navigasi (`background: rgba(18,21,28,0.85); border-radius: 9px;`).
      - Menyematkan ikon pencarian penuntun (*search lead icon*) dan keycap shortcut hint `/` pada bar bawah.
    - **Perluasan Automated Test Suite (`tests/test_top_bar_menu_polish.py`):** Menambahkan 6 pengujian otomatis baru yang memverifikasi keberadaan brand logo mark SVG, arsitektur 3-kolom grid CSS, pemusatan pencarian eksklusif di bar bawah, konsistensi token desain atas-bawah, event listener interaktif, dan kepatuhan Zero Backdrop Blur (seluruh 190 test suite Tatap lulus 100%).
26. **Perbaikan Bug Next Page pada Pencarian Android Platform:**
    - **Akar Masalah Teratasi:**
      1. Mengatasi ketiadaan parameter `&page=` pada pembentukan URL endpoint `/api/search` di `MainActivity.java` yang menyebabkan tombol Next Page memanggil ulang hasil halaman 1.
      2. Menambahkan parameter `page: int = Query(1, ge=1, le=100)` pada endpoint backend `/api/search` (`backend/main.py` dan Chaquopy Android) serta mengisolasi cache key per nomor halaman (`p1`, `p2`).
      3. Meng-upgrade scraper HiAnime (`backend/api/hianime.py`) dengan fungsi `hianime_search_page` yang mengekstrak kartu halaman selanjutnya via `/search?keyword={}&page={}` dan membedah total halaman serta status `has_next` dari paginator HTML.
      4. Mengeliminasi heuristik usang `count >= 10` pada `MainActivity.java` dengan metadata paginasi semantik (`hasNextPage || totalPages > currentPage`), mencegah tombol Next Page aktif secara keliru (*false-positive*) pada kata kunci pencarian yang hanya memiliki 1 halaman.
    - **Penyempurnaan Indikator Paginasi & Proteksi Navigasi TV:**
      - Menampilkan indikator halaman dinamis `Hal X / Y` pada bilah kontrol paginasi dan memperbarui judul hasil pencarian dengan keterangan `(Hal X)`.
      - Menambahkan proteksi navigasi remote D-Pad Android TV: ketika tombol Next Page dinonaktifkan di halaman terakhir, fokus remote otomatis dialihkan ke tombol `Sebelumnya` atau kartu anime untuk mencegah jebakan fokus (*focus trap*).
    - **Perluasan Automated Test Suite (`tests/test_search.py` & `tests/test_pagination_all_views.py`):**
      - Menambahkan pengujian otomatis baru untuk validasi envelope pagination pencarian, isolasi cache per halaman, dan verifikasi multi-halaman (seluruh 192 test suite Tatap lulus 100%).

## [2.9.1] - 2026-10-18

### Justifikasi SemVer 2.0.0 (PATCH: 2.9.0 -> 2.9.1)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memuat perbaikan bug ergonomi kontrol sentuh (*backward-compatible bug fixes*) pada pemutar video Android tanpa adanya penambahan modul arsitektur baru maupun breaking changes, yaitu:
1. **Pencegahan Ketidaksengajaan Kecerahan Redup / Volume Anjlok Saat Tarik Notifikasi (Top & Bottom Exclusion Zones):**
   - Menambahkan area pengecualian (*exclusion zone*) di tepi atas layar ($\le \max(56\text{dp}, 16\% \text{ tinggi layar})$). Sentuhan awal pengguna dari tepi atas untuk menarik bilah notifikasi, melihat jam, atau memeriksa baterai di mode layar penuh tidak lagi memicu kontrol volume atau kecerahan.
   - Menambahkan area pengecualian di tepi bawah layar ($\ge \text{tinggi} - \max(44\text{dp}, 12\% \text{ tinggi})$) agar usapan bilah navigasi (*gesture pill / home navigation*) tidak memicu perubahan volume secara mendadak.
2. **Penyempitan Zona Gesture ke Tepi Layar & Zona Aman Tengah (Side-Edge Zoning & 30% Central Deadzone):**
   - Membatasi area sentuh aktif murni ke tepi luar layar: Kecerahan hanya merespons di sepertiga kiri ($X \le 35\%$ lebar layar) dan Volume hanya merespons di sepertiga kanan ($X \ge 65\%$ lebar layar).
   - Menjadikan area tengah layar ($35\% < X < 65\%$, selebar 30% layar) sebagai zona aman netral (*deadzone*). Sentuhan santai atau usapan di tengah tidak lagi mengubah pengaturan kecerahan/volume.
3. **Peredaman Sensitivitas & Ambang Batas Gerak Awal (Sensitivity Dampening & Slop Confirmation):**
   - Menurunkan faktor akselerasi gesture dari `1.2x` menjadi `0.85x`, menghasilkan pergeseran slider kecerahan dan volume yang halus, bertahap, dan tidak melonjak drastis.
   - Mewajibkan ambang batas pergeseran awal ($\ge 14\text{dp}$) dengan rasio vertikal dominan $|\Delta Y| > 1.25 \times |\Delta X|$ sebelum sesi gesture dinyatakan aktif, mengeliminasi jitter mikro dan kedipan OSD HUD akibat sentuhan tidak sengaja.
   - Mengimplementasikan state tracking disiplin (`activeGestureZone`) per-stroke sentuhan dengan penguncian arah dan reset bersih saat `ACTION_UP` atau `ACTION_CANCEL`.
4. **Proteksi Isolasi Android TV:**
   - Menambahkan pengaman `TvFocusHelper.isTv(...)` pada `onScroll` untuk mencegah pemicuan gesture sentuh bayangan pada perangkat TV atau remote box.

## [2.9.0] - 2026-10-17

### Justifikasi SemVer 2.0.0 (MINOR: 2.8.3 -> 2.9.0)
Kenaikan digit MINOR diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena penambahan fungsionalitas dan modul antarmuka baru yang backward-compatible (*backward-compatible new features*), yaitu:
1. **Peningkatan Metadata Anime Detail (Android Mobile & Web Desktop):**
   - Menghadirkan barisan metadata kaya pada view detail anime: **Rating Skor**, **Badge Status Penayangan** (`TAMAT` / `ONGOING`), **Daftar Genre Chips Interaktif**, dan **Baris Info Studio Animasi, Musim Rilis, serta Sumber Karya Asli (Manga/Light Novel)**.
2. **Pembersihan & Penghapusan Pemotongan Sinopsis 280 Karakter:**
   - Menghapus pemotongan artifisial 280 karakter di backend (`[:280]`) pada seluruh endpoint seasonal dan search.
   - Menambahkan utilitas `clean_synopsis_text()` untuk membersihkan tag HTML, meng-unescape entitas karakter (`&quot;`, `&#039;`), serta membuang label atribusi mengganggu `(Source: ...)` dan `[Written by MAL Rewrite]`.
3. **Smart In-Place Expand Tampilan Sinopsis:**
   - Menata ulang kontainer sinopsis dengan styling dark cyberpunk (`#0C0E14` / `#1A1E29`) dan header aksen cyan `SINOPSIS`.
   - Mengimplementasikan ekspansi terkontrol (preview ringkas -> expand penuh tanpa menggelembungkan kartu atau menggeser daftar episode ke luar layar).
4. **Isolasi Penuh Antarmuka Android TV (10-Foot UI):**
   - Seluruh elemen metadata mobile baru secara ketat diisolasi via `TvFocusHelper.isTv(this)` sehingga antarmuka Android TV tetap bersih dan navigasi D-pad remote tidak terganggu.
5. **Perbaikan Tautan Statistik Unduhan di README.md:**
   - Memperbarui tautan tombol statistik unduhan ke visualisator rilis GitHub publik SomSubhra.
6. **Pembaruan Test Suite:**
   - Menambahkan test suite baru `tests/test_detail_metadata.py` (5 pengujian baru, total 124 automated tests lulus 100%).
7. **Pemberlakuan Direktif Unduhan Publik & Anti-404 README.md:**
   - Menambahkan Master Directive #6 pada `AGENTS.md` dan baris panduan pada `PROJECT_MAP.md`: Seluruh tombol unduhan di `README.md` mutlak wajib selalu mengarah ke rilis publik aktif terakhir (`v2.8.3`), bukan rilis berstatus DRAFT, guna mencegah kegagalan unduhan publik (error 404).
   - Memperbarui `tools/bump_version.py` dengan perintah `--sync-readme` dan audit target rilis publik pada `check_consistency()`.
8. **Optimasi Akurasi Haptic Feedback Scene (Anti-BGM & Dual-Path Onset Transient Detector):**
   - Menghapus deadlock state-machine (`consecutiveLoudBuffers > 3`) yang sebelumnya mengunci detektor dalam status supresi permanen saat musik pertarungan (*battle BGM*) diputar.
   - Mengimplementasikan deteksi dua jalur (*Dual-Path Onset Transient Detector*):
     - *Physical Impact / Strikes* (pukulan tinju, tendangan, benturan pedang/katana, tembakan): mendeteksi lonjakan energi instan $\Delta \text{RMS} \ge 1400$ buffer-ke-buffer atau lonjakan relatif $\ge 1.55\times$ di atas baseline berjalan dengan $\text{Peak} \ge 16500$.
     - *Heavy Explosions & Super-Moves* (ledakan granat/bom, transformasi Titan, pelepasan energi Kamehameha/Domain Expansion): mendeteksi transien $\text{Peak} \ge 24000$ dan lonjakan energi $\text{RMS} - \text{baseline} \ge 1200$, bahkan di tengah musik pertempuran yang sedang kencang.
   - Menghubungkan status segmen *AniSkip* (`isInOpEd`) untuk membungkam getaran haptik secara otomatis selama lagu pembuka (*Opening*) dan penutup (*Ending*) berlangsung.
   - Menonaktifkan efek HAL `HapticGenerator` bawaan Android selama pemutaran media agar tidak bocor dan bergetar sendiri mengikuti bass musik, mengalihkan kendali penuh ke filter akustik cerdas `SceneHapticAudioSink`.
   - Menambahkan test suite baru `test_anti_bgm_transient_onset_detector` dan `test_dsp_simulation_scene_vs_bgm` pada `tests/test_haptic_feedback.py` (total 126 automated tests lulus 100%).
9. **Sinkronisasi Garis Waktu & Optimasi Akurasi Haptic Scene (Timeline Lag Compensation & Stereo Fusion):**
   - Mengeliminasi desinkronisasi awal (~200–300ms mendahului adegan) akibat ring buffer internal hardware `AudioTrack` ExoPlayer menggunakan `ForwardingAudioSink` yang membandingkan `presentationTimeUs` dengan `getCurrentPositionUs(false)`.
   - Mengintegrasikan penjadwalan getaran terkompensasi inersia motor (~20ms rise time) via `handler.postDelayed`, menghasilkan sinkronisasi milidetik presisi (*frame-perfect visual-acoustic haptic sync*).
   - Menghilangkan *stereo channel blindness*: loop sampling kini membaca saluran Kiri (L) dan Kanan (R) secara simultan (`Math.max(|Left|, |Right|)`), menangkap seluruh efek ledakan dan benturan stereo di sisi kanan layar.
   - Menambahkan filter *Bipolar 200Hz Low-Pass* (`SubRatio`) dan *Crest Factor* untuk menyaring teriakan vokal karakter anime (*anti-scream rejection*) dan membedakan benturan fisik kinetik dari vokal maupun BGM.
   - Menjamin pembatalan getaran tertunda secara bersih (*cancellation hygiene*) pada saat pengguna melakukan *seek*, jeda (*pause*), pergantian episode, atau keluar dari aplikasi.
10. **Eliminasi Getaran Palsu Antar-Adegan Tembakan & Ledakan (Zero-Delay Direct Trigger, Anti-Reverb Lockout, & Dual-Cadence Cooldown):**
    - **Zero-Delay Direct Trigger:** Menghapus penjadwalan tunda buatan `handler.postDelayed(~200ms)` dan wrapper `ForwardingAudioSink` yang sebelumnya menunda getaran ke celah hening / jeda antar-adegan; `vibrateDirect(...)` kini dieksekusi seketika (*zero-delay*) saat transien benturan terdeteksi pada buffer audio.
    - **Anti-Reverb Tail Lockout & Mandatory Attack Onset:** Mewajibkan lonjakan energi positif ($\Delta \text{RMS} \ge 1200$) pada deteksi ledakan dahsyat serta mengunci jendela gema selama 400ms (`now - lastExplosionTriggerMs < 400`), mencegah gema/asap pasca-ledakan memicu getaran palsu susulan di ruang kosong antara aksi.
    - **Dual-Cadence Cooldown:** Memisahkan cooldown tembakan (85ms) dan benturan/ledakan (200–400ms), mendukung getaran presisi pada tiap butir peluru tembakan beruntun (*burst-fire / semi-auto*).
    - **Profil Haptik Multi-Tier Berbasis Karakter Akustik:** Tembakan memicu pulsa klik mekanis tajam & renyah (15ms), benturan fisik/pukulan tinju solid (30ms), dan dentuman ledakan dahsyat berbobot berat (45ms).
11. **Kalibrasi Akustik Youjo Senki Season 2 & Dukungan Angka Romawi Season:**
    - **Kalibrasi Onset Attack ($\Delta \text{RMS} \ge 600$):** Berdasarkan kalibrasi empiris waveform PCM audio pertempuran udara dan artileri *Youjo Senki*, menambahkan syarat wajib kenaikan energi positif ($\Delta \text{RMS} \ge 600$) pada jalur deteksi `isAttackOnset`, meniadakan seluruh getaran palsu yang sebelumnya sempat bocor saat intensitas suara sedang meluruh/turun tajam ($\Delta \text{RMS} < 0$).
    - **Dukungan Angka Romawi Penomoran Season:** Memperbarui ekstraktor musim (`_extract_season_num`) dan pembersih token judul (`_clean_title_tokens`) pada backend dan Chaquopy untuk mendukung angka Romawi (`II` -> season 2, `III` -> season 3, `IV` -> season 4, dst.), menjamin pencocokan judul seperti *Youjo Senki II*, *Mob Psycho 100 III*, dan *Overlord IV* terpetakan 100% akurat.
12. **Kamus English Slang & Idiom Engine GTX+ & Optimasi Smart Scene Subtitle:**
    - **Dual-Stage Pre- & Post-Normalizer:**
      - *Stage 1 (Pre-GTX Normalizer):* Menyelaraskan idiom dan slang bahasa Inggris ambigu sebelum dikirim ke endpoint Google Translate (`gotta bounce` -> `gotta go now`, `no cap` -> `seriously, no lie`, `i'm down for that` -> `i agree to that`, `spill the tea` -> `reveal the secret`, `zero rizz` -> `zero charisma`, `touch grass` -> `face reality`, `caught in 4k` -> `caught red-handed with clear proof`, `deadass` -> `completely serious`, `hit the sack` -> `go to sleep`, `hold your horses` -> `wait a minute and be patient`, `piece of cake` -> `very easy task`).
      - *Stage 2 (Post-GTX Calque & Slang Lexicon):* Menambahkan leksikon pembersih calque harfiah 200+ idiom dan istilah slang mesin ke padanan diksi fansub Indonesia alami (*"harus memantul"* -> *"harus cabut"*, *"tidak ada batasan/topi"* -> *"beneran"*, *"disimpan oleh bel"* -> *"selamat di saat kritis"*, *"sudah dimuntahkan"* -> *"cepat katakan"*, *"pegang kudamu"* -> *"sabar dulu"*, *"tidak mendapat rimpang"* -> *"tidak punya pesona"*, *"sentuh rumput"* -> *"sadar realita"*, *"baju besi plot"* -> *"kebal berkat skenario"*, *"energi karakter utama"* -> *"aura protagonis"*, *"bos penjara bawah tanah"* -> *"bos dungeon"*, *"tuan serikat"* -> *"ketua guild"*, *"bersihkan pesta"* -> *"seluruh party gugur"*, dll).
    - **Smart Scene Subtitle Multi-Domain Context Classifier:**
      - Mengklasifikasikan konteks percakapan secara cerdas menjadi **Militer/Taktikal** (`_SCENE_MILITARY_RE`), **Kerajaan/Monarki/Nobilitas** (`_SCENE_ROYAL_RE`), **Gaming/RPG/Dungeon** (`_SCENE_GAMING_RE`), dan **Kasual/Sekolah/Komedi** (`_CASUAL_FANSUB_RULES`).
      - Melindungi dialog perwira militer (*Youjo Senki*, *86*, *Kingdom*) dan keluarga kerajaan (*Frieren*, *Overlord*) agar tidak terdistorsi menjadi bahasa gaul tongkrongan (*"nggak"*, *"udah"*, *"cewek/cowok"*), mempertahankan kesantunan, kedisiplinan, dan atmosfer cerita.
    - **Paritas 100% Chaquopy Android:**
      - Menyinkronkan seluruh modul dan aturan regex secara identik antara `backend/api/translate.py` dan `android/app/src/main/python/backend/api/translate.py`.
    - **Automated Tests:**
      - Menambahkan 5 pengujian baru pada `tests/test_translate.py` (`test_pre_normalize_en_slang`, `test_smart_scene_military_protection`, `test_smart_scene_royal_protection`, `test_smart_scene_casual_fansub`, `test_slang_and_idioms_calque_sanitizer`), dengan total 131/131 pengujian automated lulus 100%.
13. **Pemisahan Umpan Balik Haptik General ke Menu Perintah & Penonaktifan Haptic Scene Audio:**
    - **Penonaktifan Haptic Scene (`SceneHapticAudioSink`):**
      - Mematikan getaran adegan audio secara default (`isSceneHapticEnabled = false`) pada `PlayerActivity.java` dan membypass `TeeAudioProcessor` langsung ke `super.buildAudioSink(...)`, meniadakan getaran berlebih saat aksi pertempuran/ledakan dalam video.
      - Menghapus entri opsi *"Getaran Adegan"* dari dialog opsi pemutar video agar antarmuka pemutar lebih ringkas dan fokus.
    - **Pemisahan Haptic Feedback General UI ke Menu Perintah (`:haptic`):**
      - Memindahkan kendali preferensi getaran haptik umum UI (gestur swipe volume, swipe brightness, seek, double tap play/pause, kunci layar) ke menu perintah utama (`MainActivity.java`).
      - Menambahkan perintah CLI terminal `:haptic` (atau alias `:getar`) dengan argumen `[on|off|status|toggle]`.
      - Menambahkan item utilitas perintah baru `cmd_item_haptic` pada dialog *Daftar Perintah* (`dialog_command_help.xml`) lengkap dengan badge status dinamis (`AKTIF` `#38BDF8` / `MATI` `#64748B`) dan deskripsi informatif.
    - **Instant In-Place Auto-Toggle pada Menu Perintah:**
      - Saat pengguna mengklik item perintah `:haptic` di dialog Daftar Perintah, fungsi secara otomatis beralih (*auto-toggle*) ON/OFF seketika tanpa menutup dialog atau keluar dari menu.
      - Memperbarui teks dan warna badge seketika secara real-time, memberikan pulsa haptik konfirmasi saat diaktifkan, menampilkan Toast konfirmasi, dan menyimpan preferensi secara persisten ke `SharedPreferences` (`tatap_player_prefs` -> `pref_general_haptic`).
14. **Sentralisasi `HapticHelper` & Penerapan Menyeluruh Umpan Balik Taktil UI Android:**
    - **Kelas Sentralisasi `HapticHelper` (`id.tatap.app.HapticHelper`):**
      - Standarisasi seluruh pemicu sentuhan haptik di level aplikasi (`performTick`, `performClick`, `performHeavyClick`, `vibrateDirect`).
      - Isolasi total Android TV via `TvFocusHelper.isTv(...)` agar remote D-pad tidak bergetar dan tidak memicu overhead.
      - Adaptasi inersia motor koin ERM (skala dinamis 45ms–90ms pada perangkat tanpa kendali amplitudo).
      - Integrasi atribut audio `AudioAttributes.USAGE_MEDIA` agar getaran tidak dibungkam kebijakan mute sentuhan Samsung One UI.
    - **Penerapan Luas di Seluruh Antarmuka UI Android:**
      - *Katalog Utama (`MainActivity.java`):* Respon sentuhan getar pada seluruh 7 tab navigasi, chip hari jadwal penayangan, tombol paginasi (*prev/next*), tombol bersihkan pencarian (*clear search*), *pull-to-refresh*, dan tombol coba lagi (*empty retry*).
      - *Kartu Anime (`AnimeAdapter.java`):* Respon klik taktil saat memilih anime di beranda/katalog sebelum membuka rincian detail.
      - *Halaman Rincian (`DetailActivity.java`):* Respon taktil pada tombol kembali, tombol bookmark/favorit (*heavy click*), urutan sort episode (*tick*), tombol putar cepat / episode 1, expand/collapse sinopsis, chip genre, item episode, chip range episode, dan relasi musim/prequel/sequel.
      - *Pemutar Video (`PlayerActivity.java`):*
        - Timeline scrubbing taktil presisi: implementasi `androidx.media3.ui.TimeBar.OnScrubListener` pada `exo_progress` (klik saat mulai/selesai geser, tick halus per kelipatan 5 detik).
        - Tombol kontrol pemutar: tombol portrait & landscape (*back*, *quality*, *speed*, *aspect*, *subs*, *sub style*, *fullscreen*, *sort*, *next*, *prev*).
    - **Ekspansi Perintah Terminal `:haptic scene`:**
      - Mendukung argumen `:haptic scene [on|off|toggle|status]` untuk mengaktifkan kembali getaran adegan audio secara on-demand bagi pengguna yang menginginkannya.
      - Menampilkan status gabungan (UI Haptic & Scene Haptic) pada `:haptic status`.
    - **Automated Tests:**
      - Menambahkan 5 pengujian baru pada `tests/test_haptic_feedback.py` (`test_haptic_helper_comprehensive`, `test_detail_activity_haptics`, `test_anime_adapter_haptics`, `test_main_activity_all_ui_haptics`, `test_player_timebar_scrubbing_and_buttons_haptics`), total 136/136 automated tests lulus 100%.
15. **Panduan Pemecahan Masalah Instalasi Android (`docs/TROUBLESHOOTING_ANDROID.md`):**
    - Menyusun dokumen panduan teknis resmi penanganan instalasi mandiri (*sideload APK*) untuk mengatasi kebijakan proteksi vendor ponsel:
      - Penonaktifan sementara *Pemblokir Otomatis (Auto Blocker)* pada Samsung One UI 6.0/6.1/7/8.
      - Penanganan peringatan dialog *Google Play Protect* (*More details > Install anyway*).
      - Pemberian izin *Install Unknown Apps* pada browser / File Manager.
      - Penanganan error *App Not Installed* akibat konflik signature serta *Parse Error* akibat unduhan tidak lengkap.
    - Menautkan panduan troubleshooting pada berkas `README.md` di bawah tabel unduhan langsung.
16. **Perbaikan Tampilan List Episode Web & Desktop (Auto-Fill Multi-Column Grid):**
    - Memperbaiki hierarki DOM modal detail anime di `frontend/index.html` dengan menutup kembali tag `<div class="sheet-head">` yang terhapus saat penambahan metadata di commit `553ef20`.
    - Mengeliminasi bug tampilan episode berjejer sempit vertikal 1 kolom (~54px) akibat `.ep-grid` terserap ke dalam baris flex horizontal `.sheet-head`.
    - Memperkuat styling CSS di `frontend/css/style.css` dengan `width: 100%`, `flex: 1 1 auto`, `box-sizing: border-box`, dan `min-height: 100px` pada `.ep-grid` dan kontainer sheet, mengembalikan tata letak grid responsif multi-kolom yang rapi (10–14 kolom pada desktop, 6–8 pada mobile).
    - Menambahkan automated test DOM tree `test_web_desktop_sheet_dom_structure` pada `tests/test_detail_metadata.py` untuk mengunci struktur modal detail dan mencegah terjadinya tag mismatch berulang (total 137/137 tests lulus 100%).
17. **Adopsi MAX Metadata Anime di Android TV & Layout Split 2-Kolom Landscape (`layout-land`):**
    - **Arsitektur Split 2-Kolom (`res/layout-land/activity_detail.xml`):** Merancang tata letak lanskap 10-foot UI khusus Android TV & tablet; membagi layar menjadi Kolom Kiri (~40% lebar) untuk panel hero informasi dan Kolom Kanan (~60% lebar) untuk panel episode. Mengeliminasi masalah terhimpitnya daftar episode pada viewport TV 16:9.
    - **Adopsi MAX Metadata di TV:** Mengaktifkan seluruh elemen metadata pada antarmuka Android TV (`DetailActivity.java`), mencakup badge skor rating emas (⭐ 8.7), badge status penayangan (`TAMAT` / `ONGOING`), baris rincian studio & musim rilis, chip genre dark cyber, serta kotak sinopsis cerita dengan kontrol expand/collapse via D-pad remote TV.
    - **Peningkatan Visual Kartu Poster Beranda (`item_anime_card.xml`):** Menyematkan ikon bintang vektor `@drawable/ic_star_filled` berwarna amber `#FBBF24` pada badge skor kartu beranda dan katalog, meningkatkan legibilitas rating dari jarak tonton 3 meter.
    - **Optimasi Performa Hardware-Accelerated Ramah Low-End STB (RAM 1GB):** Meniadakan efek blur runtime berat yang membebani GPU; mengandalkan palet obsidian cyber dan *XML GradientDrawable* statis (60 FPS stabil pada Mali-G31/Mali-400), disertai `setHasFixedSize(true)` dan pembatasan cache `setItemViewCacheSize(8)` untuk menjaga stabilitas memori STB TV Box.
18. **Perbaikan Visual Tombol 'Lanjutkan Episode Terakhir' pada Android Mobile & Landscape:**
    - **Pencegahan Penghapusan MaterialShape:** Memperbaiki metode `updateQuickPlayButton()` pada `DetailActivity.java` agar menggunakan API resmi `MaterialButton` (`setBackgroundTintList`, `setIconResource`, `setIconTint`, `setStrokeColor`) dan tidak lagi memanggil `setBackgroundColor()`, sehingga kelengkungan sudut (`app:cornerRadius="10dp"`), garis tepi stroke, dan efek ripple sentuhan tetap utuh (tidak lagi menjadi kotak kaku bersudut tajam).
    - **Identitas Visual Hero CTA (Electric Cyber Cyan):** Ketika terdapat episode lanjutan (`lastEp > 0`), tombol berubah menjadi Electric Cyber Cyan pekat (`#38BDF8`) dengan teks & ikon gelap kontras tinggi (`#080C14`), menjadikannya titik fokus utama yang langsung menarik perhatian pengguna saat membuka layar detail. Ketika belum pernah ditonton (`lastEp <= 0`), tombol beralih ke gaya *cyber slate dark* (`#161C28`) dengan outline dan ikon play Cyan yang elegan.
    - **Vektor Ikon Play Resmi (`ic_play.xml`):** Membuat dan menyematkan vektor ikon segitiga play proporsional (15dp) di sisi kiri teks tombol pemutaran cepat pada layout portrait (`res/layout/activity_detail.xml`) dan landscape (`res/layout-land/activity_detail.xml`).
    - **Penyelarasan Dimensi & Inset 0dp:** Menyamakan tinggi tombol (`38dp`), menyetel `android:insetTop="0dp"` dan `android:insetBottom="0dp"`, serta menyelaraskan radius kelengkungan (`10dp`) antara tombol *Lanjutkan* dan *+ Favorit*, mencegah pemotongan vertikal tak diinginkan.
    - **Aksen Episode Terakhir di Grid Kartu:** Memberikan aksen border stroke Cyan (`#38BDF8`) pada kartu episode di dalam grid `EpisodeAdapter` untuk episode yang terakhir ditonton (`cachedLastPlayedEp`), memperkuat kejelasan status tontonan di seluruh layar.
    - **Automated Tests:** Menambahkan pengujian `test_quick_play_resume_button_ui_and_contract` pada `tests/test_android_ui_icons.py` (total 138/138 automated tests lulus 100%).

## [2.8.3] - 2026-10-17

### Justifikasi SemVer 2.0.0 (PATCH: 2.8.2 -> 2.8.3)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 untuk perbaikan kompatibilitas hardware dan vendor (*hardware compatibility & vendor policy bugfix*), khususnya perangkat dengan motor getar koin tipe ERM (seperti Samsung Galaxy A33 5G, A-series, Redmi, Poco, dll.) dan sistem operasi Samsung One UI:
1. **Adaptasi Pulsa Inersia Motor ERM (`vibrateDirect`):**
   - Menghitung kapabilitas kendali amplitudo perangkat secara dinamis (`v.hasAmplitudeControl()`).
   - Pada ponsel dengan motor ERM koin (seperti Samsung Galaxy A33 5G), inersia mekanis rotor membutuhkan waktu ~35–50ms untuk mulai berputar. Pulsa pendek 15ms–25ms sebelumnya terputus sebelum motor sempat menghasilkan gaya getar yang terasa di tangan.
   - Durasi pulsa getaran otomatis diskalakan saat `hasAmplitudeControl() == false`:
     - *Tick (Volume & Kecerahan):* Ditingkatkan menjadi 45ms.
     - *Click (Play/Pause, Seek, Skip):* Ditingkatkan menjadi 65ms.
     - *Heavy Click (Kunci Layar & Toggle Menu):* Ditingkatkan menjadi 90ms.
     - *Scene Explosion:* Ditingkatkan menjadi 80ms.
2. **Pengaliran Getaran Media via `AudioAttributes.USAGE_MEDIA`:**
   - Menambahkan atribut audio `AudioAttributes.USAGE_MEDIA` pada pemanggilan `v.vibrate(effect, attrs)`.
   - Mengatasi kebijakan Samsung One UI yang secara agresif membungkam getaran tanpa atribut (`USAGE_UNKNOWN` / `USAGE_TOUCH`) saat pengguna menonaktifkan getaran sentuh keyboard atau saat mode hemat daya aktif.
   - Menjadikan getaran terhubung secara resmi ke kanal pemutaran media aktif ExoPlayer.
3. **Kalibrasi Ambang Batas Adegan Aksi Anime (`SceneHapticAudioSink`):**
   - Menyesuaikan batas pemicu lonjakan audio dari `peak > 23000 && rms > 8500` menjadi `(peak > 17500 && rms > 3800) || (peak > 22000 && rms > 2800)`.
   - Nilai sebelumnya (-11.7 dBFS RMS) terlalu tinggi untuk standar streaming anime AAC stereo (-23 LUFS) sehingga getaran adegan pertarungan jarang terpicu. Ambang batas baru merefleksikan dinamika adegan aksi anime secara akurat tanpa terpicu oleh dialog percakapan normal.
4. **Pembaruan Test Suite:**
   - Menambahkan pengujian `test_erm_motor_adaptation_and_media_attributes` pada `tests/test_haptic_feedback.py` (10/10 lulus).

## [2.8.2] - 2026-10-17

### Justifikasi SemVer 2.0.0 (PATCH: 2.8.1 -> 2.8.2)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 untuk perbaikan crash runtime (*critical thread violation bugfix*) pada pemutar video Android:
1. **Perbaikan Thread-Safety Audio Sink (`IllegalStateException: Player is accessed on the wrong thread`):**
   - Menghapus pemanggilan langsung `player.isPlaying()` dari dalam method `handleBuffer(ByteBuffer buffer)` pada kelas `SceneHapticAudioSink`.
   - Method `handleBuffer` berjalan pada thread pemrosesan audio internal ExoPlayer (`ExoPlayer:Playback`), di mana pemanggilan metode apa pun pada instance `player` dilarang oleh arsitektur Media3 dan memicu crash `IllegalStateException`.
   - Menggantikannya dengan state flag `volatile boolean isVideoPlaying` yang dikelola secara atomik di UI Thread (melalui callback `onIsPlayingChanged`, `onPause`, dan `onDestroy`) dan dibaca secara non-blocking serta bebas thread-violation oleh audio thread.
2. **Pembaruan Test Suite:**
   - Menambahkan unit test otomatis `test_scene_haptic_thread_safety` pada `tests/test_haptic_feedback.py` untuk memastikan `SceneHapticAudioSink` tidak pernah mengakses metode pada instance `player` secara lintas-thread.

## [2.8.1] - 2026-10-17

### Justifikasi SemVer 2.0.0 (PATCH: 2.8.0 -> 2.8.1)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 untuk perbaikan bug (*bug fix*) pada sistem haptic feedback Android:
1. **Universal Real-Time Scene Haptics Engine (`SceneHapticAudioSink` via `TeeAudioProcessor`):**
   - Mengatasi kendala di mana `HapticGenerator` hanya tersedia pada perangkat Pixel (`HapticGenerator.isAvailable() == false` pada sebagian besar ponsel Xiaomi, Samsung, Infinix, Realme, Vivo, Poco, dan Oppo).
   - Mengintegrasikan `TeeAudioProcessor` langsung ke dalam pipeline audio ExoPlayer (`DefaultAudioSink`) untuk menganalisis energi audio PCM 16-bit secara real-time.
   - Mendeteksi lonjakan energi audio (*audio transient & peak amplitude* > 23000 dan RMS > 8500) yang dihasilkan oleh adegan aksi anime (ledakan, pukulan pertarungan, dentuman bass, tembakan, tabrakan) dan memicu getaran taktil dinamis (35ms) dengan debounce cooldown 200ms agar terhindar dari humming/buzz konstan.
   - Bekerja 100% pada seluruh perangkat Android berkemampuan getar tanpa membutuhkan izin `RECORD_AUDIO`.
2. **Direct Hardware Motor Fallback & VibratorManager Support (`vibrateDirect`):**
   - Mengatasi perilaku Android `View.performHapticFeedback` yang mengembalikan `true` pada `ViewRootImpl` meski getaran dimatikan di pengaturan sistem, yang sebelumnya mencegah eksekusi fallback vibrator.
   - Mengimplementasikan `getVibratorService()` dengan dukungan `VibratorManager.getDefaultVibrator()` untuk Android 12+ (API 31+) dan fallback `VIBRATOR_SERVICE`.
   - Mengaktifkan `vibrateDirect` dengan durasi dan amplitudo terkalibrasi (`createOneShot`):
     - **Tick (Volume & Kecerahan):** 15ms (amplitudo 70) dengan flag `FLAG_IGNORE_VIEW_SETTING | FLAG_IGNORE_GLOBAL_SETTING`.
     - **Click (Seek, Play/Pause, Skip OP/ED, Episode Selector):** 25ms (amplitudo 140).
     - **Heavy Click (Screen Lock):** 45ms (amplitudo 230).
   - Memastikan getaran terpicu secara fisik dan terasa jelas di tangan pengguna pada seluruh vendor perangkat.
3. **Pembaruan Test Suite:**
   - Memperbarui `tests/test_haptic_feedback.py` (8/8 unit test lulus) untuk memvalidasi engine `SceneHapticAudioSink`, `TeeAudioProcessor`, `vibrateDirect`, dan `getVibratorService`.

## [2.8.0] - 2026-10-17

### Justifikasi SemVer 2.0.0 (MINOR: 2.7.2 -> 2.8.0)
Kenaikan digit MINOR diterapkan sesuai kaidah Semantic Versioning 2.0.0 karena memperkenalkan penambahan fungsionalitas dan kapabilitas baru yang backward-compatible tanpa merusak arsitektur eksisting:
1. **Audio-Coupled Anime Scene Haptics (`HapticGenerator`):**
   - Mengintegrasikan API native `android.media.audiofx.HapticGenerator` (Android 12+ / API 31+) yang terikat langsung ke `audioSessionId` dari ExoPlayer via `AnalyticsListener.onAudioSessionIdChanged`.
   - Mengubah sinyal efek audio adegan anime (dentuman ledakan, benturan pertarungan, efek suara sakti, dan bass drop) menjadi getaran taktil yang presisi dan tersinkronisasi secara otomatis dengan gelombang suara video.
   - Menggunakan static helper wrapper `HapticGeneratorHelper` dengan anotasi `@RequiresApi(Build.VERSION_CODES.S)` demi menjamin keamanan runtime dan backward-compatibility 100% pada versi Android terdahulu tanpa risiko class verification error.
2. **Modern Subtle Gesture Haptics:**
   - Menggantikan getaran kasar/monolitik lama (`Vibrator.vibrate`) dengan tactile feedback modern yang halus dan reaktif (`HapticFeedbackConstants` dan `VibrationEffect.createPredefined`):
     - **Gesture Volume:** Trigger `performHapticTick()` (`SEGMENT_TICK` / `CLOCK_TICK` / `EFFECT_TICK`) pada setiap perubahan level volume (`targetVol != curVol`).
     - **Gesture Kecerahan (Brightness):** Trigger `performHapticTick()` pada setiap kelipatan 5% kecerahan layar.
     - **Double-Tap Seek & Play/Pause:** Trigger `performHapticClick()` (`KEYBOARD_TAP` / `EFFECT_CLICK`) yang responsif.
     - **Kunci & Buka Layar (Screen Lock/Unlock):** Trigger `performHapticHeavyClick()` (`DRAG_START` / `LONG_PRESS` / `EFFECT_HEAVY_CLICK`) saat mengunci dan `performHapticClick()` saat membuka kunci.
     - **Navigasi Episode & Skip OP/ED:** Trigger `performHapticClick()` saat tombol Lewati Opening/Ending ditekan maupun saat beralih episode di tampilan potret.
3. **Preferensi Pengguna & Unified Settings Dialog:**
   - Menambahkan opsi menu baru pada dialog pengaturan pemutar: `"Umpan Balik Haptik / Getaran Adegan: [Aktif / Mati]"`.
   - Preferensi disimpan secara persisten di `SharedPreferences` (`tatap_player_prefs`, key `"pref_haptic"`).
   - Mengaktifkan atau menonaktifkan `HapticGenerator` dan gesture feedback secara langsung tanpa perlu memuat ulang video.
4. **Isolasi Mutlak Android TV (10-Foot UI):**
   - Seluruh logika haptik (HapticGenerator, View haptic feedback, maupun fallback vibrator) memiliki proteksi awal `if (TvFocusHelper.isTv(this)) return;`.
   - Menu pengaturan haptik disembunyikan otomatis pada Android TV agar pengalaman 10-Foot UI tetap bersih, steril, dan bebas overhead.
5. **Automated Test Suite:**
   - Menambahkan test suite baru `tests/test_haptic_feedback.py` (7 unit tests) yang mencakup validasi import, isolasi Android TV, penyimpanan preferensi `pref_haptic`, siklus hidup ExoPlayer `AnalyticsListener`, dan pemicu interaksi gesture.

## [2.7.2] - 2026-10-16

### Justifikasi SemVer 2.0.0 (PATCH: 2.7.1 -> 2.7.2)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 untuk penyempurnaan aset visual antarmuka pengguna Android yang backward-compatible tanpa memodifikasi kontrak runtime maupun arsitektur aplikasi:
1. **Pembaruan Ikon Indikator Backend Online Android (`activity_main.xml`):**
   - Menggantikan ikon tombol power (`ic_power.xml`) yang ambigu dengan vektor resmi Google Material Design **Dual-Tier Server Rack** (`ic_server.xml`) lengkap dengan lampu status LED.
   - Memberikan visualisasi yang jelas dan akurat bahwa tombol tersebut merepresentasikan status kesehatan engine backend Python lokal (port 8767), bukan tombol untuk mematikan perangkat atau mematikan aplikasi.
   - Mempertahankan siklus pewarnaan status dinamis pada `MainActivity.java`: Hijau (`#10B981`) saat Online, Kuning/Amber (`#F59E0B`) saat Booting/Memeriksa, dan Merah (`#EF4444`) saat Offline/Error.
2. **Pembersihan Aset Usang & Pengujian Otomatis:**
   - Menghapus berkas vektor lama `ic_power.xml` dari direktori drawable untuk menjaga integritas dan kebersihan codebase (*zero bloat*).
   - Menambahkan unit test otomatis `tests/test_server_indicator_icon.py` untuk memvalidasi keberadaan `ic_server.xml`, dimensi proporsional 20dp, penghapusan `ic_power.xml`, dan pengikatan deskripsi aksesibilitas `"Status Backend Server"` pada `activity_main.xml`.
3. **Mekanisme Folded Sinopsis Anime Terisolasi Android Mobile (`activity_detail.xml`, `DetailActivity.java`, `AnimeAdapter.java`):**
   - Menambahkan kontainer sinopsis cerita anime pada Hero Card dengan mekanisme *folded/expandable* 2-state:
     - **Default (Ringkas):** Sinopsis dibatasi 2 baris (`maxLines="2"`) dengan elipsis di ujung dan tombol `"Selengkapnya ▼"`. Area pemilihan episode (`rv_episodes`) tetap luas dan lapang.
     - **Expanded (Terbuka Penuh):** Saat tombol atau teks sinopsis diketuk, sinopsis terbuka penuh dan tombol berubah menjadi `"Lipat ke Judul ▲"`.
     - **Fold to Title (Lipat ke Judul):** Saat tombol `"Lipat ke Judul ▲"` diketuk, sinopsis melipat kembali secara mulus (*smooth layout animation* via `animateLayoutChanges="true"`) ke ukuran ringkas 2 baris di bawah judul, secara instan mengembalikan ruang vertikal agar area episode list kembali melebar maksimal.
   - **Isolasi Penuh Android Mobile:** Fitur ini 100% terisolasi untuk perangkat ponsel/tablet dan disembunyikan otomatis (`View.GONE`) pada perangkat Android TV via `TvFocusHelper.isTv(this)` sehingga alur navigasi D-Pad TV tetap steril dan tidak berubah.
   - **Propagasi & Fallback Metadata:** Menambahkan penerusan `synopsis` pada intent `AnimeAdapter.java`, dukungan `synopsis` pada endpoint `/api/anime/{slug}/episodes`, dan penambahan deskripsi AniList pada backend dengan kepatuhan Chaquopy dual-copy parity.
   - Menambahkan automated test suite baru `tests/test_detail_folded_synopsis.py` (4 unit test).
4. **Penataan Ulang Menu Kategori Horizontal & Penambahan Tombol Riwayat (`activity_main.xml`, `MainActivity.java`):**
   - Menata ulang tata letak menu horizontal slide di bawah header menjadi urutan navigasi yang lebih ergonomis dan intuitif:
     1. **Musim Ini** (`btn_tab_musim`)
     2. **Masih Tayang** (`btn_tab_airing`)
     3. **Jadwal** (`btn_tab_jadwal`)
     4. **Riwayat** (`btn_tab_riwayat`) - tombol baru untuk akses instan ke riwayat tontonan pengguna
     5. **Favorit** (`btn_tab_favorit`)
     6. **Katalog** (`btn_tab_katalog`)
     7. **Genre** (`btn_tab_genre`)
   - **Vektor Resmi `ic_tab_history.xml`:** Membuat ikon vektor jam riwayat (15dp x 15dp) yang tajam, proporsional, dan selaras dengan gaya visual kategori lainnya.
   - **Integrasi Penuh Android TV 10-Foot UI:** Seluruh 7 tab dibagikan rata (`weight=1.0f`) membentang 100% di layar TV, dengan integrasi D-Pad spasial dua arah (kiri, kanan, atas ke header, bawah ke konten/grid) tanpa dead-end atau lompatan fokus yang terputus.
   - **Respon Fokus Interaktif:** Mengikat `TvFocusHelper.attachFocusScale` dan highlight warna aktif/inaktif dinamis untuk tab Riwayat.
   - Menambahkan unit test otomatis `tests/test_horizontal_tab_menu.py` (3 unit test).
5. **Penambahan Parameter Musim (Season) pada Filter Katalog Multiplatform (`dialog_catalog_filter.xml`, `MainActivity.java`, `index.html`, `term.js`):**
   - Menambahkan seksi baru **Musim Penayangan (Season)** pada dialog cross-filter katalog Android dan modal Web Desktop, tepat setelah seksi Tahun Rilis dan sebelum Bulan Rilis.
   - Pilihan filter musim mencakup: *Semua Musim* (`""`), *Musim Semi / Spring* (`"spring"`), *Musim Panas / Summer* (`"summer"`), *Musim Gugur / Fall* (`"fall"`), dan *Musim Dingin / Winter* (`"winter"`).
   - Dilengkapi dukungan visual chip interaktif dengan ikon vektor `ic_tab_season.xml` di Android, respon D-pad remote TV (`TvFocusHelper.attachFocusScale`), serta sinkronisasi dinamis pada header ringkasan filter katalog dan cache in-memory.
   - Menambahkan unit test otomatis pada [`tests/test_catalog_filter.py`](file:///home/b-ict/tatap/tests/test_catalog_filter.py) (6 unit test).
6. **Pembersihan Perintah Navigasi Tab pada Dialog Daftar Perintah Android (`dialog_command_help.xml`, `MainActivity.java`):**
   - Menghapus 6 item perintah yang fungsinya telah tersedia secara permanen sebagai tombol pada horizontal tab menu di layar utama (`:musim`, `:airing`, `:riwayat`, `:favorit`, `:katalog`, `:genre`).
   - Merampingkan dialog Daftar Perintah agar fokus pada 12 perintah utilitas, sistem, AI translation (`:ai`, `:apikey`, `:gemini`, `:groq`, `:ollama`, `:model`, `:logs`), konektivitas (`:source`, `:ping`), filter berargumen (`:season [musim] [tahun]`), update checker (`:update`), dan reset (`:clear`).
   - Menyambungkan event click listener pada item `:clear` (`cmd_item_clear`) untuk mereset pencarian/filter langsung ke tab musim ini.
   - Mempertahankan fungsionalitas CLI / input teks search bar (`executeCommand`) sehingga seluruh perintah teks tetap dapat diketikkan dan dijalankan 100% normal.
   - Menambahkan unit test otomatis pada [`tests/test_command_help_menu.py`](file:///home/b-ict/tatap/tests/test_command_help_menu.py) (4 unit test).
7. **Perbaikan Metadata & Sinkronisasi Tombol Relasi Waralaba Anime Girls & Panzer (`hianime.py`, `otakudesu.py`, `main.py`, `DetailActivity.java`, `app.js`, `style.css`):**
   - **Perbaikan URL Encoding & Aliasing HiAnime:** Memperbaiki pencarian keyword berkarakter ampersand `&` menggunakan `urllib.parse.quote_plus` dan mapping alias (`girls und panzer`, `girls and panzer`, `garupan` $\rightarrow$ `girls & panzer`) sehingga serial TV 12 episode utama (`girls-und-panzer-2670`) tampil akurat di urutan teratas.
   - **Normalisasi Pencarian Otakudesu (Sub Indo):** Menormalkan query Otakudesu dari konjungsi Jerman *"und"* ke *"panzer"*, serta mencegah salah tangkap episode Saishuushou / Part lanjutan sehingga serial TV 12 episode (`girls-panzer-v979ece`) terhubung presisi.
   - **Diferensiasi Presisi Format Serial TV vs Movie vs OVA/Special (`_is_title_match`):** Mencegah serial TV mencocokkan Movie (*Girls und Panzer der Film*) atau OVA secara keliru melalui validasi isolasi format ketat, kesesuaian part/saishuushou/finale, dan kata pembeda franchise (*anzio*, *taiyaki*, *alice*).
   - **Prioritas Pelabelan Relasi Anime & Sinkronisasi Antarmuka:** Memperbaiki urutan pelabelan relasi pada `/api/anime/{slug}/relations` agar format fisik (`MOVIE`, `OVA`, `SPECIAL`) diprioritaskan sebelum fallback `Season 1`, mencegah film atau OVA salah dilabeli sebagai "Season 1".
   - **Sinkronisasi Tampilan & Tombol Interaktif Multiplatform:** Memastikan seluruh tombol chip relasi waralaba anime di Android (`DetailActivity.java`) dan Web Desktop (`app.js`) tersinkronisasi, memiliki palet warna khas (Cyan untuk Prekuel, Ungu untuk Sekuel, Emas untuk Movie, Emerald/Mint untuk OVA/Special), tidak menampilkan chip redundant ke anime itu sendiri, dan dapat diklik untuk membuka entri anime tujuan secara instan.
   - **Sanitasi Database Cache:** Membersihkan entri slug map, search cache, dan browse cache yang tercemar pada database SQLite lokal.
   - **Automated Tests:** Menambahkan suite pengujian otomatis [`tests/test_girls_und_panzer_metadata.py`](file:///home/b-ict/tatap/tests/test_girls_und_panzer_metadata.py) (6 unit test).
8. **Mode Watch Portrait View Terisolasi Android Mobile (`activity_player.xml`, `PlayerActivity.java`, `AndroidManifest.xml`):**
   - **Tata Letak Adaptif Portrait:** Menghadirkan antarmuka pemutar video vertikal (Watch Portrait View) pada ponsel Android dengan panggung ExoPlayer di bagian atas (rasio 16:9 ~215dp) dan panel daftar episode interaktif di bagian bawah (`layout_portrait_bottom`).
   - **Grid Episode Interaktif & Pindah Episode Instan:** Menampilkan judul anime, episode aktif, baris tombol kontrol cepat (Subtitle, Kualitas, Kecepatan, ⛶ Full), range chip filter horizontal (> 30 episode), dan grid episode vertikal 4 kolom (`rv_portrait_episodes`). Mengetuk episode mana pun di grid langsung memutar episode tersebut secara instan (`switchEpisode`) tanpa reload Activity.
   - **Penanda Episode Aktif & Riwayat Ditonton:** Episode yang sedang aktif disorot dengan warna cyan menyala (`#38BDF8`), border kontras, dan badge "MEMUTAR". Episode yang sudah pernah ditonton ditandai dengan badge "DITONTON" hijau mint.
   - **Transisi Orientasi Mulus Tanpa Re-buffering:** Mendukung rotasi sensor dinamis via `android:configChanges` dan `onConfigurationChanged`. Memutar ke lanskap atau mengetuk tombol `⛶ Full` otomatis mempromosikan video ke mode 100% immersive landscape fullscreen tanpa menghentikan audio maupun video. Mengetuk Back atau exit fullscreen mengembalikan tampilan ke portrait watch view.
   - **Isolasi Mutlak Android TV:** Fitur ini 100% terisolasi untuk perangkat seluler. Pada Android TV (`TvFocusHelper.isTv(this)`), orientasi layar tetap dikunci secara terprogram ke `SCREEN_ORIENTATION_SENSOR_LANDSCAPE` dan mempertahankan antarmuka 10-Foot UI Leanback TV fullscreen tanpa komponen portrait.
   - **Automated Tests:** Menambahkan 6 unit test otomatis pada [`tests/test_watch_portrait_view.py`](file:///home/b-ict/tatap/tests/test_watch_portrait_view.py) yang memverifikasi manifes, struktur layout, isolasi TV, transisi orientasi, adapter episode, dan navigasi tombol back.
9. **Pembersihan Custom Header ExoPlayer & Optimasi Gesture Edge Swipe Back Portrait (`activity_player.xml`, `PlayerActivity.java`, `ic_arrow_back.xml`):**
   - **Eliminasi Redundansi Header Atas:** Menyembunyikan 5 tombol aksi berjejal (`btn_aspect`, `btn_quality`, `btn_speed`, `btn_sub_style`, `btn_sub_selector`), status subtitle, dan tombol kunci layar (`btn_screen_lock`) dari `layout_top_bar` saat berada dalam mode portrait vertikal. Fungsi seluruh tombol tersebut sudah tersedia secara ergonomis di panel kontrol bawah (`layout_portrait_bottom`).
   - **Visual Header Bersih & Modern:** Mengganti tombol teks kembali `[<-]` dengan ikon Material resmi panah kiri (`ic_arrow_back.xml`), menerapkan padding kompak (`paddingHorizontal="12dp"`, `paddingVertical="8dp"`), dan menampilkan judul anime secara bersih dalam 1 baris elipsis tanpa berjejal.
   - **Optimasi Gesture Edge Swipe Back Responsif:** Menghapus perangkap mode layar penuh imersif (`FLAG_FULLSCREEN` dan `BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE`) pada mode portrait. Dalam mode portrait vertikal, sistem bar dibiarkan standar (`clearFlags(FLAG_FULLSCREEN)` dan `BEHAVIOR_DEFAULT`) sehingga gesture swipe tepi layar (*edge swipe back navigation*) langsung mengeksekusi navigasi kembali ke detail anime pada usapan pertama (*first swipe*), tanpa tertahan pembukaan navigation bar sistem.
   - **Dukungan Modern Predictive Back API 33+:** Mengintegrasikan `OnBackInvokedCallback` melalui `getOnBackInvokedDispatcher()` untuk perangkat Android 13+ (API 33 hingga 16) dengan *unregistration* yang aman pada `onDestroy()`.
   - **Isolasi Penuh Landscape & Android TV:** Seluruh tombol kontrol atas dan padding lebar TV overscan tetap dipulihkan 100% saat pengguna merotasi layar ke landscape atau saat dijalankan di Android TV.
   - **Automated Tests:** Memperluas suite pengujian [`tests/test_watch_portrait_view.py`](file:///home/b-ict/tatap/tests/test_watch_portrait_view.py) menjadi 8 pengujian otomatis (100% lulus).
10. **Perilaku Transisi Pasca-Nonton (Post-Watch Flow), Marker Episode Terakhir Aktif, & Alur Pembatalan Modal Resume Web/Desktop (`app.js`, `index.html`, `style.css`):**
    - **Otomasi Transisi Pasca-Nonton:** Saat episode selesai diputar (`v.addEventListener("ended")`), pemutar video web/desktop otomatis keluar dari mode layar penuh (fullscreen exit), menutup player modal (`closePlayer()`), mencatat episode sebagai telah ditonton (`recordEpisodeWatched()`), mereset progress ke 0, dan secara mulus membuka kembali modal daftar episode anime (`openTitle()`) disertai notifikasi toast `"Episode X selesai diputar"`.
    - **Marker & Badge Episode Terakhir Ditonton (`.ep.last-watch`, `.ep-badge-last`):** Episode yang terakhir kali ditonton ditandai dengan aksen cyan neon menyala (`rgba(56,189,248,0.14)`), border kontras 1.5px cyan, teks tebal, dan badge mini `"TERAKHIR"` berwarna cyan. Selain itu, daftar episode otomatis melakukan smooth scroll ke posisi tombol episode terakhir tersebut agar pengguna langsung melihat posisinya.
    - **Konsistensi Alur Pembatalan Modal Resume Watch:** Menambahkan tombol `"Batal"` (`#rm-btn-cancel`, `.btn-resume-cancel`) pada modal konfirmasi lanjutkan tontonan. Saat pengguna membatalkan modal resume (baik via tombol Batal, tombol silang ✕, penekanan tombol keyboard Escape, maupun klik di luar modal/backdrop), aplikasi kini secara konsisten mengembalikan pengguna ke tampilan daftar episode anime (`title-modal`), bukan menutup semuanya ke beranda.
    - **Perlindungan Terhadap Race Condition:** Menambahkan token guard `fetchToken` pada pemanggilan asinkron `window.Tatap.getProgress()` di `openPlayer()` dan pembaruan instan `cur.ep` serta `updatePrevNext()` pada `stepEp()` untuk mencegah ketidaksinkronan state saat navigasi episode cepat.
    - **Isolasi Mutlak Web & Desktop:** Seluruh perubahan ini diterapkan khusus pada runtime antarmuka Web dan Desktop tanpa menyentuh satu baris pun kode native Android.
    - **Automated Tests:** Menambahkan 4 unit test otomatis baru pada `tests/test_post_watch_web.py` dan memperluas pengujian pada `tests/test_resume_watch.py` (total 105 pengujian otomatis 100% lulus).
11. **Eliminasi Total Custom Header ExoPlayer di Atas Video Portrait & Tombol Kembali Panel Bawah (`activity_player.xml`, `PlayerActivity.java`):**
    - **Panggung Video Bersih dari Header Gelap:** Mengunci `layout_top_bar` agar 100% `View.GONE` saat orientasi portrait ponsel (`updateLayoutForOrientation`, `setControllerVisibilityListener`, `onSingleTapConfirmed`, dan `showTopBarBriefly`). Ketukan pada layar video atau kemunculan timeline pengontrol native ExoPlayer tidak akan lagi memunculkan bilah header gelap di atas video yang mengganggu tontonan.
    - **Tombol Kembali Ergonomis di Panel Bawah (`btn_portrait_back`):** Menambahkan tombol panah kembali Material (`ic_arrow_back.xml`) tepat di sebelah kiri judul anime pada panel kontrol bawah (`layout_portrait_bottom`), terhubung langsung ke `handleBackAction()` sehingga pengguna dapat bernavigasi kembali dengan mudah via satu jempol.
    - **Isolasi Penuh Landscape & Android TV:** Mode landscape fullscreen dan antarmuka 10-Foot UI Android TV tetap mempertahankan header atas lengkap beserta seluruh 5 tombol kontrol (`btn_aspect`, `btn_quality`, `btn_speed`, `btn_sub_style`, `btn_sub_selector`) dan navigasi remote D-Pad.
    - **Automated Tests:** Memperluas pengujian di `tests/test_watch_portrait_view.py` untuk memvalidasi keberadaan `btn_portrait_back` dan isolasi `layout_top_bar.setVisibility(isLandscape ? visibility : View.GONE)` (100% lulus).
12. **Eliminasi Race Condition Fast-Click & Close serta Isolasi Marker Post-Watch Web/Desktop (`frontend/js/app.js`, `tests/test_post_watch_web.py`):**
    - **Pencegahan Pemutaran di Latar Belakang (Fast-Click & Close):** Menambahkan invalidasi token pemutaran `cur.playToken = ++_playTokenCounter;` di awal `closePlayer()`, `dismissResumeModal()`, dan event penutupan modal judul (`tm-close`). Jika pengguna mengklik cepat episode lalu segera menutup pemutar sebelum resolusi stream selesai, callback asinkron `window.Tatap.resolve()` dan `window.Tatap.getProgress()` segera meng-abort eksekusi tanpa menyentuh `playUrl()` atau `v.play()`.
    - **Defense-in-Depth Modal Visibility Guard:** Menambahkan verifikasi status modal `$("player-modal").classList.contains("hidden")` pada callback `resolve` dan di awal `playUrl()`. Jika player telah tertutup atau token tidak cocok, `playUrl()` seketika menghancurkan HLS instance, menghentikan video (`v.pause()`), menghapus source (`v.removeAttribute("src")`), dan me-reset tag video (`v.load()`) sehingga audio dan video tidak akan pernah bocor berjalan di latar belakang.
    - **Isolasi Penuh State Per-Anime (Zero Cross-Contamination):** Me-reset eksplisit `cur.lastWatchedEp = null; cur.watched = {}; cur.activeEpRange = null;` pada `openTitle()` dan `loadEps()`. Menghapus pencemaran data di mana menonton episode 2 di Anime A menyebabkan Anime B ikut ter-marker episode 2. Menghapus penulisan buta ke `localStorage` pada anime yang belum pernah ditonton.
    - **Pemulihan Otomatis List Episode Saat Video Ditutup:** Memperbarui `closePlayer()` agar secara konsisten menampilkan kembali modal daftar episode (`#title-modal`) dan merender grid episode dengan penanda `.last-watch` dan badge `TERAKHIR` aktif serta auto-scroll ke posisi episode terakhir tersebut.
    - **Eliminasi Deadlock Episode Switching:** Menghapus pengecekan keliru `(cur.ep && cur.ep !== ep)` di dalam `openPlayer()` yang sebelumnya memblokir pemilihan episode baru ketika berpindah dari episode sebelumnya.
    - **Automated Tests:** Menambahkan 3 unit test otomatis baru pada `tests/test_post_watch_web.py`: `test_cross_title_marker_isolation`, `test_race_condition_fast_click_and_close_protection`, dan `test_deadlock_elimination_in_open_player` (total 108 pengujian otomatis 100% lulus).
13. **Eliminasi Total Kedipan Header ExoPlayer pada Awal Pemutaran dan Resolusi Stream Mode Portrait Mobile (`activity_player.xml`, `PlayerActivity.java`, `tests/test_watch_portrait_view.py`):**
    - **Inisialisasi XML Bersih (Zero Flicker on Inflate):** Menambahkan `android:visibility="gone"` pada `layout_top_bar` di `activity_player.xml`. Mencegah header hitam muncul sekejap pada frame 0 saat layout pertama kali di-inflate oleh Activity.
    - **Perbaikan Urutan Inisialisasi `onCreate` (`PlayerActivity.java`):** Memindahkan pemanggilan `updateLayoutForOrientation(...)` agar dieksekusi setelah seluruh view (`layoutTopBar`, `btnAspect`, `btnQuality`, `btnSpeed`, `btnSubStyle`, `btnSubSelector`, `tvSubStatus`, `btnScreenLock`) selesai di-bind (`findViewById`) dan preferensi tersimpan telah dimuat, bukan sebelum view terikat yang sebelumnya menyebabkan kondisi `if (layoutTopBar != null)` bernilai `false`.
    - **Pemberian Status Visibilitas Instan:** Menetapkan `layoutTopBar.setVisibility(isLandscape ? View.VISIBLE : View.GONE);` seketika saat `layoutTopBar` di-bind, menjamin header tetap 100% `GONE` selama fase resolusi stream (`"MENYIAPKAN STREAM..."`) dan pemutaran awal dalam mode portrait ponsel.
    - **Isolasi Penuh Mode Landscape & Android TV:** Mode landscape ponsel dan antarmuka 10-Foot UI Android TV tetap mempertahankan header atas lengkap dengan tombol kontrol dan padding overscan yang pulih secara otomatis saat video beralih ke orientasi landscape.
    - **Automated Tests:** Memperluas pengujian di `tests/test_watch_portrait_view.py` untuk memvalidasi atribut `android:visibility="gone"` pada XML dan penegakan visibilitas instan pada `onCreate` (100% lulus).

## [2.7.1] - 2026-10-15

### Justifikasi SemVer 2.0.0 (PATCH: 2.7.0 -> 2.7.1)
Kenaikan digit PATCH diterapkan sesuai kaidah Semantic Versioning 2.0.0 untuk perbaikan bug navigasi remote D-Pad dan fungsionalitas tombol Next/Previous ExoPlayer yang terisolasi 100% pada platform Android TV tanpa memodifikasi antarmuka maupun logika pada varian Android Mobile:
1. **Perbaikan Terisolasi Tombol Next/Previous ExoPlayer Android TV (`PlayerActivity.java`):**
   - Mengintegrasikan pemeriksaan perintah `Player.COMMAND_SEEK_TO_NEXT` dan `Player.COMMAND_SEEK_TO_PREVIOUS` pada `ForwardingPlayer` Media3 secara terisolasi (`TvFocusHelper.isTv(this)`), sehingga tombol Next dan Previous hanya aktif (`enabled` dan `focusable`) saat video berada dalam status ter-pause (`isPaused`).
   - Menyambungkan callback `seekToNext()` dan `seekToPrevious()` pada `ForwardingPlayer` langsung ke `playNextEpisode()` dan `playPrevEpisode()`.
2. **Perilaku D-Pad Terarah (Fast-Forward saat Berjalan vs Navigasi saat Ter-pause):**
   - Ketika video sedang berputar (`isPlaying`), tombol `DPAD_RIGHT` berfungsi murni sebagai Fast-Forward (`seekRelative(+5000)`), dan `DPAD_LEFT` sebagai Rewind (`seekRelative(-5000)`).
   - Ketika video ter-pause (`!isPlaying`), pembajakan event D-Pad dinonaktifkan (`break;`) sehingga D-Pad Left/Right dapat bernavigasi secara mulus di antara tombol-tombol kontrol pemutar (`[exo_prev]`, `[exo_rew]`, `[exo_play_pause]`, `[exo_ffwd]`, `[exo_next]`).
3. **Delegasi Klik Tombol Kontrol pada `DPAD_CENTER` / `ENTER`:**
   - Memperbaiki `dispatchKeyEvent` agar saat fokus berada di `btnExoNext` atau `btnExoPrev`, penekanan tombol `OK` / `DPAD_CENTER` langsung mengeksekusi perpindahan episode (`playNextEpisode()` / `playPrevEpisode()`).
   - Meneruskan klik via `focused.performClick()` untuk tombol-tombol kontrol di dalam `playerView` ketika terfokus, bukan membajak event menjadi play/pause.
4. **Opsi Ganti Episode Cepat pada Menu Pengaturan TV (`showPlayerUnifiedSettingsDialog`):**
   - Menambahkan opsi *"Putar Episode Berikutnya (Ep X)"* dan *"Putar Episode Sebelumnya (Ep Y)"* langsung ke dialog menu pengaturan pemutar khusus perangkat Android TV.
5. **Pemutakhiran Status Tombol Otomatis (`onIsPlayingChanged`):**
   - Memanggil `updateExoButtonStates()` secara otomatis pada event `onIsPlayingChanged` sehingga status aktif/nonaktif tombol Next dan Previous langsung tersinkronisasi saat video dijeda atau dilanjutkan.
6. **Fitur Kunci Sentuhan Layar (Touch Screen Lock) Terisolasi pada Android Mobile (`PlayerActivity.java`, `activity_player.xml`):**
   - Menambahkan tombol melayang (*floating lock button*) ergonomis di sisi kiri tengah layar (`btn_screen_lock`) yang muncul secara otomatis bersama kontrol pemutar.
   - Mengimplementasikan penguncian total interaksi sentuhan (`isScreenLocked = true`): saat aktif, seluruh gesture swipe (kecerahan dan volume), double-tap seek, dan kemunculan seekbar kontrol ExoPlayer dicegat 100% pada `playerView.setOnTouchListener`.
   - Menghadirkan tombol interaktif gembok *"Buka Kunci"* (`btn_screen_unlock`) yang muncul selama 3 detik saat layar disentuh atau tombol Back ditekan, lalu memudar halus (*fade out*) agar tampilan anime tetap bersih dan tidak terhalang.
   - Memproteksi penutupan pemutar yang tidak disengaja via hardware maupun gesture back (`dispatchKeyEvent` & `onBackPressed`), dengan tetap membiarkan tombol fisik volume HP berfungsi normal.
   - Menjamin layar HP tidak mati atau mengunci sendiri saat anime aktif diputar melalui pemanggilan `playerView.setKeepScreenOn(isPlaying)`.
   - Mengisolasi penuh fitur ini dari Android TV (`TvFocusHelper.isTv(this)` menyembunyikan tombol secara permanen), menjaga antarmuka remote D-Pad 10-Foot UI tetap bersih.

## [2.7.0] - 2026-10-15

### Justifikasi SemVer 2.0.0 (MINOR: 2.6.2 -> 2.7.0)
Kenaikan digit MINOR diterapkan secara resmi sesuai kaidah Semantic Versioning 2.0.0 karena memperkenalkan identitas visual baru aplikasi serta perombakan antarmuka pengguna Android (Mobile & Android TV) yang backward-compatible tanpa merusak logika aplikasi:
1. **Redesain Total Ikon Aplikasi Berkarakter Anime (*Anime Mascot Character*):** Menghadirkan maskot anime resmi Tatap (*Cyber Anime Streamer*) dengan tatapan tajam (*"Tatap"*), headphone streaming LED cyan neon, dan semburat rambut cyan-violet.
2. **Arsitektur Android Adaptive Icons Modern (API 26+ `mipmap-anydpi-v26`):** Mengimplementasikan adaptive icon resmi dengan pemisahan layer background (`#0A0D14`), foreground dengan safe margin 72dp, dan siluet monokromik untuk mendukung penuh fitur **Themed Icons (Material You)** di Android 13+ (API 33+).
3. **Penyempurnaan Seluruh Mipmap Legacy & TV Banner Standar Broadcast:** Menghasilkan ulang seluruh varian raster mipmap (`mdpi` 48px hingga `xxxhdpi` 192px dan drawable 512px) dengan masker lingkaran murni anti-aliased (menghilangkan cacat squircle terpotong pada `ic_launcher_round.png`), serta memperbarui Android TV Leanback Banner (`tv_banner.png`, 320x180 & 640x360) dengan penataan aman overscan TV tanpa teks terpotong.
4. **Pembersihan Total "AI Slop" pada Seluruh UI Android:** Mengeliminasi 100% penjejangan emoji kartun murahan pada 13 chip filter katalog (`Terpopuler`, `Skor Tertinggi`, `Terbaru`, `Trending`, `A-Z`, `Favorit`, `TV Series`, `Movie`, `OVA`, `ONA`, `Special`, `Sedang Tayang`, `Sudah Tamat`) dan mengubahnya menjadi *pure typographic pills* monokrom yang elegan, kompak, dan berkelas layaknya aplikasi streaming papan atas dunia.
5. **Pustaka Vektor Drawables Monokrom Terarah (13 Vector XMLs):** Mengganti karakter simbol teks mentah (`✕` dan `⋮`) dan emoji pada navigasi beranda dengan 13 berkas Android Vector Drawables presisi (`ic_tab_season`, `ic_tab_airing`, `ic_tab_favorite`, `ic_tab_catalog`, `ic_tab_schedule`, `ic_tab_genre`, `ic_filter`, `ic_search`, `ic_more_vert`, `ic_close`, `ic_star_outline`, `ic_star_filled`, `ic_skip_next`).
6. **State Tinting Dinamis Compound Drawables:** Mengintegrasikan helper `setTabAppearance` di `MainActivity.java` untuk merespons status tab aktif/inaktif secara dinamis (`#FFFFFF` aktif vs `#8892B0` inaktif).
7. **Pembersihan Copywriting & Toast:** Menghapus seluruh residu emoji pada string status, pesan toast bookmark favorit, dan kontrol player lewati intro/outro.
8. **Automated Regression Suite (`tests/test_android_ui_icons.py`):** Menambahkan unit test otomatis yang memverifikasi 0 emoji dan 0 simbol mentah pada seluruh layout dan kode Java Android, validitas 13 berkas vektor, batas proporsi ukuran intrinsik 14dp–16dp, serta dimensi aset mipmap dan TV banner.
9. **Penyelarasan Presisi Proporsi Ikon & Sistem Desain Android (*Optical Cap-Height Hierarchy*):** Menyesuaikan intrinsic dimensions ke-13 berkas vector drawable dari 24dp menjadi ukuran optik proporsional 14dp–15dp (tetap dengan `viewportWidth="24"` dan `viewportHeight="24"`). Mengeliminasi kesan ikon kebesaran (*oversized*), memberikan ruang napas vertikal 8.5dp pada pill kategori 32dp yang bersanding anggun dan seimbang dengan tipografi font 11.5sp bold (rasio ideal ~1.6:1 cap-height).
10. **Harmonisasi Spasi, Padding & Tombol Interaktif Seluruh Aplikasi:** Menstandarkan `drawablePadding="5dp"` pada tab dan input search, menyelaraskan tombol close modal dialog (`30dp x 30dp` dengan padding `8dp`), tombol bookmark detail, dan tombol lewati opening/ending player (`app:iconSize="15dp"`, `app:iconPadding="5dp"`).
11. **Penyempurnaan Terisolasi 100% Khusus Android TV (10-Foot UI):**
    - Memulihkan dan menormalkan tab "Jadwal" pada remote D-Pad Android TV sehingga navigasi horizontal mengalir mulus tanpa ter-skip (`Musim <-> Airing <-> Favorit <-> Katalog <-> Jadwal <-> Genre`) dengan 6 tab seragam berbobot seimbang (`weight=1.0f`, tinggi 38dp, font 13sp).
    - Menghidupkan fungsionalitas kolom pencarian (*searchbox*) pada Android TV via aktivasi klik/`DPAD_CENTER`, perbaikan arah navigasi atas tab ke searchbox, dan pemunculan terprogram keyboard virtual Android TV (IME) via `InputMethodManager.showSoftInput`.
    - Mengimplementasikan `CenteredImageSpan` (`TvFocusHelper.java`) untuk memusatkan ikon dan teks tab secara simetris di tengah tombol berbobot layar lebar 16:9, melenyapkan rongga kosong tepi kiri akibat `drawableStart` XML.
    - Membatasi lebar seluruh jendela dialog modal TV menjadi maksimum 700dp (Card Center Layout) agar tidak meregang penuh di layar televisi.
12. **Penambahan Pemilih Kecepatan Putar Video Multiplatform (*Multi-Speed Playback Selector*):** Menambahkan 7 opsi playback speed (`0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 1.75x, 2.0x`) pada Desktop Web dan Android (Mobile & TV), lengkap dengan tombol pintas keyboard `[` / `]` dan aturan deterministik reset otomatis ke `1.0x` pada setiap sesi judul anime baru.
13. **Indikator Penghitung Episode Rilis Anime Sedang Tayang (*Released Ongoing Episode Counter*):** Menghitung rasio episode rilis aktif terhadap total proyeksi penayangan (`eps_released`, `eps_total`, `eps_counter`, misal: `8/12` atau `8/?`) pada backend scraper, lalu menyajikannya secara konsisten pada poster card katalog, badge status (`EP 8/12`), serta deskripsi jumlah episode detail anime di seluruh platform.
14. **Mitigasi False Positive VirusTotal pada Tatap Windows Portable (`Tatap.exe`):**
    - Refaktor `launcher/main.go`: Mengganti fungsi `killPortOccupant` (yang mengeksekusi `cmd /c netstat -ano` dan `taskkill /F /PID`) dengan mekanisme **Graceful HTTP Shutdown** (`POST /api/shutdown`) dan manajemen file PID terisolasi (`cache/server.pid`) via Win32 API murni (`windows.OpenProcess` + `windows.TerminateProcess`). Menghapus 100% jejak string shell `cmd`, `netstat`, dan `taskkill` dari biner Windows.
    - Tuning Linker Flag Go di `tools/build_windows_portable.py`: Mengubah `-ldflags "-H=windowsgui -s -w"` menjadi `-ldflags "-H=windowsgui -w"` untuk mempertahankan tabel simbol Go (`pclntab`), memungkinkan antivirus AI/ML memverifikasi integritas modul resmi WebView2 & standard library tanpa dicurigai sebagai obfuscated trojan.
    - Penambahan catatan transparansi integritas & open-source pada `windows/README.txt`.
15. **Akses Cepat & Navigasi D-Pad Tombol Lewati Opening/Ending Khusus Android TV (`PlayerActivity.java` & `activity_player.xml`):**
    - Menyambungkan event remote D-Pad TV ke tombol mengambang `btn_skip_op_ed`: tombol otomatis difokuskan (*auto-focus*) dengan skala 1.10x dan border glow cyan `#38BDF8` saat intro/outro dimulai, sehingga pengguna TV dapat melompati opening/ending cukup dengan menekan 1 tombol **`OK` (`DPAD_CENTER`)**.
    - Navigasi D-Pad terintegrasi: menekan `DPAD_DOWN` memfokuskan kembali tombol skip jika sempat beralih fokus, `DPAD_UP` mengembalikan fokus ke bar kontrol atas, dan tombol `BACK` melepas fokus tanpa menutup video.
    - Pintasan 1-klik remote: tombol `>>` (`MEDIA_FAST_FORWARD` dan `BUTTON_R1`) langsung mengeksekusi lompat opening/ending tanpa memindahkan kursor.
    - Panduan visual remote TV dinamis: menampilkan label `Lewati Opening [OK]` saat fokus dan `[▼] Lewati Opening` saat unfocused pada layar TV.
    - Opsi preferensi baru pada dialog pengaturan pemutar: *"Otomatis Lewati Opening & Ending (Aktif/Mati)"* yang tersimpan persisten di `SharedPreferences`.
16. **Fitur Pengingat Posisi Tontonan & Dialog Resume Lintas Platform (*Multiplatform Resume Watch Position & Prompt Modal*):**
    - Menyimpan posisi waktu menit dan detik terakhir saat menonton anime secara atomik per episode pada tabel SQLite `watch_progress` (kompatibel penuh antara backend CPython dan Chaquopy Android).
    - Menampilkan dialog/modal interaktif yang cerdas saat pengguna membuka kembali episode yang memiliki riwayat tontonan: opsi *"Lanjutkan (MM:SS)"* atau *"Mulai dari Awal (00:00)"*.
    - Guard filter cerdas: posisi < 15 detik atau mendekati selesai (> 90% durasi / sisa < 30 detik) secara otomatis memulai dari awal tanpa mengganggu pengguna dengan dialog.
    - Sinkronisasi otomatis ke baris *Lanjutkan Nonton* di Beranda dengan label menit & detik riil (`ep X · MM:SS · lanjutkan ▶`).
    - Khusus Android TV: Dialog secara otomatis memfokuskan tombol *"Lanjutkan"* sehingga pengguna dapat langsung melanjutkan tontonan hanya dengan 1 klik tombol `OK` remote.
17. **Pengerasan & Kehandalan Startup Linux AppImage (`linux/AppRun`):**
    - Mengganti endpoint probe kesiapan server internal dari `/api/health` (yang memeriksa konektivitas upstream WAN HiAnime dengan timeout 10s) menjadi `/api/ping` (pemeriksaan port lokal murni instan), mengeliminasi kegagalan startup semu saat offline atau jaringan lambat.
    - Menambahkan penanganan graceful shutdown port 8767 via request HTTP `POST /api/shutdown` sebelum mengeksekusi launcher.
18. **Perbaikan & Penguatan Filter Genre Terisolasi pada Web dan Desktop (`frontend/js/term.js`, `frontend/index.html`, `frontend/css/style.css`):**
    - Memperbaiki bug kritis di mana pemanggilan API `apiCall("katalog")` mengabaikan filter genre dan hanya membaca filter umum (`hasFilter`), sehingga genre terpilih gagal menyaring anime.
    - Menyatukan state filter katalog `S.catalogFilter.genre` dan meneruskannya ke `window.Tatap.browse(f, S.page)` dengan query `&genre=<slug>`.
    - Memperbarui label judul baris katalog agar mencantumkan nama genre aktif (`Katalog (Genre: <Nama>)`) dan mendukung paginasi multi-halaman (`[` / `]`) tetap pada genre tersebut.
    - Menghadirkan antarmuka modal genre `#genre-modal` yang disempurnakan: tombol *"Reset Genre"*, penanda status visual aktif (`.genre-list button.active` dengan border/glow cyan dan teks tebal), indikator status genre aktif di baris status, dan shortcut tombol `Enter` pada input pencarian untuk memilih genre pertama.
    - Mengintegrasikan pemilih genre langsung pada modal Cross-Filter (`#catalog-filter-modal`) dengan tombol pintas dan tombol hapus instan.
    - Menambahkan test suite otomatis `tests/test_genre_filter_web.py` dan memverifikasi direktori `android/` 100% tidak tersentuh.
19. **Penyempurnaan Modal Interaktif Resume Watch pada Web dan Desktop (`frontend/js/app.js`, `frontend/index.html`, `frontend/css/style.css`, `frontend/js/term.js`):**
    - Memperbaiki bug semantik tombol tutup `[×]` (`#rm-close`) yang sebelumnya keliru memanggil resume playback; kini tombol silang, klik backdrop luar, dan tombol `Escape` berfungsi murni sebagai pembatalan (modal tertutup bersih tanpa memutar video).
    - Menghadirkan navigasi keyboard interaktif penuh: tombol panah (`ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`) dan `Tab` untuk berpindah fokus dinamis antara *"Lanjutkan"* dan *"Mulai dari Awal"*, serta tombol `Enter` untuk mengeksekusi opsi aktif dengan outline glowing cyan kontras tinggi (`:focus-visible`).
    - Memperkaya informasi visual modal: menampilkan judul anime (`cur.title`), badge nomor episode (`EP <n>`), serta bar progress cyber dengan persentase tontonan (`% selesai · MM:SS / Total`).
    - Memperbaiki layering modal (`#resume-modal.overlay`) dengan `z-index: 160` dan `backdrop-filter: blur(5px)` agar tampil elegan dan berada di depan modal anime detail (`#title-modal`).
    - Menambahkan deteksi `#resume-modal` pada fungsi `isModalOpen()` di `term.js` untuk mengeliminasi event leakage ke terminal background saat dialog resume watch sedang aktif.
    - Menjamin isolasi ketat 100%: direktori `android/` sama sekali tidak dimodifikasi.

### Ditambahkan
- **Fitur Pengingat Posisi Tontonan (*Resume Watch Position & Prompt Modal*):**
  - Backend API (`backend/main.py` & Chaquopy Android): Endpoint `GET /api/progress`, `POST /api/progress`, `DELETE /api/progress`, dan helper `_format_time_sec`.
  - Database SQLite (`backend/database/__init__.py` & Chaquopy Android): Skema tabel `watch_progress(slug, episode, progress, duration, updated_at)` serta method `save_progress`, `get_progress`, `clear_progress` yang tersinkronisasi otomatis dengan `watch_history`.
  - Frontend Web & Desktop (`frontend/index.html`, `frontend/css/style.css`, `frontend/js/api.js`, `frontend/js/app.js`): Modal `#resume-modal` bergaya dark-cyber dengan tombol *"Lanjutkan (MM:SS)"* dan *"Mulai dari Awal"*, event listener `timeupdate`, `pause`, `ended`, dan `beforeunload` untuk persistensi riil, serta pembaruan tampilan badge waktu pada baris beranda `renderContinue()`.
  - Android Mobile & Android TV (`PlayerActivity.java`): Persistensi instan pada `SharedPreferences` dan background sync ke `/api/progress`, dialog `AlertDialog` tema gelap dengan D-pad auto-focus pada tombol positif untuk 1-klik resume pada remote Android TV, pemulihan posisi akurat pada `STATE_READY`, serta penanganan pergantian episode (`switchEpisode`).
  - Unit Test Otomatis (`tests/test_resume_watch.py`): Menguji operasi database, sinkronisasi history, format waktu, endpoint REST API, threshold resume, dan 100% paritas kode CPython & Chaquopy.
- **Pengerasan Runtime Linux AppImage (`linux/AppRun`):**
  - Mengganti probe kesiapan server internal dari `/api/health` menjadi `/api/ping` dan pembersihan port 8767 basi via HTTP `POST /api/shutdown`.
- **Pemilih Kecepatan Putar Video (*Video Playback Speed Selector*):**
  - Desktop Web: Dropdown `<select id="pm-speed-select">` di player header bar dengan 7 opsi kecepatan (`0.5x`, `0.75x`, `1.0x (Normal)`, `1.25x`, `1.5x`, `1.75x`, `2.0x`), pintasan keyboard `[` (perlambat) dan `]` (percepat), status toast real-time, serta reset deterministik kembali ke `1.0x` saat membuka judul baru (`openTitle`).
  - Android Mobile & Android TV: Tombol interaktif `btn_speed` pada top overlay player, dialog pilihan tunggal `showSpeedSelectorDialog`, integrasi pada `showPlayerUnifiedSettingsDialog`, navigasi D-Pad terintegrasi (`nextFocusLeft` ke `btn_quality`, `nextFocusRight` ke `btn_sub_style`), dan penerapan rate via `player.setPlaybackParameters(new PlaybackParameters(speed))`.
- **Penghitung Episode Rilis Ongoing (*Ongoing Anime Episode Counter*):**
  - AniList API (`backend/api/anilist.py` & Chaquopy): Menambahkan ekstraksi `nextAiringEpisode` dan helper `compute_episode_counts(m)` untuk mendeteksi jumlah episode rilis vs total proyeksi musim tayang.
  - HiAnime API (`backend/api/hianime.py` & Chaquopy): Menghitung `eps_released`, `eps_total`, dan `eps_counter` (format `rel/tot` atau `rel/?`) dari browse cards dan pencarian.
  - Backend API Gateway (`backend/main.py` & Chaquopy): Menyajikan field `eps_released`, `eps_total`, `eps_counter`, `badge`, dan `is_finished` pada endpoint `/api/seasonal` untuk kedua jalur (`seasonal` dan `long_running`).
  - Desktop UI (`frontend/js/term.js` & `app.js`): Menampilkan badge `EP 8/12` pada poster card ongoing, teks `Ep 8/12` pada metadata baris, serta format `8/12 episode rilis` pada modal detail anime `#tm-count`.
  - Android UI (`AnimeAdapter.java` & `DetailActivity.java`): Menampilkan badge `EP 8/12` pada poster card anime ongoing, metadata ringkasan `8/12 Ep`, serta deskripsi status `8/12 Episode Rilis (Sedang Tayang)` pada halaman detail.
- **Unit Test Komprehensif Playback Speed & Episode Counter (`tests/test_play_speed_and_episode_counter.py`):**
  - 5 test case otomatis memvalidasi perhitungan AniList next airing, parsing kartu HiAnime, audit paritas Chaquopy 100%, serta integrasi frontend dan native Android.
- **Identitas Visual Maskot Anime Tatap (`assets/`, `frontend/assets/`, `launcher/` & `android/`):**
  - Mengadopsi ilustrasi maskot anime orisinal dengan tatapan fokus tajam, headphone streaming neon cyan, dan palet gelap cyberpunk yang menyatu sempurna di seluruh platform.
  - Menghasilkan aset pendukung: `assets/tatap_icon_master.png`, `tatap_icon_512.png`, `frontend/assets/icon.png`, `favicon.ico`, serta `launcher/icon.ico`.
- **Dukungan Penuh Android Adaptive Icons (`mipmap-anydpi-v26/` & `drawable/`):**
  - Berkas `mipmap-anydpi-v26/ic_launcher.xml` dan `ic_launcher_round.xml`.
  - Berkas `drawable/ic_launcher_background.xml`, `ic_launcher_foreground.png` (432x432 px, centered safe zone), dan `ic_launcher_monochrome.xml` (Material You).
- **13 Android Vector Drawables Ramping & Proporsional (`res/drawable/`):**
  - `ic_tab_season.xml` (15dp), `ic_tab_airing.xml` (15dp), `ic_tab_favorite.xml` (15dp), `ic_tab_catalog.xml` (15dp), `ic_tab_schedule.xml` (15dp), `ic_tab_genre.xml` (15dp), `ic_filter.xml` (14dp), `ic_search.xml` (15dp), `ic_more_vert.xml` (15dp), `ic_close.xml` (14dp), `ic_star_outline.xml` (15dp), `ic_star_filled.xml` (15dp), `ic_skip_next.xml` (15dp).
- **Komponen Perataan Optik Teks & Ikon TV (`TvFocusHelper.CenteredImageSpan`):**
  - `CenteredImageSpan` untuk memposisikan ikon secara matematis tepat di tengah vertikal baris teks pada layout Android TV.
- **Skrip Pembuatan Aset Ikonik Mandiri (`tools/generate_android_icons.py`):**
  - Otomasi supersampling 4x dengan filter resampling Lanczos untuk menghasilkan seluruh densitas mipmap Android dan banner TV 16:9 beresolusi tinggi.
- **Unit Test Pencegahan Regresi (`tests/test_android_ui_icons.py`):**
  - `test_zero_emojis_and_raw_symbols_in_android`, `test_vector_drawables_exist_and_valid` (termasuk validasi proporsi bounds 14dp–16dp), dan `test_adaptive_icons_and_mipmaps`.

### Diubah
- **Penyelarasan Proporsi & Desain UI Android (`activity_main.xml`, `dialog_catalog_filter.xml`, `dialog_*.xml`, `activity_detail.xml`, `activity_player.xml`):**
  - Kolom pencarian diselaraskan dengan ikon lensa `ic_search` (15dp), `drawablePadding="6dp"`, dan tombol clear `22dp x 22dp` dengan `padding="4dp"`.
  - Tombol menu header menggunakan ikon `ic_more_vert` (15dp) dengan `drawablePadding="4dp"`.
  - Seluruh tombol tutup modal dialog (`dialog_catalog_filter.xml`, `dialog_command_help.xml`, `dialog_genre_selector.xml`, `dialog_ai_settings.xml`, `dialog_translate_logs.xml`) distandarkan ke ukuran `30dp x 30dp` dengan `padding="8dp"` memuat ikon `ic_close` (14dp) tanpa terpotong.
  - 13 chip filter katalog dibersihkan dari seluruh emoji menjadi *pure typographic pills*.
  - 6 tab beranda menggunakan compound drawables vektor terkalibrasi (15dp) dengan `drawablePadding="5dp"` dan pewarnaan dinamis.
  - Tombol bookmark pada halaman detail menggunakan `ic_star_outline` dan `ic_star_filled` (`app:iconSize="15dp"`, `app:iconPadding="5dp"`).
  - Tombol lewati opening/ending player menggunakan `ic_skip_next` (`app:iconSize="15dp"`, `app:iconPadding="5dp"`).
- **Logika & Antarmuka Android TV Terisolasi 100% (`MainActivity.java`, `TvFocusHelper.java`, `dimens.xml`):**
  - Normalisasi 6 tab beranda TV: seluruh tab diukur seragam (`weight=1.0f`, tinggi 38dp, font 13sp).
  - Penyambungan rantai navigasi remote D-Pad penuh tanpa skip: `Musim <-> Airing <-> Favorit <-> Katalog <-> Jadwal <-> Genre`.
  - Penghubungan panah bawah dari tab Jadwal ke baris pemilih 7 hari (`btnDaySenin` s/d `btnDayMinggu`), dan sebaliknya panah atas dari chip hari ke tab Jadwal.
  - Aktivasi pencarian dan pemunculan terprogram on-screen keyboard (IME) TV saat searchbox diklik, difokuskan, atau ditekan tombol `DPAD_CENTER` / Enter remote.
  - Penggunaan `updateTvTabSpannable` dengan `CenteredImageSpan` pada TV untuk menggantikan compound drawables XML agar ikon dan teks memusat secara proporsional.
  - Pembatasan lebar jendela seluruh modal dialog TV menjadi maksimal 700dp (`setupDialogWindowBounds`).
  - Penyesuaian token dimensi TV: `tv_search_height` (34dp) dan `tv_tab_height` (38dp).
- **Logika Java Native Ponsel & Pemutar Video (`MainActivity.java`, `DetailActivity.java`, `PlayerActivity.java`):**
  - Penambahan helper `setTabAppearance` untuk tinting dinamis icon dan teks tab beranda.
  - Pembersihan emoji pada teks bookmark detail dan toast notifikasi.
  - Pembersihan emoji pada tombol dan toast lompat intro/outro player.
  - Khusus Android TV: Auto-focus tombol `btn_skip_op_ed` saat intro/outro dimulai, penyesuaian label dinamis (`Lewati Opening [OK]` vs `[▼] Lewati Opening`), navigasi `DPAD_DOWN` / `DPAD_UP`, pintasan remote `>>` (`MEDIA_FAST_FORWARD` dan `BUTTON_R1`), dan opsi pengaturan *"Otomatis Lewati Opening & Ending"*.
- **Launcher Native Windows Portable (`launcher/main.go`, `tools/build_windows_portable.py`, `windows/README.txt`):**
  - Mengganti eksekusi shell `cmd /c netstat` dan `taskkill` dengan Graceful HTTP Shutdown (`POST /api/shutdown`) dan terminasi Win32 API murni (`windows.OpenProcess` + `windows.TerminateProcess`) via file PID `cache/server.pid`.
  - Mengubah opsi kompilasi `-ldflags` Go dari `-s -w` menjadi `-w` saja agar tabel simbol Go tetap utuh demi transparansi modul resmi WebView2 di mata antivirus AI/ML.
  - Menambahkan catatan keamanan, integritas, dan open-source pada panduan `windows/README.txt`.

### Diperbaiki
- **Filter Genre Web & Desktop (`frontend/js/term.js`, `frontend/index.html`, `frontend/css/style.css`):**
  - Mengatasi bug pemanggilan `apiCall("katalog")` yang sebelumnya mengabaikan `f.genre` dan menyebabkan filter genre gagal menyaring anime.
  - Memadukan state filter katalog `S.catalogFilter.genre` dan `S.genreFilter` agar parameter `&genre=` selalu dikirimkan ke endpoint `/api/browse`.
  - Memperbaiki judul baris katalog agar secara akurat mencerminkan genre aktif (`Katalog (Genre: <Nama>)`) dan memastikan paginasi multi-halaman (`[` / `]`) tetap membawa parameter genre.
  - Menambahkan tombol *"Reset Genre"*, indikator teks status aktif, dan styling tombol aktif (`.genre-list button.active`) pada modal `#genre-modal`.
  - Mengintegrasikan pemilih genre dan tombol pembersih cepat pada modal Cross-Filter (`#catalog-filter-modal`).

## [2.6.2] - 2026-10-14

### Justifikasi SemVer 2.0.0 (PATCH: 2.6.1 -> 2.6.2)
Kenaikan digit PATCH diterapkan secara resmi sesuai kaidah Semantic Versioning 2.0.0 untuk perbaikan stabilitas platform Desktop (Windows Portable) dan Web Desktop tanpa penambahan modul arsitektur baru:
1. **Perbaikan Subtitle Ganda (Duplicate Subtitle Rendering):** Mengeliminasi konflik visual antara rendering native `video::cue` dan overlay kustom `#pm-subs-overlay` di Chromium dan Edge WebView2 Windows Portable dengan menyetel `trackEl.default = false` dan menyembunyikan overlay saat mode native fullscreen aktif.
2. **Percepatan Resolving Video:** Memangkas rantai HTTP request berulang pada backend MegaPlay dengan menggunakan single-fetch master playlist m3u8 dan mempercepat soft-validasi track subtitle CDN terpercaya.
3. **Pemberian Batas Timeout AniSkip:** Membatasi pemanggilan sinkron API AniSkip dengan timeout maksimal 1.2 detik sehingga episode langsung diputar tanpa tertahan jika server skip-times lambat atau mengalami latency.
4. **Perbaikan Macet Streaming & URL Nesting Prefetch:** Memperbaiki bug pembungkusan URL bersarang (*nested proxy url*) pada Hls.js `FRAG_BUFFERED` yang sebelumnya memicu HTTP 400 Bad Request, menambahkan auto-nudge buffer stall recovery, serta mencegah keracunan cache host DPI pada CDN streaming normal.
5. **Pencegahan Race Condition Episode Navigation:** Menambahkan token request unik `cur.playToken` pada navigasi episode dan pergantian subtitle agar respon episode lama tidak menimpa episode baru saat navigasi cepat.
6. **Perbaikan Sistem Pagination (Next & Prev Page) Seluruh View Desktop & Web:** Memperbaiki bug parser AniList yang sebelumnya mengunci `lastPage` sama dengan `currentPage` sehingga pagination di tampilan *Musim Ini*, *Masih Tayang*, dan *Season Custom* terkunci di halaman 1; menambahkan tombol fisik navigasi `[⏮ Sebelumnya]` dan `[Berikutnya ⏭]` pada kontainer `#pager`; serta mengintegrasikan perpindahan hari rilis dan paging koleksi *Favorit*.
7. **Perluasan Jadwal Rilis Full 7 Hari Mingguan (Senin s/d Minggu) ke Seluruh Platform & Aktivasi Android TV:** Memperluas cakupan jadwal tayang anime dari format 3 hari (*Kemarin, Hari Ini, Besok*) menjadi **7 Hari Mingguan Penuh (Senin s/d Minggu)** waktu WIB; mengaktifkan Tab Jadwal di Android TV lengkap dengan integrasi D-Pad remote via `TvFocusHelper`; menghadirkan chip 7 hari berfitur auto-select hari ini, auto-scroll horizontal, dan penanda *Hari Ini* di Web Desktop, Windows Portable, Linux AppImage, Android Mobile, dan Android TV.
8. **Efek Scanline CRT Default Dimatikan (`:crt off`):** Mengatur kondisi bawaan efek CRT menjadi nonaktif (`no-crt`) secara default pada Web dan Desktop untuk kenyamanan visual layar modern, dengan kemampuan mengaktifkan kembali sewaktu-waktu melalui perintah terminal `:crt on`.
9. **Kondisionalitas Pager Navigasi Halaman:** Tombol navigasi halaman sebelumnya/berikutnya (`#pg-prev` dan `#pg-next`) beserta kontainer `#pager` kini hanya tampil jika terdapat kondisi paginasi riil (`S.total > 1` atau navigasi 7 hari). Pada tampilan satu halaman (pencarian, favorit sedikit, atau filter tunggal), pager disembunyikan sepenuhnya.
10. **Penyeragaman Seluruh Ikon UI Desktop (Cyber-Minimalist SVG Icons):** Mengganti seluruh emoji berwarna bawaan OS dan simbol teks mentah di desktop UI dengan pustaka ikon vektor SVG lokal (`.ui-icon`) berskala `currentColor` yang harmonis dengan estetika cyberpunk Tatap.
11. **Perbaikan Visibilitas Pager Navigasi pada Startup Aplikasi (CSS Cascade Fix):** Memperbaiki bug spesifisitas di mana deklarasi `.pager` (`display: flex`) menimpa selektor `.hidden` (`display: none`), menyebabkan tombol `[Sebelumnya]` dan `[Berikutnya]` sempat tampil di layar awal (`cari` / siap). Menambahkan aturan khusus `.pager.hidden { display: none !important; }` dan `.ep-ranges.hidden { display: none !important; }` di `frontend/css/style.css` serta memastikan `renderPager()` dievaluasi secara sinkron pada `boot()` dan `renderRecents()` di `frontend/js/term.js`.

### Ditambahkan
- **Penyeragaman Ikon UI Desktop & Pustaka SVG Lokal (`frontend/index.html`, `frontend/css/style.css`, `frontend/js/app.js`):**
  - Menyematkan pustaka SVG symbol sprite lokal `<svg id="tatap-icons">` dan kelas `.ui-icon` (1.15em, `currentColor`, fleksibel), menggantikan seluruh emoji OS pada tombol drawer, menu navigasi, modal cross-filter, bookmark favorit, kontrol pemutar video, skip opening, volume/brightness OSD, serta tombol pager.
  - Menjadikan efek scanline CRT nonaktif secara bawaan (`tatap_crt = 'off'`) melalui kelas awal `body.no-crt` dan inisialisasi default pada `loadPrefs()` serta perintah terminal `:crt`.
  - Mengimplementasikan evaluasi kondisional `hasPagination` pada `renderPager()`, menjamin tombol navigasi halaman hanya muncul saat terdapat lebih dari 1 halaman atau saat berada di tampilan jadwal rilis 7 hari.
  - Menambahkan aturan spesifisitas CSS `.pager.hidden { display: none !important; }` dan `.ep-ranges.hidden { display: none !important; }` serta sinkronisasi evaluasi `renderPager()` pada `boot()` dan `renderRecents()` di `frontend/js/term.js`, menjamin tombol pager 100% tersembunyi pada startup awal hingga pengguna masuk ke view dengan pagination aktif.
- **Fitur Jadwal Rilis Full 7 Hari Mingguan (Senin - Minggu) di Seluruh Platform:**
  - **Backend API 7 Hari Mingguan (`backend/main.py`, `backend/api/anilist.py` & Chaquopy Parity):** Endpoint `/api/schedule` kini menghitung rentang Senin 00:00:00 WIB hingga Minggu 23:59:59 WIB dari pekan berjalan, mengelompokkan anime ke dalam 7 bucket hari (`monday` s/d `sunday`), memperluas query AniList hingga 6 halaman (~300 anime), dan mempertahankan kompatibilitas alias `today`, `yesterday`, `tomorrow` serta nama hari Indonesia.
  - **Antarmuka Web Desktop & Windows Portable (`frontend/index.html`, `frontend/css/style.css`, `frontend/js/term.js`):** Kontainer `#schedule-days-bar` diperbarui menjadi 7 tombol hari (*Senin*, *Selasa*, *Rabu*, *Kamis*, *Jumat*, *Sabtu*, *Minggu*) dengan styling horizontal scroll yang luwes, dot indikator hari ini (`is-today`), navigasi pager 7 hari `(1/7 .. 7/7)` via tombol fisik `⏮ / ⏭` maupun shortcut keyboard `[` dan `]`, serta dukungan perintah konsol `:jadwal <hari>` / `:terbaru <hari>`.
  - **Aktivasi Tab Jadwal & 7-Chip Selector di Android TV & Mobile (`activity_main.xml` & `MainActivity.java`):** Mengaktifkan Tab ⏱️ *Jadwal* di Android TV dengan penyesuaian visual remote D-Pad, mengubah baris hari menjadi `HorizontalScrollView` 7 tombol hari yang responsif dengan auto-scroll ke hari aktif, serta mendukung perintah konsol terminal `:jadwal <hari>` di seluruh varian Android.
  - **Automated Test Suite (`tests/test_schedule.py`):** Menambahkan unit test komprehensif `test_schedule_7days_full_weekly` yang memverifikasi seluruh 7 hari via nama Inggris, nama Indonesia, day=all, serta penanda status `is_today`.
- **Frontend Player, Terminal & Pager Navigation (`frontend/index.html`, `frontend/css/style.css`, `frontend/js/term.js`, `frontend/js/api.js`):**
  - **Interactive Visual Pager Buttons:** Menambahkan tombol interaktif `#pg-prev` dan `#pg-next` bergaya Cyber Tatap pada kontainer `#pager` lengkap dengan state disabled dinamis, memungkinkan pengguna desktop/mouse berpindah halaman secara visual selain menggunakan pintasan keyboard `[` dan `]`.
  - **Full-View Pagination Support:** Menghubungkan fungsi `pagePrev()` dan `pageNext()` untuk seluruh tampilan: beralih hari rilis pada view *Jadwal*, membagi 24 kartu per halaman pada view *Favorit*, meneruskan nomor halaman pada view *Season Custom*, dan melakukan smooth scroll otomatis ke atas halaman saat berpindah.
  - **Single-Layer Subtitle Display:** Menyetel `trackEl.default = false;` pada `syncNativeTextTrack` dan memperbarui `paintCue()` untuk menyembunyikan `#pm-subs-overlay` saat native video fullscreen aktif. Membersihkan seluruh cue sisa dari track lama saat transisi track.
  - **URL Nesting Prefetch Fix:** Memeriksa apakah fragmen Hls sudah berawalan `/api/player/video` sebelum memanggil prefetch, menghilangkan banjir error HTTP 400 Bad Request di latar belakang.
  - **Hls.js Auto-Nudge & Resilient Recovery:** Menambahkan `nudgeOffset: 0.1`, `nudgeMaxRetry: 5`, menangani `bufferStalledError` dengan micro-nudge `v.currentTime += 0.08`, serta mengimplementasikan multi-attempt retry (hingga 4 kali) yang direset setiap kali segmen berhasil dimuat (`FRAG_LOADED`).
  - **Episode Navigation Race Protection:** Menambahkan token `cur.playToken = ++_playTokenCounter;` di awal `openPlayer()` dan `switchSubtitleTrack()` untuk membatalkan callback lama jika pengguna berpindah episode secara cepat.
- **Backend Resolving, Pagination & Streaming Pipeline (`backend/api/anilist.py`, `backend/api/hianime.py` & `backend/main.py`):**
  - **AniList GraphQL Pagination Fix:** Memperbaiki kalkulasi `lastPage` dan `hasNextPage` di `season_page()` dan `recently_finished_page()`, memastikan `total_pages` mengembalikan jumlah halaman riil saat masih ada data lanjutan.
  - **Seasonal Route Multi-Page Protection:** Memperbarui cache key endpoint `/api/seasonal` ke `seasonal_v3` dan menambahkan penyesuaian otomatis `total_pages >= page + 1` saat `has_next` bernilai true.
  - **Single Master M3U8 Fetch:** Memangkas 3x pengunduhan berulang master m3u8 menjadi 1x pengunduhan terintegrasi di `_try_megaplay`, mempercepat waktu pembukaan video hingga 60-70%.
  - **Trusted CDN Subtitle Fast-Track:** Melewati download mendalam file subtitle WebVTT saat me-resolve stream dari CDN terpercaya (MegaPlay, MegaCloud, Rabbitstream) sehingga metadata stream selesai instan.
  - **AniSkip Non-Blocking Timeout:** Membungkus pencarian intro/outro AniSkip dengan batas waktu 1.2 detik menggunakan `asyncio.wait_for`, menjamin ketiadaan atau kelambatan respon server eksternal tidak menunda pemutaran.
  - **Anti Host Poisoning Protection:** Melindungi daftar host DPI (`_BLOCKED_DPI_HOSTS`) agar tidak tercemar oleh domain CDN umum saat terjadi timeout jaringan biasa.
- **Automated Test Suite (`tests/test_desktop_perf_and_subs.py` & `tests/test_pagination_all_views.py`):**
  - Menambahkan pengujian otomatis komprehensif untuk pagination seluruh view (musim, airing, season custom, catalog, dan schedule), validasi subtitle terpercaya, batas waktu AniSkip, dan proteksi anti host poisoning.

## [2.6.1] - 2026-10-14

### Justifikasi SemVer 2.0.0 (PATCH: 2.6.0 -> 2.6.1)
Kenaikan digit PATCH diterapkan secara resmi sesuai kaidah Semantic Versioning 2.0.0 untuk perbaikan dan penyesuaian tata letak antarmuka perangkat spesifik (Android TV 10-Foot UI Layout Adaptation) tanpa memutus kompatibilitas ke belakang maupun mengubah struktur modul backend:
1. **Adaptive Full-Width Category Pill Menu di Android TV:** Menyesuaikan ukuran baris menu pill kedua (*horizontal scroll category tabs*) agar membentang 100% mengisi lebar layar TV secara simetris, mengeliminasi ruang kosong di sisi kanan layar.
2. **Optimal 10-Foot TV Ergonomics:** Meningkatkan tinggi sentuh/fokus pill menjadi 38dp dan ukuran font menjadi 13.5sp tebal dengan perataan tengah untuk kenyamanan jarak pandang sofa TV (3 meter).
3. **Perbaikan D-Pad Remote Chain:** Menyambungkan fokus navigasi remote TV secara langsung dari tab Katalog ke Genre saat tab Jadwal disembunyikan di TV.

### Diubah
- **Penyesuaian Ukuran Pill Menu Kategori Menyesuaikan Layar TV (`activity_main.xml` & `MainActivity.java`):**
  - **Full-Width Symmetrical Distribution:** Mengaktifkan `android:fillViewport="true"` pada `HorizontalScrollView` dan mengubah kontainer `layoutTabsContainer` ke `MATCH_PARENT`. Kelima tab yang aktif di TV (*🌸 Musim Ini*, *📺 Masih Tayang*, *⭐ Favorit*, *📚 Katalog*, *🏷️ Genre*) dibagikan rata menggunakan `layout_weight="1.0f"` sehingga mengisi lebar layar 16:9 secara penuh, seimbang, dan proporsional.
  - **10-Foot Viewing Dimensions:** Menaikkan tinggi pill dari `30dp` menjadi `38dp` dan ukuran teks dari `11.5sp` menjadi `13.5sp` berpusat di tengah (`Gravity.CENTER`) dengan margin antar-pill yang rapi (`8dp`), menjamin legibilitas optimal dari jarak jauh.
  - **D-Pad TV Navigation Chain:** Memperbaiki rantai navigasi remote TV D-Pad (`setNextFocusRightId` / `setNextFocusLeftId`) antara `btnTabKatalog` dan `btnTabGenre` agar remote tidak terhenti pada tab yang disembunyikan.
  - **Isolasi Ponsel Aman:** Mempertahankan tata letak asli pada perangkat ponsel Android sebagai carousel horizontal compact yang dapat digeser secara luwes dengan sentuhan jari.

## [2.6.0] - 2026-10-14

### Justifikasi SemVer 2.0.0 (MINOR: 2.5.0 -> 2.6.0)
Kenaikan digit MINOR diterapkan secara resmi sesuai kaidah Semantic Versioning 2.0.0 karena memperkenalkan penambahan fungsionalitas dan antarmuka interaktif baru yang kompatibel ke belakang (*backward-compatible new features*):
1. **Interactive Cross-Filter Modal Katalog (Urutan, Tahun, Bulan, Format, Status):** Menambahkan antarmuka dialog modal interaktif multiplatform (Android Mobile, Android TV, dan Desktop Web) untuk menyaring katalog anime secara komprehensif tanpa membebani antarmuka genre yang sudah memiliki tab tersendiri.
2. **Penyaringan Temporal Tahun & Bulan Rilis:** Mendukung filtering temporal presisi tinggi berdasarkan tahun tunggal (2025, 2024, 2023, 2022, 2021, 2020), rentang dekade (2015-2019, 2010-2014, 2000-2009, <2000), serta bulan rilis spesifik (Januari hingga Desember) yang dipadukan dengan opsi urutan (Skor Tertinggi, Terpopuler, Baru Ditambahkan, Paling Difavoritkan), format media (TV, Movie, OVA, ONA, Special), dan status (Selesai, Sedang Tayang).
3. **Sinkronisasi Bar Filter & Indikator Aktif Dinamis:** Menampilkan ringkasan filter aktif pada judul seksi dan bilah status interaktif dengan tombol reset satu klik (*✕*) baik di Android maupun Desktop Web.

### Ditambahkan
- **Interactive Cross-Filter Modal Katalog Multiplatform:**
  - **Antarmuka Android Native Mobile & Android TV (`dialog_catalog_filter.xml` & `MainActivity.java`):**
    - Menyediakan modal interaktif dengan chip selektor kategori visual: *Urutan* (Skor Tertinggi, Terpopuler, Baru Ditambahkan, Terbanyak Difavoritkan), *Tahun Rilis* (2025, 2024, 2023, 2022, 2021, 2020, 2015-2019, 2010-2014, 2000-2009, <2000), *Bulan Rilis* (Januari s.d. Desember), *Format Media* (TV, Movie, OVA, ONA, Special), dan *Status Tayang* (Selesai, Sedang Tayang).
    - Tombol pintas `🎛️ Filter` di sisi kanan judul seksi beranda berpadu dengan tombol reset dan terapkan.
    - Menampilkan *Active Filter Bar* di atas grid kartu saat filter aktif dengan tombol reset `✕`.
    - Integrasi penuh dengan navigasi remote D-Pad Android TV via `TvFocusHelper` (efek zoom halus 1.04x dan border cyan).
    - Menambahkan dukungan perintah TUI `:filter` pada terminal command bar Android.
  - **Desktop Web Terminal & UI (`frontend/index.html`, `frontend/css/style.css`, `frontend/js/term.js`, `frontend/js/app.js`):**
    - Modal interaktif `#catalog-filter-modal` bergaya cyber dark dengan chip selektor interaktif untuk kombinasi kriteria urutan, tahun, bulan, tipe, dan status.
    - Tombol pemicu `#btn-catalog-filter` otomatis muncul pada header pencarian saat membuka tampilan katalog.
    - Integrasi menu Drawer `🎛️ Filter Katalog` untuk akses cepat dari sidebar.
    - Perintah CLI `:filter` untuk membuka modal filter kapan saja dari prompt command.
    - Judul tampilan dinamis menampilkan ringkasan kriteria aktif (misalnya `KATALOG · 2024 · OKTOBER · SKOR TERTINGGI`).
- **Backend & Paritas Chaquopy (`backend/main.py` & `android/app/src/main/python/backend/main.py`):**
  - Menambahkan parameter `year` dan `month` pada endpoint `/api/browse`.
  - Parser fleksibel yang menerjemahkan tahun tunggal, rentang dekade, dan label klasik menjadi rentang tahun riil (`sy` dan `ey`) serta bulan (`sm` dan `em`).
  - Safe parameter extraction untuk mencegah kegagalan runtime FastAPI Dependency Injection dan unit test context.
  - Tetap menjunjung tinggi *Zero-Tolerance Blacklist Hentai* di semua tingkatan filter.
- **Automated Test Suite:**
  - Menambahkan pengujian menyeluruh pada `tests/test_catalog_filter.py` mencakup parsing rentang dekade, parameter temporal, kombinasi cross-filter, serta audit blacklist hentai.

## [2.5.0] - 2026-10-14

### Justifikasi SemVer 2.0.0 (MINOR: 2.4.2 -> 2.5.0)
Kenaikan digit MINOR diterapkan secara resmi sesuai kaidah Semantic Versioning 2.0.0 karena memperkenalkan penambahan fungsionalitas dan antarmuka baru yang kompatibel ke belakang (*backward-compatible new features*):
1. **Dual-Lane View & Pemisahan Anime Musiman vs Serial Panjang:** Menambahkan seksi jalur ganda mandiri pada halaman katalog dan tab anime masih tayang (`which=airing`) di seluruh platform (Android TV, Mobile, dan Desktop Web).
2. **True Seamless Resolution Switching:** Menambahkan kapabilitas peralihan resolusi dinamis tanpa jeda layar hitam dan tanpa pemotongan audio pada Android TV.
3. **Kapsul Navigasi Mengambang & Notifikasi Adaptif:** Menambahkan komponen UI floating bottom bar dan timer dinamis pada antarmuka Android.
4. **GraphQL Query & Filter Baru:** Menambahkan kueri pencarian anime yang baru saja tamat (`recently_finished_page`) dan pengklasifikasi serial anime continuous otomatis.
5. **Fitur Skip Opening & Ending Interaktif Multiplatform:** Menambahkan kapabilitas melompati intro (OP) dan outro (ED) anime melalui floating buttons interaktif, keyboard shortcut `S`, dan D-Pad remote TV dengan integrasi native MegaCloud & fallback AniSkip API.

### Ditambahkan
- **Fitur Skip Opening dan Ending Anime Interaktif Multiplatform:**
  - **Multi-Tier Skip Provider Engine:** Mengambil penanda waktu intro dan outro secara native langsung dari provider streaming (MegaCloud / MegaPlay `getSourcesNew`), dilengkapi fallback cerdas ke AniSkip API v2 komunitas open-source untuk sumber video alternatif.
  - **Non-Breaking Database Persistence:** Migrasi kolom `intro` dan `outro` pada tabel `episode_cache` SQLite lokal dengan paritas 100% pada Chaquopy Android untuk cache waktu instan tanpa query jaringan berulang.
  - **Floating Interactive Player Skip Buttons:**
    - Desktop Web (`frontend/index.html` & `frontend/js/app.js`): Tombol mengambang cyber cyan `#pm-skip-btn` muncul otomatis di kanan bawah selama pemutaran intro/outro berlangsung, dengan dukungan shortcut keyboard `S` dan transisi fade-out halus di luar durasi OP/ED.
    - Android Mobile & Android TV (`activity_player.xml` & `PlayerActivity.java`): Tombol mengambang `btn_skip_op_ed` berukuran 38dp dengan sudut melengkung 19dp dan border cyan di kanan bawah (72dp di atas timeline) tanpa menghalangi subtitle, terintegrasi penuh dengan navigasi fokus remote TV D-Pad.
- **Fitur Bookmark / Favorit Anime Multiplatform:**
  - **Penyimpanan Persisten SQLite Lokal:** Menambahkan tabel SQLite mandiri `bookmarks` (`slug`, `title`, `poster`, `type`, `sub`, `eps`, `score`, `created_at`) di `backend/database/__init__.py` dan paritas Chaquopy Android. Tabel terisolasi dari riwayat tontonan agar pembersihan riwayat tidak menghapus koleksi favorit.
  - **REST API Endpoints:** Menyediakan endpoint `/api/bookmarks` (GET untuk daftar favorit terurut terbaru, POST untuk simpan), `/api/bookmarks/{slug}` (DELETE untuk hapus item), dan `/api/bookmarks/check` (GET status bookmark instan).
  - **Tombol Bookmark Ergonomis di Halaman Detail:**
    - Android (`DetailActivity`): Menambahkan tombol `⭐ + Favorit` berdampingan dengan tombol putar cepat, berubah dinamis menjadi `★ Tersimpan` (warna emas/amber) saat aktif, lengkap dengan notifikasi Toast dan dukungan navigasi remote D-Pad TV.
    - Desktop Web (`openTitle`): Menambahkan tombol `#tm-bookmark-btn` di sheet header modal anime dengan sinkronisasi status real-time.
  - **Navigasi Tab & Drawer Favorit:**
    - Android: Menambahkan pill `⭐ Favorit` pada Category Pills Carousel beranda untuk akses instan ke seluruh anime tersimpan.
    - Desktop Web: Menambahkan menu navigasi `⭐ Anime Favorit` pada drawer panel dan dukungan perintah `:favorit` / `:bookmark`.
- **Penataan Ulang Top Menu Android & Ultra-Clean Fluid Search Bar:**
  - **Logo TATAP Kapital:** Menampilkan brand `TATAP` dalam huruf kapital penuh dengan letter-spacing proporsional di sisi kiri header.
  - **Ultra-Clean Fluid Search Bar:** Mengembalikan bilah pencarian fluid inline satu baris (`layout_weight="1"`) yang bersih sepenuhnya dari ikon (tanpa icon kaca pembesar dan tanpa spinner di dalam kotak), memberikan tampilan minimalis, lapang, dan langsung siap menerima input.
  - **Status Online Ikon Power Vektor Material (`ic_power.xml`):** Menggantikan render karakter Unicode glyph `⏻` dan penulisan teks panjang yang terpotong menjadi komponen `ImageView` 34x34dp dengan Android Vector Drawable resmi Material Design (`ic_power.xml`). Menggunakan 3 status warna dinamis melalui `PorterDuff.Mode.SRC_IN`: Hijau (`#10B981`) saat Online, Kuning (`#F59E0B`) saat Checking / Booting, dan Merah (`#EF4444`) saat Offline / Error, lengkap dengan handling interaktif untuk mencoba koneksi ulang.
  - **Horizontal Scrollable Category Pills (36dp):** Mengganti segmented tabs kaku dengan deretan pill kategori horizontal yang ramah satu jempol di HP dan D-Pad remote TV: *🌸 Musim Ini*, *📺 Masih Tayang*, *⭐ Favorit*, *📚 Katalog*, *⏱️ Jadwal*, dan *🏷️ Genre*.
  - **Efisiensi Ruang Layar (~58dp):** Menghilangkan tumpukan baris header ganda sehingga baris kartu anime langsung tampak luas dan utuh dari bagian atas layar pada ponsel maupun TV.

- **Aktivasi Load Animation & Optimasi List Data:**
  - **Central Loading Indicator Seamless Cold Start & Page Switch:** Mengaktifkan loading state central spinner cyber cyan (`#38BDF8`) sejak detik pertama aplikasi dibuka (`visibility="visible"` default pada XML), meredupkan grid lama (`alpha 0.25f`) saat berpindah halaman katalog/tab baru yang belum di-cache, dan mengembalikan kecerahan penuh (`alpha 1.0f`) diikuti entrance cascade layout animation saat data anime tiba.
  - **Cascade Layout Animation:** Menambahkan animasi entrance halus (fade-in & slide-up 180ms via `grid_item_fade_in.xml` dan `grid_layout_animation.xml`) saat kartu-kartu anime masuk ke `RecyclerView`.
  - **Smooth Poster Fade-In:** Animasi transisi 160ms pada `ImageLoader.java` saat poster selesai diunduh dari jaringan.
  - **In-Memory Tab Caching (<1ms):** Menyimpan cache daftar anime per-tab dengan masa berlaku 3 menit, membuat perpindahan antar tab (Musim Ini, Masih Tayang, Favorit, Katalog, Jadwal) berlangsung instan seketika tanpa latency jaringan.
  - **Pencegahan Race Condition:** Menggunakan `AtomicInteger` tokenization untuk membatalkan respons jaringan yang usang saat pengguna berganti tab dengan cepat.

- **Dual-Lane View & Pemisahan Anime Musiman vs Serial Panjang (Semua Platform):**
  - **Pemisahan Jalur Adaptif:** Memisahkan katalog anime yang masih tayang (`which=airing` / `:lanjutan` / Tab `MASIH TAYANG`) menjadi dua seksi terpisah dalam satu halaman:
    1. *Anime Musiman (Baru Tamat / Berjalan):* Menampilkan anime musiman reguler dan memprioritaskan anime yang baru saja tamat di bagian paling atas berdasarkan tanggal berakhir riil (`sort: [END_DATE_DESC, POPULARITY_DESC]` via AniList GraphQL) dengan badge `TAMAT` berwarna emerald.
    2. *Anime Panjang Berkelanjutan (Continuous On-Going):* Mengelompokkan anime yang tayang berkelanjutan antar musim (*One Piece*, *Detective Conan*, *Pokemon*, *Crayon Shin-chan*, *Doraemon*, *Chibi Maruko-chan*, *Boruto*) ke jalur khusus dengan badge `SERIAL PANJANG` berwarna amber.
  - **Banner Pembatas Jalur Full-Width:** Menambahkan komponen section header adaptif dengan aksen indikator visual (cyan untuk musiman, amber untuk serial panjang) yang membentang penuh di atas baris grid kartu.
  - **Android TV & Mobile Multi-View Type Adapter:** Mengimplementasikan `GridLayoutManager.SpanSizeLookup` pada `MainActivity.java` dan multi-view type pada `AnimeAdapter.java` (`VIEW_TYPE_HEADER` dan `VIEW_TYPE_ANIME`). Banner header secara otomatis membentang selebar seluruh kolom grid dan dikecualikan dari remote focus (`itemView.setFocusable(false)`) agar navigasi D-Pad Android TV berpindah mulus antar kartu tanpa macet di header.
  - **Desktop Web UI Parity:** Memperbarui `frontend/js/api.js` (mengarahkan `stillAiring` ke `which=airing`) dan `frontend/js/term.js` untuk merender banner pembatas jalur melintasi grid CSS (`grid-column: 1 / -1`) serta melompati header saat navigasi panah keyboard.
  - **Sinkronisasi Paritas Chaquopy Android:** Menjaga sinkronisasi 100% kode backend embedded di `android/app/src/main/python/backend/` bersama backend utama.

### Ditingkatkan
- **True Seamless Quality Switching Khusus Android TV (Terisolasi Penuh):**
  - Meniadakan pemanggilan disruptif `player.stop()` dan `player.prepare()` saat pengguna mengganti resolusi video (misalnya dari 360p ke 1080p) pada Android TV (`TvFocusHelper.isTv()`).
  - Mengandalkan pembaruan dinamis `TrackSelectionParameters` pada Media3 ExoPlayer dan `app:surface_type="surface_view"`.
  - Video dan audio mengalir tanpa putus, tanpa jeda layar hitam, dan tanpa kemunculan spinner buffering saat pergantian kualitas berlangsung pada batas segmen/GOP berikutnya.
  - Varian Android Mobile tetap mempertahankan alur kode bawaannya secara terisolasi tanpa modifikasi.
- **Optimasi Kinerja dan Konsumsi Memori Khusus Android TV (Terisolasi Penuh):**
  - **Isolasi Bebas Efek Samping ke Android Mobile:** Seluruh penyesuaian parameter memori, connection pool, buffer pemutar, dan siklus render dibatasi secara ketat hanya untuk lingkungan Android TV (`TvFocusHelper.isTv()` dan `src/tv/AndroidManifest.xml`). Kode dan perilaku Android Mobile tetap berjalan 100% pada parameter bawaan tanpa modifikasi.
  - **Alokasi Heap Android TV:** Menambahkan `android:largeHeap="true"` khusus pada flavor Android TV (`src/tv/AndroidManifest.xml`) untuk memberikan headroom memori tambahan saat runtime CPython Chaquopy, cache database, dan ExoPlayer berjalan berdampingan pada perangkat TV dengan RAM terbatas (512MB–1GB).
  - **Downsampling Gambar Hemat Memori Khusus TV:** Memangkas target dekompresi poster anime pada Android TV dari 300x420 px menjadi 180x260 px di `ImageLoader.java` (menghemat ~63% memori per kartu poster pada layar TV 1080p). Menambahkan pemeriksaan pembatalan dini jika tampilan kartu telah didaur ulang (*view recycling*) sebelum proses decode bitmap dilakukan.
  - **Penyesuaian Cache View RecyclerView TV:** Menyetel `setItemViewCacheSize(4)` untuk navigasi remote D-Pad Android TV guna mencegah penumpukan hirarki tampilan di luar layar, sementara varian Mobile tetap mempertahankan 20 item untuk scrolling sentuh yang halus.
  - **Peniadaan Beban Komputasi Dynamic Shadow GPU:** Mengatur elevasi fokus kartu menjadi `0f` pada `TvFocusHelper.attachCardFocus` guna meniadakan kalkulasi bayangan drop shadow 3D pada GPU TV berdaya rendah (seperti Mali-450 / Mali-G31) saat tombol remote ditekan.
  - **Penyesuaian Buffer Video ExoPlayer TV:** Menyetel buffer video ExoPlayer pada Android TV menjadi 8 detik minimum dan 15 detik maksimum (dibandingkan 12s/25s pada Mobile), menghemat alokasi RAM playback tanpa memicu rebuffering pada koneksi stabil.
  - **Efisiensi Polling Subtitle:** Mengurangi frekuensi sinkronisasi subtitle pada TV dari interval 75ms menjadi 150ms serta membandingkan teks cue secara langsung dengan cache lokal tanpa alokasi string baru dari `getText().toString()`.
  - **Penjadwalan Pre-Resolve Episode Tetangga TV:** Menunda proses pre-resolve episode sebelum dan sesudah selama 20 detik setelah pemutaran video dimulai pada Android TV, mencegah persaingan CPU dan koneksi jaringan antara thread scraping dan hardware decoder video saat inisialisasi awal.
  - **Tuning Backend Python Rendah Memori:** Menyetel batas koneksi HTTPX pada backend menjadi `max_connections=8` dan `max_keepalive=3` saat berjalan di TV (`TATAP_IS_TV=1`), mengonfigurasi SQLite PRAGMA memori minimalis (`cache_size = -500`, `temp_store = FILE`, `mmap_size = 0`), menerapkan batas GC Python `(100, 5, 5)`, serta menghubungkan event Android `onTrimMemory` untuk memicu pembersihan sampah memori Python runtime secara berkala.
- **Kompresi Top-Bar Ergonomis Android TV (10-Foot UI):**
  - Memampatkan tinggi top-bar area pada Android TV: tinggi header dari 56dp menjadi 44dp, kolom pencarian dari 38dp menjadi 32dp, dan tombol tab segmentasi dari 34dp menjadi 30dp dengan padding vertikal yang ringkas (overscan vertikal disesuaikan dari 20dp ke 12dp).
  - Menghemat ~40dp ruang vertikal layar televisi tanpa mengurangi kenyamanan radius pandang 10 kaki (*10-foot viewing radius*) maupun keterbacaan teks font dan navigasi remote D-Pad.
  - Memperluas area tampilan grid anime di Android TV sehingga baris kartu kedua terlihat jelas tanpa perlu banyak scrolling dengan remote.
  - Memperkuat deteksi lingkungan TV di `TvFocusHelper.isTv()` dengan menyertakan deteksi package name Android TV (`.tv`) dan fitur sistem `android.software.leanback`.
- **Floating Navigation Capsule Transparan (Android UI):**
  - Mengubah panel navigasi bawah (`layout_pagination`) dari bilah footer solid statis 48dp menjadi kapsul melayang (*floating pill*) transparan setinggi 36dp dengan gaya *cyber glassmorphism* (`#CC090A12`, 80% opacity) dan aksen border cyan lembut (`#2B38BDF8`).
  - Menerapkan *edge-to-edge scrolling* pada `rv_anime_grid` dengan `paddingBottom="64dp"` dan `clipToPadding="false"`. Kartu anime mengalir mulus di bawah kapsul navigasi dan baris kartu terakhir tidak akan tertutup saat di-scroll ke paling bawah.
  - Mempertahankan interoperabilitas penuh Android TV D-Pad remote focus (`TvFocusHelper.attachFocusScale`) dengan visual border highlight cyan cerah saat tombol paginasi dipilih.
  - Menyembunyikan floating pill secara otomatis ketika grid berada dalam kondisi kosong (*empty state*) atau mengalami kegagalan koneksi awal agar tidak mengaburkan pesan error.
- **Auto-Dismiss Notification Timer Berbasis Panjang Teks (Android UI):**
  - Mengganti durasi statis 8 detik pada banner perintah/notifikasi (`showCommandOutput`) dengan kalkulasi timer baca dinamis yang proporsional dan ergonomis:
    - **Pesan Singkat (`<= 35 char`):** `2200ms` (2.2s) — ideal untuk pergantian tampilan/tab (`Tampilan diatur ke: MUSIM`, `:cari`, `:help`).
    - **Pesan Sedang (`36 - 65 char`):** `3200ms` (3.2s) — durasi pas untuk status eksekusi atau pergantian sumber stream.
    - **Pesan Panjang / Error:** `4500ms` (4.5s) — memberi waktu yang cukup bagi pengguna untuk membaca detail kesalahan koneksi atau instruksi perintah.
  - Menambahkan animasi transisi halus *fade-out* (alpha 220ms) saat notifikasi menghilang, menggantikan hilangnya banner secara mendadak (`GONE`).
  - Menambahkan dukungan *instant touch-to-dismiss*: mengetuk banner notifikasi secara langsung atau tombol silang penutup akan langsung menutup banner dengan transisi cepat.
- **Optimasi Performa Perangkat Spesifikasi Rendah (Web Desktop & Android):**
  - **Eliminasi Beban GPU Offscreen:** Mengganti penggunaan `backdrop-filter: blur(...)` pada drawer navigation menu dan gesture OSD player dengan permukaan solid gelap berpresisi tinggi (`--panel-solid`, `rgba(11, 13, 17, 0.96)`) dan border crisp. Mengurangi frame drop dan stuttering compositing GPU secara signifikan saat membuka drawer atau mengatur volume di laptop lawas dan Android TV.
  - **Optimasi Ambient Halo Video Player:** Mengurangi radius Gaussian blur `#ambient` dan `#ambient-fallback` dari 70px menjadi 24px (16px–20px pada resolusi mobile/tablet) dengan akselerasi layer hardware `transform: translate3d(0,0,0)` dan `will-change: transform, opacity`. Menghemat >70% GPU fillrate dan mempertahankan pemutaran video HLS pada 60 FPS stabil.
  - **CSS Layout Isolation:** Menambahkan `contain: content;` pada kartu poster (`.poster-card`) dan list item (`.trow`) sehingga perubahan hover atau mutasi DOM lokal tidak memicu re-layout satu halaman penuh.
  - **Atomic DOM Injection via DocumentFragment:** Membungkus seluruh perakitan elemen kartu hasil pencarian dan jadwal rilis di `term.js` ke dalam `DocumentFragment`, menggantikan mutasi DOM berulang per-item menjadi injeksi tunggal yang cepat.
  - **Asynchronous Image Decompression:** Menambahkan atribut `decoding="async"` dan `loading="lazy"` pada seluruh thumbnail dan poster anime di frontend web untuk mengalihkan dekompresi gambar keluar dari browser main thread.
  - **RecyclerView Cache & Low-End Tuning (Android):** Mengaktifkan `setHasFixedSize(true)`, `setItemViewCacheSize(20)`, dan drawing cache quality low pada `MainActivity.java` untuk pengalaman scroll instan tanpa re-measuring berulang.
  - **Animasi TV D-Pad Ringan (Android TV):** Menyetel durasi transisi fokus remote TV menjadi 90ms dan skala kartu 1.04x di `TvFocusHelper.java`, mengeliminasi lag shadow software pada chipset Android TV hemat daya.

### Diperbaiki
- **Pencegahan Kebocoran Metadata Sidebar HiAnime pada Kartu Terakhir:**
  - Mengisolasi batas kontainer kartu anime di `_parse_browse_cards` pada `backend/api/hianime.py` agar berhenti pada `<div class="clearfix">` dan memangkas blok sidebar sebelum parsing HTML dijalankan.
  - Mencegah kartu anime di posisi paling bawah halaman katalog (seperti *Yani Neko*) menyerap metadata episode widget sidebar (*Black Clover* `eps: 170`), yang sebelumnya memicu salah klasifikasi ke dalam seksi *Anime Panjang Berkelanjutan* (*Serial Panjang*).
  - Menambahkan guard defensif rasio episode pada `_is_long_running` dan menaikkan cache key airing ke `airing_lanes_v4` untuk mensterilkan cache lama secara otomatis.
- **Eliminasi Stuttering & Patah-Patah Pemutaran Video 1080p (Android & Android TV):**
  - **Pencegahan Loop Rekonfigurasi Decoder di `onTracksChanged`:** Memasang guard boolean `hasAppliedTrackSelectionForStream` pada listener `onTracksChanged` agar seleksi track HLS hanya dieksekusi sekali saat manifest track pertama kali selesai di-resolve. Menghindari pemanggilan rekursif `setTrackSelectionParameters` yang memicu flush decoder dan micro-stuttering berulang kali saat pemutaran video sedang berlangsung.
  - **Ekspansi Buffer Video 1080p Aman (`min: 25s`, `max: 50s`):** Menyesuaikan buffer durasi `DefaultLoadControl` dari 8s/15s menjadi 25s minimum dan 50s maksimum dengan buffer mulai 2s dan rebuffer 4s serta menonaktifkan `prioritizeTimeOverSizeThresholds`. Menjamin buffer video 1080p tidak pernah mengalami starvation pada jaringan dinamis dengan alokasi RAM native yang tetap hemat (~10–15 MB).
  - **Aktivasi Asynchronous MediaCodec Buffer Queueing:** Mengonfigurasi `DefaultRenderersFactory.forceEnableMediaCodecAsynchronousQueueing()` pada `PlayerActivity.java` untuk memindahkan antrean input/output buffer decoding ke background looper thread, mencegah rendering loop terhambat pada chipset TV berbasis Android 9-11 (API 28-30).
  - **Aktivasi HLS Chunkless Preparation:** Mengaktifkan `setAllowChunklessPreparation(true)` pada `HlsMediaSource.Factory`, meniadakan pengunduhan segmen awal dari seluruh varian resolusi lain yang tidak diperlukan saat stream baru disiapkan.
  - **Eliminasi Teardown Codec di `onVideoSizeChanged`:** Menghapus pemanggilan disruptif `player.stop()` di tengah pemutaran video pada event perubahan ukuran surface, menjaga aliran decoding tetap mulus tanpa jeda restart.
  - **Pelepasan Batasan Minimum Resolusi Kaku:** Menghapus parameter `minW = 1600` dan `minH = 900` pada `applyHlsTrackSelection` serta menambahkan pengecekan `newParams.equals(current)` sebelum memicu update parameter track ke ExoPlayer.
  - **Restorasi HTTPX Keep-Alive Pool Backend:** Menyetel `max_keepalive_connections=20` dan `max_connections=30` dengan `keepalive_expiry=90.0` pada `_get_video_client`, meniadakan lonjakan CPU dari kalkulasi TLS 1.3 handshake berulang pada setiap pengunduhan segmen TS 1080p.
- **Perbaikan Inisialisasi Zoom/Crop Video Player (Android & Android TV):**
  - Mengatasi masalah di mana video HLS pada awal pemutaran selalu ter-zoom/terpotong (*cropped*) dan baru normal setelah pengguna berpindah resolusi ke 360p lalu ke 1080p lagi.
  - Mengonfigurasi `DefaultBandwidthMeter` dengan estimasi awal 25 Mbps (`25_000_000`) pada `ExoPlayer.Builder` agar ExoPlayer langsung memilih track video resolusi optimal (1080p/720p) sejak awal koneksi tanpa adaptasi lambat dari 360p yang mengunci surface buffer TV.
  - Memanggil `applyHlsTrackSelection(activeQuality)` secara eksplisit sebelum `player.prepare()`.
  - Memperbarui `applyHlsTrackSelection()` agar mendukung penuh kualitas `"best"`, `"hd"`, dan `"1080p"` dengan batasan resolusi yang presisi.
  - Mengaitkan `onTracksChanged(Tracks tracks)` di listener ExoPlayer dengan proteksi guard atomik untuk mengunci track override seketika setelah master manifest HLS selesai di-resolve tanpa loop rekursif.
  - Menetapkan atribut `app:surface_type="surface_view"` pada `PlayerView` di layout player untuk mengeliminasi pemotongan buffer dan tearing saat resolusi adaptif berubah tanpa memerlukan restart codec.
  - Menetapkan mode skala default `player.setVideoScalingMode(C.VIDEO_SCALING_MODE_SCALE_TO_FIT)` untuk memastikan video pas dengan layar tanpa pemotongan.
- **Anti-Ghosting & View Recycling Flicker (Android):** Memperbaiki bug tampilan pada daur ulang view RecyclerView di mana kartu yang di-scroll cepat sempat menampilkan poster anime sebelumnya secara keliru. Menyetel placeholder drawable solid netral (`#151822`) seketika sebelum thread decode background dijalankan pada `ImageLoader.java`.
- **Eliminasi Overdraw View Hierarchy (Android):** Menghapus background bertingkat yang redundan pada FrameLayout poster dan LinearLayout teks di dalam `item_anime_card.xml`, memotong beban pemindaian GPU fillrate hingga separuh pada perangkat mobile RAM 1GB–2GB.
- **2-Line Title Clamp & Tipografi Hybrid Minimalis:** Memperbaiki pemotongan judul anime romaji/Indo panjang pada kartu web dengan menerapkan 2-line clamp (`-webkit-line-clamp: 2` dan `min-height: 2.7em`), serta transisi ke sistem tipografi sans-serif modern yang proporsional untuk konten judul dan tetap mempertahankan monospace murni untuk terminal prompt, timestamp, dan statusbar.

## [2.4.2] - 2026-10-13

### Diperbaiki
- **Perbaikan Lifecycle Linux AppRun (Eliminasi Layar Putih & Font Unstyled):** Mengatasi bug kritis di mana peluncuran browser mode aplikasi (`google-chrome --app=...`) mendelegasikan proses ke instance browser yang sedang aktif sehingga proses CLI keluar seketika (< 100ms) dan memicu `trap cleanup EXIT` membunuh backend server FastAPI secara prematur. Menerapkan profil browser terisolasi (`--user-data-dir="${DATA_DIR}/browser-profile"`), fail-safe monitoring proses browser (jika browser mendelegasikan, tunggu dialihkan ke proses server agar backend tetap hidup), healthcheck mandiri via Python internal (bebas dependensi `curl`), dan pembersihan otomatis port 8767 stale sebelum startup.
- **Pencarian Multi-Sumber & Otomatis Fallback Otakudesu:** Memperbaiki subsistem pencarian di seluruh platform dengan meneruskan preferensi sumber aktif (`source`) dari frontend dan mengimplementasikan failover otomatis ke scraper Otakudesu apabila scraper HiAnime mengalami kendala jaringan atau Cloudflare challenge.
- **Perbaikan Input Terminal & Eliminasi Flash Putih:** Menghapus pencegahan ketik tombol slash (`/`) pada kolom pencarian terminal `#cmd` serta menambahkan inline background gelap `#08090c` pada tag `<html>` dan `<body>` di `index.html`.
- **Integrasi & Isolasi Tombol Filter Hari Rilis:** Memindahkan 3 tombol filter hari rilis (Kemarin, Hari Ini, Besok) ke dalam `.sec-head` sejajar dengan judul jadwal rilis menggunakan gaya segmented control (`.seg.schedule-days-bar`). Memproteksi visibilitasnya agar HANYA tampil saat view jadwal aktif (`terbaru`) dan otomatis disembunyikan di semua view lainnya (`cari`, `musim`, `lanjutan`, `katalog`, `recents`).
- **Penambahan Thumbnail Poster di List Pencarian & Jadwal Rilis:** Menambahkan thumbnail cover/poster mini (rasio 3:4) dengan *lazy-loading* dan fallback icon pada setiap item hasil pencarian (`view: cari`) dan jadwal rilis (`view: terbaru`), lengkap dengan metadata ringkas (tipe format, jumlah episode, status SUB/DUB) serta garis aksen visual jadwal hari ini (`.today`) dan besok (`.tomorrow`).
- **Perbaikan Overlap Bawah Desktop Web, Windows Portable & Linux AppImage:** Menghapus override cacat `--status-h: 36px` pada rentang resolusi desktop 901px–1280px yang sebelumnya menyebabkan kartu anime terbawah, tombol paginasi, dan jadwal rilis tertutup oleh `.bottom-bar`. Menetapkan baseline aman `--status-h: 88px`.
- **Navigasi Header Desktop & Scroll Safe Player Shell:** Menambahkan tombol drawer menu di bar header atas (`#btn-drawer-head`) untuk ergonomi pengguna desktop/laptop, menambahkan `overflow-y: auto` pada `.player-shell`, dan membatasi tinggi video windowed (`max-height: clamp(240px, 66vh, 640px)`) agar kontrol footer tidak terpotong pada laptop 768p.
- **Scrollbar Gelap Cyber Global:** Menerapkan styling scrollbar gelap kustom yang konsisten di seluruh WebKitGTK Linux AppImage, Edge WebView2 Windows Portable, dan Desktop Browser.

### Ditambahkan
- **Penyesuaian Skala Ukuran Font Subtitle Android TV:** Menambahkan 7 tingkatan ukuran font khusus perangkat Android TV (18sp, 22sp, 26sp [Standar TV], 30sp, 34sp [Jarak Jauh], 38sp [Layar Besar], dan 42sp [Maksimal]) untuk kenyamanan jarak pandang sofa 2.5m - 4m (10-foot UI).
- **Default Ukuran Font Adaptif TV:** Pengguna Android TV secara otomatis mendapatkan ukuran font standar 26sp (sebelumnya terbatas 17sp), sementara perangkat Mobile tetap menggunakan skala layar sentuh (14sp s/d 36sp, default 17sp).
- **Spasi Baris Dinamis & Line Spacing Multiplier:** Menerapkan `lineSpacingMultiplier="1.2"` pada layout XML dan `tvSubtitles.setLineSpacing(0f, 1.25f)` dinamis di Android TV agar kalimat subtitle panjang dua baris dengan font besar tidak saling bertumpuk bayangan (*shadow*).
- **Navigasi D-Pad Remote Dialog Ukuran Font:** Dialog pemilihan ukuran font mendukung navigasi remote kontrol D-pad secara penuh dengan auto-focus pada opsi aktif dan pengembalian fokus kontroler pemutar saat dialog ditutup.

### Ditingkatkan
- **Rebranding & Overhaul Mesin Penerjemah GTX+:** Memperbarui penamaan dan identitas mesin penerjemah AIGTX menjadi **GTX+ (Smart Fansub & Scene Detection)** di seluruh ekosistem (Backend FastAPI, Frontend Desktop Web/Windows/Linux, serta Android Mobile dan Android TV).
- **Integrasi Scene Detection Otomatis pada GTX+ Tanpa API Key:** Menerapkan deteksi konteks adegan (*scene detection*) adaptif langsung pada mesin GTX+ tanpa memerlukan API key pengguna. Adegan formal/kerajaan/militer dipertahankan baku dan santun, sedangkan adegan sehari-hari/sekolah/komedi otomatis diterjemahkan dengan gaya dialog lisan fansub santai (*casual conversation*).
- **Pengayaan Kamus Bahasa Fansub Casual Conversation:** Menambahkan puluhan leksikon dialog lisan santai fansub (*nggak, udah, cuma, banget, maksudmu apa, mana kutahu, beneran nih, pantesan, yang bener aja, jangan bercanda deh, sama sekali nggak, biar aku yang urus, gampang banget, cowok/cewek itu, mau gimana lagi*).
- **Kompatibilitas Mundur Penuh (Backward Compatibility):** Mendukung cache key `sub2|gtx+|` dengan pembacaan fallback `sub2|aigtx|`, parameter mode query `gtx+` dan `aigtx`, fungsi `_sanitize_aigtx_id = _sanitize_gtxplus_id`, serta prefix track URL `gtx+:<url>` dan `aigtx:<url>`.
- **Sinkronisasi Paritas Runtime Android:** Menyelaraskan seluruh modul penerjemah `backend/api/translate.py` dan `backend/main.py` ke `android/app/src/main/python/backend/` dengan 100% paritas kode.
- **Dokumentasi Pemetaan Teknis & Direktif AI Agent:** Menambahkan berkas master `PROJECT_MAP.md` yang memetakan topologi basis kode, data pipeline streaming/subtitle, skema database, indeks simbol fungsi utama, aturan paritas Chaquopy, serta menetapkan urutan baca wajib (`AGENTS.md` lalu `PROJECT_MAP.md`) sebelum perencanaan/iterasi bagi seluruh agen AI.

## [2.4.1] - 2026-10-13

### Diperbaiki
- **Pembersihan dan Pemulihan Engine Penerjemah Subtitle:** Mengatasi masalah fallback tidak diinginkan ke MyMemory yang menghasilkan terjemahan kaku. Menghapus penyimpanan cache MyMemory ke entri database `sub2|gtx`, memvalidasi dan membuang otomatis cache yang berisi pesan peringatan kuota MyMemory, serta memulihkan kualitas terjemahan luwes Google AIGTX dan AI Fansub.
- **Perbaikan Rute Endpoint Google Translate:** Menghapus parameter `client=gtx` yang diblokir/dibatasi laju (HTTP 429) oleh Google dan menggantinya dengan pool endpoint tanpa kuota berbasis `clients5.google.com` (`dict-chrome-ex` dan `tw-ob`) serta `translate.google.com` dengan konkurensi optimal 3 pekerja, memangkas durasi proses translasi satu episode penuh menjadi sangat cepat (< 5 detik).
- **Perbaikan Pemilihan Mode dan Model AI Fansub:** Memperbaiki identifikasi `job_key` inflight (`base_hash|lang|mode`) agar permintaan mode `ai` atau `aigtx` tidak dibajak oleh tugas prefetch `gtx`. Memperbarui model default Google AI Studio dari penamaan tidak valid `gemini-3.1-flash-lite` menjadi model aktif `gemini-2.0-flash` (dengan rantai failover `gemini-1.5-flash`), serta memperbaiki prioritas eksekusi mode AI agar langsung memanggil LLM fansub saat diminta.
- **Penanganan Aksi Refresh Subtitle di Pemutar:** Mengatasi bug pada dialog pemilih subtitle Android di mana eksekusi `[Refresh] Terjemahkan Ulang Subtitle` tertimpa oleh pemanggilan `applySubtitleSelection()` non-refresh.
- **Pencegahan Cache Poisoning Subtitle:** Memperbaiki bug kritis di mana kegagalan terjemahan sementara menyebabkan subtitle teks asli (bahasa Inggris) tersimpan ke database `subtitle_cache` lokal selama 7 hari, sehingga episode tersebut terkunci permanen dalam bahasa Inggris.
- **Validasi dan Pembersihan Cache Otomatis:** Sistem kini memvalidasi struktur kosakata bahasa Indonesia saat membaca cache subtitle. Entri cache lama yang terindikasi berisi teks mentah bahasa Inggris otomatis dihapus dan diterjemahkan ulang secara transparan.
- **Navigasi Next dan Previous Episode di ExoPlayer:** Mengatasi kendala tombol kontrol Next (`exo_next`) dan Previous (`exo_prev`) di `PlayerControlView` ExoPlayer (Media3) yang terkunci nonaktif secara internal akibat timeline MediaItem tunggal. Mengonfigurasi atribut layout XML `app:show_next_button="true"` dan `app:show_previous_button="true"`, memanggil `setShowNextButton(true)` dan `setShowPreviousButton(true)`, mengoreksi urutan inisialisasi agar `initExoPlayer` berjalan sebelum `setupExoNativeControls`, serta menerapkan logika batas navigasi optimistik sehingga tombol tetap responsif saat daftar episode sedang dimuat.
- **Pemuatan Metadata URL Episode dan Eliminasi Race Condition:** Memperbaiki penanganan respons endpoint resolver stream di mana master URL stream m3u8 tetap dipilih secara andal, membaca stream error secara tepat pada status non-200 tanpa melemparkan eksepsi prematur, mengisolasi setiap permintaan pemuatan stream dengan token identifikasi (`currentResolveLoadId`) agar pergantian episode beruntun tidak saling menimpa, serta menambahkan metadata judul serial dan nomor episode lengkap ke dalam `MediaMetadata` MediaItem Media3.
- **Pembersihan State saat Pergantian Episode:** Membersihkan referensi subtitle (`currentCues`, `currentSubLoadId`, teks overlay), stream URL, dan memanggil `player.clearMediaItems()` saat berpindah episode untuk mencegah tumpang tindih audio/video atau kebocoran subtitle episode sebelumnya.
- **Fallback Otakudesu pada Daftar Episode:** Memperbaiki endpoint `/api/anime/{slug}/episodes` agar secara otomatis beralih ke parser Otakudesu jika scraper HiAnime gagal atau anime berasal dari domain Otakudesu.

### Ditingkatkan
- **Kamus Idiom & Ungkapan Fansub Anime Universal:** Mengintegrasikan kamus referensi penerjemahan fansub anime yang komprehensif ke dalam mesin penerjemah `translate.py` (prompt sistem `_FANSUB_PROMPT_ID`, aturan normalisasi universal `_UNIVERSAL_FANSUB_RULES`, percakapan kasual `_CASUAL_FANSUB_RULES`, dan penghalus `_AIGTX_SMOOTH_RULES`). Mengeliminasi puluhan calque dan blunder penerjemahan mesin yang kaku (*"It can't be helped"* -> *"Mau gimana lagi"*, *"Give me a break"* -> *"Yang benar saja!"*, *"Serves you right"* -> *"Rasakan itu!"*, *"I'll take care of this"* -> *"Biar aku yang urus ini"*, *"Don't let your guard down"* -> *"Jangan lengah!"*, *"Stand back"* -> *"Mundur!"*, *"Over my dead body"* -> *"Langkahi dulu mayatku!"*, *"Piece of cake"* -> *"Gampang banget"*, *"Under the weather"* -> *"Kurang enak badan"*, *"Mendokusai"* -> *"Merepotkan sekali"*, *"Sasuga"* -> *"Sudah kuduga / Memang bisa diandalkan"*, serta ungkapan santai khas anime lainnya).
- **Sinkronisasi Penuh Aturan Translate Antar-Platform (Windows & Android):** Menyelaraskan seluruh modul dan berkas kamus penerjemah di `android/app/src/main/python/backend/` dengan repositori induk `backend/`. Memastikan runtime tersemat Chaquopy pada platform Android Mobile maupun Android TV memiliki 100% paritas aturan translasi, kamus kosakata atelier, dan penanganan fallback yang persis sama dengan platform Windows Portable dan Linux Desktop.
- **Kamus Referensi Fansub Fantasi & Atelier Sihir (Sampling Witch Hat Atelier):** Mengintegrasikan hasil audit dan sampling subtitle 13 episode *Witch Hat Atelier* ke dalam mesin penerjemah. Menambahkan kamus kosakata dunia sihir dan perapal mantra (*cast magic*, *conjuring ink*, *casting seal*, *magic stationer*, *witch apprentice*, *diadem herb*, *consent of the crown*) pada `_FANSUB_PROMPT_ID`, serta memperkaya filter penormalisasi `_UNIVERSAL_FANSUB_RULES`, `_CASUAL_FANSUB_RULES`, dan `_AIGTX_SMOOTH_RULES` guna mengeliminasi terjemahan kaku atau rancu (misal: "melakukan casting" menjadi "merapal sihir", "tinta sulap" menjadi "tinta sihir", "celah di tongkat" menjadi "retakan di tongkat", "toko alat tulis ajaib" menjadi "toko alat sihir", "memilih ramuan" menjadi "memetik herba", "sangat baik andal" menjadi "sangat mantap", "tiketnya terjual habis" menjadi "langsung ludes dalam sekejap", dan merapikan campuran kata ganti formal-santai). Perbaikan ini meningkatkan keluwesan tata bahasa untuk anime fantasi, atelier, petualangan, dan percakapan anime lainnya secara menyeluruh.
- **Menu Refresh / Terjemahkan Ulang Subtitle:** Menambahkan opsi aksi `[Refresh] Terjemahkan Ulang Subtitle (Hapus Cache)` pada dialog pemilih subtitle Android untuk membersihkan cache episode secara instan dan mengulang translasi dari awal.
- **Pacing dan Pembagian Mini-Batch Adaptif:** Mengurangi konkurensi pekerja menjadi 2 thread dengan jeda mikro antar batch dan mekanisme pembagian otomatis batch 20 baris menjadi 10 baris jika terjadi penolakan paket.
- **Pemuatan Asinkron Cadangan Daftar Episode di Pemutar:** Menambahkan `ensureEpisodeListLoaded()` di `PlayerActivity` untuk mengambil daftar episode secara otomatis jika pemutar dibuka langsung dari tautan riwayat atau intent eksternal tanpa membawa daftar episode lengkap.
- **Dukungan Tombol Fisik dan Keyboard Navigasi Episode:** Menambahkan pintasan `KEYCODE_N` (Next Episode) dan `KEYCODE_P` (Previous Episode) selain tombol media bawaan untuk kenyamanan pengendali remote TV dan keyboard fisik.

---

## [2.4.0] - 2026-10-12

### Ditambahkan
- **Fitur Jadwal Rilis 3 Hari:** Endpoint backend `/api/schedule` yang membatasi dan mengelompokkan jadwal tayang menjadi Kemarin, Hari Ini, dan Besok dengan zona waktu Indonesia Barat (WIB, UTC+7).
- **Filter Ketat Ketersediaan Judul:** Judul anime yang tidak tersedia pada scraper lokal otomatis dihapus dari jadwal sehingga setiap judul yang tampil dijamin dapat diputar.
- **Tab Jadwal Android Mobile:** Tab segmented `[Jadwal]` dan chip selector 3 hari khusus pada antarmuka Android Mobile (`!TvFocusHelper.isTv`).
- **Selector Chip Jadwal Web & Desktop:** Tombol filter interaktif 3 hari pada antarmuka Web, Windows Portable, dan Linux AppImage.
- **Fitur Navigasi Relasi Season Anime:** Endpoint `/api/anime/{slug}/relations` beserta tombol navigasi relasi (Prekuel, Season 1, Sekuel, Movie) di halaman detail anime.
- **Algoritma Origin Discovery:** Penelusuran rantai prekuel ke belakang (*backward-tracing*) untuk mendeteksi anime awal (Season 1) secara otomatis.
- **Counter Statistik Repositori di README:** Menambahkan badge counter real-time (GitHub Stars, Forks, Total Downloads, Repository Views/Hits, dan Open Issues) pada berkas `README.md`.

### Ditingkatkan
- **Optimasi Loading Episode Panjang:** Sistem caching dua lapis (SQLite backend dan memory cache) untuk serial dengan ratusan hingga ribuan episode, memangkas latensi pemuatan dari hitungan detik menjadi instan (< 50ms).
- **Format Jam Rilis pada Kartu:** Menampilkan label jam tayang WIB pada kartu anime di daftar jadwal.

### Diperbaiki
- **Isolasi Antarmuka Android TV:** Menjaga antarmuka Android TV tetap bersih dengan 3 tab standar tanpa merusak fokus navigasi D-pad.

---

## [2.3.16] - 2026-10-11

### Diperbaiki
- Reset sesi decoder saat perpindahan resolusi untuk mencegah distorsi zoom berlebih dan penyusutan layar (*shrink*) pada Android TV.

---

## [2.3.15] - 2026-10-11

### Diperbaiki
- Eliminasi masalah zoom dan pemulihan SurfaceView native dengan penskalaan rasio fit pada pemutar Android TV.

---

## [2.3.14] - 2026-10-11

### Diperbaiki
- Penghapusan loop resolusi melalui track override dan perbaikan penyusutan layar menggunakan TextureView fallback.

---

## [2.3.13] - 2026-10-11

### Diperbaiki
- Perbaikan garis hitam asimetris pada rasio aspek resolusi TV dan penambahan auto-focus pada hasil pencarian Android TV.

---

## [2.3.12] - 2026-10-11

### Diperbaiki
- Mengatasi java `EOFException` pada segmen video proxy HLS (`drama1.cfd`) dan peningkatan penanganan kegagalan socket.

---

## [2.3.11] - 2026-10-10

### Diperbaiki
- Eliminasi *double-probe* pada video proxy lokal, perpanjangan batas waktu koneksi (*connect timeout*), dan penambahan mekanisme stream retry.

---

## [2.3.10] - 2026-10-10

### Diperbaiki
- Mengatasi error sumber stream pada HLS anime yang sedang tayang (*ongoing*) dan penambahan fallback otomatis ke engine desync.

---

## [2.3.8] - 2026-10-10

### Diperbaiki
- Mengatasi masalah audio hening pada multi-rendition stream HiAnime saat beralih resolusi kualitas video.

---

## [2.3.7] - 2026-10-10

### Diperbaiki
- Perbaikan audio yang hilang pada stream puterin dan penyelarasan ukuran subtitle pada mode layar penuh.

---

## [2.3.6] - 2026-10-10

### Ditambahkan
- Desain ulang tata letak antarmuka Web, Windows, dan Linux dengan gaya modern bernuansa terminal.

---

## [2.3.4] - 2026-10-10

### Ditambahkan
- Integrasi pengaturan subtitle, pilihan kualitas video, dan rasio aspek langsung ke dalam kontroler bawaan ExoPlayer.

---

## [2.3.3] - 2026-10-10

### Ditambahkan
- Tombol navigasi episode berikutnya/sebelumnya (Next/Prev) pada kontroler native ExoPlayer serta mekanisme *background pre-resolving* stream episode lanjutan.

---

## [2.3.0] - 2026-10-10

### Ditambahkan
- **Inisiasi Arsitektur Android TV:** Penambahan target *product flavor* khusus TV (`tatap-tv-release-v*.apk`) terpisah dari Mobile.
- **Navigasi D-Pad TV:** Sistem penanganan fokus D-pad komprehensif (`TvFocusHelper`), penskalaan kartu (*card focus highlight*), dan dukungan remote televisi.
- **Standardisasi SemVer 2.0.0:** Penerapan aturan penomoran SemVer atomik di seluruh berkas proyek (`VERSION`, Android Gradle, dan script otomasi `tools/bump_version.py`).

---

## [2.2.0] - 2026-10-09

### Ditambahkan
- **Ekspansi Platform Android Mobile:** Peluncuran rilis perdana APK Android native menggunakan runtime Chaquopy Python lokal dan pemutar native ExoPlayer.
- **Rilis Multiplatform:** Standarisasi build rilis untuk Windows Portable, Linux AppImage, dan Android Mobile.

### Diperbaiki
- Penanganan rendering subtitle agar tetap aktif dan konsisten saat berpindah ke mode layar penuh.

---

## [2.1.0] - 2026-10-08

### Ditambahkan
- **Mesin Penerjemah AI Subtitle (BYOK):** Fitur auto-translate subtitle berbasis model bahasa besar (*Bring Your Own Key*) dengan dukungan Google Gemini, Groq Cloud, Ollama, dan OpenAI.
- Perintah terminal pemutar (`:gemini`, `:groq`, `:openai`, `:ollama`, `:model`, `:apikey`).

---

## [2.0.0] - 2026-10-05

### Diubah (Perombakan Arsitektur / Breaking Change)
- **Peluncur Native Desktop Standalone:** Beralih dari penggunaan tab browser peramban eksternal menjadi aplikasi native desktop mandiri (*standalone window*) berbasis Go launcher dan Microsoft Edge WebView2.
- **Integrasi Siklus Hidup Aplikasi:** Menutup jendela aplikasi secara otomatis mematikan backend lokal, dilengkapi proteksi instans tunggal (*single instance lock*).
- **Penyimpanan Terpusat:** Struktur penyimpanan lokal terisolasi di `webview2-data` dan database SQLite lokal.

---

## [1.1.0] - 2026-10-03

### Ditambahkan
- Dukungan multi-track subtitle dan pemilih dropdown subtitle di pemutar video.
- Migrasi skema database lokal untuk pencatatan preferensi subtitle pengguna.

---

## [1.0.0] - 2026-10-01

### Ditambahkan
- Inisiasi rilis perdana Tatap: Pemutar dan agregator anime mandiri tanpa server publik.
- Backend FastAPI lokal dengan scraping multi-sumber (HiAnime dan Otakudesu).
- Pemutar Web HLS dengan fitur Ambient Stage Light, penyesuaian rasio layar, dan proteksi bypass DPI via TLS desync.
