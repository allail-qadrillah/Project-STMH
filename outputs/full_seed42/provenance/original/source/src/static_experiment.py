"""Fixed full-day random baseline and independent static GA."""

from time import perf_counter

from .evaluation import evaluate_placement
from .fitness import calculate_fitness
from .genetic_algorithm import run_ga
from .randomness import make_stream


def run_static(demand, config):
    rng, baseline_stream = make_stream(config, "static_baseline")
    start = perf_counter()
    baseline = rng.integers(1, config["infrastructure"]["available_pm_count"] + 1, size=demand.shape[1])
    metrics, loads = evaluate_placement(demand, baseline, config, baseline)
    baseline_result = {"placement": baseline, "loads_vcpu": loads,
                       "metrics": {**metrics, "fitness": calculate_fitness(metrics, config, "static")},
                       "runtime_seconds": perf_counter() - start}
    baseline_stream["final_state"] = rng.bit_generator.state
    rng, ga_stream = make_stream(config, "static_ga")
    ga = run_ga(demand, config, rng, "static", reference=baseline)
    ga_stream["final_state"] = rng.bit_generator.state
    return {"baseline": baseline_result, "ga": ga, "streams": [baseline_stream, ga_stream]}
