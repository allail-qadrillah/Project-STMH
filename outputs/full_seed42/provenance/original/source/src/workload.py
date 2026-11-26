"""Convert utilization ratios into configured VM CPU demand in vCPU."""

import numpy as np


def cpu_demand_vcpu(utilization, vm_cpu_capacity_vcpu):
    utilization = np.asarray(utilization, dtype=np.float64)
    if utilization.ndim != 2 or not all(utilization.shape):
        raise ValueError("Workload must be a nonempty samples-by-VM matrix")
    if not np.isfinite(utilization).all() or np.any(utilization < 0) or np.any(utilization > 1):
        raise ValueError("Utilization ratios must be finite and in [0, 1]")
    if not np.isfinite(vm_cpu_capacity_vcpu) or vm_cpu_capacity_vcpu <= 0:
        raise ValueError("VM CPU capacity must be finite and positive, in vCPU")
    return utilization * vm_cpu_capacity_vcpu
