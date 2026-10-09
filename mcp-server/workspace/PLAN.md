# 📋 Rencana Pengerjaan: Landing Page

Dokumen ini mendeskripsikan **apa yang akan kita buat, bagaimana strukturnya, dan detail teknisnya** secara lengkap. Landing page akan dibuat dari **2 file**:
- `landing_page.html` → struktur & konten
- `style.css` → tampilan, layout, warna, responsivitas

> **Karakteristik umum:** modern, minimalis, bersih, satu halaman (single-page), dan **responsif** (rata di HP, tablet, dan desktop) tanpa library/framework (pure HTML + CSS, tanpa JS eksternal).

---

## 1. 🎨 Konsep & Tema

| Aspek | Keterangan |
|---|---|
| **Jenis** | Landing page bisnis/SaaS contoh (tema netral, mudah kamu ganti isinya) |
| **Gaya** | Modern & minimalis, aksen warna biru/indigo + latar terang |
| **Font** | Font system (tanpa load font eksternal agar cepat) — fallback sans-serif |
| **Warna primer** | Indigo `#4f46e5` sebagai aksen (tombol, link, highlight) |
| **Warna latar** | Putih `#ffffff` & abu sangat muda `#f8fafc` untuk section bernuansa |
| **Warna teks** | Gelap `#1e293b` untuk teks, abu `#64748b` untuk teks pendukung |
| **Angle** | Judul besar di hero + CTA (Call to Action) yang jelas |

> Semua warna digatur lewat **CSS Variables** di `:root` agar gampang di-custom.

---

## 2. 🧱 Struktur Section (dari atas ke bawah)

### 2.1 Navbar (Header / Navigasi)
- Logo di kiri (teks "BrandName" — placeholder).
- Menu di kanan: **Beranda, Fitur, Tentang, Testimoni, Kontak**.
- Tombol CTA kecil di paling kanan: "Mulai Sekarang".
- **Perilaku:** posisi `sticky` (nempel di atas saat scroll). Di layar mobile, menu menyatu dengan brand (sederhana, tanpa hamburger/JS).

### 2.2 Hero
- **Headline** besar: "Wujudkan Ide Kamu Jadi Produk Digital yang Berdampak".
- Sub-headline penjelas 1–2 baris.
- **2 tombol CTA:** primer "Coba Gratis" + sekunder "Pelajari Lebih Lanjut".
- Sisi lain: area placeholder gambar/illustrasi (kotak bergradien, karena tanpa gambar eksternal).
- Layout: 2 kolom di desktop (teks kiri, visual kanan), menumpuk di mobile.

### 2.3 Fitur / Keunggulan
- Judul section: "Kenapa Memilih Kami" + sub-judul singkat.
- **Grid 3 kartu** (jadi satu baris di desktop, menumpuk di mobile), masing-masing berisi:
  - Ikon (emoj 🚀 ✅ 🛡 sebagai placeholder)
  - Judul fitur (misal: "Cepat & Ringan", "Mudah Digunakan", "Aman & Teruji")
  - Deskripsi 2 baris.
- Kartu punya efek **hover** (naik sedikit + bayangan) untuk kesan hidup.

### 2.4 Tentang Kami
- Judul: "Tentang Kami".
- Teks paragraf 1–2 describing profil/visi (placeholder).
- Disertai **statistik singkat** dalam 1 baris: contoh `10k+ Pengguna`, `99% Kepuasan`, `24/7 Dukungan` — ditampilkan sebagai angka besar + label.

### 2.5 Testimoni
- Judul: "Apa Kata Mereka".
- Grid **2–3 kartu testimoni**: kutipan, nama, dan jabatan (placeholder).
- Kartu bernuansa abu muda, rapi, dengan tanda kutip di atas.

### 2.6 Call to Action (CTA Finale)
- Latar bergradien (indigo → violet) untuk menjadi penutup yang kuat.
- Headline: "Siap Memulai?" + tombol besar berteks "Daftar Sekarang".

### 2.7 Footer
- Logo/brand + deskripsi singkat.
- Sidebar kolom: **Navigasi** (pengulangan menu), **Kontak** (email, telepon, alamat placeholder), dan **sosial media** (ikon teks).
- Copyright baris paling bawah (© 2025 BrandName).

---

## 3. 📐 Tata Letak & Teknik Responsif

- **Layout utama:** berpusat dengan lebar maksimum `.container` (±1100px) agar rapi di layar besar.
- **Grid & Flexbox** untuk kartu fitur, testimoni, dan statistik.
- **Breakpoint:**
  - `≥ 768px` → layout multi-kolom.
  - `< 768px` → semua kolom menumpuk vertikal, padding dikecilkan, font headline diperkecil.
- **Selector utama** akan diberi `section[id]` (`#beranda`, `#fitur`, `#tentang`, `#testimoni`, `#kontak`) supaya menu navigasi bisa *smooth scroll* ke tiap bagian.

---

## 4. 🎯 Urutan Pengerjaan

1. ✅ Dokumen rencana (file ini).
2. 📝 `landing_page.html` — tulis struktur + konten semua section (step berikutnya).
3. 🎨 `style.css` — styling semua section, variabel warna, grid, efek hover, dan media query responsif.
4. ▶️ Cek/tes tampilan (buka di browser desktop, tablet, dan mobile) untuk memastikan layout responsif, navigasi smooth-scroll, dan efek hover berjalan baik.
5. ✏️ Revisi & poles — sesuaikan copy, warna, spacing, dan placeholder sesuai kebutuhan.

---

## 5. 📌 Catatan & Hal Teknis Tambahan

- **Tanpa gambar/font eksternal:** semua visual memakai placeholder (gradien CSS, emoji) supaya halaman tetap ringan dan langsung bisa dibuka offline.
- **CSS Variables di `:root`:** `--primary` (indigo), `--bg-light` (#f8fafc), `--text-dark` (#1e293b), `--text-muted` (#64748b), dll — memudahkan ganti tema.
- **Accessibility:** atribut `alt` pada elemen visual, kontras warna memadai, dan semantik HTML (`<header>`, `<nav>`, `<section>`, `<footer>`).
- **Performance:** pure HTML + CSS, tanpa JS eksternal → cepat dimuat.
- **Placeholder content:** brand, teks, angka, dan kontak masih contoh — tinggal digantikan data asli.

---

## 6. ✅ Checklist Final

- [ ] Semua 7 section selesai (Navbar, Hero, Fitur, Tentang, Testimoni, CTA, Footer)
- [ ] Navigasi smooth-scroll ke tiap `section[id]`
- [ ] Navbar `sticky` di semua ukuran layar
- [ ] Grid kartu menumpuk rapi di layar `< 768px`
- [ ] Efek hover aktif pada tombol dan kartu
- [ ] Warna konsisten via CSS Variables
- [ ] Terlihat rapi di desktop, tablet, dan HP