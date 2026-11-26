"""One crossover trial per parent pair; complementary independent 50/50 gene mask."""

import numpy as np


def uniform_crossover(parent1, parent2, rng, probability):
    a, b = np.asarray(parent1), np.asarray(parent2)
    if (a.ndim != 1 or a.shape != b.shape or not a.size
            or not np.issubdtype(a.dtype, np.integer) or not np.issubdtype(b.dtype, np.integer)):
        raise ValueError("Crossover requires equal nonempty integer chromosomes")
    if not 0 <= probability <= 1:
        raise ValueError("Crossover probability must lie in [0, 1]")
    if rng.random() >= probability:
        return a.copy(), b.copy()
    mask = rng.random(a.size) < 0.5
    return np.where(mask, a, b), np.where(mask, b, a)
