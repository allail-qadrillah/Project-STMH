"""Attempt to empty one PM; reject entire attempt unless every move is feasible."""

from time import perf_counter

import numpy as np

from .evaluation import evaluate_placement


def consolidate_one_pm(placement, demand, config, rng, reference=None, counters=None):
    started = perf_counter()
    original = np.asarray(placement).copy()
    result = original.copy()
    pm_count = config["infrastructure"]["available_pm_count"]
    active = np.unique(original)
    if counters is None:
        counters = {"attempts": 0, "successful": 0, "failed": 0,
                    "pms_emptied": 0, "vms_moved": 0,
                    "feasibility_evaluations": 0, "runtime_seconds": 0.0}
    counters["attempts"] = counters.get("attempts", 0) + 1
    if len(active) < 2:
        counters["failed"] = counters.get("failed", 0) + 1
        counters["runtime_seconds"] = counters.get("runtime_seconds", 0.0) + perf_counter() - started
        return original
    source = int(rng.choice(active))
    vm_indices = rng.permutation(np.flatnonzero(original == source))
    destinations = [int(pm) for pm in active if int(pm) != source]
    moved = 0
    for vm in vm_indices:
        order = rng.permutation(destinations)
        placed = False
        for destination in order:
            candidate = result.copy()
            candidate[vm] = destination
            metrics, _ = evaluate_placement(demand, candidate, config, reference)
            counters["feasibility_evaluations"] = counters.get("feasibility_evaluations", 0) + 1
            if metrics["status"] == "FEASIBLE":
                result = candidate
                moved += 1
                counters["tentative_moves"] = counters.get("tentative_moves", 0) + 1
                placed = True
                break
        if not placed:
            counters["discarded_moves"] = counters.get("discarded_moves", 0) + moved
            counters["failed"] = counters.get("failed", 0) + 1
            counters["runtime_seconds"] = counters.get("runtime_seconds", 0.0) + perf_counter() - started
            return original
    counters["successful"] = counters.get("successful", 0) + 1
    counters["pms_emptied"] = counters.get("pms_emptied", 0) + 1
    counters["vms_moved"] = counters.get("vms_moved", 0) + moved
    counters["runtime_seconds"] = counters.get("runtime_seconds", 0.0) + perf_counter() - started
    return result
