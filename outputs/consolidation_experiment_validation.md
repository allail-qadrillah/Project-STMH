# Consolidation experiment validation

## Corrective revalidation — current status

**Latest complete suites pass; full optimization remains prohibited pending separate approval.** Historical failure report below is retained as evidence, not current status.

| Branch | Tests | Passed | Failed | Duration |
|---|---:|---:|---:|---:|
| `experiment/active-pm-aware-initialization` | 27 | 27 | 0 | 86.600 s |
| `experiment/feasibility-preserving-relocation` | 27 | 27 | 0 | 89.352 s |
| `experiment/consolidation-aware-mutation` | 29 | 29 | 0 | 158.230 s |

All HEADs remain `21cf4c1c9125cde31ca758f45fc4d8c812fb8fe9`. Changes are uncommitted worktree edits. Command: `.venv/bin/python -m unittest discover -s tests -v`. Final logs, schema manifests and output protection manifests are in `outputs/validation_evidence/`. Earlier consolidation suite hit 120-second tool timeout without assertion failure; final complete invocation used 300-second timeout and passed. Durations are concurrent test-suite timings, not algorithm benchmarks.

### Corrected initialization

Obsolete operator tests now independently replay 39 compact draws followed by ten uniform chromosomes. All branches include evaluation-only initialization tests: exactly 50 slots, one deliberate inherited slot, infeasible inherited retention, no rejection/resampling, seed-42 draw/state replay, last-timestamp overload at 12/288 samples. Existing 12-PM regression tests remain intact.

### 24-PM integration

Static synthetic workload uses 288 samples and 1,033 genes, one reproduction update. Dynamic synthetic workload uses 13 VMs, 288 samples, both 24-window tracks, one update/window. Tests validate allele bounds, population shapes, inherited slots, references and recompute every selected-placement metric over its entire window. Five-VM pipeline schema test exercises all persisted artifacts at 24 PMs; legacy 100-update five-VM pipeline also passes. None loads PlanetLab.

Each branch now has `configs/controlled_24.yaml`: 24 PMs and separate output directory. Original default YAML stays 12 PM solely for legacy regression coverage. No 12-PM results enter controlled comparison.

### Operator tests

Relocation rejection fixture passes with unchanged source and exact attempts/rejections. Low-demand integration executes accepted relocations and verifies resulting feasibility. Dedicated coverage does not exhaust every accepted active-count partition.

Consolidation new tests pass: successful emptying; failure after one tentative move; complete rollback; one-active-PM edge case; attempt/success/failure conservation; committed/tentative/discarded move conservation; one attempt for every marked gene. Partial-progress fixture uses 13 unit-demand VMs: first move gives destination load 12, next would give 13 and fails, restoring original placement. One-active-PM triggers count as failed attempts. Tentative and discarded moves are retained in diagnostics.

### RNG and migration references

Shared migration reference uses seed 42, PCG64, spawn key `(2,0)` in every arm. Each arm's test compares against same independently constructed reference vector, establishing cross-arm equality. Static/cold/warm optimization roles: initialization 501/503/504, relocation 601/603/604, consolidation 701/703/704. Subsequent references follow each arm's own selected placement. Seed-42 replay tests pass in all branches.

### Diagnostic schemas

All five required artifact headers compared programmatically across branches: **identical**. Integration verifies 49 initial CSVs with 50 rows; 49 generation CSVs with 2 rows; 49 operator CSVs with 1 row; two per-window CSVs with 24 rows; one summary CSV with four rows. Common observer/reporting code preserves union of all operator counters. Column names, types, missing-value conventions, row counts and stream table documented in `server_consolidation_ga/DIAGNOSTIC_SCHEMA.md`.

Population fitness and total feasibility evaluations persist separately; operator checks counted once. Original `fitness_history.csv` retained. Summary `static_baseline` means random placement reference, not original GA comparison arm. Reproduction timing is retained separately from operator-only runtime; those quantities must not be conflated.

### Original baseline instrumentation

Each branch loads committed original GA via `git show` into isolated module. Instrumented and uninstrumented executions match final RNG state, initial populations, selected placements, all best chromosomes, loads, original fitness-history fields and final metrics. Checks cover synthetic static and dynamic runs at 24 PMs, 288 samples, seed 42 and three updates. Observer calls original functions in original order, once per call, without RNG draws. No original baseline file is modified. Observer is serial-only within each process.

### Output protection

