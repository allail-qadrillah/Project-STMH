"""Rebuild four-approach figures from saved GA artifacts; never executes optimization."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "outputs/four_experiments_comparison"
SOURCES = {
    "Initial GA (Original Baseline)": {
        "branch": "main (original source, isolated replay)",
        "root": Path("/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-active-pm-init/outputs/full_seed42/original"),
        "directory": "outputs/full_seed42/original",
    },
    "Experiment 1: Active-PM-aware Initialization": {
        "branch": "experiment/active-pm-aware-initialization",
        "root": Path("/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-active-pm-init/outputs/full_seed42/initialization"),
        "directory": "outputs/full_seed42/initialization",
    },
    "Experiment 2: Feasibility-preserving Relocation": {
        "branch": "experiment/feasibility-preserving-relocation",
        "root": Path("/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-feasible-relocation/outputs/full_seed42/relocation"),
        "directory": "outputs/full_seed42/relocation",
    },
    "Experiment 3: Consolidation-aware Mutation": {
        "branch": "experiment/consolidation-aware-mutation",
        "root": Path("/home/qadrillah/.local/share/opencode/worktree/de2f85/ga-consolidation-mutation/outputs/full_seed42/consolidation_retry2"),
        "directory": "outputs/full_seed42/consolidation_retry2",
    },
}
COLORS = dict(zip(SOURCES, plt.rcParams["axes.prop_cycle"].by_key()["color"]))


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def available(root, track):
    base = root / "experiments/dynamic" / track
    result = []
    if base.exists():
        for directory in sorted(base.glob("window_*")):
            metrics = directory / "metrics.csv"
            history = directory / "fitness_history.csv"
            if metrics.is_file():
                row = read_csv(metrics)[0]
                row["window"] = int(directory.name.removeprefix("window_"))
                row["history"] = read_csv(history) if history.is_file() else []
                result.append(row)
    return result


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data, source_manifest = {}, {}
    for label, item in SOURCES.items():
        root = item["root"]
        status_path = root / "summaries/execution_status.json"
        config_path = root / "summaries/experiment_config.json"
        static_path = root / "experiments/static/ga/metrics.csv"
        static_history = root / "experiments/static/ga/fitness_history.csv"
        static_generation = root / "experiments/static/ga/per_generation_metrics.csv"
        if not static_path.is_file():
            raise FileNotFoundError(static_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))["configuration"]
        static = read_csv(static_path)[0]
        data[label] = {
            "root": root,
            "status": json.loads(status_path.read_text(encoding="utf-8"))["status"] if status_path.exists() else "UNKNOWN",
            "config": config,
            "static": static,
            "static_history": read_csv(static_generation if static_generation.exists() else static_history),
            "cold": available(root, "cold_start"),
            "warm": available(root, "warm_start"),
        }
        files = [config_path, static_path]
        for p in (static_generation, static_history,
                  root / "experiments/static/ga/operator_metrics.csv",
                  root / "experiments/static/ga/cost.json"):
            if p.is_file():
                files.append(p)
        for track in ("cold_start", "warm_start"):
            for row in data[label]["cold" if track == "cold_start" else "warm"]:
                w = row["window"]
                directory = root / f"experiments/dynamic/{track}/window_{w:02d}"
                files.extend(p for p in (directory/"metrics.csv", directory/"fitness_history.csv",
                                         directory/"per_generation_metrics.csv", directory/"operator_metrics.csv",
                                         directory/"cost.json") if p.is_file())
        source_manifest[label] = {
            "branch": item["branch"], "output_directory": str(root), "declared_relative_directory": item["directory"],
            "run_status": data[label]["status"], "commit": "21cf4c1c9125cde31ca758f45fc4d8c812fb8fe9",
            "configuration": {"seed": config["project"]["master_seed"], "pm_count": config["infrastructure"]["available_pm_count"],
                              "vm_count": config["dataset"]["expected_vm_count"], "samples": config["dataset"]["expected_samples_per_vm"],
                              "population": config["genetic_algorithm"]["population_size"], "updates": config["genetic_algorithm"]["max_generations"]},
            "files": [{"path": str(p), "size_bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted(set(files))],
        }
    (OUTPUT / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2), encoding="utf-8")

    labels = list(SOURCES)
    seed = 42
    fig, axes = plt.subplots(1, 2, figsize=(9, 3))
    for ax, metric in zip(axes, ("active_pm_count", "overload_events")):
        vals = [int(data[k]["static"][metric]) for k in labels]
        ax.bar(["Original", "Exp 1", "Exp 2", "Exp 3"], vals,
               color=[COLORS[k] for k in labels])
        ax.set(ylabel=metric)
    fig.suptitle(f"static_comparison — single run, seed {seed}")
    save(fig, OUTPUT / "static_comparison.png")

    fig, ax = plt.subplots(figsize=(10, 3))
    for label in labels:
        hist = data[label]["static_history"]
        xkey = "generation"
        ykey = "best_fitness"
        ax.plot([int(r[xkey]) for r in hist], [float(r[ykey]) for r in hist],
                label=label, color=COLORS[label])
    ax.set(xlabel="Generation (0 = initialization)", ylabel="Best-so-far fitness")
    ax.legend(fontsize=7)
    fig.suptitle(f"ga_convergence_static — single run, seed {seed}")
    save(fig, OUTPUT / "ga_convergence_static.png")

    dynamic_rows = {}
    for track, track_title in (("cold", "cold_start"), ("warm", "warm_start")):
        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        for ax, metric in zip(axes.flat, ("active_pm_count", "migration_count",
                                         "mean_active_pm_utilization_ratio", "overload_events")):
            for label in labels:
                rs = data[label][track]
                ax.plot([r["window"] for r in rs], [float(r[metric]) for r in rs],
                        label=label, marker="o", linewidth=0.8, color=COLORS[label])
            ax.set(xlabel="Window", ylabel=metric, xticks=range(1, 25))
            ax.legend(fontsize=6)
        fig.suptitle(f"dynamic_comparison_{track_title} — single run, seed {seed}")
        save(fig, OUTPUT / f"dynamic_comparison_{track_title}.png")

        fig, ax = plt.subplots(figsize=(11, 4))
        for label in labels:
            for r in data[label][track]:
                h = r["history"]
                if h:
                    ax.plot([int(x["generation"]) for x in h], [float(x["best_fitness"]) for x in h],
                            label=f"{label}, W{r['window']:02d}", linewidth=0.8, color=COLORS[label])
        ax.set(xlabel="Generation", ylabel="Best-so-far fitness")
        ax.legend(title="Approach, window", ncol=4, fontsize=6)
        fig.suptitle(f"ga_convergence_dynamic_{track_title} — single run, seed {seed}")
        save(fig, OUTPUT / f"ga_convergence_dynamic_{track_title}.png")

        fig, ax = plt.subplots(figsize=(10, 4))
        for label in labels:
            rs = data[label][track]
            ax.plot([r["window"] for r in rs], [float(r["runtime_seconds"]) for r in rs],
                    label=label, marker="o", linewidth=0.8, color=COLORS[label])
        ax.set(xlabel="Window", ylabel="Optimization runtime (seconds)", xticks=range(1, 25))
        ax.legend(fontsize=7)
        fig.suptitle(f"runtime_per_window_{track_title} — single run, seed {seed}")
        save(fig, OUTPUT / f"runtime_per_window_{track_title}.png")
        dynamic_rows[track_title] = {k: data[k][track] for k in labels}

    matrix = np.load(data[labels[0]]["root"] / "data/workload_matrix.npy")
    config = data[labels[0]]["config"]
    capacity = config["infrastructure"]["pm_cpu_capacity_vcpu"]
    threshold = config["infrastructure"]["safe_cpu_threshold"]
    pm_colors = plt.get_cmap("tab20")(np.linspace(0, 1, 24))
    workload_series = {}
    for label in labels:
        root = data[label]["root"]
        workload_series[(label, "Static GA")] = np.load(root / "experiments/static/ga/raw.npz")["loads_vcpu"]
        for track, name in (("cold", "Dynamic cold-start"), ("warm", "Dynamic warm-start")):
            rows = data[label][track]
            arrays = [np.load(root / f"experiments/dynamic/{'cold_start' if track == 'cold' else 'warm_start'}/window_{r['window']:02d}/raw.npz")["loads_vcpu"] for r in rows]
            if len(arrays) == 24:
                workload_series[(label, name)] = np.vstack(arrays)

    # Main's saved-result workload figure: 13 x 5.5, same PM-ID tab20 mapping and limits.
    full_profiles = [key for key in workload_series if key[1] != "Static GA"]
    fig, axes = plt.subplots(len(full_profiles), 1, figsize=(13, 5.5 * len(full_profiles)), sharex=True, sharey=True)
    axes = np.atleast_1d(axes)
    ymax = max(capacity, max(float(x.max()) for x in workload_series.values())) * 1.08
    for ax, (label, kind) in zip(axes, full_profiles):
        loads = workload_series[(label, kind)]
        for pm in range(24):
            ax.plot(np.arange(len(loads)), loads[:, pm], color=pm_colors[pm], lw=0.8, label=f"PM {pm + 1}")
        ax.axhline(capacity * threshold, color="black", ls="--", lw=1.4, label=f"Safe capacity {capacity*threshold:g} vCPU")
        ax.axhline(capacity, color="crimson", ls=":", lw=1.4, label=f"Physical capacity {capacity:g} vCPU")
        ax.set(title=f"{label} / {kind}", xlabel="Sample index (zero-based)", ylabel="CPU workload (vCPU)", xlim=(0, 287), ylim=(0, ymax))
        ax.grid(alpha=0.2)
        ax.legend(ncol=7, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.19))
    fig.suptitle(f"workload_timeseries_dynamic_comparison — single run, seed {seed}")
    save(fig, OUTPUT / "workload_timeseries_dynamic_comparison.png")

    # Main's comparison histogram definition: active PMs only; inactive PMs excluded.
    fig, ax = plt.subplots()
    for label in labels:
        values = []
        root = data[label]["root"]
        for track in ("cold_start", "warm_start"):
            rows = data[label]["cold" if track == "cold_start" else "warm"]
            for r in rows:
                loads = np.load(root / f"experiments/dynamic/{track}/window_{r['window']:02d}/raw.npz")["loads_vcpu"]
                used = np.unique(np.load(root / f"experiments/dynamic/{track}/window_{r['window']:02d}/raw.npz")["placement"]) - 1
                values.extend((loads[:, used] / capacity).ravel())
        if values:
            ax.hist(values, bins=30, histtype="step", density=True, label=label, color=COLORS[label])
    ax.axvline(threshold, color="black", linestyle="--", label="safe threshold")
    ax.set(xlabel="Active-PM CPU utilization ratio (inactive PMs excluded)", ylabel="Density")
    ax.legend(fontsize=7)
    fig.suptitle(f"utilization_distribution_dynamic — single run, seed {seed}")
    save(fig, OUTPUT / "utilization_distribution_dynamic.png")

    for label in labels:
        root = data[label]["root"]
        loads = np.load(root / "experiments/static/ga/raw.npz")["loads_vcpu"]
        fig, ax = plt.subplots(figsize=(10, 4))
        image = ax.imshow(loads.T / capacity, aspect="auto", origin="lower", vmin=0)
        ax.set(xlabel="Sample index (zero-based)", ylabel="PM ID",
               yticks=np.arange(24), yticklabels=np.arange(1, 25))
        fig.colorbar(image, ax=ax, label=f"CPU utilization ratio (safe threshold {threshold})")
        fig.suptitle(f"pm_utilization_heatmap_static_ga — {label}, single run, seed {seed}")
        slug = ("original" if label.startswith("Initial GA") else
                "experiment_1" if label.startswith("Experiment 1") else
                "experiment_2" if label.startswith("Experiment 2") else "experiment_3")
        save(fig, OUTPUT / f"pm_utilization_heatmap_static_ga_{slug}.png")

    # Original saved-results performance dashboard structure and metric definitions.
    metric_specs = (("feasibility", "Feasible fraction"), ("active_pm", "Active PM count"),
                    ("migration", "VM migrations (static/dynamic definitions differ)"),
                    ("overload", "Overloaded PM–sample pairs"))
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    compact = ["Original", "Exp 1", "Exp 2", "Exp 3"]
    approach_colors = ["#377f78"] * 4
    for ax, (metric, ylabel) in zip(axes.flat, metric_specs):
        vals, annotations = [], []
        for label in labels:
            r = data[label]["static"]
            if metric == "feasibility":
                val = 1.0 if r["status"] == "FEASIBLE" else 0.0
                annotation = f"{r['status']}\n(full-day static)"
            elif metric == "active_pm":
                val = int(r["active_pm_count"])
                annotation = str(val)
            elif metric == "migration":
                val = int(r["migration_count"])
                annotation = f"{val:,}"
            else:
                val = int(r["overload_events"])
                annotation = f"{val:,}" + ("\nINFEASIBLE" if r["status"] != "FEASIBLE" else "")
            vals.append(val)
            annotations.append(annotation)
        bars = ax.bar(compact, vals, color=approach_colors)
        ax.bar_label(bars, labels=annotations, padding=5, fontsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.set(ylabel=ylabel, ylim=(0, max(max(vals) * 1.5, 1.5)))
        ax.set_title(metric.replace("_", " ").title(), fontsize=10)
        ax.grid(axis="y", alpha=0.2)
    fig.text(0.5, 0.01, "Static migrations: from each run's random reference. Green: feasible.", ha="center", fontsize=9)
    fig.suptitle(f"experiment_summary_dashboard_static — single run, seed {seed}")
    save(fig, OUTPUT / "experiment_summary_dashboard_static.png")

    summary_csv = OUTPUT / "comparison_summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as stream:
        fields = ["approach", "source_branch", "run_status", "static_status", "active_pm_count", "pm_reduction_percent",
                  "overload_events", "static_migrations", "static_runtime_seconds", "cold_windows_available",
                  "cold_feasible_windows", "cold_migrations_available", "warm_windows_available", "warm_feasible_windows", "warm_migrations_available"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for label in labels:
            d = data[label]
            r = d["static"]
            cold, warm = d["cold"], d["warm"]
            writer.writerow({"approach": label, "source_branch": SOURCES[label]["branch"], "run_status": d["status"],
                "static_status": r["status"], "active_pm_count": r["active_pm_count"],
                "pm_reduction_percent": f"{(24-int(r['active_pm_count']))/24*100:.6f}",
                "overload_events": r["overload_events"], "static_migrations": r["migration_count"],
                "static_runtime_seconds": r["runtime_seconds"], "cold_windows_available": len(cold),
                "cold_feasible_windows": sum(x["status"] == "FEASIBLE" for x in cold),
                "cold_migrations_available": sum(int(x["migration_count"]) for x in cold),
                "warm_windows_available": len(warm), "warm_feasible_windows": sum(x["status"] == "FEASIBLE" for x in warm),
                "warm_migrations_available": sum(int(x["migration_count"]) for x in warm)})

    dynamic_csv = OUTPUT / "dynamic_window_summary.csv"
    with dynamic_csv.open("w", newline="", encoding="utf-8") as stream:
        fields = ["approach", "track", "window", "status", "active_pm_count", "migration_count", "overload_events",
                  "mean_active_pm_utilization_ratio", "runtime_seconds", "fitness"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for label in labels:
            for track, key in (("cold_start", "cold"), ("warm_start", "warm")):
                for row in data[label][key]:
                    writer.writerow({"approach": label, "track": track, **{field: row.get(field, "") for field in fields[2:]}})

    operator_csv = OUTPUT / "operator_diagnostics.csv"
    with operator_csv.open("w", newline="", encoding="utf-8") as stream:
        fields = ["approach", "track", "window", "attempts", "accepted", "rejected", "reducing_active_pm",
                  "same_active_pm", "increasing_active_pm", "successful", "failed", "pms_emptied", "vms_moved",
                  "tentative_moves", "discarded_moves", "feasibility_evaluations", "runtime_seconds"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for label in labels:
            root = data[label]["root"]
            targets = [("static", 0)]
            targets += [(track, row["window"]) for track, key in (("cold_start", "cold"), ("warm_start", "warm")) for row in data[label][key]]
            for track, window in targets:
                path = root / ("experiments/static/ga/operator_metrics.csv" if track == "static" else f"experiments/dynamic/{track}/window_{window:02d}/operator_metrics.csv")
                if path.exists():
                    r = read_csv(path)[0]
                    writer.writerow({"approach": label, "track": track, "window": window or "", **{field: r.get(field, "") for field in fields[3:]}})

    summary = ["# Four-approach GA comparison", "", "Seed 42 single-run comparison. No statistical significance or winner claim.", "",
               "## Data availability", "",
               "Original, Experiment 1, and Experiment 2: static plus all 24 cold-start and 24 warm-start windows. Experiment 3: static plus cold-start windows 1–4 only; warm-start has zero completed windows. Missing windows are omitted, never set to zero, interpolated, or extrapolated. Experiment 3 run remains incomplete (`RUNNING` status at source capture).", "",
               "## Static comparison", "", "| Approach | Source branch | PMs | Status | Active PMs | PM reduction vs 24 | Overload events | Migrations | GA runtime (s) |", "|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for label in labels:
        r = data[label]["static"]
        summary.append(f"| {label} | {SOURCES[label]['branch']} | {data[label]['config']['infrastructure']['available_pm_count']} | {r['status']} | {r['active_pm_count']} | {(24-int(r['active_pm_count']))/24*100:.2f}% | {r['overload_events']} | {r['migration_count']} | {float(r['runtime_seconds']):.3f} |")
    summary += ["", "Static migration count is measured against each run's random static placement reference; it is not a cross-approach migration comparison. Static runs use 24 PMs for all rows. Historical main output uses 12 PMs and is excluded from this comparison.", "", "## Dynamic availability", "", "| Approach | Cold-start windows | Warm-start windows |", "|---|---:|---:|"]
    for label in labels:
        summary.append(f"| {label} | {len(data[label]['cold'])}/24 | {len(data[label]['warm'])}/24 |")
    summary += ["", "Dynamic migration includes initial-placement-to-window-1 and subsequent window transitions, consistently within each run. Feasible fractions and PM utilization use original definitions. Fitness/convergence is best-so-far per generation.", "", "## Runtime and diagnostics", "",
                "`dynamic_window_summary.csv` contains saved window metrics and runtime. `operator_diagnostics.csv` contains saved counters only; absent rows mean unavailable artifact, not zero. Relocation and consolidation counters are operator-specific and are not equivalent operation counts. Per-generation histories and initial population quality remain in the source results and are hash-listed in `source_manifest.json`.", "",
                "## Figures", "", "`static_comparison.png`, `ga_convergence_static.png`, `dynamic_comparison_cold_start.png`, `dynamic_comparison_warm_start.png`, `ga_convergence_dynamic_cold_start.png`, `ga_convergence_dynamic_warm_start.png`, `runtime_per_window_cold_start.png`, `runtime_per_window_warm_start.png`, `experiment_summary_dashboard_static.png`, `workload_timeseries_dynamic_comparison.png`, `utilization_distribution_dynamic.png`, and four `pm_utilization_heatmap_static_ga_*.png` files. Dynamic curves contain only saved windows.", "",
                "## Reproduction", "", "Run from this project checkout with Python and matplotlib/numpy installed: `python server_consolidation_ga/compare_four_experiments.py`. Script reads saved source files, verifies expected run structures, hashes inputs, and writes only this output directory. It never imports or executes GA optimization code.", "",
                "## Limitations", "", "Single seed 42; descriptive only. Original baseline is a replay of original `main` GA source under approved 24-PM protocol; historical main result used 12 PM and is not mixed. Experiment 3 partial dynamic output cannot support complete cold/warm or 24-window claims. Source run status is preserved in manifest.", ""]
    (OUTPUT / "README.md").write_text("\n".join(summary), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
