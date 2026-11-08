"""Strict configuration loading; paths resolve relative to the YAML file."""

from pathlib import Path
import math

import yaml


def load_config(path):
    path = Path(path).resolve(strict=True)
    with path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")
    required = {
        "project": ("name", "random_seeds", "master_seed", "rng", "stream_ids"),
        "dataset": ("path", "format", "input_scale", "expected_vm_count",
                    "expected_samples_per_vm", "sample_interval_minutes", "date_label",
                    "file_pattern", "timestamp_column", "vm_id_column"),
        "preprocessing": ("missing_value_policy", "invalid_value_policy", "stable_vm_order"),
        "infrastructure": ("vm_cpu_capacity_vcpu", "pm_cpu_capacity_vcpu",
                           "available_pm_count", "safe_cpu_threshold"),
        "genetic_algorithm": ("population_size", "max_generations", "tournament_size",
                              "crossover", "mutation", "elitism_count"),
        "fitness": ("server_weight", "migration_weight", "feasibility_tolerance"),
        "experiments": ("static", "dynamic"),
        "output": ("directory", "save_placements", "save_per_generation_history",
                   "save_per_seed_metrics", "save_plots"),
    }
    for section, keys in required.items():
        if not isinstance(config.get(section), dict):
            raise ValueError(f"Missing or invalid section: {section}")
        for key in keys:
            if key not in config[section]:
                raise ValueError(f"Missing configuration: {section}.{key}")
    nested = {
        ("genetic_algorithm", "crossover"): ("type", "probability"),
        ("genetic_algorithm", "mutation"): ("type", "per_gene_probability"),
        ("experiments", "static"): ("enabled", "evaluate_all_samples", "include_migration_in_objective"),
        ("experiments", "dynamic"): ("enabled", "window_size_samples", "compare_cold_start",
                                    "compare_warm_start", "same_initial_placement"),
    }
    for (section, key), fields in nested.items():
        value = config[section][key]
        if not isinstance(value, dict) or any(field not in value for field in fields):
            raise ValueError(f"Missing settings in {section}.{key}: {fields}")
    integers = {
        "project": ("random_seeds",),
        "dataset": ("expected_vm_count", "expected_samples_per_vm", "sample_interval_minutes"),
        "infrastructure": ("available_pm_count",),
        "genetic_algorithm": ("population_size", "max_generations", "tournament_size", "elitism_count"),
    }
    for section, keys in integers.items():
        for key in keys:
            value = config[section][key]
            if type(value) is not int or value <= 0:
                raise ValueError(f"{section}.{key} must be a positive integer")
    project = config["project"]
    if project["random_seeds"] != 1 or project["master_seed"] != 42 or type(project["master_seed"]) is not int:
        raise ValueError("Approved experiment requires exactly one run with master seed 42")
    if project["rng"] != "PCG64":
        raise ValueError("Approved RNG is NumPy PCG64")
    streams = project["stream_ids"]
    if (not isinstance(streams, dict) or set(streams) != {
            "static_baseline", "static_ga", "dynamic_initial", "cold_start", "warm_start"}
            or any(type(v) is not int or v < 0 for v in streams.values())
            or len(set(streams.values())) != len(streams)):
        raise ValueError("stream_ids must assign distinct nonnegative integer IDs to all five roles")
    if config.get("methodology") != {
        "warm_start_inherited_count": 1,
        "warm_start_remaining": "independent_uniform_random",
        "tournament_replacement": True,
        "tournament_ties": "random_participant",
        "elitism_ties": "random",
        "best_so_far_ties": "first_seen",
        "initial_placement": "migration_reference_only",
        "generation_count": "reproduction_updates",
        "infeasible_windows": "continue_with_selected",
        "migration_transitions": "include_initial",
    }:
        raise ValueError("Missing or unsupported approved methodology policy")
    infra, ga, fit = (config[k] for k in ("infrastructure", "genetic_algorithm", "fitness"))
    for name, value in {
        "vm_cpu_capacity_vcpu": infra["vm_cpu_capacity_vcpu"],
        "pm_cpu_capacity_vcpu": infra["pm_cpu_capacity_vcpu"],
        "feasibility_tolerance": fit["feasibility_tolerance"],
    }.items():
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    for name, value in {
        "safe_cpu_threshold": infra["safe_cpu_threshold"],
        "server_weight": fit["server_weight"], "migration_weight": fit["migration_weight"],
        "crossover.probability": ga["crossover"]["probability"],
        "mutation.per_gene_probability": ga["mutation"]["per_gene_probability"],
    }.items():
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be a finite probability")
    if not 0 < infra["safe_cpu_threshold"] < 1:
        raise ValueError("safe_cpu_threshold must be strictly between 0 and 1")
    if not math.isclose(fit["server_weight"] + fit["migration_weight"], 1, abs_tol=1e-12):
        raise ValueError("Fitness weights must sum to 1")
    if infra["available_pm_count"] < 2:
        raise ValueError("Random reassignment requires at least two PMs")
    if ga["elitism_count"] >= ga["population_size"] or ga["tournament_size"] > ga["population_size"]:
        raise ValueError("Invalid elitism or tournament size")
    if ga["crossover"]["type"] != "uniform" or ga["mutation"]["type"] != "random_reassignment":
        raise ValueError("Unsupported GA operators; user clarification required")
    data, prep = config["dataset"], config["preprocessing"]
    if data["format"] != "planetlab_per_vm_files":
        raise ValueError("Unsupported dataset layout; ask user before changing format")
    if data["timestamp_column"] is not None or data["vm_id_column"] is not None:
        raise ValueError("Per-VM line layout has no timestamp or VM ID column; ask user")
    if data["input_scale"] not in ("percentage", "ratio"):
        raise ValueError("input_scale must be percentage or ratio")
    if data["file_pattern"] is not None and (not isinstance(data["file_pattern"], str) or not data["file_pattern"]):
        raise ValueError("file_pattern must be null or a nonempty glob")
    if prep != {"missing_value_policy": "exclude_vm", "invalid_value_policy": "error", "stable_vm_order": True}:
        raise ValueError("Unsupported preprocessing policy; user clarification required")
    for section, keys in {
        "static": ("enabled", "evaluate_all_samples", "include_migration_in_objective"),
        "dynamic": ("enabled", "compare_cold_start", "compare_warm_start", "same_initial_placement"),
    }.items():
        for key in keys:
            if type(config["experiments"][section][key]) is not bool:
                raise ValueError(f"experiments.{section}.{key} must be boolean")
    static, dynamic = (config["experiments"][key] for key in ("static", "dynamic"))
    if not static["evaluate_all_samples"] or static["include_migration_in_objective"]:
        raise ValueError("Static experiment must use all samples and exclude migration objective")
    if not all(dynamic[key] for key in ("compare_cold_start", "compare_warm_start", "same_initial_placement")):
        raise ValueError("Dynamic comparison requires both methods and common initial placement")
    window = dynamic["window_size_samples"]
    if type(window) is not int or window <= 0 or data["expected_samples_per_vm"] % window:
        raise ValueError("Window size must divide sample count exactly")
    for key in ("save_placements", "save_per_generation_history", "save_per_seed_metrics", "save_plots"):
        if config["output"][key] is not True:
            raise ValueError(f"Required output must be enabled: {key}")
    for section, key in (("dataset", "path"), ("output", "directory")):
        value = config[section][key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{section}.{key} must be a nonempty path")
        config[section][key] = str((path.parent / value).resolve())
    return config
