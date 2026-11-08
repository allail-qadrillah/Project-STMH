# Perbandingan performa

## Tujuan

Mengevaluasi hasil eksperimen: kelayakan, jumlah PM aktif, migrasi, dan event
overload.

## Daftar figur

- `active_pm_comparison.png`
- `experiment_summary_dashboard.png`
- `feasibility_comparison.png`
- `migration_comparison.png`
- `overload_comparison.png`

- `feasibility_comparison.png` — status kelayakan keempat metode.
- `active_pm_comparison.png` — jumlah PM aktif.
- `migration_comparison.png` — total migrasi dan reduksi warm vs. cold.
- `overload_comparison.png` — event overload; baseline ditandai tidak layak.
- `experiment_summary_dashboard.png` — keempat panel digabung.

## Metode yang dibandingkan

Baseline acak statik, GA statik, cold-start dinamis, warm-start dinamis (satu
run masing-masing, seed 42).

## Makna tiap metrik

- Kelayakan: statik — satu placement sepanjang hari memenuhi kendala ambang
  aman; dinamis — banyak window yang layak dari 24 (keduanya 24/24).
- PM aktif: PM yang menampung minimal satu VM; batang dinamis menampilkan
  rentang per window (12 di setiap window).
- Migrasi: perubahan PM per VM, definisi berbeda di bawah.
- Event overload: pasangan PM/cuplikan dengan utilisasi melebihi 0.8.

Satu run eksperimen, master seed 42. Nilai yang dilaporkan:

| Metode | Status | PM aktif | Migrasi | Overload |
|---|---|---:|---:|---:|
| static_baseline | FEASIBLE | 24 | 0 | 0 |
| static_ga | FEASIBLE | 24 | 987 | 0 |
| cold_start | FEASIBLE | 24.0 | 19086 | 0 |
| warm_start | FEASIBLE | 24.0 | 785 | 0 |

Reduksi migrasi dinamis, warm-start vs. cold-start: 95.9%.

Keempat metode memakai 12 PM aktif; tidak ada pengurangan jumlah PM yang terbukti.

## Perhitungan reduksi migrasi

Reduksi (%) = (migrasi cold − migrasi warm) / migrasi cold × 100.
Untuk run ini hasilnya sekitar 58,6%, mencakup seluruh 24 transisi (termasuk
placement awal ke Window 1).

## Definisi migrasi berbeda

Migrasi GA statik: VM yang PM-nya berbeda dari placement baseline acak (satu
pengukuran sepanjang hari). Migrasi dinamis: per window, perpindahan relatif
terhadap placement terpilih window sebelumnya, dijumlahkan atas 24 transisi.
Keempat angka migrasi karena itu tidak langsung ekuivalen — perbandingan yang
sah adalah cold vs. warm di dalam dinamis.

## Mengapa 12 PM aktif bukan reduksi

Keempat metode berakhir dengan 12 PM aktif dan metode dinamis mempertahankan 12
sepanjang waktu. Eksperimen ini membuktikan kelayakan dan perilaku migrasi,
bukan konsolidasi server: pengurangan jumlah PM aktif di bawah 12 belum
terbukti. Jangan mengklaim GA mengurangi PM aktif.

## Kelayakan dan konsolidasi itu tujuan yang terpisah

Kelayakan adalah kendala (tidak ada PM di atas CPU ambang aman); konsolidasi
adalah objektif (PM aktif lebih sedikit). Metode bisa layak tanpa berkonsolidasi
— persis yang terjadi di sini.

## Batasan

- Satu run per metode; tidak ada uji signifikansi maupun deviasi standar.
- Baseline statik hanya referensi; migrasinya nol karena ia jadi patokan, bukan
  karena unggul.

## Relasi ke output lain

Nilai identik dengan `../../summaries/experiment_summary.csv`; rincian per
window: `../../experiments/dynamic/*/per_window_metrics.csv`.
