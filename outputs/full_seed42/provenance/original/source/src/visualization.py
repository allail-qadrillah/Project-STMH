"""Single-run figures; utilization means exclude inactive PMs, no cross-run stats."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .output_layout import figure_path, legacy_category


def plot_experiment(destination, matrix, results, config):
    seed = config["project"]["master_seed"]
    threshold = config["infrastructure"]["safe_cpu_threshold"]
    capacity = config["infrastructure"]["pm_cpu_capacity_vcpu"]

    def save(fig, name):
        fig.suptitle(f"{fig._suptitle.get_text() if fig._suptitle else name} — single run, seed {seed}")
        fig.tight_layout()
        path = figure_path(destination, config, legacy_category(name), name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(path)
        fig.savefig(path, dpi=150)
        plt.close(fig)

    def heatmap(loads, name):
        fig, ax = plt.subplots(figsize=(10, 4))
        image = ax.imshow(loads.T / capacity, aspect="auto", origin="lower", vmin=0)
        ax.set(xlabel="Sample index (zero-based)", ylabel="PM ID",
               yticks=np.arange(loads.shape[1]), yticklabels=np.arange(1, loads.shape[1] + 1))
        fig.colorbar(image, ax=ax, label=f"CPU utilization ratio (safe threshold {threshold})")
        save(fig, name)

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(matrix.sum(axis=1) * config["infrastructure"]["vm_cpu_capacity_vcpu"])
    ax.set(xlabel="Sample index (zero-based)", ylabel="Aggregate CPU demand (vCPU)")
    save(fig, "workload_timeseries")
    runtime_labels, runtimes = [], []
    distributions = []
    if "static" in results:
        static = results["static"]
        fig, ax = plt.subplots()
        ax.plot([h["generation"] for h in static["ga"]["history"]],
                [h["best_fitness"] for h in static["ga"]["history"]])
        ax.set(xlabel="Generation (0 = initialization)", ylabel="Best-so-far fitness")
        save(fig, "ga_convergence_static")
        for method in ("baseline", "ga"):
            heatmap(static[method]["loads_vcpu"], f"pm_utilization_heatmap_static_{method}")
            runtime_labels.append("static_" + method)
            runtimes.append(static[method]["runtime_seconds"])
            active = np.unique(static[method]["placement"]) - 1
            distributions.append(("static_" + method, (static[method]["loads_vcpu"][:, active] / capacity).ravel()))
        fig, axes = plt.subplots(1, 2, figsize=(9, 3))
        for ax, key in zip(axes, ("active_pm_count", "overload_events")):
            ax.bar(["baseline", "ga"], [static[m]["metrics"][key] for m in ("baseline", "ga")])
            ax.set(ylabel=key)
        save(fig, "static_comparison")
    if "dynamic" in results:
        dynamic = results["dynamic"]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for ax, method in zip(axes, ("cold_start", "warm_start")):
            for r in dynamic[method]:
                ax.plot([h["generation"] for h in r["history"]],
                        [h["best_fitness"] for h in r["history"]], label=str(r["window"]), linewidth=0.8)
            ax.set(title=method, xlabel="Generation", ylabel="Best-so-far fitness")
            ax.legend(title="Window", ncol=4, fontsize=6)
        save(fig, "ga_convergence_dynamic")
        for method in ("cold_start", "warm_start"):
            windows = dynamic[method]
            heatmap(np.vstack([r["loads_vcpu"] for r in windows]), f"pm_utilization_heatmap_dynamic_{method}")
            runtime_labels.append(method)
            runtimes.append(sum(r["runtime_seconds"] for r in windows))
            distributions.append((method, np.concatenate([
                (r["loads_vcpu"][:, np.unique(r["placement"]) - 1] / capacity).ravel() for r in windows])))
        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        for ax, key in zip(axes.flat, ("active_pm_count", "migration_count",
                                     "mean_active_pm_utilization_ratio", "overload_events")):
            for method in ("cold_start", "warm_start"):
                ax.plot([r["window"] for r in dynamic[method]],
                        [r["metrics"][key] for r in dynamic[method]], label=method)
            ax.set(xlabel="Window", ylabel=key)
            ax.legend()
        save(fig, "dynamic_comparison")
        fig, ax = plt.subplots()
        for method in ("cold_start", "warm_start"):
            ax.plot([r["window"] for r in dynamic[method]],
                    [r["runtime_seconds"] for r in dynamic[method]], label=method)
        ax.set(xlabel="Window", ylabel="Optimization runtime (seconds)")
        ax.legend()
        save(fig, "runtime_per_window")
    if distributions:
        fig, ax = plt.subplots()
        for label, values in distributions:
            ax.hist(values, bins=30, histtype="step", density=True, label=label)
        ax.axvline(threshold, color="black", linestyle="--", label="safe threshold")
        ax.set(xlabel="Active-PM CPU utilization ratio (inactive PMs excluded)", ylabel="Density")
        ax.legend()
        save(fig, "utilization_distribution")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(runtime_labels, runtimes)
    ax.set(ylabel="Runtime (seconds; dynamic = sum of window calls)")
    save(fig, "runtime_comparison")
