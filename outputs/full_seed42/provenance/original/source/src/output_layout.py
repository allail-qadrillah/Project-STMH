"""One relative-path policy for writers and offline output organization."""

from pathlib import Path


CATEGORIES = {
    "workload": ("workload_timeseries",),
    "utilization": ("utilization_distribution", "pm_utilization_heatmap_static_baseline",
                    "pm_utilization_heatmap_static_ga", "pm_utilization_heatmap_dynamic_cold_start",
                    "pm_utilization_heatmap_dynamic_warm_start"),
    "convergence": ("ga_convergence_static", "ga_convergence_dynamic"),
    "comparison": ("static_comparison", "dynamic_comparison", "runtime_comparison", "runtime_per_window"),
    "workload_timeseries": ("static_ga", "static_baseline", "static_comparison",
                            "dynamic_cold_start", "dynamic_warm_start", "dynamic_comparison"),
    "performance_comparison": ("feasibility_comparison", "active_pm_comparison", "migration_comparison",
                               "overload_comparison", "experiment_summary_dashboard"),
}


def relative_path(value):
    path = Path(value)
    if not isinstance(value, str) or not value.strip() or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Output path must be nonempty, relative, and contained in output root: {value}")
    return path


def output_path(root, config, section, *parts):
    folder = config["output"].get("folders", {}).get(section, section)
    return Path(root) / relative_path(folder) / Path(*parts)


def figure_path(root, config, category, name, extension="png"):
    if category not in CATEGORIES or name not in CATEGORIES[category]:
        raise ValueError(f"Unclassified visualization: {category}/{name}")
    filename = config["output"].get("figure_names", {}).get(f"{category}/{name}", name)
    filename = relative_path(filename)
    if len(filename.parts) != 1 or filename.suffix:
        raise ValueError("Figure names must be plain filename stems")
    return output_path(root, config, "visualizations", category, f"{filename}.{extension}")


def legacy_category(name):
    for category in ("workload", "utilization", "convergence", "comparison"):
        if name in CATEGORIES[category]:
            return category
    raise ValueError(f"Unclassified legacy figure: {name}")


def validate_layout(config):
    folders = [relative_path(config["output"].get("folders", {}).get(k, k))
               for k in ("data", "experiments", "visualizations", "summaries")]
    if any(a == b or a in b.parents or b in a.parents
           for i, a in enumerate(folders) for b in folders[i + 1:]):
        raise ValueError("Output folders must be distinct and non-overlapping")
    paths = [figure_path(".", config, category, name)
             for category, names in CATEGORIES.items() for name in names]
    if len(set(paths)) != len(paths):
        raise ValueError("Visualization filenames conflict")
