"""Persist validation and single-run experiment artifacts without overwrites."""

import csv
import json
from pathlib import Path
import platform
import sys

import numpy as np
import yaml

from .output_layout import output_path


def write_csv(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_validation(config, matrix, ids, manifest, actions, destination, experiment=False):
    destination = Path(destination)
    # Refuse existing destinations to preserve previous artifacts.
    destination.mkdir(parents=True, exist_ok=False)
    data_dir = output_path(destination, config, "data")
    summaries = output_path(destination, config, "summaries")
    data_dir.mkdir(parents=True)
    summaries.mkdir(parents=True)
    np.save(data_dir / "workload_matrix.npy", matrix, allow_pickle=False)
    write_csv(data_dir / "vm_order.csv", [{"column_index": i, "vm_id": vm} for i, vm in enumerate(ids)],
              ["column_index", "vm_id"])
    write_csv(data_dir / "dataset_files.csv", manifest,
              ["vm_id", "path", "sha256", "samples", "status", "reason"])
    totals = matrix.sum(axis=1) * config["infrastructure"]["vm_cpu_capacity_vcpu"]
    summary = {
        "observed_samples": matrix.shape[0], "observed_vms": matrix.shape[1],
        "minimum_utilization_ratio": float(matrix.min()),
        "maximum_utilization_ratio": float(matrix.max()),
        "mean_utilization_ratio": float(matrix.mean()),
        "mean_aggregate_demand_vcpu": float(totals.mean()),
        "maximum_aggregate_demand_vcpu": float(totals.max()),
        "minimum_aggregate_demand_vcpu": float(totals.min()),
    }
    write_csv(data_dir / "dataset_summary.csv", [summary], list(summary))
    report = ["Data validation for experiment." if experiment else "VALIDATION ONLY: no GA or experiment was run.",
              "Schema: one numeric sample per line, no header; sample-index alignment.",
              "Stable VM order: lexicographic filename order.",
              f"Input scale: {config['dataset']['input_scale']}; output scale: ratio.",
              "Scale taken from explicit configuration, not inferred from magnitude.",
              f"Expected VM count: {config['dataset']['expected_vm_count']}; observed: {len(ids)}.",
              f"Excluded traces: {len(actions)}."]
    if len(ids) != config["dataset"]["expected_vm_count"]:
        report.append("VM COUNT MISMATCH: review exclusions before any experiment.")
    report.extend(json.dumps(action) for action in actions)
    (data_dir / "data_validation.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    effective = {"configuration": config, "observed_dataset": summary,
                 "random_seed_list": None, "stage": "DATA_VALIDATION_ONLY",
                 "provenance": config["dataset"].get("provenance"),
                 "environment": {"python": sys.version, "platform": platform.platform(),
                                 "numpy": np.__version__, "PyYAML": yaml.__version__}}
    (summaries / "experiment_config.json").write_text(json.dumps(effective, indent=2) + "\n", encoding="utf-8")
    write_csv(summaries / "run_status.csv", [{"stage": "data_validation", "status": "VALIDATED",
              "experiment_started": False}], ["stage", "status", "experiment_started"])
    return summary


def save_result(directory, result, ids, config):
    """One optimization or baseline, including physical PM labels and all samples."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write_csv(directory / "placement.csv",
              ({"vm_id": vm, "pm_id": int(pm)} for vm, pm in zip(ids, result["placement"])),
              ["vm_id", "pm_id"])
    metrics = {"seed": config["project"]["master_seed"], **result["metrics"],
               "runtime_seconds": result["runtime_seconds"]}
    for key in ("window", "sample_start", "sample_end"):
        if key in result:
            metrics[key] = result[key]
    write_csv(directory / "metrics.csv", [metrics], list(metrics))
    arrays = {"placement": result["placement"], "loads_vcpu": result["loads_vcpu"],
              "utilization_ratio": result["loads_vcpu"] / config["infrastructure"]["pm_cpu_capacity_vcpu"]}
    for key in ("initial_population", "best_chromosomes", "reference"):
        if key in result:
            arrays[key] = result[key]
    np.savez_compressed(directory / "raw.npz", **arrays)
    if "history" in result:
        write_csv(directory / "fitness_history.csv", result["history"], list(result["history"][0]))
    return metrics


def dynamic_summary(method, windows, vm_count, seed):
    metrics = [r["metrics"] for r in windows]
    migrations = sum(m["migration_count"] for m in metrics)
    runtime = sum(r["runtime_seconds"] for r in windows)
    feasible = sum(m["status"] == "FEASIBLE" for m in metrics)
    return {"method": method, "seed": seed,
            "status": "FEASIBLE" if feasible == len(windows) else "INFEASIBLE",
            "feasible_windows": feasible, "infeasible_windows": len(windows) - feasible,
            "transitions": len(windows), "migration_count": migrations,
            "migration_rate": migrations / (vm_count * len(windows)),
            "mean_migrations_per_window": migrations / len(windows),
            "mean_active_pm_count": float(np.mean([m["active_pm_count"] for m in metrics])),
            "minimum_active_pm_count": min(m["active_pm_count"] for m in metrics),
            "maximum_active_pm_count": max(m["active_pm_count"] for m in metrics),
            "overload_events": sum(m["overload_events"] for m in metrics),
            "runtime_seconds": runtime, "mean_runtime_per_window_seconds": runtime / len(windows)}
