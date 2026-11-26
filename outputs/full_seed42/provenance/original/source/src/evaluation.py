"""Metrics use every PM and timestamp; active utilization excludes empty PMs."""

import numpy as np

from .placement import pm_loads_vcpu, validate_placement


def evaluate_placement(demand_vcpu, placement, config, reference=None):
    infra, fit = config["infrastructure"], config["fitness"]
    m = infra["available_pm_count"]
    loads = pm_loads_vcpu(demand_vcpu, placement, m)
    placement = np.asarray(placement)
    active = np.unique(placement)
    capacity = infra["pm_cpu_capacity_vcpu"]
    threshold = infra["safe_cpu_threshold"]
    utilization = loads / capacity
    overload = np.maximum(0, utilization - threshold)
    violation = float(np.mean((overload / (1 - threshold)) ** 2))
    # Section 5's pointwise hard constraint remains necessary; V is not a substitute.
    feasible = bool(np.all(loads <= capacity * threshold + fit["feasibility_tolerance"])
                    and violation <= fit["feasibility_tolerance"])
    migrations = None
    if reference is not None:
        reference = validate_placement(reference, len(placement), m)
        migrations = int(np.count_nonzero(placement != reference))
    metrics = {
        "status": "FEASIBLE" if feasible else "INFEASIBLE",
        "active_pm_count": int(len(active)),
        "mean_active_pm_utilization_ratio": float(utilization[:, active - 1].mean()),
        "maximum_pm_utilization_ratio": float(utilization.max()),
        "maximum_pm_load_vcpu": float(loads.max()),
        "overload_events": int(np.count_nonzero(utilization > threshold)),
        "overload_percentage_pm_time_pairs": float(100 * np.mean(utilization > threshold)),
        "maximum_overload_utilization_ratio": float(overload.max()),
        "total_overload_utilization_ratio": float(overload.sum()),
        "normalized_cpu_violation": violation,
        "migration_count": migrations,
        "normalized_migration_cost": None if migrations is None else migrations / len(placement),
    }
    return metrics, loads
