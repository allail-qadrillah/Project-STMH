"""Validate numeric samples before any scale conversion."""

import numpy as np


def validate_samples(values, scale, vm_id):
    values = np.asarray(values, dtype=np.float64)
    upper = {"percentage": 100.0, "ratio": 1.0}[scale]
    if values.ndim != 1 or values.size == 0:
        raise ValueError(f"{vm_id}: samples must be a nonempty vector")
    if not np.isfinite(values).all():
        raise ValueError(f"{vm_id}: non-finite CPU sample")
    if np.any(values < 0) or np.any(values > upper):
        raise ValueError(f"{vm_id}: {scale} sample outside [0, {upper}]")
    return values
