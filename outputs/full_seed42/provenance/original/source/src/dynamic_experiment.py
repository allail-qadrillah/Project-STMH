"""Cold/warm daily controllers; selected infeasible results remain references."""

from .genetic_algorithm import run_ga
from .randomness import make_stream


def run_dynamic(demand, config, on_window=None):
    window_size = config["experiments"]["dynamic"]["window_size_samples"]
    if demand.shape[0] % window_size:
        raise ValueError("Dynamic sample count must divide into complete windows")
    rng, initial_stream = make_stream(config, "dynamic_initial")
    initial = rng.integers(1, config["infrastructure"]["available_pm_count"] + 1, size=demand.shape[1])
    initial_stream["final_state"] = rng.bit_generator.state
    results = {"initial_placement": initial, "streams": [initial_stream]}
    for method in ("cold_start", "warm_start"):
        reference = initial.copy()
        windows = []
        for start in range(0, demand.shape[0], window_size):
            window = start // window_size + 1
            rng, record = make_stream(config, method, window)
            inherited = reference if method == "warm_start" and window > 1 else None
            result = run_ga(demand[start:start + window_size], config, rng, "dynamic", reference, inherited)
            result.update(window=window, sample_start=start + 1, sample_end=start + window_size,
                          reference=reference.copy())
            record["final_state"] = rng.bit_generator.state
            results["streams"].append(record)
            windows.append(result)
            reference = result["placement"].copy()
            if on_window is not None:
                on_window(method, result)
        results[method] = windows
    return results
