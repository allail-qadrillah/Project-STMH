# GA server consolidation

Modular, offline Python simulation: full-day static random baseline/static GA,
then 24-window cold-start/warm-start GA. CPU demand and capacity use **vCPU**.
VM capacity 1 vCPU, PM capacity 16 vCPU, 12 PMs, safe threshold 0.80.
These capacities are simulation assumptions, not PlanetLab-provided allocations.

## Run

From `server_consolidation_ga/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python main.py --config configs/experiment_config.yaml
```

CLI runs acceptance tests again before optimization. Gate includes hand calculations,
operators, infeasible-window continuation, reproducibility, and complete five-VM
pipeline with 100 updates and all 24 dynamic windows. Gate report is saved with run.
Test seeds are isolated checks, not extra experimental runs. Each method has exactly
one experimental run, master seed **42**, NumPy **PCG64**. Runtime varies between runs;
placements and fitness histories reproduce with identical inputs/config/software.

All settings reside in `configs/experiment_config.yaml`; relative paths resolve
against configuration file, not current shell directory. Run output is
`outputs/seed_42/`. Existing destinations are never overwritten. Change output
directory in configuration to rerun without discarding earlier results.

Validation-only command (existing `outputs/validation/` is preserved):

```bash
.venv/bin/python main.py --config configs/experiment_config.yaml --validate-data
```

## Methodology

- Population 50, tournament size 3 with replacement, uniform crossover 0.80,
  reassignment mutation 0.02 per gene to a different PM, two unchanged elites.
- Equal-best tournament participants and elitism ties resolve randomly.
  Best-so-far retains first-seen chromosome on equal fitness.
- Generation 0 evaluates initialization; generations 1–100 are reproduction updates.
  No early stopping, repair, heuristic placement, or PM-label canonicalization.
- Warm Window 2 onward: one previous selected chromosome plus 49 independently
  uniform random chromosomes. No mutated initialization copies. Window 1 uses
  independently generated cold/warm populations; common initial placement is only
  migration reference.
- Static placement uses all 288 samples. Feasible objective is active PMs / 12.
  Migration from random baseline is recorded, not optimized.
- Dynamic placement uses 12 samples/window. Feasible objective is
  `0.70 * active_pm_count / 12 + 0.30 * migrations / vm_count`.
- Feasible fitness: `1 + 1/(1+objective)`; infeasible fitness: `1/(1+V)`.
  Pointwise CPU limit and normalized violation both use configured tolerance.
  Overload event counting retains strict utilization `> 0.80`.
- Infeasible windows keep status and selected minimum-violation chromosome;
  processing continues using that chromosome as next reference and warm candidate.
- Migration rate includes all 24 transitions, including initial placement to Window 1.
  Temporal means across windows/samples are labeled; no cross-run statistics exist.

`OPEN_DECISIONS.md` records approved overrides to original version-4.0 specification.
Stream keys are `(configured_role_id, one_based_window)`; static/initial streams
use window 0. Independent roles/windows share master seed 42, not generator state.

## Input schema

`planetlab_per_vm_files`: one UTF-8 file per VM, one numeric sample per line,
no header or timestamp column. Filename is VM ID; line number is sample index.
Files sort lexicographically. A null `file_pattern` selects all immediate files;
otherwise it is an explicit glob relative to `dataset.path`.

Wrong sample count or blank samples exclude VM and record reason. Nonnumeric,
non-finite, negative, or out-of-range values stop loading, including invalid values
in wrong-length traces. `input_scale: percentage` validates [0,100] and divides
once; `ratio` validates [0,1] without dividing. No scale guessing. Same processed
matrix and stable VM IDs are used by every method.

## Outputs

`main.py --config configs/experiment_config.yaml` writes one run into
`<output.directory>/seed_42/` using this layout (also created directly by the
pipeline for fresh runs):

- `data/`: processed matrix, VM order, file manifest, workload summary,
  validation/exclusion log.
- `experiments/static/{baseline,ga}/`: `placement.csv`, `metrics.csv`,
  `raw.npz`; GA adds `fitness_history.csv`. `static/baseline_placements.csv`,
  `ga_placements.csv`, `fitness_history.csv` are the requested combined views.
- `experiments/dynamic/initial_placement.csv`: shared migration reference.
- `experiments/dynamic/{cold_start,warm_start}/`: `window_01/`–`window_24/` GA
  artifacts, `per_window_metrics.csv`, plus combined `placements.csv` and
  `fitness_history.csv` keyed by seed and window.
- `visualizations/{workload,utilization,convergence,comparison}/`: original
  figures by analytical purpose; every category has its own README.
- `visualizations/workload_timeseries/`, `visualizations/performance_comparison/`:
  figures reconstructed from saved placements and metrics (PNG + SVG).
- `summaries/`: resolved configuration, provenance, source/test hashes, RNG
  stream records, acceptance report, `experiment_summary.csv`, `run_status.csv`,
  `execution_status.json`.
- `README.md` files throughout document axes, legends, and interpretation limits.

Existing destinations are never overwritten. Change `output.directory` (and, for
the organizer, `output.existing_run`) to rerun; relative paths resolve against
the configuration file. Output folders and figure stems are configurable via
`output.folders` and `output.figure_names` without code changes.

## Reorganize saved outputs without rerunning

```bash
.venv/bin/python organize_outputs.py --config configs/experiment_config.yaml \
  --check-reference-summary
```

Copies the finished run (`output.existing_run`) into the organized layout after
verifying it: workload shape, 51 placements, PM ranges, per-window
reconstruction, and every saved metric are recomputed and compared with the
stored values first. Figures are rendered from saved placements/metrics only; no
GA is executed. Writes `summaries/structure_validation.json` and a per-file
`structure_migration_log.md` (source, destination, action, SHA-256 status).
Originals remain byte-identical; conflicting destinations abort before copying.

No claim of global optimality, power savings, real-time control, or prediction.
No migration overhead, network constraint, power model, or extra objective.
Theoretical basis: specification Section 21, course GA materials, Yang (2014), Ch. 5.

Existing `outputs/validation/` records earlier data-only checks. Its null seed and
old 30-run configuration describe that historical validation, not current
experiments. `outputs/seed_42/` also retains its pre-reorganization flat layout
(`static/`, `dynamic/`, `plots/`) as the untouched original of the organized copy
at the outputs root.
Separate 13-VM tests check capacity boundary: at most ten 1-vCPU VMs cannot
overload 12.8-vCPU safe PM capacity.
