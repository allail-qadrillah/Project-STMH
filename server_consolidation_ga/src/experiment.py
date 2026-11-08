"""Run orchestration and incremental persistence; no algorithm choices here."""

import hashlib
import json
from pathlib import Path

import matplotlib

from .dynamic_experiment import run_dynamic
from .reporting import dynamic_summary, save_result, save_validation, write_csv
from .static_experiment import run_static
from .visualization import plot_experiment
from .workload import cpu_demand_vcpu
from .output_layout import output_path
from .output_documentation import document_outputs
from .output_organization import save_combined_tables
from .result_visualization import plot_saved_results


def run_experiment(config, matrix, ids, manifest, actions, destination, gate=None, progress=None):
    destination = Path(destination)
    save_validation(config, matrix, ids, manifest, actions, destination, experiment=True)
    summaries = output_path(destination, config, "summaries")
    experiments = output_path(destination, config, "experiments")
    effective_path = summaries / "experiment_config.json"
    effective = json.loads(effective_path.read_text(encoding="utf-8"))
    source_root = Path(__file__).resolve().parents[1]
    sources = [source_root / "main.py", source_root / "requirements.txt",
               *sorted((source_root / "src").glob("*.py")), *sorted((source_root / "tests").glob("*.py"))]
    effective.update(stage="EXPERIMENT", random_seed_list=[config["project"]["master_seed"]],
                     run_count_per_method=config["project"]["random_seeds"],
                     rng="numpy.random.Generator(PCG64(SeedSequence(master_seed, spawn_key=(role_id, window))))",
                     source_sha256={str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sources}, gate=gate)
    effective["environment"]["matplotlib"] = matplotlib.__version__
    effective_path.write_text(json.dumps(effective, indent=2) + "\n", encoding="utf-8")
    if gate is not None:
        (summaries / "acceptance_tests.txt").write_text(gate["report"], encoding="utf-8")
    status_path = summaries / "execution_status.json"
    status_path.write_text(json.dumps({"status": "RUNNING"}) + "\n", encoding="utf-8")
    streams, summary_rows, status_rows = [], [], []
    results = {}
    seed = config["project"]["master_seed"]
    try:
        demand = cpu_demand_vcpu(matrix, config["infrastructure"]["vm_cpu_capacity_vcpu"])
        if config["experiments"]["static"]["enabled"]:
            static = run_static(demand, config)
            results["static"] = static
            streams.extend(static["streams"])
            for method in ("baseline", "ga"):
                row = {"method": "static_" + method,
                       **save_result(experiments / "static" / method, static[method], ids, config)}
                summary_rows.append(row)
                status_rows.append({k: row[k] for k in ("method", "seed", "status")})
            write_csv(experiments / "static" / "per_seed_metrics.csv", summary_rows, list(summary_rows[0]))
            if progress is not None:
                progress("static_ga", static["ga"])
        if config["experiments"]["dynamic"]["enabled"]:
            def save_window(method, result):
                save_result(experiments / "dynamic" / method / f"window_{result['window']:02d}", result, ids, config)
                if progress is not None:
                    progress(method, result)

            dynamic = run_dynamic(demand, config, on_window=save_window)
            results["dynamic"] = dynamic
            streams.extend(dynamic["streams"])
            write_csv(experiments / "dynamic" / "initial_placement.csv",
                      ({"vm_id": vm, "pm_id": int(pm)} for vm, pm in zip(ids, dynamic["initial_placement"])),
                      ["vm_id", "pm_id"])
            for method in ("cold_start", "warm_start"):
                windows = dynamic[method]
                rows = [{"seed": seed, "window": r["window"], "sample_start": r["sample_start"],
                         "sample_end": r["sample_end"], **r["metrics"],
                         "runtime_seconds": r["runtime_seconds"]} for r in windows]
                write_csv(experiments / "dynamic" / method / "per_window_metrics.csv", rows, list(rows[0]))
                summary_rows.append(dynamic_summary(method, windows, len(ids), seed))
                status_rows.extend({"method": method, "seed": seed, "window": r["window"],
                                    "status": r["metrics"]["status"]} for r in windows)
        fields = list(dict.fromkeys(key for row in summary_rows for key in row))
        write_csv(summaries / "experiment_summary.csv", summary_rows, fields)
        write_csv(summaries / "run_status.csv", status_rows, ["method", "seed", "window", "status"])
        (summaries / "random_streams.json").write_text(json.dumps(streams, indent=2) + "\n", encoding="utf-8")
        plot_experiment(destination, matrix, results, config)
        save_combined_tables(destination, config)
        plot_saved_results(destination, matrix, results, config)
        document_outputs(destination, config)
        status_path.write_text(json.dumps({"status": "COMPLETED", "seed": seed,
                              "feasibility_status": "INFEASIBLE" if any(
                                  r["status"] == "INFEASIBLE" for r in status_rows) else "FEASIBLE"}) + "\n",
                              encoding="utf-8")
    except BaseException as exc:
        status_path.write_text(json.dumps({"status": "FAILED", "error": str(exc),
                                         "error_type": type(exc).__name__}) + "\n", encoding="utf-8")
        raise
    return results
