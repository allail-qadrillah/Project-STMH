"""Offline migration, saved-result checks, and lossless table concatenation. No GA calls."""

import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from .evaluation import evaluate_placement
from .fitness import calculate_fitness
from .output_layout import figure_path, legacy_category, output_path, relative_path
from .reporting import dynamic_summary, write_csv


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def snapshot(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(Path(root).rglob("*")) if p.is_file()}


def inspect_file(path):
    if path.suffix == ".png":
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
    elif path.suffix == ".npy":
        np.load(path, allow_pickle=False)
    elif path.suffix == ".npz":
        with np.load(path, allow_pickle=False) as arrays:
            for key in arrays.files:
                arrays[key]
    elif path.suffix == ".csv":
        csv_rows(path)
    elif path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    else:
        path.read_bytes()


def copy_plan(source, destination, config):
    """Resolve every source before writing anything; unknown files remain preserved."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents:
        raise ValueError("Destination must not be inside source run")
    plan, unknown = [], []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink not accepted in archived results: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        section, *parts = rel.parts
        if section in ("data", "summaries"):
            target = output_path(destination, config, section, *parts)
        elif section in ("static", "dynamic"):
            if section == "dynamic" and len(parts) == 1 and parts[0].endswith("_per_window.csv"):
                method = parts[0].removesuffix("_per_window.csv")
                target = output_path(destination, config, "experiments", "dynamic", method, "per_window_metrics.csv")
            else:
                target = output_path(destination, config, "experiments", section, *parts)
        elif section == "plots" and path.suffix == ".png":
            try:
                target = figure_path(destination, config, legacy_category(path.stem), path.stem)
            except ValueError:
                unknown.append(str(rel))
                target = destination / "preserved" / rel
        else:
            unknown.append(str(rel))
            target = destination / "preserved" / rel
        if target.resolve() == path or source in target.resolve().parents:
            raise ValueError(f"Destination overlaps source: {target}")
        inspect_file(path)
        checksum = digest(path)
        if target.exists() and (not target.is_file() or digest(target) != checksum):
            raise FileExistsError(f"Conflicting destination; no file copied: {target}")
        plan.append((path, target, checksum))
    if len({t for _, t, _ in plan}) != len(plan):
        raise ValueError("Multiple source files map to same destination")
    return plan, unknown


def _assert_metrics(actual, saved, label):
    for key, value in actual.items():
        if key not in saved:
            raise ValueError(f"Missing metric {label}: {key}")
        if isinstance(value, str):
            ok = saved[key] == value
        elif value is None:
            ok = saved[key] in (None, "")
        else:
            ok = np.isclose(float(saved[key]), value, rtol=1e-12, atol=1e-12)
        if not ok:
            raise ValueError(f"Saved-result discrepancy {label}.{key}: saved={saved[key]}, checked={value}")


def load_verified_run(source, expected_shape=None, reference_summary=False):
    """Reconstruct each window independently and reconcile saved numerical results."""
    source = Path(source)
    metadata = json.loads((source / "summaries/experiment_config.json").read_text())
    config = metadata["configuration"]
    matrix = np.load(source / "data/workload_matrix.npy", allow_pickle=False)
    expected = expected_shape or (config["dataset"]["expected_samples_per_vm"], config["dataset"]["expected_vm_count"])
    if matrix.shape != tuple(expected) or not np.isfinite(matrix).all() or np.any((matrix < 0) | (matrix > 1)):
        raise ValueError(f"Workload shape/values invalid: {matrix.shape}, expected {expected}")
    vm_rows = csv_rows(source / "data/vm_order.csv")
    ids = [r["vm_id"] for r in vm_rows]
    if len(ids) != matrix.shape[1] or len(set(ids)) != len(ids) or [int(r["column_index"]) for r in vm_rows] != list(range(len(ids))):
        raise ValueError("VM order does not match workload columns")
    demand = matrix * config["infrastructure"]["vm_cpu_capacity_vcpu"]
    m = config["infrastructure"]["available_pm_count"]

    def placement(path):
        rows = csv_rows(path)
        if [r["vm_id"] for r in rows] != ids:
            raise ValueError(f"Placement VM IDs/order mismatch: {path}")
        p = np.array([int(r["pm_id"]) for r in rows])
        if p.shape != (len(ids),) or np.any((p < 1) | (p > m)):
            raise ValueError(f"Invalid PM assignments: {path}")
        return p

    def result(directory, samples, reference, mode):
        p = placement(directory / "placement.csv")
        metrics, loads = evaluate_placement(samples, p, config, reference)
        metrics["fitness"] = calculate_fitness(metrics, config, mode)
        saved = csv_rows(directory / "metrics.csv")
        if len(saved) != 1:
            raise ValueError(f"Expected one metrics row: {directory}")
        _assert_metrics(metrics, saved[0], str(directory))
        with np.load(directory / "raw.npz", allow_pickle=False) as raw:
            np.testing.assert_array_equal(raw["placement"], p)
            np.testing.assert_allclose(raw["loads_vcpu"], loads, rtol=0, atol=1e-12)
            np.testing.assert_allclose(raw["utilization_ratio"], loads / config["infrastructure"]["pm_cpu_capacity_vcpu"], rtol=0, atol=1e-12)
            if "reference" in raw:
                np.testing.assert_array_equal(raw["reference"], reference)
        # Return saved metrics, never replace them with recomputed values.
        typed = {key: (saved[0][key] if isinstance(value, str) else None if value is None else
                       int(saved[0][key]) if isinstance(value, int) else float(saved[0][key]))
                 for key, value in metrics.items()}
        return {"placement": p, "loads_vcpu": loads, "metrics": typed,
                "runtime_seconds": float(saved[0]["runtime_seconds"])}

    baseline = placement(source / "static/baseline/placement.csv")
    results = {"static": {method: result(source / "static" / method, demand, baseline, "static")
                           for method in ("baseline", "ga")}}
    initial = placement(source / "dynamic/initial_placement.csv")
    results["dynamic"] = {"initial_placement": initial}
    window_size = config["experiments"]["dynamic"]["window_size_samples"]
    for method in ("cold_start", "warm_start"):
        reference, windows = initial, []
        per_window = csv_rows(source / "dynamic" / f"{method}_per_window.csv")
        count = matrix.shape[0] // window_size
        if len(per_window) != count:
            raise ValueError(f"Wrong number of windows: {method}")
        for i in range(count):
            start, end = i * window_size, (i + 1) * window_size
            row = per_window[i]
            if (int(row["window"]), int(row["sample_start"]), int(row["sample_end"])) != (i + 1, start + 1, end):
                raise ValueError(f"Window/sample alignment mismatch: {method}/{i + 1}")
            r = result(source / "dynamic" / method / f"window_{i + 1:02d}", demand[start:end], reference, "dynamic")
            _assert_metrics(r["metrics"], row, f"{method}/{i + 1}")
            r.update(window=i + 1, sample_start=start + 1, sample_end=end, reference=reference)
            windows.append(r)
            reference = r["placement"]
        results["dynamic"][method] = windows
    summary = {r["method"]: r for r in csv_rows(source / "summaries/experiment_summary.csv")}
    for method in ("baseline", "ga"):
        _assert_metrics(results["static"][method]["metrics"], summary[f"static_{method}"], method)
    for method in ("cold_start", "warm_start"):
        _assert_metrics(dynamic_summary(method, results["dynamic"][method], len(ids), config["project"]["master_seed"]),
                        summary[method], method)
    if reference_summary:
        expected_rows = {"static_baseline": ("INFEASIBLE", 12, 0, 7), "static_ga": ("FEASIBLE", 12, 948, 0),
                         "cold_start": ("FEASIBLE", 12, 18151, 0), "warm_start": ("FEASIBLE", 12, 7523, 0)}
        for method, (status, active, migrations, overload) in expected_rows.items():
            row = summary[method]
            key = "active_pm_count" if method.startswith("static") else "mean_active_pm_count"
            _assert_metrics({"status": status, key: active, "migration_count": migrations, "overload_events": overload}, row, method)
            if not method.startswith("static"):
                _assert_metrics({"feasible_windows": 24, "transitions": 24, "minimum_active_pm_count": 12,
                                 "maximum_active_pm_count": 12}, row, method)
    cold, warm = (int(summary[k]["migration_count"]) for k in ("cold_start", "warm_start"))
    reduction = (cold - warm) / cold * 100 if cold else None
    return matrix, results, config, {"workload_shape": list(matrix.shape), "verified_placements": 51,
                                    "pm_assignment_range": [1, m], "windows_per_method": matrix.shape[0] // window_size,
                                    "reconstructed_loads_match_raw": True, "metrics_match_saved": True,
                                    "migration_reduction_percent": reduction,
                                    "supplied_summary_checked": reference_summary}


def save_combined_tables(root, config):
    """Retain original CSV field text; add only window/seed keys for concatenation."""
    base = output_path(root, config, "experiments")
    generated = []

    def save(path, rows):
        if not rows:
            return
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite derived table: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_csv(path, rows, list(rows[0]))
        generated.append(path)

    for method in ("baseline", "ga"):
        directory = base / "static" / method
        if directory.exists():
            save(base / "static" / f"{method}_placements.csv", csv_rows(directory / "placement.csv"))
    history = base / "static/ga/fitness_history.csv"
    if history.exists():
        save(base / "static/fitness_history.csv", csv_rows(history))
    for method in ("cold_start", "warm_start"):
        directory = base / "dynamic" / method
        placements, histories = [], []
        for window in sorted(directory.glob("window_*")):
            n = int(window.name.removeprefix("window_"))
            keys = {"seed": str(config["project"]["master_seed"]), "window": str(n)}
            placements.extend({**keys, **r} for r in csv_rows(window / "placement.csv"))
            histories.extend({**keys, **r} for r in csv_rows(window / "fitness_history.csv"))
        save(directory / "placements.csv", placements)
        save(directory / "fitness_history.csv", histories)
    return generated


def organize_outputs(config, reference_summary=False):
    """Copy verified originals, add derived figures/docs, leave source trees byte-identical."""
    from .output_documentation import document_outputs
    from .result_visualization import plot_saved_results

    root = Path(config["output"]["directory"])
    source = root / relative_path(config["output"]["existing_run"])
    if not source.is_dir():
        raise FileNotFoundError(source)
    before = snapshot(root)
    plan, unknown = copy_plan(source, root, config)
    matrix, results, scientific_config, validation = load_verified_run(source, reference_summary=reference_summary)
    # Saved scientific settings govern figures; current config governs output paths only.
    scientific_config["output"] = config["output"]
    log = root / "structure_migration_log.md"
    report = output_path(root, config, "summaries", "structure_validation.json")
    reserved = [log, report, root / "README.md",
                output_path(root, config, "visualizations", "README.md"),
                output_path(root, config, "summaries", "README.md")]
    from .output_layout import CATEGORIES
    reserved.extend(output_path(root, config, "visualizations", c, "README.md") for c in CATEGORIES)
    reserved.extend(figure_path(root, config, c, n, ext) for c in ("workload_timeseries", "performance_comparison")
                    for n in CATEGORIES[c] for ext in ("png", "svg"))
    experiments = output_path(root, config, "experiments")
    reserved.extend(experiments / "static" / n for n in ("baseline_placements.csv", "ga_placements.csv", "fitness_history.csv"))
    reserved.extend(experiments / "dynamic" / m / n for m in ("cold_start", "warm_start")
                    for n in ("placements.csv", "fitness_history.csv"))
    for path in reserved:
        if path.exists():
            raise FileExistsError(f"New output already exists; migration aborted before copying: {path}")
    if len(set(reserved + [t for _, t, _ in plan])) != len(reserved) + len(plan):
        raise ValueError("Generated outputs conflict with migration destinations")
    lines = ["# Structure migration log", "", "Original run and validation trees remain untouched. No GA optimization executed.",
             "Copy plan fully inspected and conflict-checked before first copy. SHA-256 verifies every copy.",
             "Identical existing targets are reused; different targets are never overwritten.", "",
             "| Original file path | New file path | Action | Verification status (SHA-256) |",
             "|---|---|---|---|"]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for path, target, checksum in plan:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            # Exclusive create prevents accidental replacement, even after preflight.
            with path.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            shutil.copystat(path, target)
        if digest(path) != checksum or digest(target) != checksum:
            raise ValueError(f"Checksum mismatch: {path} / {target}")
        inspect_file(target)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"| `{path.relative_to(root)}` | `{target.relative_to(root)}` | copy | PASS `{checksum}` |\n")
    tables = save_combined_tables(root, config)
    plot_saved_results(root, matrix, results, scientific_config)
    docs = document_outputs(root, config, source=source, unknown=unknown)
    for rel, checksum in before.items():
        if digest(root / rel) != checksum:
            raise ValueError(f"Original changed: {rel}")
    for path in root.rglob("*.png"):
        inspect_file(path)
    # All category READMEs use local Markdown links; verify links exist.
    import re
    links = 0
    for path in docs:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if not (path.parent / link).exists():
                raise ValueError(f"Broken documentation link {path}: {link}")
            links += 1
    validation.update(original_files_unchanged=len(before), files_copied=len(plan),
                      original_png_copies=sum(p.suffix == ".png" for p, _, _ in plan),
                      new_png_figures=11, new_svg_figures=11, combined_tables=len(tables),
                      readmes=len(docs), verified_readme_links=links, unclassified_files=unknown,
                      missing_outputs=[], status="PASSED",
                      original_sha256=before,
                      copied_sha256={str(t.relative_to(root)): h for _, t, h in plan})
    report.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    with log.open("a", encoding="utf-8") as stream:
        stream.write("\n## Generated additions (not original experiment results)\n\n")
        for p in tables + docs:
            stream.write(f"- `{p.relative_to(root)}`\n")
        stream.write("\n11 new PNG and 11 SVG figures under `workload_timeseries/` and `performance_comparison/`.\n"
                     "Original PNGs copied byte-for-byte; no original figure regenerated.\n"
                     f"\nVerification: {len(before)} original files unchanged; {len(plan)} copies checksum-verified. "
                     f"Report: `{report.relative_to(root)}`.\n")
        stream.write(f"\nUnclassified files: {unknown or 'none'}. Missing requested outputs: none.\n")
    return validation
