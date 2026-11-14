"""Derived figures from existing results only; never import or execute GA."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .output_layout import figure_path


def plot_saved_results(root, matrix, results, config):
    """Existing/reconstructed PM loads, same PM colors and workload scales everywhere."""
    infra = config["infrastructure"]
    capacity = infra["pm_cpu_capacity_vcpu"]
    safe = capacity * infra["safe_cpu_threshold"]
    pm_count = infra["available_pm_count"]
    series, records = {}, []
    labels = {"static_baseline": "Static random baseline", "static_ga": "Static GA",
              "dynamic_cold_start": "Dynamic cold-start", "dynamic_warm_start": "Dynamic warm-start"}
    if "static" in results:
        for method in ("baseline", "ga"):
            r = results["static"][method]
            key = f"static_{method}"
            series[key] = r["loads_vcpu"]
            records.append((key, r["metrics"]["status"], r["metrics"]["active_pm_count"],
                            r["metrics"]["migration_count"], r["metrics"]["overload_events"], None))
    if "dynamic" in results:
        for method in ("cold_start", "warm_start"):
            windows = results["dynamic"][method]
            key = f"dynamic_{method}"
            series[key] = np.vstack([r["loads_vcpu"] for r in windows])
            feasible = sum(r["metrics"]["status"] == "FEASIBLE" for r in windows)
            active = [r["metrics"]["active_pm_count"] for r in windows]
            records.append((key, "FEASIBLE" if feasible == len(windows) else "INFEASIBLE",
                            max(active), sum(r["metrics"]["migration_count"] for r in windows),
                            sum(r["metrics"]["overload_events"] for r in windows),
                            (feasible, len(windows), min(active), max(active))))
    if not series:
        return
    colors = plt.get_cmap("tab20")(np.linspace(0, 1, pm_count))
    ymax = max(capacity, max(float(a.max()) for a in series.values())) * 1.08

    def save(fig, category, name):
        fig.suptitle(f"{name.replace('_', ' ')} — single run, seed {config['project']['master_seed']}")
        fig.tight_layout(rect=(0, 0.03, 1, 0.95))
        for extension in ("png", "svg"):
            path = figure_path(root, config, category, name, extension)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                raise FileExistsError(f"Refusing to overwrite figure: {path}")
            fig.savefig(path, dpi=160)
        plt.close(fig)

    def workload(ax, key):
        loads = series[key]
        if loads.shape != (matrix.shape[0], pm_count):
            raise ValueError(f"Wrong reconstructed load shape: {key}")
        for pm in range(pm_count):
            ax.plot(np.arange(len(loads)), loads[:, pm], color=colors[pm], lw=0.8, label=f"PM {pm + 1}")
        ax.axhline(safe, color="black", ls="--", lw=1.4, label=f"Safe capacity {safe:g} vCPU")
        ax.axhline(capacity, color="crimson", ls=":", lw=1.4, label=f"Physical capacity {capacity:g} vCPU")
        ax.set(title=labels[key], xlabel="Sample index (zero-based)", ylabel="CPU workload (vCPU)",
               xlim=(0, matrix.shape[0] - 1), ylim=(0, ymax))
        ax.grid(alpha=0.2)
        ax.legend(ncol=7, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.19))

    for key in series:
        fig, ax = plt.subplots(figsize=(13, 5.5))
        workload(ax, key)
        save(fig, "workload_timeseries", key)
    for kind, keys in (("static", ("static_baseline", "static_ga")),
                       ("dynamic", ("dynamic_cold_start", "dynamic_warm_start"))):
        if all(k in series for k in keys):
            fig, axes = plt.subplots(2, 1, figsize=(13, 11), sharex=True, sharey=True)
            for ax, key in zip(axes, keys):
                workload(ax, key)
            save(fig, "workload_timeseries", f"{kind}_comparison")

    method_names = [labels[r[0]].replace(" ", "\n", 1) for r in records]
    method_colors = ["#b4544d" if r[1] == "INFEASIBLE" else "#377f78" for r in records]
    cold = next((r[3] for r in records if r[0] == "dynamic_cold_start"), None)
    warm = next((r[3] for r in records if r[0] == "dynamic_warm_start"), None)
    reduction = (cold - warm) / cold * 100 if cold else None

    def panel(ax, metric):
        if metric == "feasibility":
            values = [int(r[1] == "FEASIBLE") if r[5] is None else r[5][0] / r[5][1] for r in records]
            annotations = [f"{r[1]}\n(full-day static)" if r[5] is None else
                           f"{r[1]}\n{r[5][0]}/{r[5][1]} feasible windows" for r in records]
            ax.set(ylim=(0, 1.55), ylabel="Feasible fraction (static: full-day 0 or 1)")
        else:
            index = {"active_pm": 2, "migration": 3, "overload": 4}[metric]
            values = [r[index] for r in records]
            annotations = [f"{v:,}" for v in values]
            if metric == "active_pm":
                annotations = [str(r[2]) if r[5] is None else f"{r[5][2]}–{r[5][3]} in all {r[5][1]} windows"
                               for r in records]
            if metric == "overload":
                annotations = [text + ("\nINFEASIBLE" if r[1] == "INFEASIBLE" else "")
                               for text, r in zip(annotations, records)]
            ax.set(ylabel={"active_pm": "Active PM count (dynamic: range annotated)",
                           "migration": "VM migrations (different static/dynamic definitions)",
                           "overload": "Overloaded PM–sample pairs"}[metric],
                   ylim=(0, max(max(values) * 1.5, 1.5)))
        bars = ax.bar(method_names, values, color=method_colors)
        ax.bar_label(bars, labels=annotations, padding=5, fontsize=8)
        ax.tick_params(axis="x", labelsize=8)
        ax.set_title({"feasibility": "Feasibility: static day vs. dynamic windows",
                      "active_pm": "Active PMs — no PM reduction demonstrated",
                      "migration": "Migrations — compare cold vs. warm within dynamic",
                      "overload": "Overload events — strict utilization > safe threshold"}[metric], fontsize=10)
        if metric == "migration" and reduction is not None:
            ax.text(0.98, 0.95, f"Warm vs. cold: {reduction:.1f}% fewer migrations",
                    transform=ax.transAxes, ha="right", va="top", fontsize=8)
        ax.grid(axis="y", alpha=0.2)

    for metric, name in (("feasibility", "feasibility_comparison"), ("active_pm", "active_pm_comparison"),
                         ("migration", "migration_comparison"), ("overload", "overload_comparison")):
        fig, ax = plt.subplots(figsize=(11, 5))
        panel(ax, metric)
        fig.text(0.5, 0.01, "Static migrations: from baseline. Dynamic: all window transitions, including initial to Window 1.",
                 ha="center", fontsize=8)
        save(fig, "performance_comparison", name)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    for ax, metric in zip(axes.flat, ("feasibility", "active_pm", "migration", "overload")):
        panel(ax, metric)
    fig.text(0.5, 0.01, "Red: infeasible method. Green: feasible method. Static and dynamic migration totals have different definitions.",
             ha="center", fontsize=9)
    save(fig, "performance_comparison", "experiment_summary_dashboard")
