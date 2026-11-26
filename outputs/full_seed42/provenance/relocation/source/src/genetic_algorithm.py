"""One optimization: generation 0 plus configured reproduction updates, no repair."""

from time import perf_counter

import numpy as np

from .crossover import uniform_crossover
from .evaluation import evaluate_placement
from .feasible_relocation import relocate_feasibly
from .fitness import calculate_fitness
from .mutation import mutate
from .placement import validate_placement
from .selection import elite_indices, tournament


def initialize_population(vm_count, config, rng, inherited=None):
    size = config["genetic_algorithm"]["population_size"]
    pm_count = config["infrastructure"]["available_pm_count"]
    if vm_count < 1:
        raise ValueError("Population requires at least one VM")
    uniform_count = max(1, size // 5)
    chromosomes = [] if inherited is None else [validate_placement(inherited, vm_count, pm_count).copy()]
    for _ in range(size - uniform_count - len(chromosomes)):
        subset_size = int(rng.integers(1, pm_count))
        subset = rng.choice(pm_count, size=subset_size, replace=False) + 1
        chromosomes.append(rng.choice(subset, size=vm_count))
    chromosomes.extend(rng.integers(1, pm_count + 1, size=(uniform_count, vm_count)))
    return np.asarray(chromosomes, dtype=int)


def reproduce(population, fitness, config, rng, demand=None, reference=None, operator_counters=None):
    ga = config["genetic_algorithm"]
    pm_count = config["infrastructure"]["available_pm_count"]
    children = [population[i].copy() for i in elite_indices(fitness, rng, ga["elitism_count"])]
    while len(children) < ga["population_size"]:
        a, b = (population[tournament(fitness, rng, ga["tournament_size"])] for _ in range(2))
        offspring = uniform_crossover(a, b, rng, ga["crossover"]["probability"])
        for child in offspring:
            if len(children) == ga["population_size"]:
                break
            if demand is None:
                children.append(mutate(child, rng, pm_count, ga["mutation"]["per_gene_probability"]))
            else:
                children.append(relocate_feasibly(child, demand, config, rng,
                    ga["mutation"]["per_gene_probability"], reference, operator_counters))
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
    operator_counters = {"attempts": 0, "accepted": 0, "rejected": 0,
                         "reducing_active_pm": 0, "same_active_pm": 0,
                         "feasibility_evaluations": 0, "runtime_seconds": 0.0}
    for generation in range(config["genetic_algorithm"]["max_generations"] + 1):
        metrics = [evaluate_placement(demand, p, config, reference)[0] for p in population]
        fitness = np.array([calculate_fitness(m, config, mode) for m in metrics])
        feasible_metrics = [m for m in metrics if m["status"] == "FEASIBLE"]
        active_counts = [m["active_pm_count"] for m in metrics]
        candidate = int(np.argmax(fitness))
        if fitness[candidate] > best_fitness:
            best_fitness = float(fitness[candidate])
            best = population[candidate].copy()
            best_metrics = dict(metrics[candidate])
        history.append({"generation": generation, "population_size": len(population),
                        "population_best_fitness": float(fitness.max()),
                        "population_mean_fitness": float(fitness.mean()),
                        "feasible_population_count": sum(m["status"] == "FEASIBLE" for m in metrics),
                        "infeasible_population_count": sum(m["status"] != "FEASIBLE" for m in metrics),
                        "best_feasible_active_pm_count": min((m["active_pm_count"] for m in feasible_metrics), default=None),
                        "mean_feasible_active_pm_count": float(np.mean([m["active_pm_count"] for m in feasible_metrics])) if feasible_metrics else None,
                        "population_active_pm_counts": ";".join(map(str, active_counts)),
                        "unique_active_pm_count_values": len(set(active_counts)),
                        "best_normalized_cpu_violation": min(m["normalized_cpu_violation"] for m in metrics),
                        "best_fitness": best_fitness, **best_metrics})
        chromosomes.append(best.copy())
        if generation < config["genetic_algorithm"]["max_generations"]:
            population = reproduce(population, fitness, config, rng, demand, reference, operator_counters)
    selected_metrics, loads = evaluate_placement(demand, best, config, reference)
    return {"placement": best, "metrics": {**selected_metrics, "fitness": best_fitness},
            "loads_vcpu": loads, "history": history,
            "best_chromosomes": np.asarray(chromosomes), "initial_population": initial_population,
            "operator_metrics": operator_counters,
            "runtime_seconds": perf_counter() - start}


import sys
from .diagnostics import observe
run_ga = observe(run_ga, sys.modules[__name__])
