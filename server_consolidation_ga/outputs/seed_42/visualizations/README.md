# Visualisasi

Figur dikelompokkan per tujuan analitis. Setiap folder kategori memiliki README
sendiri yang menjelaskan sumbu, legenda, warna, dan batasan interpretasi. Semua
figur berasal dari run yang sama (seed 42).

## Kategori

- `workload/` — beban kerja CPU agregat sepanjang hari (1 figur).
- `utilization/` — utilisasi CPU per PM dan kendala kapasitas (5 figur).
- `convergence/` — kemajuan optimasi GA (2 figur).
- `comparison/` — perbandingan metode statik/dinamis/runtime (4 figur).
- `workload_timeseries/` — deret beban per PM hasil rekonstruksi (6 figur).
- `performance_comparison/` — kelayakan, PM aktif, migrasi, overload (5 figur).

## Hubungan antar kategori

Figur utilisasi adalah deret beban per PM di `workload_timeseries/` dibagi
kapasitas PM (16.0 vCPU). Nilai batang pada
`performance_comparison/` identik dengan angka di
`../../summaries/experiment_summary.csv`. Riwayat konvergensi adalah data yang
sama dengan `../../experiments/*/fitness_history.csv`.

## Urutan baca yang disarankan

1. `workload/` — besaran dan fluktuasi beban total.
2. `workload_timeseries/` — sebaran beban ke 12 PM.
3. `utilization/` — pemeriksaan kapasitas PM dan kelayakan terhadap ambang
   aman 0.8.
4. `convergence/` — kemajuan optimasi GA dan perilaku fitness.
5. `comparison/` — perilaku per-window dan biaya runtime.
6. `performance_comparison/` — evaluasi hasil akhir semua metode.
