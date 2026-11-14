"""Plot only available seed-42 artifacts; partial tracks remain visibly partial."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = Path(__file__).resolve().parents[1]
ROOTS = {
    "Original": BASE / "outputs/full_seed42/original",
    "Initialization": BASE / "outputs/full_seed42/initialization",
    "Relocation": BASE.parent / "ga-feasible-relocation/outputs/full_seed42/relocation",
    "Consolidation (partial)": BASE.parent / "ga-consolidation-mutation/outputs/full_seed42/consolidation_retry2",
}
COLORS = ["#555f6d", "#2674c7", "#d17b19", "#27865b"]


def read(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", dpi=160)
    plt.close(fig)


def main():
    out = BASE / "outputs/full_seed42/available_results_visualizations"
    out.mkdir(exist_ok=True, parents=True)
    static, histories, dynamic = {}, {}, {}
    for variant, root in ROOTS.items():
        static[variant] = read(root / "experiments/static/ga/metrics.csv")[0]
        histories[variant] = read(root / "experiments/static/ga/per_generation_metrics.csv")
        for track in ("cold_start", "warm_start"):
            d = root / f"experiments/dynamic/{track}"
            dynamic[variant, track] = []
            if d.exists():
                for window in sorted(d.glob("window_*")):
                    metrics = window / "metrics.csv"
                    if metrics.exists():
                        row = read(metrics)[0]
                        row["window"] = int(window.name.split("_")[1])
                        dynamic[variant, track].append(row)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for color, (variant, row) in zip(COLORS, static.items()):
        axes[0].bar(variant, int(row["active_pm_count"]), color=color)
        axes[1].bar(variant, float(row["runtime_seconds"])/60, color=color)
        axes[2].bar(variant, int(row["overload_events"]), color=color)
    axes[0].set(title="Static GA: active PMs", ylabel="PM count")
    axes[1].set(title="Static GA runtime", ylabel="Minutes")
    axes[2].set(title="Static GA overload events", ylabel="Events")
    for ax in axes:
        ax.tick_params(axis="x", rotation=30)
    save(fig, out, "static_comparison")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for color, variant in zip(COLORS, ROOTS):
        hs = histories[variant]
        axes[0].plot([int(x["generation"]) for x in hs], [int(x["best_feasible_active_pm_count"]) if x["best_feasible_active_pm_count"] else np.nan for x in hs], label=variant, color=color)
        axes[1].plot([int(x["generation"]) for x in hs], [int(x["feasible_population_count"]) for x in hs], label=variant, color=color)
        axes[2].plot([int(x["generation"]) for x in hs], [float(x["best_fitness"]) for x in hs], label=variant, color=color)
    for ax, title, ylabel in zip(axes, ("Best feasible active PMs", "Feasible candidates", "Best fitness"), ("PM count", "Count / 50", "Fitness")):
        ax.set(title=title, xlabel="Generation", ylabel=ylabel)
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=7)
    save(fig, out, "static_convergence")

    for track in ("cold_start", "warm_start"):
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        for color, variant in zip(COLORS, ROOTS):
            rows = dynamic[variant, track]
            if not rows:
                continue
            x = [r["window"] for r in rows]
            axes[0].plot(x, [int(r["active_pm_count"]) for r in rows], marker="o", label=f"{variant} (n={len(rows)})", color=color)
            axes[1].plot(x, [int(r["migration_count"]) for r in rows], marker="o", label=variant, color=color)
        axes[0].set(title=f"{track}: active PMs by completed window", ylabel="Active PMs")
        axes[1].set(title="VM migrations", xlabel="Window", ylabel="VMs migrated")
        for ax in axes:
            ax.set_xticks(range(1, 25))
            ax.grid(alpha=.2)
            ax.legend(fontsize=8)
        save(fig, out, f"{track}_partial")

    rows = ["# Available evaluation results", "", "Seed 42, single-run observations. Consolidation results are partial; no winner claim.", "", "## Static GA", "", "| Variant | Status | Active PMs | Overload events | Migrations | Runtime (min) |", "|---|---|---:|---:|---:|---:|"]
    for variant, r in static.items():
        rows.append(f"| {variant} | {r['status']} | {r['active_pm_count']} | {r['overload_events']} | {r['migration_count']} | {float(r['runtime_seconds'])/60:.2f} |")
    rows += ["", "![Static comparison](static_comparison.png)", "", "![Static convergence](static_convergence.png)", "", "## Dynamic progress", "", "| Variant | Cold windows | Warm windows | Cold feasible | Warm feasible |", "|---|---:|---:|---:|---:|"]
    for variant in ROOTS:
        cold, warm = dynamic[variant, "cold_start"], dynamic[variant, "warm_start"]
        cf = sum(r["status"] == "FEASIBLE" for r in cold)
        wf = sum(r["status"] == "FEASIBLE" for r in warm)
        rows.append(f"| {variant} | {len(cold)}/24 | {len(warm)}/24 | {cf}/{len(cold)} | {wf}/{len(warm)} |")
    rows += ["", "Full 24-window tracks exist for Original, Initialization, and Relocation. Consolidation has 4 completed cold-start windows; warm-start has not begun. Missing windows are not plotted as zero or inferred.", "", "![Cold-start partial results](cold_start_partial.png)", "", "![Warm-start results](warm_start_partial.png)", "", "Consolidation static GA completed. Its dynamic run remains partial. Plots show available saved artifacts only; they do not represent a completed four-variant dynamic comparison.", ""]
    (out / "README.md").write_text("\n".join(rows))
    print(out)


if __name__ == "__main__":
    main()
