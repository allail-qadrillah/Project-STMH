# Experiment 1 — Context Summary (for AI handover)

Full report: `outputs/research_handover/EXPERIMENT_1_ACTIVE_PM_AWARE_INITIALIZATION.md`.
Repo root: `/mnt/e/.TEMPORARY/Project STMH`. Branch: `experiment/active-pm-aware-initialization` (HEAD `ed24a32`).

## What the project is

A Python (NumPy) genetic algorithm for the **server consolidation problem**: pack 1,033 PlanetLab VMs onto the fewest 16-vCPU Physical Machines so that per-PM CPU never exceeds the 80% safe threshold (→ 12.8 vCPU effective) at any of 288 five-minute timestamps. VM capacity 1 vCPU. Workload date 20110420 (beloglazov/planetlab-workload-traces). Peak aggregate demand 123.88 vCPU → aggregate lower bound 10 PMs (never achieved here; GA found 14).

## What the research investigates

Whether GA *initialization* and *operator* changes improve consolidation, evaluated as three isolated branch experiments against an unmodified baseline on `main`:

- **Experiment 1 (this one)** — active-PM-aware (compact) initialization.
- Experiment 2 — feasibility-preserving relocation mutation.
- Experiment 3 — consolidation-aware mutation.

## What Experiment 1 changes

Only `initialize_population` in `src/genetic_algorithm.py:15–28`.

- Original: every chromosome = uniform random VM→PM over all 24 PMs.
- Experiment 1: **40 compact + 10 uniform** chromosomes (cold/static/warm-window-1); **1 inherited + 39 compact + 10 uniform** (warm windows 2–24).
- "Compact" = pick a random PM subset of size 1–23, assign each VM uniformly within it. **It is a random allele-range restriction, NOT a CPU-aware/feasibility-aware packer** (no first-fit, no threshold enforcement, no time-series demand use). Infeasible candidates are retained by design.

Everything else — selection (tournament 3, replacement), uniform crossover (0.80, 50% gene mask), random-reassignment mutation (0.02/gene, never same PM), elitism (2), constraint-dominant fitness, generational replacement — is **identical** to the original GA.

## How the algorithm works

1. Load 1,033 per-VM files (percentage scale → /100) → 288×1033 matrix → ×1 vCPU demand.
2. Fitness (maximize): feasible = `1 + 1/(1 + cost)`; static cost = active/24; dynamic cost = `0.70·active/24 + 0.30·migrations/1033`. Infeasible = `1/(1 + V)`, V = mean squared normalized CPU violation. Feasible ⟺ all pointwise loads ≤ 16·0.80 + 1e-9 and V ≤ 1e-9.
3. Static = 1 run (gen 0 + 100 updates). Dynamic = 24 windows × 12 samples, cold-start (fresh init each window) and warm-start (inherit previous placement).
4. Seed 42, NumPy PCG64, streams keyed `(role_id, window)`; shared migration reference `(2,0)`.

## Important parameters

1033 VMs · 288 samples · 5 min · 1 vCPU/VM · 16 vCPU/PM · 24 PMs · threshold 0.80 · pop 50 · 100 reproduction updates (101 generations) · tournament 3 w/ replacement · uniform crossover 0.80 · mutation 0.02/gene · elitism 2 · weights 0.70/0.30 · tolerance 1e-9 · seed 42 · PCG64 · 24 dynamic windows · 12 samples/window.

## Results and limitations

Single seed 42, descriptive only (no statistical claims).

| Track | Original GA | Experiment 1 |
|---|---|---|
| Static active PMs | 24 | **14** |
| Static max PM util | 0.582 | 0.791 |
| Dynamic cold (mean active) | 24.0 | **12.75** (11–16) |
| Dynamic warm (mean active) | 24.0 | **13.125** (12–14) |
| Dynamic warm migrations | 785 | 5,942 |

The 14-PM solution exists **at generation 0**; evolution never improves it — initialization does all the work. Trade-off: consolidation raises dynamic migrations. All windows of all arms feasible, zero overloads.

## Relevant source files

- `server_consolidation_ga/src/genetic_algorithm.py` (init 15–28, `run_ga` 45–111)
- `src/{fitness,selection,crossover,mutation,placement,evaluation,randomness}.py`
- `src/{static,dynamic}_experiment.py`, `src/experiment.py`, `src/reporting.py`, `src/diagnostics.py`
- `configs/controlled_24.yaml` (approved comparison; `experiment_config.yaml` is 12-PM legacy only)
- `evaluate_frozen.py` (produced results), `verify_full_results.py` (read-only proof), `compare_full_results.py`
- Results: `outputs/full_seed42/{initialization,original}/**`, provenance snapshots under `outputs/full_seed42/provenance/*`

## Important open questions

1. Optimal active-PM count unknown — GA found 14, aggregate bound 10, no exact solver run.
2. No statistical inference (single seed). Replication needed for a paper.
3. Results were generated from HEAD `21cf4c1` + uncommitted edits (frozen in `provenance/`); the generating worktree was deleted; live branch is 2 commits ahead.
4. Variant naming drift: frozen config says "active_pm_initialization", current `experiment.py` says "active_pm_aware_initialization".
5. Operator weakness is inferred, not isolated (Experiments 2–3 handle operators).