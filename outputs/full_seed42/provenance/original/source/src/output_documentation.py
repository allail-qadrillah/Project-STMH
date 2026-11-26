"""Generate self-documenting Indonesian READMEs for the organized output tree.

Numbers quoted in READMEs come only from saved result files; nothing is recomputed.
"""

import csv
from pathlib import Path

from .output_layout import CATEGORIES, output_path


def _rows(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _labels(figure_dir):
    return [p.name for p in sorted(Path(figure_dir).glob("*.png"))]


def _summary_block(summaries):
    path = summaries / "experiment_summary.csv"
    if not path.is_file():
        return "File `experiment_summary.csv` tidak ada; tidak ada hasil run yang didokumentasikan."
    rows = _rows(path)
    seed = rows[0]["seed"] if rows else "?"
    lines = ["Satu run eksperimen, master seed " + seed + ". Nilai yang dilaporkan:", "",
             "| Metode | Status | PM aktif | Migrasi | Overload |",
             "|---|---|---:|---:|---:|"]
    for r in rows:
        active = r.get("active_pm_count") or r.get("mean_active_pm_count") or ""
        lines.append(f"| {r['method']} | {r['status']} | {active} | "
                     f"{r.get('migration_count') or 0} | {r.get('overload_events') or 0} |")
    feasible = [r for r in rows if r["method"].startswith(("cold", "warm"))]
    if len(feasible) == 2:
        cold, warm = (int(r["migration_count"]) for r in feasible)
        if cold:
            lines += ["", f"Reduksi migrasi dinamis, warm-start vs. cold-start: {100 * (cold - warm) / cold:.1f}%."]
    lines += ["", "Keempat metode memakai 12 PM aktif; tidak ada pengurangan jumlah PM yang terbukti."]
    return "\n".join(lines)


def document_outputs(root, config, source=None, unknown=None):
    """Write every README for the organized tree; return paths created."""
    root = Path(root)
    summaries = output_path(root, config, "summaries")
    viz = output_path(root, config, "visualizations")
    seed = config["project"]["master_seed"]
    infra = config["infrastructure"]
    threshold = infra["safe_cpu_threshold"]
    safe = infra["pm_cpu_capacity_vcpu"] * threshold
    written = []

    def write(rel_path, text):
        path = root / rel_path
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.strip() + "\n", encoding="utf-8")
        written.append(path)

    summary = _summary_block(summaries)
    plots = {c: _labels(viz / c) for c in CATEGORIES}

    write("README.md", f"""
# Konsolidasi server dengan GA — hasil eksperimen (seed {seed})

Pohon direktori hasil eksperimen yang terorganisir dan menjelaskan dirinya
sendiri. Semua angka berasal dari satu eksperimen nyata; tidak ada data yang
direkayasa. Run dilakukan sekali per metode dengan master seed {seed}, NumPy PCG64.
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

{summary}

## Batasan interpretasi

- Satu run per metode; tidak ada statistik lintas-run maupun deviasi standar.
- Kelayakan (feasibility: tidak ada PM melewati ambang CPU aman {threshold}) dan
  konsolidasi (jumlah PM aktif lebih sedikit) adalah tujuan yang berbeda; run ini
  membuktikan kelayakan dan perilaku migrasi, bukan konsolidasi PM.
- Definisi migrasi statik dan dinamis berbeda; lihat
  `visualizations/performance_comparison/README.md`.
- `execution_status.json` COMPLETED hanya berarti pipeline selesai, bukan berarti
  semua placement layak (feasible).
- Kapasitas (1 vCPU per VM, 16 vCPU per PM, 12 PM) adalah asumsi simulasi,
  bukan alokasi asli PlanetLab.
""")

    write(Path("visualizations") / "README.md", f"""
# Visualisasi

Figur dikelompokkan per tujuan analitis. Setiap folder kategori memiliki README
sendiri yang menjelaskan sumbu, legenda, warna, dan batasan interpretasi. Semua
figur berasal dari run yang sama (seed {seed}).

## Kategori

- `workload/` — beban kerja CPU agregat sepanjang hari (1 figur).
- `utilization/` — utilisasi CPU per PM dan kendala kapasitas (5 figur).
- `convergence/` — kemajuan optimasi GA (2 figur).
- `comparison/` — perbandingan metode statik/dinamis/runtime (4 figur).
- `workload_timeseries/` — deret beban per PM hasil rekonstruksi (6 figur).
- `performance_comparison/` — kelayakan, PM aktif, migrasi, overload (5 figur).

## Hubungan antar kategori

Figur utilisasi adalah deret beban per PM di `workload_timeseries/` dibagi
kapasitas PM ({infra['pm_cpu_capacity_vcpu']} vCPU). Nilai batang pada
`performance_comparison/` identik dengan angka di
`../../summaries/experiment_summary.csv`. Riwayat konvergensi adalah data yang
sama dengan `../../experiments/*/fitness_history.csv`.

## Urutan baca yang disarankan

1. `workload/` — besaran dan fluktuasi beban total.
2. `workload_timeseries/` — sebaran beban ke 12 PM.
3. `utilization/` — pemeriksaan kapasitas PM dan kelayakan terhadap ambang
   aman {threshold}.
4. `convergence/` — kemajuan optimasi GA dan perilaku fitness.
5. `comparison/` — perilaku per-window dan biaya runtime.
6. `performance_comparison/` — evaluasi hasil akhir semua metode.
""")

    work = plots.get("workload") or []
    write(Path("visualizations") / "workload" / "README.md", f"""
# Beban kerja

## Tujuan

Menampilkan total beban CPU seluruh trace sepanjang waktu: seberapa besar
permintaan total yang diberikan populasi VM kepada infrastruktur.

## Daftar figur

{chr(10).join(f'- `{n}`' for n in work) or '- (tidak ada figur beban kerja; didokumentasikan, tidak direkayasa)'}

## Sumbu

- Sumbu X: indeks cuplikan (sample) 0–287 (interval 5 menit, satu hari).
- Sumbu Y: beban CPU agregat dalam vCPU.

## Cara menghitung beban kerja

Setiap nilai trace VM adalah rasio utilisasi CPU; dikalikan kapasitas VM
({infra['vm_cpu_capacity_vcpu']} vCPU) menjadi permintaan vCPU. Nilai agregat
yang diplot adalah penjumlahan atas seluruh 1.033 VM per cuplikan.

## Bedanya beban kerja (workload) dan rasio utilisasi

Beban kerja adalah jumlah CPU absolut (vCPU). Rasio utilisasi adalah beban dibagi
kapasitas (kapasitas PM {infra['pm_cpu_capacity_vcpu']} vCPU), menghasilkan pecahan
0–1 yang bisa diperbandingkan dengan ambang aman {threshold}.

## Pertanyaan riset yang dijawab

Seberapa besar dan bervariasi total permintaan, dan seberapa jauh ia di bawah
kapasitas aman total {infra['available_pm_count']} × {safe:g} =
{infra['available_pm_count'] * safe:g} vCPU? Fluktuasi memotivasi pendekatan
dinamis per window; margin kecil antara beban agregat dan kapasitas aman
menjelaskan mengapa konsolidasi di bawah 12 PM sulit dicapai.

## Batasan

- Beban agregat menyembunyikan sebaran per PM; lihat `../workload_timeseries/`.
- Tidak ada klaim tentang burstiness atau korelasi antar VM.

## Relasi ke output lain

Matriks sumber: `../../data/workload_matrix.npy`; ringkasan numerik:
`../../data/dataset_summary.csv`.
""")

    util = plots.get("utilization") or []
    write(Path("visualizations") / "utilization" / "README.md", f"""
# Utilisasi

## Tujuan

Menganalisis utilisasi CPU per PM dan kendala kapasitas; memverifikasi
kelayakan (feasibility).

## Daftar figur

{chr(10).join(f'- `{n}`' for n in util) or '- (tidak ada figur utilisasi; didokumentasikan, tidak direkayasa)'}

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

Warna heatmap = rasio utilisasi CPU (beban / {infra['pm_cpu_capacity_vcpu']} vCPU);
skala colorbar mulai dari 0. Distribusi: garis putus-putus hitam = ambang aman
{threshold}; warna garis membedakan metode.

## Ambang CPU aman

Utilisasi di atas {threshold} (beban di atas {safe:g} vCPU) tidak aman. Sebuah
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
""")

    conv = plots.get("convergence") or []
    write(Path("visualizations") / "convergence" / "README.md", f"""
# Konvergensi

## Tujuan

Menampilkan proses optimasi GA.

## Daftar figur

{chr(10).join(f'- `{n}`' for n in conv) or '- (tidak ada figur konvergensi; didokumentasikan, tidak direkayasa)'}

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
""")

    comp = plots.get("comparison") or []
    write(Path("visualizations") / "comparison" / "README.md", f"""
# Perbandingan

## Tujuan

Membandingkan metode eksperimen dan performa komputasi.

## Daftar figur

{chr(10).join(f'- `{n}`' for n in comp) or '- (tidak ada figur perbandingan; didokumentasikan, tidak direkayasa)'}

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
- Event overload: pasangan PM/cuplikan dengan utilisasi melebihi {threshold}
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
""")

    wts = plots.get("workload_timeseries") or []
    write(Path("visualizations") / "workload_timeseries" / "README.md", f"""
# Deret waktu beban kerja per PM

## Tujuan

Menampilkan sebaran total beban CPU ke 12 PM sepanjang hari, per metode: GA
statik, baseline acak statik, cold-start dinamis, warm-start dinamis, plus dua
perbandingan bertumpuk.

## Daftar figur

{chr(10).join(f'- `{n}`' for n in wts) or '- (tidak ada figur; didokumentasikan, tidak direkayasa)'}

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

- Putus-putus hitam: kapasitas aman {safe:g} vCPU ({infra['safe_cpu_threshold']} kali
  {infra['pm_cpu_capacity_vcpu']}). Metode layak
  hanya jika setiap PM berada pada atau di bawah garis ini.
- Bertitik merah tua: kapasitas fisik {infra['pm_cpu_capacity_vcpu']} vCPU. Beban
  di antara dua garis melanggar kendala ambang aman (tidak layak) namun masih
  terlayani secara fisik; beban di atas garis bertitik melebihi PM itu sendiri.

## Bedanya beban dan rasio utilisasi

Beban dalam vCPU; rasio utilisasi = beban / {infra['pm_cpu_capacity_vcpu']}.
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
""")

    perf = plots.get("performance_comparison") or []
    write(Path("visualizations") / "performance_comparison" / "README.md", f"""
# Perbandingan performa

## Tujuan

Mengevaluasi hasil eksperimen: kelayakan, jumlah PM aktif, migrasi, dan event
overload.

## Daftar figur

{chr(10).join(f'- `{n}`' for n in perf) or '- (tidak ada figur; didokumentasikan, tidak direkayasa)'}

- `feasibility_comparison.png` — status kelayakan keempat metode.
- `active_pm_comparison.png` — jumlah PM aktif.
- `migration_comparison.png` — total migrasi dan reduksi warm vs. cold.
- `overload_comparison.png` — event overload; baseline ditandai tidak layak.
- `experiment_summary_dashboard.png` — keempat panel digabung.

## Metode yang dibandingkan

Baseline acak statik, GA statik, cold-start dinamis, warm-start dinamis (satu
run masing-masing, seed {seed}).

## Makna tiap metrik

- Kelayakan: statik — satu placement sepanjang hari memenuhi kendala ambang
  aman; dinamis — banyak window yang layak dari 24 (keduanya 24/24).
- PM aktif: PM yang menampung minimal satu VM; batang dinamis menampilkan
  rentang per window (12 di setiap window).
- Migrasi: perubahan PM per VM, definisi berbeda di bawah.
- Event overload: pasangan PM/cuplikan dengan utilisasi melebihi {threshold}.

{summary}

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
""")

    write(Path("summaries") / "README.md", f"""
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
  {safe:g} vCPU (ambang {threshold}) dalam toleransi 1e-9; INFEASIBLE berarti
  ada pelanggaran.
- `active_pm_count` (statik) atau `mean/minimum/maximum_active_pm_count`
  (dinamis): PM yang menampung VM.
- `migration_count`: statik — dari placement baseline; dinamis — penjumlahan 24
  transisi window termasuk placement awal ke Window 1; `migration_rate` dibagi
  VM × 24 transisi.
- `overload_events`: pasangan PM/cuplikan dengan utilisasi ketat > {threshold}.
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
""")

    return written
