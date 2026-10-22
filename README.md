# Info-Bot

Info-Bot meneruskan postingan baru dari akun X (Twitter), akun Instagram, dan feed RSS ke channel Discord. Satu channel Discord bisa memantau banyak sumber, dan bot melayani banyak channel sekaligus. Bot berjalan otomatis di GitHub Actions tiap 5 menit, jadi komputer Anda tidak perlu menyala.

Contoh pemakaian: channel `#footballinfo` menerima postingan Fabrizio Romano, channel `#valorantinfo` menerima postingan akun resmi Valorant, dan channel `#newsinfo` menerima berita dari BBC dan Antara.

## Daftar isi

- [Isi repositori](#isi-repositori)
- [Cara kerja](#cara-kerja)
- [Yang dibutuhkan](#yang-dibutuhkan)
- [Pemasangan](#pemasangan)
- [Mengatur channel dan sumber](#mengatur-channel-dan-sumber)
- [Daftar secret](#daftar-secret)
- [Menjalankan dan memeriksa hasil](#menjalankan-dan-memeriksa-hasil)
- [Menjalankan di komputer sendiri](#menjalankan-di-komputer-sendiri)
- [Pemecahan masalah](#pemecahan-masalah)
- [File yang dibuat program](#file-yang-dibuat-program)
- [Keamanan dan privasi](#keamanan-dan-privasi)
- [Cara memperbarui dan menghapus](#cara-memperbarui-dan-menghapus)
- [Batasan yang diketahui](#batasan-yang-diketahui)

## Isi repositori

| Nama | Fungsinya |
|------|-----------|
| `social_to_discord.py` | Program utama. Berisi daftar channel dan sumber (`CHANNELS`), pembaca feed, dan pengirim pesan ke Discord. |
| `.github/workflows/social.yml` | Jadwal otomatis di GitHub Actions. Menyalakan RSSHub, menjalankan program, lalu menyimpan `seen.json`. |
| `seen.json` | Catatan postingan yang sudah dilihat. Dibuat otomatis oleh bot, tidak perlu dibuat sendiri. |

## Cara kerja

1. GitHub Actions menjalankan `social.yml` tiap 5 menit (jadwal GitHub bisa molor beberapa menit).
2. Workflow menyalakan **RSSHub** di dalam runner. RSSHub adalah layanan sumber terbuka yang mengubah akun X dan Instagram menjadi RSS.
3. `social_to_discord.py` membaca setiap sumber di `CHANNELS`: akun X dan Instagram lewat RSSHub, feed RSS langsung dari situsnya.
4. Postingan yang belum ada di `seen.json` dikirim ke webhook channel yang sesuai.
5. Workflow menyimpan `seen.json` kembali ke repositori, supaya postingan yang sama tidak dikirim dua kali.

Aturan yang perlu diketahui:

- **Sumber baru hanya ditandai, tidak dikirim.** Saat sebuah sumber pertama kali dibaca, semua postingan yang sudah ada dicatat sebagai sudah dilihat. Pesan baru muncul dari run berikutnya. Ini mencegah channel dibanjiri postingan lama.
- **Maksimal 5 pesan per sumber per pengecekan** (`MAX_PER_SOURCE`). Postingan lebih lama di luar 5 itu dicatat tanpa dikirim.
- **Instagram dicek tiap 30 menit saja** (`IG_MIN_INTERVAL`), bukan tiap 5 menit, supaya akun cadangan tidak mudah dibatasi.
- **Bentuk pesan.** Untuk X dan Instagram, pesan berisi nama sumber dan link. Link diganti ke `fxtwitter.com` (untuk X) dan `kkinstagram.com` (untuk Instagram) agar Discord menampilkan gambar atau video langsung. Untuk RSS, pesan berisi judul dan link.
- Bot mengingat 200 postingan terakhir per sumber.

## Yang dibutuhkan

- Akun GitHub (gratis, tanpa kartu).
- Server Discord yang Anda kelola, dengan izin membuat webhook.
- Satu **akun X cadangan** dan satu **akun Instagram cadangan**, bila Anda ingin memantau X dan Instagram. Jangan pakai akun utama (lihat [Keamanan dan privasi](#keamanan-dan-privasi)). Untuk sumber RSS saja, kedua akun ini tidak diperlukan.
- Chrome atau browser lain di laptop untuk mengambil cookie akun cadangan.
- Repositori GitHub berstatus **Public**. Repositori publik mendapat menit GitHub Actions tanpa batas. [PERLU DIVERIFIKASI: kuota menit untuk repositori private tidak diuji, kemungkinan tidak cukup untuk jadwal tiap 5 menit.]

Python tidak perlu dipasang di komputer Anda untuk jalur GitHub Actions. Python 3.12 dipasang oleh workflow.

## Pemasangan

### 1. Siapkan akun cadangan dan ambil cookie

**Cookie X (`auth_token`):**

1. Buka jendela **Incognito** di Chrome, lalu login ke x.com dengan akun cadangan.
2. Tekan **F12**, buka tab **Application**, lalu pilih **Storage → Cookies → https://x.com**.
3. Klik baris `auth_token` dan salin nilainya.

**Cookie Instagram:**

1. Di jendela Incognito, login ke instagram.com dengan akun cadangan.
2. Tekan **F12**, buka tab **Network**, lalu tekan **F5**.
3. Klik salah satu request ke instagram.com, buka **Headers → Request Headers**, lalu salin seluruh nilai baris `cookie`.

Setelah selesai, **tutup jendela Incognito tanpa menekan Logout**. Logout mematikan sesi di server dan membuat cookie tidak berlaku.

### 2. Buat webhook Discord

Di tiap channel tujuan: **Edit Channel → Integrations → Webhooks → New Webhook → Copy Webhook URL**. Satu webhook untuk satu channel.

### 3. Buat repositori GitHub

1. Buat repositori baru berstatus **Public**.
2. Unggah `social_to_discord.py` ke akar repositori.
3. Buat file `.github/workflows/social.yml` (ketik path-nya persis begitu di GitHub), lalu tempel isinya.

### 4. Isi secret

Buka **Settings → Secrets and variables → Actions → New repository secret**, lalu buat satu per satu sesuai [Daftar secret](#daftar-secret). Nama harus persis sama, nilai ditempel utuh tanpa tanda kutip dan tanpa spasi di awal atau akhir.

### 5. Beri izin tulis ke workflow

Buka **Settings → Actions → General → Workflow permissions**, pilih **Read and write permissions**, lalu **Save**. Tanpa ini, bot tidak bisa menyimpan `seen.json`.

### 6. Aktifkan dan jalankan

Buka tab **Actions**. Bila ada tombol untuk mengaktifkan workflow, klik. Lalu jalankan [uji pertama](#menjalankan-dan-memeriksa-hasil).

## Mengatur channel dan sumber

Semua pengaturan sumber ada di blok `CHANNELS` pada `social_to_discord.py`. Contoh bentuknya:

```python
"footballinfo": {
    "webhook_env": "WEBHOOK_BOLA",
    "sources": [
        ("x", "FabrizioRomano"),
        ("rss", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ],
},
```

`webhook_env` adalah nama secret yang berisi webhook channel itu. `sources` adalah daftar sumbernya.

### Jenis sumber

| Bentuk | Artinya | Butuh |
|--------|---------|-------|
| `("x", "username")` | Akun X, tanpa tanda `@`. | Secret `TWITTER_AUTH_TOKEN` |
| `("ig", "username")` | Akun Instagram, tanpa tanda `@`. | Secret `IG_COOKIE` |
| `("rss", "https://...")` | Feed RSS dari situs berita, blog, atau YouTube. | Tidak ada |

### Sumber yang terpasang

| Channel | Secret webhook | Sumber |
|---------|----------------|--------|
| `newsinfo` | `WEBHOOK_BERITA` | RSS BBC News, Al Jazeera, Antara |
| `techinfo` | `WEBHOOK_TECH` | RSS Ars Technica, The Verge, TechCrunch |
| `footballinfo` | `WEBHOOK_BOLA` | X Fabrizio Romano dan David Ornstein, RSS BBC Sport dan The Guardian |
| `animeinfo` | `WEBHOOK_ANIME` | RSS Anime News Network |
| `gameinfo` | `WEBHOOK_GAME` | RSS Eurogamer, GameSpot, PC Gamer |
| `mobilelegendsinfo` | `WEBHOOK_MLBB` | X `mplidofficial`, `mlbbesports_en`, `real_mlbbid`; Instagram `mpl.id.official` |
| `eafcinfo` | `WEBHOOK_EAFC` | X `EASPORTSFC` |
| `pubgminfo` | `WEBHOOK_PUBGM` | X `PUBGMOBILE`, `pubgmesportsid`; Instagram `pubgmobile.esports.id` |
| `freefireinfo` | `WEBHOOK_FREEFIRE` | Instagram `freefirebgid` |
| `valorantinfo` | `WEBHOOK_VALORANT` | X `PlayVALORANT`, `ValorantEsports`, `vctpacific`; Instagram `vctpacific` |

[PERLU DIVERIFIKASI: URL RSS Antara, Anime News Network, GameSpot, dan PC Gamer, serta handle `real_mlbbid` dan `mpl.id.official` di Instagram, ditulis dari ingatan atau dari sumber yang belum dikonfirmasi langsung. Bila salah, log hanya menampilkan `Gagal baca` untuk sumber itu.]

### Mengganti atau menambah sumber

1. Buka `social_to_discord.py` di GitHub, klik ikon pensil.
2. Tambah, hapus, atau ubah baris di `sources`.
3. Klik **Commit changes**.

Sumber baru ikut dibaca di run berikutnya dan, menurut aturan di atas, hanya ditandai di pengecekan pertamanya.

### Menambah feed RSS

1. Buka situsnya, lihat bagian bawah halaman (footer), cari tulisan atau ikon **RSS**.
2. Salin URL feed, lalu tambahkan sebagai `("rss", "url")`.
3. Uji URL itu di browser. Bila muncul teks XML berisi daftar berita, URL benar.

### Menambah channel baru

1. Buat channel dan webhooknya di Discord.
2. Buat secret baru di GitHub, misalnya `WEBHOOK_ANIME2`.
3. Tambahkan satu blok di `CHANNELS` dengan `webhook_env` yang sama dengan nama secret itu.
4. Di `social.yml`, tambahkan satu baris di bagian `env` langkah **Cek akun dan kirim ke Discord**:

```yaml
WEBHOOK_ANIME2: ${{ secrets.WEBHOOK_ANIME2 }}
```

Tanpa langkah 4, secret tidak sampai ke program dan channel itu dilewati.

### Pengaturan tambahan

Pengaturan ini dibaca dari environment variable. Di `social.yml`, tambahkan di bagian `env` langkah **Cek akun dan kirim ke Discord** bila ingin mengubahnya.

| Nama | Bawaan | Fungsinya |
|------|--------|-----------|
| `MAX_PER_SOURCE` | `5` | Batas pesan per sumber per pengecekan. |
| `IG_MIN_INTERVAL` | `30` | Jeda minimal (menit) antar pengecekan akun Instagram. |
| `RSSHUB_URL` | `http://localhost:1200` | Alamat RSSHub. Di GitHub Actions sudah diatur oleh workflow. |
| `RUN_ONCE` | tidak aktif | Bila `1`, program mengecek sekali lalu selesai. Sudah diatur oleh workflow. |
| `POLL_SECONDS` | `180` | Jeda antar pengecekan saat dijalankan di komputer sendiri. Tidak dipakai di GitHub Actions. |

## Daftar secret

| Nama secret | Isinya | Wajib bila |
|-------------|--------|-----------|
| `TWITTER_AUTH_TOKEN` | Nilai cookie `auth_token` akun X cadangan. | Memakai sumber `x`. |
| `IG_COOKIE` | Seluruh isi cookie akun Instagram cadangan. | Memakai sumber `ig`. |
| `WEBHOOK_BERITA` | URL webhook channel `newsinfo`. | Channel itu dipakai. |
| `WEBHOOK_TECH` | URL webhook channel `techinfo`. | Channel itu dipakai. |
| `WEBHOOK_BOLA` | URL webhook channel `footballinfo`. | Channel itu dipakai. |
| `WEBHOOK_ANIME` | URL webhook channel `animeinfo`. | Channel itu dipakai. |
| `WEBHOOK_GAME` | URL webhook channel `gameinfo`. | Channel itu dipakai. |
| `WEBHOOK_MLBB` | URL webhook channel `mobilelegendsinfo`. | Channel itu dipakai. |
| `WEBHOOK_EAFC` | URL webhook channel `eafcinfo`. | Channel itu dipakai. |
| `WEBHOOK_PUBGM` | URL webhook channel `pubgminfo`. | Channel itu dipakai. |
| `WEBHOOK_FREEFIRE` | URL webhook channel `freefireinfo`. | Channel itu dipakai. |
| `WEBHOOK_VALORANT` | URL webhook channel `valorantinfo`. | Channel itu dipakai. |

Channel yang secret webhooknya kosong dilewati, dan log menulis `[skip]`. Jadi Anda boleh memulai dari satu channel saja.

Setelah disimpan, nilai secret tidak bisa dilihat lagi. Bila salah, buka secret itu, klik **Update**, lalu tempel ulang.

## Menjalankan dan memeriksa hasil

1. Buka tab **Actions → social-to-discord → Run workflow**. Gunakan tombol ini, bukan **Re-run**, karena Re-run memakai versi file lama.
2. Tunggu sampai semua langkah hijau.
3. Jalankan sekali lagi. Run pertama hanya menandai postingan yang sudah ada, jadi channel masih kosong. Itu normal.
4. Tunggu beberapa menit. Postingan baru dari sumber yang terbaca akan masuk ke channel.

### Membaca log

Buka run terakhir, klik job **run**, lalu buka langkah **Cek akun dan kirim ke Discord**.

| Baris di log | Artinya |
|--------------|---------|
| `[ok] nama\|jenis\|sumber: 20 entri` | Sumber terbaca dan berisi 20 postingan. |
| `[ok] ...: 0 entri` | Sumber terbaca tetapi kosong. Untuk X atau Instagram, biasanya cookie bermasalah. |
| `[+] #channel <- sumber: link` | Satu pesan terkirim. |
| `[!] Gagal baca ...` | Sumber tidak bisa dibaca. |
| `[!] Gagal kirim ...` | Pesan gagal dikirim ke Discord. |
| `[skip] channel: secret ... belum diisi` | Secret webhook channel itu belum dibuat atau namanya salah. |

Peringatan tentang Node.js 20 atau Ubuntu 26 di halaman ringkasan adalah pemberitahuan dari GitHub dan tidak menghentikan bot.

## Menjalankan di komputer sendiri

Jalur ini opsional, untuk mencoba tanpa GitHub. Komputer harus tetap menyala selama bot berjalan.

1. Pasang Python 3.8 atau lebih baru dan Docker.
2. Jalankan RSSHub:

```
docker run -d --name rsshub -p 1200:1200 -e TWITTER_AUTH_TOKEN=nilai_cookie diygod/rsshub
```

3. Pasang pustaka: `pip install feedparser requests`
4. Isi webhook lewat environment variable. Di Command Prompt Windows:

```
set WEBHOOK_BERITA=https://discord.com/api/webhooks/...
```

5. Jalankan: `python social_to_discord.py`

Program mengecek tiap `POLL_SECONDS` detik dan berjalan terus sampai dihentikan. [PERLU DIVERIFIKASI: nama variabel cookie Instagram (`IG_COOKIE`) dan cara memasukkannya ke RSSHub di Docker belum diuji di komputer sendiri.]

## Pemecahan masalah

| Gejala | Penyebab kemungkinan | Cara mengatasi |
|--------|----------------------|----------------|
| Setelah run pertama, channel kosong | Normal. Run pertama hanya menandai postingan yang ada. | Tunggu run berikutnya. |
| Langkah **Simpan seen.json** gagal dengan `rejected (fetch first)` | Run memakai versi lama (biasanya karena tombol Re-run), sementara `main` sudah berubah. | Pakai **Run workflow**, bukan Re-run. Workflow terbaru sudah memakai `git pull --rebase` sebelum push. |
| Langkah **Simpan seen.json** gagal dengan `403` atau `Permission denied` | Workflow tidak punya izin menulis. | Atur **Read and write permissions** di Settings → Actions → General. |
| `[skip] ... belum diisi` | Nama secret salah ketik, belum dibuat, atau belum ditambahkan di bagian `env` pada `social.yml`. | Samakan nama secret di `CHANNELS`, di Secrets, dan di `social.yml`. |
| `[!] Gagal baca` untuk RSS | URL salah, atau situsnya memblokir server GitHub. | Uji URL di browser. Bila XML muncul di browser tetapi gagal di GitHub, situs memblokir server GitHub, jadi ganti sumber. |
| `[!] Gagal baca` atau `0 entri` untuk X | Cookie salah, kedaluwarsa, atau akun cadangan dibatasi. | Ambil cookie baru (lihat [Pemasangan](#pemasangan)) dan perbarui secret `TWITTER_AUTH_TOKEN`. |
| `[!] Gagal baca` atau `0 entri` untuk Instagram | Cookie kedaluwarsa, format cookie tidak sesuai, atau Instagram memblokir server GitHub. | Ambil cookie baru. Bila tetap gagal, Instagram kemungkinan tidak bisa dipakai dari GitHub Actions. |
| Semua sumber X berhenti sekaligus | Cookie hangus karena akun logout atau password diganti. | Ambil cookie baru lewat Incognito dan jangan menekan Logout. |
| Jadwal otomatis berhenti | GitHub menonaktifkan jadwal di repositori yang lama tidak ada aktivitas. | Buka tab Actions, aktifkan kembali workflow, lalu jalankan manual sekali. |
| Channel kebanjiran pesan | Terlalu banyak sumber yang ramai di satu channel. | Kurangi sumber atau turunkan `MAX_PER_SOURCE`. |
| `[!] Gagal kirim` | Webhook dihapus atau URL-nya salah. | Buat webhook baru dan perbarui secret-nya. |
| Gambar atau video tidak tampil di Discord | Layanan embed (`fxtwitter`, `kkinstagram`) sedang bermasalah. [PERLU DIVERIFIKASI: layanan ini milik pihak ketiga dan bisa berubah.] | Tunggu, atau buka linknya langsung. |
| Workflow gagal di langkah pip atau Docker setelah GitHub memindahkan `ubuntu-latest` ke Ubuntu 26 | Perubahan versi runner. | Di `social.yml`, ganti `ubuntu-latest` dengan `ubuntu-24.04`. [PERLU DIVERIFIKASI: belum terlihat error akibat perpindahan ini.] |

## File yang dibuat program

| File | Isinya | Kapan dibuat |
|------|--------|--------------|
| `seen.json` | Daftar postingan yang sudah dilihat per sumber (maksimal 200 terakhir per sumber), dan waktu pengecekan terakhir tiap akun Instagram. | Saat run pertama, lalu diperbarui bila ada perubahan. |

Kunci di dalam `seen.json` berbentuk `channel|jenis|sumber`, misalnya `footballinfo|x|FabrizioRomano`.

Untuk membuat bot menganggap semua sumber sebagai baru, hapus `seen.json`. Di run berikutnya semua postingan yang ada ditandai lagi dan tidak dikirim.

## Keamanan dan privasi

- **Cookie sama dengan akses ke akun.** Siapa pun yang memegang cookie bisa masuk ke akun itu tanpa password. Simpan hanya di GitHub Secrets. Jangan menempelnya di kode, di chat, atau di tangkapan layar.
- **Pakai akun cadangan.** Mengakses X dan Instagram dengan cara ini bisa melanggar ketentuan layanan mereka, dan akun yang dipakai bisa dibatasi atau ditangguhkan. Jangan pakai akun utama.
- **Webhook sama dengan hak mengirim pesan ke channel.** Bila URL webhook bocor, hapus webhooknya di Discord dan buat yang baru.
- **Repositori publik bersifat terbuka.** Kode, daftar akun yang Anda pantau, `seen.json`, dan log Actions bisa dilihat siapa pun. Nilai secret disamarkan menjadi `***` di log, tetapi nama akun dan link tidak.
- Bot hanya mengirim link dan judul ke Discord. Bot tidak menyimpan isi postingan di repositori.
- Server GitHub bisa diblokir oleh X atau Instagram, dan itu bukan tanda bahwa cookie Anda bocor.

## Cara memperbarui dan menghapus

Memperbarui:

1. Buka file yang ingin diubah di GitHub, lalu klik ikon pensil.
2. Tempel isi versi baru, lalu **Commit changes**.
3. Jalankan **Run workflow** sekali untuk memastikan semuanya hijau.

Menghapus:

1. Buka **Settings → Actions → General** dan nonaktifkan Actions, atau hapus `.github/workflows/social.yml`.
2. Hapus webhook yang tidak dipakai di Discord.
3. Hapus secret di GitHub, lalu hapus repositorinya bila tidak diperlukan lagi.
4. Bila akun cadangan tidak dipakai lagi, logout atau hapus akunnya.

## Batasan yang diketahui

- **Tidak real time.** Jadwal tiap 5 menit sering molor, jadi jeda praktisnya sekitar 5 sampai 15 menit. Instagram dicek tiap 30 menit.
- **X dan Instagram bergantung pada scraping lewat RSSHub.** Cara ini rapuh. X atau Instagram bisa mengubah sistemnya, memblokir server GitHub, atau membatasi akun cadangan, dan feed bisa berhenti kapan saja. Sumber RSS biasa jauh lebih stabil.
- **Cookie harus diperbarui secara manual** saat kedaluwarsa.
- **Jumlah akun.** [PERLU DIVERIFIKASI: batas aman akun X dan Instagram per akun cadangan tidak diuji. Perkiraan awal: puluhan akun X dan belasan akun Instagram.]
- **Hanya link dan judul yang dikirim.** Tampilan gambar dan video bergantung pada embed Discord.
- **Balasan dan repost.** [PERLU DIVERIFIKASI: belum diketahui apakah RSSHub menyertakan balasan atau repost dari akun X, sehingga bisa ikut terkirim.]
- **Alternatif resmi untuk X.** X menyediakan API berbayar sesuai pemakaian, yang lebih stabil. [PERLU DIVERIFIKASI: harga dan batasnya bisa berubah, cek halaman harga resmi X.] Instagram tidak menyediakan API resmi untuk memantau akun orang lain.
- Repositori ini belum mencantumkan lisensi.
