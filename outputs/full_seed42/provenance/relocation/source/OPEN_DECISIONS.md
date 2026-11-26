# Approved methodology — overrides to version 4.0

No unresolved methodology blockers. User's approved decisions supersede conflicting
text in `../GA_Server_Consolidation_EN_v4_RENDER_READY.md` (especially Sections 8,
10, 13.5, 14, and 20). Original specification remains unchanged for provenance.

| Topic | Approved implementation |
|---|---|
| Runs | Exactly one per method; master seed 42; NumPy PCG64 |
| Warm initialization | One previous selected chromosome, 49 independent uniform random chromosomes; no mutated copies |
| Window 1 | Independent random populations for cold/warm; common initial placement is migration reference only |
| Tournament | Three draws with replacement; random equal-best participant slot |
| Elitism | Two unchanged elites; random ties |
| Best-so-far | Strict fitness improvement only; first-seen wins ties |
| Generations | Initialization at 0, then 100 reproduction updates; history 0–100 |
| Infeasible window | Keep minimum-violation chromosome and INFEASIBLE status; continue all windows using selected reference/inherited chromosome |
| Statistics | Actual single-run results, no cross-run mean or standard deviation |
| Migration rate | All 24 transitions, including initial placement to Window 1 |

## Recorded implementation details

Stream allocation uses configured distinct role IDs. Each stream is
`Generator(PCG64(SeedSequence(42, spawn_key=(role_id, window))))`.
Window is one-based for dynamic optimization and zero for static/initial placement.
This allocation is deterministic and independent of execution order. IDs, keys,
SeedSequence pool size, and initial/final generator states are recorded.

Uniform crossover makes one probability trial per parent pair, then uses independent
50/50 gene masks with complementary children. Mutation samples a different PM
uniformly. No PM relabeling, repair, heuristic initialization, early stopping, or
secondary fitness tie-breaker is introduced.

Pointwise safe capacity uses absolute tolerance `1e-9` vCPU and also requires
`V <= 1e-9`. Overload event metrics use strict utilization `> 0.80`.
Only active PMs contribute to mean active-PM utilization.

Dataset schema: explicit per-VM numeric lines, lexicographic filename order,
sample-index alignment, configured scale without value-based guessing.
Download date remains unknown (`null`); exact file hashes and archive provenance
are recorded. Capacities remain simulation assumptions, not PlanetLab metadata.

CLI enforces hand/operator/full five-VM acceptance tests before any full run.
Any newly discovered material ambiguity still requires user approval.
