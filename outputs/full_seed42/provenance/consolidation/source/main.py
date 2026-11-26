"""Validate input or run seed-42 experiments after mandatory acceptance tests."""

import argparse
import json
import io
import sys
import unittest
from pathlib import Path

from src.config import load_config
from src.data_loader import load_workload
from src.reporting import save_validation
from src.experiment import run_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--validate-data", action="store_true", help="Validate and save processed workload only")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        gate = None
        if not args.validate_data:
            destination = Path(config["output"]["directory"]) / f"seed_{config['project']['master_seed']}"
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite existing results: {destination}")
            report = io.StringIO()
            suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / "tests"))
            tests = unittest.TextTestRunner(stream=report, verbosity=2).run(suite)
            print(report.getvalue(), file=sys.stderr, flush=True)
            if not tests.wasSuccessful():
                raise ValueError("Acceptance gate failed; full optimization not started")
            gate = {"status": "PASSED", "tests_run": tests.testsRun, "report": report.getvalue()}
        matrix, ids, manifest, actions = load_workload(config)
        if args.validate_data:
            destination = Path(config["output"]["directory"]) / "validation"
            summary = save_validation(config, matrix, ids, manifest, actions, destination)
            print(json.dumps({"output": str(destination), **summary}, indent=2))
        else:
            def progress(method, result):
                print(json.dumps({"method": method, "window": result.get("window"),
                                  **result["metrics"], "runtime_seconds": result["runtime_seconds"]}), flush=True)
            run_experiment(config, matrix, ids, manifest, actions, destination, gate, progress)
            print(json.dumps({"output": str(destination), "execution_status": "COMPLETED"}), flush=True)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
