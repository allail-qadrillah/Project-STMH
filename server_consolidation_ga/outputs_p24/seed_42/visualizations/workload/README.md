# Beban kerja

## Tujuan

Menampilkan total beban CPU seluruh trace sepanjang waktu: seberapa besar
permintaan total yang diberikan populasi VM kepada infrastruktur.

## Daftar figur

- `workload_timeseries.png`

## Sumbu

- Sumbu X: indeks cuplikan (sample) 0–287 (interval 5 menit, satu hari).
- Sumbu Y: beban CPU agregat dalam vCPU.

## Cara menghitung beban kerja

Setiap nilai trace VM adalah rasio utilisasi CPU; dikalikan kapasitas VM
(1.0 vCPU) menjadi permintaan vCPU. Nilai agregat
yang diplot adalah penjumlahan atas seluruh 1.033 VM per cuplikan.

## Bedanya beban kerja (workload) dan rasio utilisasi

Beban kerja adalah jumlah CPU absolut (vCPU). Rasio utilisasi adalah beban dibagi
kapasitas (kapasitas PM 16.0 vCPU), menghasilkan pecahan
0–1 yang bisa diperbandingkan dengan ambang aman 0.8.

## Pertanyaan riset yang dijawab

Seberapa besar dan bervariasi total permintaan, dan seberapa jauh ia di bawah
kapasitas aman total 24 × 12.8 =
307.2 vCPU? Fluktuasi memotivasi pendekatan
dinamis per window; margin kecil antara beban agregat dan kapasitas aman
menjelaskan mengapa konsolidasi di bawah 12 PM sulit dicapai.

## Batasan

- Beban agregat menyembunyikan sebaran per PM; lihat `../workload_timeseries/`.
- Tidak ada klaim tentang burstiness atau korelasi antar VM.

## Relasi ke output lain

Matriks sumber: `../../data/workload_matrix.npy`; ringkasan numerik:
`../../data/dataset_summary.csv`.
