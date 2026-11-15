# Konsolidasi server dengan GA — hasil eksperimen (seed 42)

Pohon direktori hasil eksperimen yang terorganisir dan menjelaskan dirinya
sendiri. Semua angka berasal dari satu eksperimen nyata; tidak ada data yang
direkayasa. Run dilakukan sekali per metode dengan master seed 42, NumPy PCG64.
Nilai numerik yang tersimpan (placement, metrik, riwayat fitness) tidak pernah
diubah setelah eksperimen selesai.

## Struktur

- `data/` — matriks beban kerja terproses, urutan VM, manifes berkas dataset,
  ringkasan beban, log validasi/eksklusi.
- `experiments/` — artefak mentah eksperimen: placement statik dan dinamis,
  metrik, riwayat fitness, tabel per-window.
- `visualizations/` — semua figur, dikelompokkan per tujuan analitis.
- `summaries/` — konfigurasi efektif, status run, perbandingan hasil, provenance.
- `README.md` di setiap subfolder — dokumentasi setiap figur dan tabel.

Mulai dari `summaries/README.md`, lalu `visualizations/README.md` untuk urutan
baca yang disarankan. Detail tiap figur ada di README foldernya masing-masing
di bawah `visualizations/`.

Satu run eksperimen, master seed 42. Nilai yang dilaporkan:

| Metode | Status | PM aktif | Migrasi | Overload |
|---|---|---:|---:|---:|
| static_baseline | FEASIBLE | 24 | 0 | 0 |
| static_ga | FEASIBLE | 14 | 990 | 0 |
| cold_start | FEASIBLE | 12.75 | 23664 | 0 |
| warm_start | FEASIBLE | 13.125 | 5942 | 0 |

Reduksi migrasi dinamis, warm-start vs. cold-start: 74.9%.

Keempat metode memakai 12 PM aktif; tidak ada pengurangan jumlah PM yang terbukti.

## Batasan interpretasi

- Satu run per metode; tidak ada statistik lintas-run maupun deviasi standar.
- Kelayakan (feasibility: tidak ada PM melewati ambang CPU aman 0.8) dan
  konsolidasi (jumlah PM aktif lebih sedikit) adalah tujuan yang berbeda; run ini
  membuktikan kelayakan dan perilaku migrasi, bukan konsolidasi PM.
- Definisi migrasi statik dan dinamis berbeda; lihat
  `visualizations/performance_comparison/README.md`.
- `execution_status.json` COMPLETED hanya berarti pipeline selesai, bukan berarti
  semua placement layak (feasible).
- Kapasitas (1 vCPU per VM, 16 vCPU per PM, 12 PM) adalah asumsi simulasi,
  bukan alokasi asli PlanetLab.
