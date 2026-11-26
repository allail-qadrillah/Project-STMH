"""One optimization: generation 0 plus configured reproduction updates, no repair."""

from time import perf_counter

import numpy as np

from .crossover import uniform_crossover
from .evaluation import evaluate_placement
from .fitness import calculate_fitness
from .mutation import mutate
from .placement import validate_placement
from .selection import elite_indices, tournament


def initialize_population(vm_count, config, rng, inherited=None):
    size = config["genetic_algorithm"]["population_size"]
    pm_count = config["infrastructure"]["available_pm_count"]
    if vm_count < 1:
        raise ValueError("Population requires at least one VM")
    if inherited is None:
        return rng.integers(1, pm_count + 1, size=(size, vm_count))
    inherited = validate_placement(inherited, vm_count, pm_count)
    # Exactly one inherited chromosome; remaining draws independent, never mutated copies.
    return np.vstack((inherited, rng.integers(1, pm_count + 1, size=(size - 1, vm_count))))


def reproduce(population, fitness, config, rng):
    ga = config["genetic_algorithm"]
    pm_count = config["infrastructure"]["available_pm_count"]
    children = [population[i].copy() for i in elite_indices(fitness, rng, ga["elitism_count"])]
    while len(children) < ga["population_size"]:
        a, b = (population[tournament(fitness, rng, ga["tournament_size"])] for _ in range(2))
        offspring = uniform_crossover(a, b, rng, ga["crossover"]["probability"])
        for child in offspring:
            if len(children) == ga["population_size"]:
                break
            children.append(mutate(child, rng, pm_count, ga["mutation"]["per_gene_probability"]))
    return np.asarray(children)


def run_ga(demand_vcpu, config, rng, mode, reference=None, inherited=None):
    start = perf_counter()
    demand = np.asarray(demand_vcpu, dtype=np.float64)
    if demand.ndim != 2 or not all(demand.shape):
        raise ValueError("GA requires nonempty sample-by-VM demand matrix")
    if mode not in ("static", "dynamic") or (mode == "dynamic" and reference is None):
        raise ValueError("GA requires valid mode and dynamic migration reference")
    population = initialize_population(demand.shape[1], config, rng, inherited)
    initial_population = population.copy()
    best_fitness = -np.inf
    history, chromosomes = [], []
    for generation in range(config["genetic_algorithm"]["max_generations"] + 1):
        metrics = [evaluate_placement(demand, p, config, reference)[0] for p in population]
        fitness = np.array([calculate_fitness(m, config, mode) for m in metrics])
        candidate = int(np.argmax(fitness))
        if fitness[candidate] > best_fitness:
            best_fitness = float(fitness[candidate])
            best = population[candidate].copy()
            best_metrics = dict(metrics[candidate])
        history.append({"generation": generation, "population_size": len(population),
                        "population_best_fitness": float(fitness.max()),
                        "population_mean_fitness": float(fitness.mean()),
                        "feasible_population_count": sum(m["status"] == "FEASIBLE" for m in metrics),
                        "best_fitness": best_fitness, **best_metrics})
        chromosomes.append(best.copy())
        if generation < config["genetic_algorithm"]["max_generations"]:
            population = reproduce(population, fitness, config, rng)
    selected_metrics, loads = evaluate_placement(demand, best, config, reference)
    return {"placement": best, "metrics": {**selected_metrics, "fitness": best_fitness},
            "loads_vcpu": loads, "history": history,
            "best_chromosomes": np.asarray(chromosomes), "initial_population": initial_population,
            "runtime_seconds": perf_counter() - start}
