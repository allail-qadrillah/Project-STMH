# HOW-TO-RUN — Menjalankan dan Men-tuning Eksperimen

Panduan menjalankan ulang eksperimen dan mengubah parameter (misalnya jumlah PM).
Semua parameter ada di `configs/experiment_config.yaml`; validator `src/config.py`
yang menentukan mana yang boleh diubah.

## Prasyarat

```bash
cd server_consolidation_ga
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Dataset harus ada di `../../data/planetlab/20110420` (relatif ke file config).

## Perintah utama

```bash
# Eksperimen penuh (gerbang penerimaan 22 tes jalan otomatis dulu,
# lalu optimasi statik + 48 window dinamis)
.venv/bin/python main.py --config configs/experiment_config.yaml

# Validasi data saja, tanpa GA
.venv/bin/python main.py --config configs/experiment_config.yaml --validate-data

# Tes saja
.venv/bin/python -m unittest discover -s tests -v
```

### Tanpa venv (environment yang sudah terpasang)

```bash
/tmp/opencode/stmh-venv/bin/python main.py --config configs/experiment_config.yaml
```

## Parameter yang boleh diubah

| Kunci config | Ketentuan validator |
|---|---|
| `infrastructure.available_pm_count` | Jumlah PM; integer ≥ 2 |
| `infrastructure.pm_cpu_capacity_vcpu` | Kapasitas PM; > 0 |
| `infrastructure.safe_cpu_threshold` | Ambang aman; 0–1 |
| `genetic_algorithm.population_size` | Integer ≥ 1 |
| `genetic_algorithm.max_generations` | Jumlah pembaruan reproduksi |
| `genetic_algorithm.tournament_size` | ≤ `population_size` |
| `genetic_algorithm.crossover.probability` | 0–1 |
| `genetic_algorithm.mutation.per_gene_probability` | 0–1 |
| `genetic_algorithm.elitism_count` | < `population_size` |
| `fitness.server_weight` + `fitness.migration_weight` | Harus berjumlah tepat 1 |
| `experiments.dynamic.window_size_samples` | Harus habis membagi 288 |
| `output.directory` | Folder tujuan; wajib belum ada saat run |

Output selalu masuk ke `<output.directory>/seed_42/`. Tujuan yang sudah ada
selalu ditolak (tidak pernah menimpa hasil lama). Ubah `output.directory`
setiap kali menjalankan varian baru.

## Parameter yang terkunci (menolak perubahan)

- `project.master_seed` harus 42, `random_seeds` harus 1, `rng` harus PCG64.
- `project.stream_ids`: lima role, ID integer unik ≥ 0.
- Seluruh kebijakan `methodology:` dan `preprocessing:` bentuknya sudah fix.
- `experiments.static.*` / `experiments.dynamic.*` tidak boleh dimatikan.
- `dataset.*`: skema `planetlab_per_vm_files`, 1.033 VM, 288 cuplikan,
  `input_scale` tidak boleh dikira-kira.

Mengubah butir terkunci = mengubah metodologi, bukan tuning. Bisa dilakukan
dengan mengedit `src/config.py` dan `tests/test_ga.py` bersamaan, lalu
men-decision-kan lewat `OPEN_DECISIONS.md` terlebih dahulu.

## Contoh: tuning jumlah PM menjadi 10

1. Salin config (salinan harus tetap berada di `configs/`; path relatif
   dataset dan output dihitung dari lokasi file config):

   ```bash
   cp configs/experiment_config.yaml configs/experiment_p10.yaml
   ```

2. Edit `configs/experiment_p10.yaml`:

   ```yaml
   infrastructure:
     available_pm_count: 10
   output:
     directory: "../outputs_p10"
   ```

3. Jalankan:

   ```bash
   .venv/bin/python main.py --config configs/experiment_p10.yaml
   ```

4. Hasil ada di `outputs_p10/seed_42/` dengan layout terorganisir yang sama
   (data, experiments, visualizations, summaries, README Bahasa Indonesia).
   Bandingkan dengan run lama melalui file ringkasan masing-masing:

   ```bash
   cat outputs/seed_42/summaries/experiment_summary.csv
   cat outputs_p10/seed_42/summaries/experiment_summary.csv
   ```

## Panduan memilih jumlah PM

Kapasitas aman total = `available_pm_count` × `pm_cpu_capacity_vcpu` ×
`safe_cpu_threshold`. Beban agregat harian dataset ini 93,37–123,88 vCPU, jadi:

- 123,88 / (16 × 0,80) ≈ 9,68 → **minimum 10 PM** agar peluang feasible ada.
- 9 PM atau lebih sedikit hampir pasti semua window INFEASIBLE (tidak error;
  pipeline tetap lanjut dan menandai status per window).

## Catatan interpretasi hasil tuning

- Objektif memakai `active_pm_count / available_pm_count`, jadi nilai fitness,
  rasio PM aktif, dan migrasi antar config dengan N berbeda tidak langsung
  sebanding. Bandingkan metrik dalam konteks N masing-masing.
- PM ID di `placement.csv` otomatis jadi 1..N sesuai config.
- Satu run per config (seed tetap 42). Perbedaan antar varian adalah observasi
  run tunggal, bukan bukti statistik.
