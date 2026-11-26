# GA consolidation comparison protocol

## Status

Latest user approval supersedes earlier independent-initialization operator comparisons. Draft code does not yet implement this complete protocol. No full optimization launched. No winner or comparative performance claim is justified. Earlier passing tests do not validate latest corrections or this revised protocol.

## Approved common conditions

- 24 available PMs for every comparison; never mix 12-PM results into comparison.
- PM capacity 16 vCPU; safe CPU threshold 0.80; VM capacity 1 vCPU; existing feasibility tolerance 1e-9.
- Same 1,033 VMs, unchanged dataset and stable VM order.
- Static evaluates all 288 samples; dynamic evaluates all 12 samples per window, 24 windows, both cold-start and warm-start.
- Population 50; 100 reproduction updates plus generation 0; tournament size 3 with replacement; uniform crossover probability 0.80; two unchanged elites; unchanged fitness and selection.
- One run per arm/track, master seed 42, PCG64. Separate deterministic optimization streams; save actual stream identifiers and generator states.
- Identical initial migration-reference placement across comparison arms, including initial placement to window 1 in migration counts. Subsequent references are each arm's previous selected placement.
- Preserve existing baseline branch and outputs; use isolated worktrees and branch-specific fresh output directories.

## Comparison arms

| Arm | Initialization | Mutation | Comparison purpose |
|---|---|---|---|
| Original baseline | Original uniform policy, including original warm inheritance | Original random reassignment | Measure original methodology |
| Controlled baseline / Experiment 1 | Compact mixture | Original random reassignment | Measure initialization effect relative to original |
| Experiment 2 | Same compact mixture | Feasibility-preserving relocation | Measure relocation effect relative to controlled baseline |
| Experiment 3 | Same compact mixture | Consolidation-aware mutation | Measure consolidation effect relative to controlled baseline |

Operators remain isolated: relocation and consolidation are never combined. Revised approval explicitly requires compact initialization in both operator arms.

## Compact initialization

- Static and cold-start, and warm window 1: 40 compact + 10 uniform slots.
- Warm windows 2–24: 1 inherited + 39 compact + 10 uniform slots.
- Every chromosome retains one valid PM ID per VM.
- Draft compact sampler chooses subset size uniformly from 1..23, samples physical PM IDs without replacement, then assigns VMs uniformly within subset. Compactness does not imply feasibility.
- Complete-window evaluation required for every candidate. Retain every candidate regardless of feasibility; record status and normalized CPU violation. No rejection, retries, resampling or repair. Always preserve one inherited slot, even if infeasible in the next window. Random duplicate genotypes are not additional inherited slots and must not be filtered.

## Operators

Relocation: each 0.02 per-gene trigger proposes a different PM; accept only when complete-window evaluation is feasible. Count attempts, accepted/rejected proposals, active-count decreases/unchanged/increases, checks, and operator runtime.

Consolidation: each 0.02 per-gene trigger starts one attempt. Choose occupied source PM randomly, shuffle its VM order, try other occupied PMs randomly, check complete-window feasibility, and roll back whole attempt on failure. Failed attempt leaves its input chromosome byte-identical. Count attempts, successes/failures, PMs emptied, successful VM moves, checks and overhead. Distinguish discarded tentative moves from committed moves.

## Baseline instrumentation

One fresh original-baseline evaluation approved in isolated worktree, at 24 PMs. Instrumentation must preserve algorithm behavior, RNG consumption and execution order. Validate against uninstrumented execution on small workloads, comparing placements, original history fields, and final RNG state. Existing saved results remain untouched.

## Mandatory gate before full optimization

1. Validate initialization evaluation-only policy without filtering.
2. Revalidate latest corrections with focused operator tests and small controlled static/dynamic runs.
3. Verify chromosome lengths/ranges, complete-window CPU constraints including last timestamp, transactional rollback after partial progress, deterministic replay, and exact counters.
4. Verify identical migration references across arms and independent optimization streams.
5. Verify all 24 windows and initial transition migration accounting; recompute saved metrics from raw placements.
6. Verify instrumentation leaves original baseline execution unchanged.
7. Persist gate evidence before any full optimization.

Count population fitness evaluations and all feasibility checks separately, including initialization retries if approved. Record runtime per generation and operator-only runtime. Equal generations do not imply equal computational budgets.

## Statistical interpretation

Only seed 42 is authorized. Report single-run descriptive comparisons, never standard deviation across runs, statistical significance across seeds, or general superiority. Dynamic windows and generations are dependent observations, not independent replicate runs. Inferential winner claims require a separately approved replicated design.

## Initialization acceptance approval and validation

User explicitly approved feasibility evaluation, not filtering. Normal evolution handles infeasibility. Population stays 50. Uniform slots use original random assignment; inherited slot is never replaced, repaired or discarded. Compact candidates seek consolidation without asserting feasibility; existing random-subset constructor remains unchanged apart from approved warm composition. No additional feasibility-directed packing heuristic has been introduced.

`tests/test_initialization_policy.py` passed on controlled-baseline branch: fixed seed-42 draw replay including RNG state, exact 50 slots, 40/10 and 1/39/10 composition, feasible and infeasible compact candidates, infeasible inherited retention, and last-timestamp overload checks over both 12- and 288-sample windows. Low-demand and overloaded inputs produce identical initial populations, proving acceptance does not depend on feasibility. Generation-zero checks total 50 candidate evaluations plus one final selected evaluation. Initial per-chromosome metrics persist in `initial_population_metrics.csv`.

Full protocol gate remains pending; this focused test does not authorize a full launch. Initialization code has also been aligned in both operator branches; their latest complete suites still require revalidation.

## Worktrees

- `experiment/active-pm-aware-initialization`: `/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-active-pm-init`
- `experiment/feasibility-preserving-relocation`: `/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-feasible-relocation`
- `experiment/consolidation-aware-mutation`: `/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-consolidation-mutation`

Original baseline evaluation worktree still to be created. Source edits remain drafts, not finished experimental evidence.
