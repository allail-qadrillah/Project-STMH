"""Reorganize saved outputs and render derived figures. Never run GA optimization."""

import argparse
import json

from src.config import load_config
from src.output_organization import organize_outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--check-reference-summary", action="store_true",
                        help="Also verify supplied seed-42 table (12 PMs, migrations 948/18151/7523)")
    args = parser.parse_args()
    try:
        report = organize_outputs(load_config(args.config), args.check_reference_summary)
        print(json.dumps({k: v for k, v in report.items() if not k.endswith("sha256")}, indent=2))
    except (ValueError, OSError, AssertionError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
