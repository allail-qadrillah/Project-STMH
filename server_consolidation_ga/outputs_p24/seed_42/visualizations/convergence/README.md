# Konvergensi

## Tujuan

Menampilkan proses optimasi GA.

## Daftar figur

- `ga_convergence_dynamic.png`
- `ga_convergence_static.png`

- `ga_convergence_static.png` — GA statik, satu run sepanjang hari.
- `ga_convergence_dynamic.png` — 24 window cold-start dan 24 window warm-start.

## Sumbu

- Sumbu X: indeks generasi. Generasi 0 adalah populasi awal; generasi 1–100
  adalah pembaruan reproduksi (total 101 populasi terevaluasi).
- Sumbu Y: fitness best-so-far.

## Desain fitness dominan-kendala

Fitness placement layak: `1 + 1/(1+objektif)`; placement tidak layak: `1/(1+V)`
dengan V pelanggaran ternormalisasi. Best-so-far menyimpan kromosom pertama yang
terlihat saat seri, sehingga kurva tidak pernah turun.

## Nilai fitness layak vs. tidak layak

Fitness layak berada di (1, 2]; fitness tidak layak di (0, 1). Rentangnya tidak
komparable: fitness tak-layak yang naik hanya berarti pelanggaran menurun, bukan
solusi layak yang lebih baik. Jangan menafsirkan fitness lebih tinggi sebagai
solusi layak lebih baik tanpa memeriksa status kelayakannya. Kurva yang melompat
dari bawah 1 ke atas 1 menandai generasi layak pertama; setelah itu, bagian datar
berarti tidak ditemukan solusi first-seen yang lebih baik.

## Pertanyaan riset yang dijawab

Apakah GA cepat mencapai placement yang layak dengan objektif rendah, dan apakah
warm start memanfaatkan solusi window sebelumnya secara efektif?

## Batasan

- Satu run; bentuk konvergensi bergantung pada seed.
- Figur dinamis menampilkan riwayat 101 generasi tiap window sendiri, bukan
  satu optimasi global sepanjang hari.

## Relasi ke output lain

Nilai yang sama dengan `../../experiments/static/ga/fitness_history.csv` dan
`../../experiments/dynamic/*/window_*/fitness_history.csv`; kromosom terbaik
per generasi ada di `raw.npz`.
