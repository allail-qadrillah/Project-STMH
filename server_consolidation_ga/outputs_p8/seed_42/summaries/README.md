# Ringkasan

## Tujuan tiap file

- `experiment_config.json` — konfigurasi efektif, provenance dataset, versi
  lingkungan, hash sumber, deskripsi RNG, hasil gerbang penerimaan.
- `experiment_summary.csv` — satu baris per metode berisi metrik akhir.
- `run_status.csv` — status kelayakan run statik dan setiap window dinamis.
- `random_streams.json` — catatan seluruh 51 stream RNG (role, window, spawn
  key, state PCG64 awal/akhir).
- `acceptance_tests.txt` — laporan tes penerimaan yang benar-benar dijalankan
  sebelum optimasi.
- `execution_status.json` — status pipeline: RUNNING/COMPLETED/FAILED.
- `structure_validation.json` — hasil verifikasi reorganisasi (hanya ada pada
  pohon yang direorganisasi).

## Makna metrik yang dilaporkan

- `status`/kelayakan: FEASIBLE berarti beban setiap pasangan PM/cuplikan ≤
  12.8 vCPU (ambang 0.8) dalam toleransi 1e-9; INFEASIBLE berarti
  ada pelanggaran.
- `active_pm_count` (statik) atau `mean/minimum/maximum_active_pm_count`
  (dinamis): PM yang menampung VM.
- `migration_count`: statik — dari placement baseline; dinamis — penjumlahan 24
  transisi window termasuk placement awal ke Window 1; `migration_rate` dibagi
  VM × 24 transisi.
- `overload_events`: pasangan PM/cuplikan dengan utilisasi ketat > 0.8.
- `runtime_seconds`: waktu dinding terukur; `feasible_windows`: window dinamis
  yang memenuhi kendala.

## Cara menafsirkan kelayakan dan status run

`execution_status.json` COMPLETED berarti pipeline selesai, tidak berarti semua
placement layak. Kelayakan keseluruhan bernilai INFEASIBLE selama ada metode/
window yang tidak layak (baseline acak statik tidak layak). Nilai setiap metode
dinilai dari barisnya sendiri di `experiment_summary.csv` dan `run_status.csv`
per window. Granularitasnya juga berbeda: statik satu keputusan sepanjang hari,
dinamis 24 keputusan per window.

## Mengapa tidak ada deviasi standar

Metodologi yang disetujui melakukan tepat satu run per metode dengan master
seed tetap. Deviasi standar lintas run membutuhkan beberapa run, yang tidak
dilakukan; kolomnya karena itu memang tidak ada, bukan data yang hilang. Nilai
tunggal tidak punya interval kepercayaan; perbedaan antar metode adalah
observasi run tunggal, bukan bukti statistik.
