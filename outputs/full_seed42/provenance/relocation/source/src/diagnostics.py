"""Read-only observation: no RNG draws and no additional candidate evaluations."""

from functools import wraps
from time import perf_counter
from unittest.mock import patch

COUNTERS = ("attempts", "accepted", "rejected", "reducing_active_pm", "same_active_pm",
            "increasing_active_pm", "successful", "failed", "pms_emptied", "vms_moved",
            "tentative_moves", "discarded_moves", "feasibility_evaluations", "runtime_seconds")


def observe(run, module):
    """Serial-run observer; wrap only module-bound calls, never operator evaluations."""
    @wraps(run)
    def observed(*args, **kwargs):
        evaluations, generations = [], []
        evaluate, reproduce = module.evaluate_placement, module.reproduce

        def record(*a, **k):
            result = evaluate(*a, **k)
            evaluations.append(dict(result[0]))
            return result

        def update(*a, **k):
            start = perf_counter()
            result = reproduce(*a, **k)
            generations.append(perf_counter() - start)
            return result

        with patch.object(module, "evaluate_placement", record), patch.object(module, "reproduce", update):
            result = run(*args, **kwargs)
        size = len(result["initial_population"])
        history = result["history"]
        assert len(evaluations) == size * len(history) + 1
        result["initial_population_metrics"] = evaluations[:size]
        operator = {key: result.get("operator_metrics", {}).get(key, 0) for key in COUNTERS}
        result["operator_metrics"] = operator
        result["evaluation_counts"] = {"fitness": size * len(history),
            "feasibility": len(evaluations) + operator["feasibility_evaluations"]}
        result["reproduction_runtime_seconds"] = generations
        for g, row in enumerate(history):
            batch = evaluations[g * size:(g + 1) * size]
            feasible = [m for m in batch if m["status"] == "FEASIBLE"]
            counts = [m["active_pm_count"] for m in batch]
            row.update(infeasible_population_count=size-len(feasible),
                best_feasible_active_pm_count=min((m["active_pm_count"] for m in feasible), default=None),
                mean_feasible_active_pm_count=sum(m["active_pm_count"] for m in feasible)/len(feasible) if feasible else None,
                population_active_pm_counts=";".join(map(str, counts)),
                unique_active_pm_count_values=len(set(counts)),
                best_normalized_cpu_violation=min(m["normalized_cpu_violation"] for m in batch))
        return result
    return observed


def save_diagnostics(directory, result, write_csv):
    initial = [{"chromosome_index": i, **m} for i, m in enumerate(result["initial_population_metrics"])]
    write_csv(directory / "initial_population_metrics.csv", initial, list(initial[0]))
    fields = ["generation", "population_size", "best_fitness", "feasible_population_count",
              "infeasible_population_count", "best_feasible_active_pm_count", "mean_feasible_active_pm_count",
              "population_active_pm_counts", "unique_active_pm_count_values", "best_normalized_cpu_violation"]
    rows = [{k: h[k] for k in fields} for h in result["history"]]
    write_csv(directory / "per_generation_metrics.csv", rows, fields)
    write_csv(directory / "operator_metrics.csv", [result["operator_metrics"]], list(COUNTERS))
