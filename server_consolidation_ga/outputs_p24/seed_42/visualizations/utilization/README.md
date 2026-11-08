# Utilisasi

## Tujuan

Menganalisis utilisasi CPU per PM dan kendala kapasitas; memverifikasi
kelayakan (feasibility).

## Daftar figur

- `pm_utilization_heatmap_dynamic_cold_start.png`
- `pm_utilization_heatmap_dynamic_warm_start.png`
- `pm_utilization_heatmap_static_baseline.png`
- `pm_utilization_heatmap_static_ga.png`
- `utilization_distribution.png`

- `utilization_distribution.png` — histogram utilisasi cuplikan PM aktif.
- `pm_utilization_heatmap_static_baseline.png` — baseline acak statik.
- `pm_utilization_heatmap_static_ga.png` — GA statik.
- `pm_utilization_heatmap_dynamic_cold_start.png` — 24 window cold-start.
- `pm_utilization_heatmap_dynamic_warm_start.png` — 24 window warm-start.

## Sumbu

- Heatmap: sumbu X indeks cuplikan (0–287; dinamis = window 1–24
  digabungkan), sumbu Y ID PM (1–12).
- Distribusi: sumbu X rasio utilisasi, sumbu Y densitas.

## Warna dan garis referensi

Warna heatmap = rasio utilisasi CPU (beban / 16.0 vCPU);
skala colorbar mulai dari 0. Distribusi: garis putus-putus hitam = ambang aman
0.8; warna garis membedakan metode.

## Ambang CPU aman

Utilisasi di atas 0.8 (beban di atas 12.8 vCPU) tidak aman. Sebuah
metode layak (feasible) hanya jika tidak ada pasangan PM/cuplikan yang melewati
ambang dalam toleransi 1e-9.

## Beda utilisasi layak dan tidak layak

Layak: setiap PM berada pada atau di bawah ambang di setiap cuplikan. Tidak layak
: minimal satu pasangan PM/cuplikan melewatinya (baseline statik: 7 event
overload). Warna gelap tidak otomatis berarti PM tidak aktif: semua baris PM
ikut diplot termasuk yang kosong (beban 0), jadi gelap dengan nilai tepat nol
berarti tidak aktif; sel gelap-nonnol hanya berarti beban ringan.

## Pertanyaan riset yang dijawab

Placement mana yang menjaga semua PM di bawah ambang aman sambil menyeimbangkan
beban? Heatmap membantu mengenali PM kurang terpakai (baris gelap) dan PM
terbebati tinggi (sel terang).

## Batasan

- Heatmap menampilkan utilisasi, bukan beban vCPU; kalikan kapasitas untuk
  mendapatkannya kembali.
- Rata-rata utilisasi menghitung PM aktif saja; PM nyaris menganggur tetap tampak gelap.
- Distribusi hanya memuat PM aktif, jadi PM nonaktif tidak dihitung.

## Relasi ke output lain

Data yang sama dengan `../workload_timeseries/` dibagi kapasitas PM; angka per
PM: `../../experiments/static/*/metrics.csv`, `raw.npz`.
