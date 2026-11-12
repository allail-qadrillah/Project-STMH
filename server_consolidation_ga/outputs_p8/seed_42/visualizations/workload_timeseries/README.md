# Deret waktu beban kerja per PM

## Tujuan

Menampilkan sebaran total beban CPU ke 12 PM sepanjang hari, per metode: GA
statik, baseline acak statik, cold-start dinamis, warm-start dinamis, plus dua
perbandingan bertumpuk.

## Daftar figur

- `dynamic_cold_start.png`
- `dynamic_comparison.png`
- `dynamic_warm_start.png`
- `static_baseline.png`
- `static_comparison.png`
- `static_ga.png`

- `static_ga.png`, `static_baseline.png` — satu placement untuk seluruh 288 cuplikan.
- `static_comparison.png` — baseline (atas) vs. GA (bawah), sumbu identik.
- `dynamic_cold_start.png`, `dynamic_warm_start.png` — placement 24 window.
- `dynamic_comparison.png` — cold (atas) vs. warm (bawah), sumbu identik.

## Sumbu

- Sumbu X: indeks cuplikan 0–287 (12 cuplikan per window; Window 1 = 0–11,
  Window 2 = 12–23, ..., Window 24 = 276–287).
- Sumbu Y: beban CPU dalam vCPU.

## Cara menghitung beban PM dalam vCPU

Per PM: jumlah permintaan vCPU VM yang ditugaskan ke PM itu pada cuplikan
tersebut. Statik: satu placement simpanan dipakai untuk semua cuplikan. Dinamis
: beban direkonstruksi terpisah per window dari placement terpilih window itu —
setiap window punya placement sendiri, sehingga garis PM bisa melompat di batas
window.

## Garis referensi

- Putus-putus hitam: kapasitas aman 12.8 vCPU (0.8 kali
  16.0). Metode layak
  hanya jika setiap PM berada pada atau di bawah garis ini.
- Bertitik merah tua: kapasitas fisik 16.0 vCPU. Beban
  di antara dua garis melanggar kendala ambang aman (tidak layak) namun masih
  terlayani secara fisik; beban di atas garis bertitik melebihi PM itu sendiri.

## Bedanya beban dan rasio utilisasi

Beban dalam vCPU; rasio utilisasi = beban / 16.0.
Heatmap utilisasi adalah deret yang sama dibagi kapasitas. Warna PM konsisten
dan batas sumbu identik antar metode agar sebanding.

## Cara menafsirkan

Pemisahan garis yang rata menandakan sebaran beban seimbang; lonjakan menuju
garis putus-putus menandakan PM mendekati kapasitas; garis menembus ke atasnya
menandai ketidaklayakan (hanya baseline statik). Lompatan di batas window
merefleksikan migrasi VM antar placement — jauh lebih sering pada cold-start.

## Batasan

- Rekonstruksi dari placement simpanan; tidak ada dinamika runtime maupun
  biaya migrasi yang dimodelkan.
- Tumpang-tindih warna menyembunyikan nilai persis; angka ada di `raw.npz`.

## Relasi ke output lain

Placement sumber: `../../experiments/static/*/placement.csv`,
`../../experiments/dynamic/*/window_*/placement.csv`; tampilan utilisasi:
`../utilization/`.
