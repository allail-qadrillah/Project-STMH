"""Tournament participants sampled with replacement; equal best slots tie randomly."""

import numpy as np


def tournament(fitness, rng, size):
    fitness = np.asarray(fitness, dtype=float)
    if fitness.ndim != 1 or not fitness.size or not np.isfinite(fitness).all() or size < 1:
        raise ValueError("Tournament requires finite fitness values and positive size")
    participants = rng.integers(0, len(fitness), size=size)
    scores = fitness[participants]
    return int(rng.choice(participants[scores == scores.max()]))


def elite_indices(fitness, rng, count):
    fitness = np.asarray(fitness, dtype=float)
    if fitness.ndim != 1 or not np.isfinite(fitness).all() or not 0 <= count <= len(fitness):
        raise ValueError("Invalid fitness or elite count")
    shuffled = rng.permutation(len(fitness))
    return shuffled[np.argsort(-fitness[shuffled], kind="stable")[:count]]
