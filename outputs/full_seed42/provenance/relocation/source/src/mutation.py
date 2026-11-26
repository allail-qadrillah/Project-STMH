"""Per-gene random reassignment; never reassign to the current PM."""

import numpy as np


def mutate(placement, rng, pm_count, probability):
    result = np.asarray(placement).copy()
    if result.ndim != 1 or not np.issubdtype(result.dtype, np.integer):
        raise ValueError("Mutation requires an integer chromosome")
    if pm_count < 2 or np.any(result < 1) or np.any(result > pm_count):
        raise ValueError("Invalid PM count or chromosome")
    if not 0 <= probability <= 1:
        raise ValueError("Mutation probability must lie in [0, 1]")
    mask = rng.random(len(result)) < probability
    draws = rng.integers(1, pm_count, size=int(mask.sum()))
    result[mask] = draws + (draws >= result[mask])
    return result
