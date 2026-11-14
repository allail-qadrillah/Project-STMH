# Controlled diagnostic CSV contract

Applies identically to all three controlled branches. UTF-8 CSV, header always present, decimal integers/floats, no index column. Missing values are empty CSV cells (Python None), never zero substitutes. Unused operator counters are integer zero. Runtime is measured float seconds; no cross-run runtime equality expected. Counts are integers unless explicitly marked float. PM IDs are one-based; chromosome indices and generations are zero-based.

## Initial population

`experiments/static/ga/initial_population_metrics.csv` and each dynamic `window_NN/initial_population_metrics.csv`: exactly 50 rows, in population order.

Columns: `chromosome_index` (int), `status` (FEASIBLE/INFEASIBLE), `active_pm_count` (int), `mean_active_pm_utilization_ratio` (float), `maximum_pm_utilization_ratio` (float), `maximum_pm_load_vcpu` (float), `overload_events` (int), `overload_percentage_pm_time_pairs` (float), `maximum_overload_utilization_ratio` (float), `total_overload_utilization_ratio` (float), `normalized_cpu_violation` (float), `migration_count` (nullable int), `normalized_migration_cost` (nullable float).

Migration fields are empty if caller supplied no reference. No filtering, repair or resampling of initial candidates. Warm inherited slot is index 0.

## Generations

Same directories: `per_generation_metrics.csv`, G+1 rows (101 for approved full settings, 2 for one-update integration).

Columns: `generation`, `population_size`, `best_fitness` (float), `feasible_population_count`, `infeasible_population_count`, `best_feasible_active_pm_count` (nullable int, current-population minimum), `mean_feasible_active_pm_count` (nullable float), `population_active_pm_counts` (semicolon-delimited integer string, 50 values in population order), `unique_active_pm_count_values`, `best_normalized_cpu_violation` (float).

Feasible active fields are empty if no feasible candidate exists. `best_fitness` is best-so-far; this is not interchangeable with current-population feasible minimum. Original `fitness_history.csv` remains available.

## Operators

Same directories: `operator_metrics.csv`, one cumulative row per optimization.

Ordered columns: `attempts`, `accepted`, `rejected`, `reducing_active_pm`, `same_active_pm`, `increasing_active_pm`, `successful`, `failed`, `pms_emptied`, `vms_moved`, `tentative_moves`, `discarded_moves`, `feasibility_evaluations`, `runtime_seconds`.

All integer counts except runtime float. Relocation uses accepted/rejected and active-count partitions. Consolidation uses successful/failed, committed VM moves, tentative accepted moves including later rollback, discarded moves, PMs emptied. One-active-PM consolidation is a failed attempt with zero checks. `attempts = successful + failed` for consolidation; `tentative_moves = vms_moved + discarded_moves`. These counters describe the new operators; controlled baseline has no new operator and uses zero counters, not a claim that original random mutation performs zero gene changes.

Population fitness and total feasibility counts are stored separately in metrics; observer adds no candidate evaluations. Reproduction durations retained separately from operator-only runtime. Validation checks are not optimization fitness evaluations.

## Dynamic windows

`experiments/dynamic/{cold_start,warm_start}/per_window_metrics.csv`: 24 rows each. Ordered columns: `seed`, `window`, `sample_start`, `sample_end`, followed by all initial-population metric fields except chromosome_index, followed by `fitness` and `runtime_seconds` (floats). Window and sample endpoints are one-based and inclusive. Initial-reference to window 1 is included.

## Summary

`summaries/experiment_summary.csv`: four rows in existing pipeline: `static_baseline` (random-placement reference, **not original GA comparator**), `static_ga`, `cold_start`, `warm_start`.

Columns are deterministic union, first appearance order, of static metric rows and dynamic summary rows. Static fields: `method` (string), `seed`, all initial metric fields except chromosome_index, `fitness`, `runtime_seconds`; GA adds `fitness_evaluations`, `feasibility_evaluations`, each operator column prefixed `operator_`, and `initial_active_pm_distribution` (JSON object string). Dynamic-only fields: `feasible_windows`, `infeasible_windows`, `transitions`, `migration_rate` (float), `mean_migrations_per_window` (float), `mean_active_pm_count` (float), `minimum_active_pm_count`, `maximum_active_pm_count`, `mean_runtime_per_window_seconds` (float). Inapplicable static/dynamic cells are empty. Header equality is checked across branches.

## Streams and configurations

Seed 42, PCG64, spawn key `(role_id, window)`. Shared migration reference: `dynamic_initial=2`, window 0. Static GA / cold / warm optimization IDs: initialization 501/503/504; relocation 601/603/604; consolidation 701/703/704. Static random reference IDs: initialization 500, operators 0. Static reference does not enter static fitness. Original baseline roles remain 0/1/2/3/4.

`experiment_config.yaml` stays 12 PM for legacy regression fixtures only. `controlled_24.yaml` is separate approved comparison configuration; no 12-PM result enters 24-PM comparison. Integration tests explicitly set 24 PMs. All tests are synthetic; none runs PlanetLab optimization.
