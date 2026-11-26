"""Integer placement labels are physical PM IDs, starting at 1."""

import numpy as np


def validate_placement(placement, vm_count, pm_count):
    placement = np.asarray(placement)
    if placement.shape != (vm_count,) or not np.issubdtype(placement.dtype, np.integer):
        raise ValueError("Placement must contain exactly one integer PM ID per VM")
    if np.any(placement < 1) or np.any(placement > pm_count):
        raise ValueError(f"PM IDs must lie in [1, {pm_count}]")
    return placement


def pm_loads_vcpu(demand_vcpu, placement, pm_count):
    demand = np.asarray(demand_vcpu, dtype=np.float64)
    if demand.ndim != 2 or not all(demand.shape) or not np.isfinite(demand).all() or np.any(demand < 0):
        raise ValueError("CPU demand must be a nonempty, finite, nonnegative matrix in vCPU")
    placement = validate_placement(placement, demand.shape[1], pm_count)
    loads = np.zeros((demand.shape[0], pm_count), dtype=np.float64)
    for pm in range(1, pm_count + 1):
        loads[:, pm - 1] = demand[:, placement == pm].sum(axis=1)
    return loads
