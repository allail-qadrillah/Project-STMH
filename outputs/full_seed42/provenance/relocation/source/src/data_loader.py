"""One UTF-8 file per VM, one numeric CPU sample per line, no header.

File basenames are VM identifiers. Files sort lexicographically; line index
aligns samples. Blank lines exclude that VM; invalid numeric values stop loading.
No value-based scale guessing: a percentage trace can legitimately stay below 1.
"""

from pathlib import Path
import hashlib

import numpy as np

from .data_validation import validate_samples


def load_workload(config):
    data = config["dataset"]
    root = Path(data["path"])
    if not root.is_dir():
        raise ValueError(f"Dataset directory does not exist: {root}")
    files = sorted(p for p in root.glob(data["file_pattern"] or "*") if p.is_file())
    if not files:
        raise ValueError(f"No VM files selected in {root}")
    if len({p.name for p in files}) != len(files):
        raise ValueError("Duplicate VM identifiers in selected files")
    columns, ids, manifest, actions = [], [], [], []
    for path in files:
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        entry = {"vm_id": path.name, "path": str(path.resolve()),
                 "sha256": hashlib.sha256(raw).hexdigest(), "samples": len(lines)}
        manifest.append(entry)
        # Check all present values, including files later excluded for length.
        try:
            present = [float(line) for line in lines if line.strip()]
        except ValueError as exc:
            raise ValueError(f"{path.name}: invalid numeric sample") from exc
        if present:
            validate_samples(present, data["input_scale"], path.name)
        reasons = []
        if len(lines) != data["expected_samples_per_vm"]:
            reasons.append(f"expected {data['expected_samples_per_vm']} samples; observed {len(lines)}")
        if any(not line.strip() for line in lines):
            reasons.append("missing sample")
        if reasons:
            entry["status"] = "EXCLUDED"
            entry["reason"] = "; ".join(reasons)
            actions.append({"vm_id": path.name, "action": "exclude_vm", "reason": entry["reason"]})
            continue
        entry["status"] = "INCLUDED"
        columns.append(validate_samples(present, data["input_scale"], path.name))
        ids.append(path.name)
    if not columns:
        raise ValueError("No valid VM traces remain")
    matrix = np.column_stack(columns)
    if data["input_scale"] == "percentage":
        matrix = matrix / 100.0
    return matrix, ids, manifest, actions