Before tests, SHA-256 manifest captured 1,057 original output files. After final suites, independently enumerated paths and hashes match exactly: **zero added, deleted or changed files**. Before/after manifests retained. Original `main` HEAD unchanged; tracked source/config/tests have no diff. Existing dirty worktree never reset or cleaned.

### Remaining limitations

No full optimization or comparative performance claims. Only descriptive single-seed interpretation is permitted. Changes remain uncommitted; immutable source provenance is needed before publication. Baseline observer equivalence is validated in an isolated module, but dedicated full-evaluation baseline worktree has not been created. Observer retains per-evaluation dictionaries in memory and is serial-only; full-run memory/timing overhead is not benchmarked. Accepted relocation counter partitions could use additional dedicated cases. Wait for separate approval before full optimization.

---

## Historical validation before corrections

## Decision: BLOCKED — stop on failure

Validation only. Both latest operator suites failed. No full PlanetLab optimization launched. No corrective source/configuration edits made during this validation pass. Additional gates remain pending; this report does not authorize optimization.

## Branches and commit hashes

All four branch HEADs are `21cf4c1c9125cde31ca758f45fc4d8c812fb8fe9`:

| Branch | Role | Worktree |
|---|---|---|
| `main` | Original baseline | `/mnt/e/.TEMPORARY/Project STMH` |
| `experiment/active-pm-aware-initialization` | Controlled baseline | `/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-active-pm-init` |
| `experiment/feasibility-preserving-relocation` | Relocation | `/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-feasible-relocation` |
| `experiment/consolidation-aware-mutation` | Consolidation | `/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-consolidation-mutation` |

Implementations are uncommitted worktree changes. HEAD hashes identify common committed foundation, not distinct completed variant implementations. Reproduction requires those working-tree changes; commit hashes alone are insufficient.

## Test counts and results

Command in each operator worktree's `server_consolidation_ga/`:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Both suites were started concurrently; they are small synthetic tests, not full workload runs. Durations are test-suite wall times, not optimization benchmarks.

| Branch | Tests | Passed | Failed | Duration | Evidence freshness |
|---|---:|---:|---:|---:|---|
| Controlled baseline | 24 | 24 | 0 | 66.009 s | Previous validation turn; not rerun after stop condition |
| Relocation | 23 | 22 | 1 | 70.589 s | Latest full suite, this validation pass |
| Consolidation | 23 | 22 | 1 | 82.494 s | Latest full suite, this validation pass |
| Original baseline | — | — | — | — | Not executed in this pass |

Logs from this pass:

- `/tmp/opencode/relocation-validation.log`
- `/tmp/opencode/consolidation-validation.log`

## Failure details

Both operator branches fail:

```text
test_warm_population_one_inherited_plus_49_independent_draws
tests/test_ga.py:107
np.testing.assert_equal(actual[1:], expected_random)
Mismatched elements: 314 / 343 (91.5%)
```

Test expects superseded one-inherited-plus-49-uniform initialization. Implementation now generates one inherited, 39 compact, and 10 uniform chromosomes. Failure is an outdated test expectation; it must be replaced with an independent check of approved composition and RNG draw sequence. Merely removing the failing assertion would leave a coverage gap.

## Initialization validation

Controlled-baseline prior suite includes `test_initialization_policy.py`, covering:

- Exactly 50 chromosomes, cold composition 40 compact/10 uniform and warm composition 1 inherited/39 compact/10 uniform.
- Independent seed-42 initialization draw replay and final RNG-state equality.
- Feasible and infeasible compact candidates, retained infeasible inherited chromosome.
- Last-timestamp overload in both 12-sample and 288-sample windows.
- Same initial populations for zero-demand and overloaded inputs, confirming no feasibility filtering/resampling.
- 50 initial candidate evaluations plus one selected-placement evaluation.

Operator branches have aligned compact initialization code, but lack this dedicated policy test. Their latest warm-start test asserts shape and inherited slot before failing at random-population equality. This is partial evidence, not a passed initialization gate.

Exactly one inherited slot means exactly one deliberate inherited insertion. Randomly generated duplicate genotypes must not be rejected; requiring unique genotype equality for every seed/workload would introduce filtering bias.

## Operator validation

### Relocation

`test_feasible_relocation_rejects_overload_without_changing_source` passed. Fixture uses two PMs with 12 unit-demand VMs each; every proposed relocation overloads destination. Test verifies 24 attempts/rejections and unchanged placement.

Remaining coverage: explicit accepted relocation and active-count decrease/unchanged/increase partitions; full counter conservation; operator-only timing scope; complete-window boundary cases at 24 PMs; persisted diagnostics.

### Consolidation

