# Perbandingan

## Tujuan

Membandingkan metode eksperimen dan performa komputasi.

## Daftar figur

- `dynamic_comparison.png`
- `runtime_comparison.png`
- `runtime_per_window.png`
- `static_comparison.png`

- `static_comparison.png` — baseline statik vs. GA: PM aktif dan event overload.
- `dynamic_comparison.png` — per window, cold vs. warm: PM aktif, migrasi,
  utilisasi rata-rata, event overload selama 24 window.
- `runtime_comparison.png` — total runtime per metode.
- `runtime_per_window.png` — runtime optimasi per window.

## Metode yang dibandingkan

Baseline acak statik, GA statik, GA dinamis cold-start, GA dinamis warm-start.
Semua memakai 12 PM yang sama dan beban kerja yang sama.

## Makna tiap metrik

- Jumlah PM aktif: PM yang menampung minimal satu VM.
- Migrasi: VM yang PM-nya berbeda dari placement referensi.
- Event overload: pasangan PM/cuplikan dengan utilisasi melebihi 0.8
  (ketat, tanpa toleransi).
- Runtime: waktu dinding optimasi (tidak bisa dibandingkan antar mesin).

## Definisi migrasi statik dan dinamis berbeda

Migrasi GA statik dihitung dari placement baseline acak untuk satu penempatan
sepanjang hari. Migrasi dinamis dihitung per window relatif terhadap placement
window sebelumnya, dan mencakup transisi placement-awal ke Window 1. Eksperimen
dinamis memuat 24 window, sehingga total dinamis adalah penjumlahan 24 transisi
— tidak ekuivalen dengan angka tunggal statik.

## Cara menafsirkan

Kedua metode dinamis mempertahankan 12 PM aktif di seluruh 24 window dengan
nol overload. Semua metode yang dilaporkan memakai 12 PM aktif; GA tidak
mengurangi jumlah PM aktif. Keunggulan warm-start terlihat pada migrasi per
window yang lebih sedikit di `dynamic_comparison.png`.

## Batasan

- Satu run per metode; perbedaan adalah observasi run tunggal, bukan statistik.
- Runtime hanya mencakup evaluasi; tidak ada model biaya migrasi.

## Relasi ke output lain

Nilai batang/garis identik dengan `../../summaries/experiment_summary.csv` dan
`../../experiments/dynamic/*/per_window_metrics.csv`.
