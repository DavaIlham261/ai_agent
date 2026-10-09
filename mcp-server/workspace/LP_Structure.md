# Struktur HTML — `landing_page.html`

Dokumen ini merangkum struktur (hierarki tag & kelas) dari `landing_page.html`
sebagai acuan untuk penulisan CSS di `style.css`.

> Nomenklatur kelas mengikuti **BEM** (Block__Element--Modifier).

---

## Ringkasan Blok Utama

| # | Blok (ID / Kelas)     | Kegunaan                          |
|---|----------------------|-----------------------------------|
| 2.1 | `.navbar` (`#navbar`) | Navigasi atas / header            |
| 2.2 | `.hero` (`#beranda`)  | Section penebar pesan utama (hero) |
| 2.3 | `.features` (`#fitur`)| Keunggulan / fitur produk         |
| 2.4 | `.about` (`#tentang`) | Perkenalan tim & statistik        |
| 2.5 | `.testimonials` (`#testimoni`) | Kutipan pengguna         |
| 2.6 | `.cta` (`#kontak`)    | Ajakan bertindak akhir            |
| 2.7 | `.footer`             | Info kontak & navigasi bawah      |

Komponen global pendukung:

- `.section` — pembungkus section (padding vertikal), varian `.section--tint` memberi latar beda tone.
- `.container` — pembungkus lebar terpusat (max-width + margin auto).
- `.section__header`, `.section__title`, `.section__subtitle` — header umum section.
- `.btn` — tombol, varian: `.btn--primary`, `.btn--secondary`, `.btn--light`.
- `.card`, `.stat`, `.testimonial`, `.text-accent` — komponen berulang.

---

## Detail Struktur

### 2.1 Navbar (`.navbar`)
```
header.navbar#navbar
└── div.container.navbar__inner
    ├── a.navbar__logo            → "Brand" + span "Name"
    ├── nav.navbar__menu
    │   └── a.navbar__link ×5     (Beranda, Fitur, Tentang, Testimoni, Kontak)
    └── a.btn.btn--primary.navbar__cta → "Mulai Sekarang"
```

### 2.2 Hero (`.hero`)
```
section.hero.section#beranda
└── div.container.hero__grid
    ├── div.hero__text
    │   ├── span.hero__badge              (🚀 AI Agent ...)
    │   ├── h1.hero__title                + span.text-accent
    │   ├── p.hero__subtitle
    │   └── div.hero__actions
    │       ├── a.btn.btn--primary        ("Coba Gratis")
    │       └── a.btn.btn--secondary      ("Pelajari Lebih Lanjut")
    └── div.hero__visual
        ├── div.hero__card.hero__card--main
        │   ├── div.hero__card-header     (3× span.dot: dot--red/yellow/green)
        │   ├── p.hero__card-title
        │   └── ul.hero__card-list        (3× li)
        └── div.hero__card.hero__card--float
            ├── span.hero__card-stat      ("10k+")
            └── span.hero__card-label     ("Pengguna Puas")
```

### 2.3 Fitur (`.features`)
```
section.features.section.section--tint#fitur
└── div.container
    ├── div.section__header
    │   ├── h2.section__title
    │   └── p.section__subtitle
    └── div.features__grid
        └── article.card ×3
            └── div.card__icon
            └── h3.card__title
            └── p.card__desc
```

### 2.4 Tentang (`.about`)
```
section.about.section#tentang
└── div.container.about__grid
    ├── div.about__text
    │   ├── h2.section__title.about__title
    │   └── p.about__desc ×2
    └── div.about__stats
        └── div.stat ×3
            ├── span.stat__num└── span.stat__label
```

### 2.5 Testimoni (`.testimonials`)
```
section.testimonials.section.section--tint#testimoni
└── div.container
    ├── div.section__header
    │   ├── h2.section__title
    │   └── p.section__subtitle
    └── div.testimonials__grid
        └── figure.testimonial ×3
            ├── div.testimonial__quote     (❝)
            ├── blockquote.testimonial__text
            └── figcaption.testimonial__author
                ├── span.testimonial__name
                └── span.testimonial__role
```

### 2.6 CTA Finale (`.cta`)
```
section.cta.section#kontak
└── div.container.cta__inner
    ├── h2.cta__title
    ├── p.cta__subtitle
    └── a.btn.btn--light.cta__btn         ("Daftar Sekarang")
```
> Catatan: di file saat ini `.cta` berada di dalam `<main>`,
> setelah `</main>` pertama namun sebelum closing tag kedua.
> Idealnya tetap bagian dari `<main>` — bisa dibenahi nanti.

### 2.7 Footer (`.footer`)
```
footer.footer
├── div.container.footer__grid
│   ├── div.footer__brand
│   │   ├── a.footer__logo          ("Brand" + span "Name")
│   │   └── p.footer__desc
│   └── div.footer__col ×3
│       ├── h3.footer__heading       (Navigasi / Kontak / Ikuti Kami)
│       └── ul.footer__list          (li > a.footer__link | span.footer__text)
│                                      └── varian: ul.footer__list.footer__social
└── div.footer__bottom
    └── div.container
        └── p.footer__copy
```

---

## Catatan untuk CSS

1. **Responsive**: gunakan grid `auto-fit / minmax` untuk
   `.features__grid`, `.testimonials__grid`, `.footer__grid`, dan
   `2 kolom → 1 kolom` untuk `.hero__grid` & `.about__grid` pada layar kecil.
2. **Variasi latar**: `.section--tint` untuk memberi background berbeda
   agar section bergantian (z-tone) dan mudah dibaca.
3. **Tombol**: satu kelas dasar `.btn` + modifier `--primary`, `--secondary`,
   `--light` supaya mudah konsistensi warna & hover.
4. **Dots di hero card**: `dot--red`, `dot--yellow`, `dot--green` meniru
   tiga titik jendela browser (Mac window chrome).
5. **Aksesibilitas**: jaga `:focus-visible`, kontras warna, dan ukuran
   font minimal 16px untuk body.