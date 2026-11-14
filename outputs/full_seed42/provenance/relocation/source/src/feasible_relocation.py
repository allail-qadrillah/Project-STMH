"""Per-gene relocation accepted only when complete-window CPU constraints hold."""

import numpy as np
from time import perf_counter

from .evaluation import evaluate_placement


def relocate_feasibly(placement, demand, config, rng, probability, reference=None, counters=None):
    started = perf_counter()
    result = np.asarray(placement).copy()
    pm_count = config["infrastructure"]["available_pm_count"]
    mask = rng.random(len(result)) < probability
    if counters is None:
        counters = {"attempts": 0, "accepted": 0, "rejected": 0,
                    "reducing_active_pm": 0, "same_active_pm": 0,
                    "runtime_seconds": 0.0}
    for key in ("attempts", "accepted", "rejected", "reducing_active_pm", "same_active_pm", "increasing_active_pm", "feasibility_evaluations", "runtime_seconds"):
        counters.setdefault(key, 0)
    for index in np.flatnonzero(mask):
        source = int(result[index])
        draw = int(rng.integers(1, pm_count))
        destination = draw + (draw >= source)
        candidate = result.copy()
        candidate[index] = destination
        counters["attempts"] = counters.get("attempts", 0) + 1
        before = len(np.unique(result))
        metrics, _ = evaluate_placement(demand, candidate, config, reference)
        counters["feasibility_evaluations"] = counters.get("feasibility_evaluations", 0) + 1
        if metrics["status"] == "FEASIBLE":
            result = candidate
            counters["accepted"] += 1
            if len(np.unique(result)) < before:
                counters["reducing_active_pm"] += 1
            elif len(np.unique(result)) == before:
                counters["same_active_pm"] += 1
            else:
                counters["increasing_active_pm"] += 1
        else:
            counters["rejected"] += 1
    counters["runtime_seconds"] += perf_counter() - started
    return result
