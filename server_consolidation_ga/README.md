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

Within `outputs/seed_42/`:

- `data/`: processed matrix, VM order, exact filenames/SHA-256 manifest, observed
  workload summary, validation/exclusion log.
- `static/{baseline,ga}/`: `placement.csv`, `metrics.csv`, `raw.npz`.
  GA adds `fitness_history.csv`. Combined table: `static/per_seed_metrics.csv`.
- `dynamic/initial_placement.csv`: shared migration reference.
- `dynamic/{cold_start,warm_start}/window_01/` through `window_24/`: same GA
  artifacts, plus migration reference and one-based sample ranges.
- `dynamic/{cold_start,warm_start}_per_window.csv`: window comparison tables.
- `raw.npz`: placement, PM loads (vCPU), utilization ratios; GA also includes full
  initial population and best-so-far chromosomes for all 101 generations.
  Chromosome columns map to `data/vm_order.csv`; PM column index 0 means PM ID 1.
- `fitness_history.csv`: generation, population size/fitness, feasible count,
  best-so-far fitness and complete metrics, including status and violation.
- `plots/`: workload, convergence, utilization heatmaps/distribution, static/dynamic
  comparisons, runtime totals and per-window runtime.
- `summaries/experiment_config.json`: resolved settings, dimensions, seed, provenance,
  Python/NumPy/PyYAML/Matplotlib versions, source/test hashes, gate result.
- `summaries/random_streams.json`: role, window, seed, spawn key, pool size,
  initial/final PCG64 state for all 51 streams.
- `summaries/acceptance_tests.txt`: actual pre-run test report.
- `summaries/experiment_summary.csv`, `run_status.csv`: actual single-run results,
  explicit infeasible statuses, daily migration/runtimes and window aggregates.
- `summaries/execution_status.json`: RUNNING, COMPLETED, or FAILED, separate from
  placement feasibility. COMPLETED never implies every placement is feasible.

No claim of global optimality, power savings, real-time control, or prediction.
No migration overhead, network constraint, power model, or extra objective.
Theoretical basis: specification Section 21, course GA materials, Yang (2014), Ch. 5.

Existing `outputs/validation/` records earlier data-only checks. Its null seed and
old 30-run configuration describe that historical validation, not current experiments.
Separate 13-VM tests check capacity boundary: at most ten 1-vCPU VMs cannot
overload 12.8-vCPU safe PM capacity.
