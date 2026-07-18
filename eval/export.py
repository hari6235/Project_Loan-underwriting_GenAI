# FILE: eval/export.py
"""Exports eval results to JSON/CSV for CI pipeline integration
(Section 3.5). Pure stdlib -- no pandas dependency needed for a flat
metrics table."""
from __future__ import annotations

import csv
import json
import os


def export_json(report: dict, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def export_csv(report: dict, path: str) -> str:
    """Flattens report["checks"] (metric -> {value, threshold, passed})
    into one row per metric -- the shape a CI dashboard or spreadsheet
    typically wants, rather than the nested JSON."""
    checks = report.get("checks", {})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "threshold", "passed"])
        for metric, data in checks.items():
            writer.writerow([metric, data.get("value"), data.get("threshold"), data.get("passed")])
    return path