`test_consolidation_is_transactional_on_failure_and_feasibility_checked` passed. Its fixture has four 7-vCPU demands under two PMs and is already infeasible. It verifies rejection and unchanged placement, but does not prove rollback after one or more accepted tentative moves. The fixture also exceeds configured per-VM 1-vCPU capacity and is an evaluator-level stress case, not a realistic workload fixture.

Remaining coverage: feasible successful emptying, failure after partial progress, committed versus discarded VM moves, exact per-gene-trigger accounting, one-active-PM handling, and persisted counters.

## Reproducibility

Both operator suites passed `test_complete_ga_replays_exactly` and stream tests for deterministic, role/window-specific PCG64 replay. These compare selected placements, loads, initial populations, best chromosomes, histories and metrics on small inputs.

This does not yet establish full RNG/counter equivalence for all new instrumentation. Original-baseline instrumented-versus-uninstrumented replay has not been implemented/validated. Cross-arm identical migration references remain unverified; controlled-baseline YAML still assigns `dynamic_initial: 502`, while operator drafts retain original stream allocation.

## Static and dynamic integration

Both operator suites passed `test_five_vm_full_pipeline_100_updates_24_windows_and_artifacts`. It uses five synthetic VMs, 288 samples, static GA, 24 cold-start windows and 24 warm-start windows. Checks include saved placements, load/fitness reconstruction, previous-placement references, migration accounting, population shapes, histories, streams and expected files.

These integration tests still use the legacy default 12-PM configuration. They are useful regression evidence but do not satisfy approved 24-PM controlled-comparison gate. They do not require new initial-population CSV or new operator diagnostics, so their success does not establish schema compliance.

## Output schema consistency: FAILED

Source inspection of `src/reporting.py:68-88` in both operator branches confirms original save schema only: placement, metrics, loads/utilization, initial population, best chromosomes/reference, and fitness history.

| Artifact / field | Controlled baseline | Relocation | Consolidation |
|---|---|---|---|
| `initial_population_metrics.csv` | Implemented | Missing | Missing |
| Initial candidate status/violation rows | Returned and saved | Not saved | Not saved |
| Evaluation counters saved in metrics | Implemented | Missing | Missing |
| Operator counters saved | Placeholder zero counters | Returned but not saved by reporting | Returned but not saved by reporting |
| Population active-count diagnostics | Added | Partially added | Original history schema |

Identical diagnostic schemas are not achieved. No artifacts were fabricated to hide missing diagnostics. Schema contract must be explicit and tested across all three controlled branches, including column names, data types, missing-value conventions and row counts.

## Original baseline and output preservation

`git worktree list --porcelain` confirms `main` remains at original commit `21cf4c1c9125cde31ca758f45fc4d8c812fb8fe9`.

Read-only check:

```bash
git -C '/mnt/e/.TEMPORARY/Project STMH' diff --name-only -- server_consolidation_ga/src server_consolidation_ga/configs server_consolidation_ga/tests
```

Returned no paths: tracked baseline source, configurations and tests match HEAD. Validation commands ran in isolated operator worktrees; test outputs use temporary directories. No write operation targeted original baseline or existing experiment outputs in this pass.

Existing outputs were already dirty before this task. No pre-pass cryptographic manifest exists, so byte-for-byte preservation cannot be independently certified retrospectively. Do not describe the original worktree as clean or equate unchanged branch HEAD with unchanged output bytes. Before next validation pass, take read-only SHA-256 manifests of existing outputs and compare afterwards.

## Coverage comparison and remaining issues

1. Update both obsolete warm-start tests to independently validate approved mixture.
2. Port evaluation-only initialization policy coverage to both operators, including infeasible inherited retention and no resampling.
3. Align and test diagnostic persistence, particularly `initial_population_metrics.csv` and operator/evaluation counts.
4. Configure and validate all comparison arms at 24 PMs. Controlled-baseline current YAML still says 12; operator integration fixtures also remain legacy 12-PM tests.
5. Verify common initial migration reference and distinct optimization stream allocation across arms.
6. Add partial-progress rollback and successful-operator/counter tests.
7. Verify instrumented original baseline against unchanged execution and RNG state.
8. Capture baseline/output preservation manifests before subsequent execution.
9. Rerun complete suites and small 24-PM static/dynamic integration only after corrections are authorized.

Stop condition honored: no new optimization runs or fixes after identified failures. Wait for approval before corrections/revalidation and, separately, before full optimization. Single-seed observations can only support descriptive comparisons, not significance or statistically established winner claims.
