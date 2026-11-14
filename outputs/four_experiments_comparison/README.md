# Four-approach GA comparison

Seed 42 single-run comparison. No statistical significance or winner claim.

## Data availability

Original, Experiment 1, and Experiment 2: static plus all 24 cold-start and 24 warm-start windows. Experiment 3: static plus cold-start windows 1–4 only; warm-start has zero completed windows. Missing windows are omitted, never set to zero, interpolated, or extrapolated. Experiment 3 run remains incomplete (`RUNNING` status at source capture).

## Static comparison

| Approach | Source branch | PMs | Status | Active PMs | PM reduction vs 24 | Overload events | Migrations | GA runtime (s) |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Initial GA (Original Baseline) | main (original source, isolated replay) | 24 | FEASIBLE | 24 | 0.00% | 0 | 987 | 8.431 |
| Experiment 1: Active-PM-aware Initialization | experiment/active-pm-aware-initialization | 24 | FEASIBLE | 14 | 41.67% | 0 | 990 | 5.574 |
| Experiment 2: Feasibility-preserving Relocation | experiment/feasibility-preserving-relocation | 24 | FEASIBLE | 15 | 37.50% | 0 | 984 | 114.512 |
| Experiment 3: Consolidation-aware Mutation | experiment/consolidation-aware-mutation | 24 | FEASIBLE | 11 | 54.17% | 0 | 979 | 3852.742 |

Static migration count is measured against each run's random static placement reference; it is not a cross-approach migration comparison. Static runs use 24 PMs for all rows. Historical main output uses 12 PMs and is excluded from this comparison.

## Dynamic availability

| Approach | Cold-start windows | Warm-start windows |
|---|---:|---:|
| Initial GA (Original Baseline) | 24/24 | 24/24 |
| Experiment 1: Active-PM-aware Initialization | 24/24 | 24/24 |
| Experiment 2: Feasibility-preserving Relocation | 24/24 | 24/24 |
| Experiment 3: Consolidation-aware Mutation | 4/24 | 0/24 |

Dynamic migration includes initial-placement-to-window-1 and subsequent window transitions, consistently within each run. Feasible fractions and PM utilization use original definitions. Fitness/convergence is best-so-far per generation.

## Runtime and diagnostics

`dynamic_window_summary.csv` contains saved window metrics and runtime. `operator_diagnostics.csv` contains saved counters only; absent rows mean unavailable artifact, not zero. Relocation and consolidation counters are operator-specific and are not equivalent operation counts. Per-generation histories and initial population quality remain in the source results and are hash-listed in `source_manifest.json`.

## Figures

`static_comparison.png`, `ga_convergence_static.png`, `dynamic_comparison_cold_start.png`, `dynamic_comparison_warm_start.png`, `ga_convergence_dynamic_cold_start.png`, `ga_convergence_dynamic_warm_start.png`, `runtime_per_window_cold_start.png`, `runtime_per_window_warm_start.png`, `experiment_summary_dashboard_static.png`, `workload_timeseries_dynamic_comparison.png`, `utilization_distribution_dynamic.png`, and four `pm_utilization_heatmap_static_ga_*.png` files. Dynamic curves contain only saved windows.

## Reproduction

Run from this project checkout with Python and matplotlib/numpy installed: `python server_consolidation_ga/compare_four_experiments.py`. Script reads saved source files, verifies expected run structures, hashes inputs, and writes only this output directory. It never imports or executes GA optimization code.

## Limitations

Single seed 42; descriptive only. Original baseline is a replay of original `main` GA source under approved 24-PM protocol; historical main result used 12 PM and is not mixed. Experiment 3 partial dynamic output cannot support complete cold/warm or 24-window claims. Source run status is preserved in manifest.
