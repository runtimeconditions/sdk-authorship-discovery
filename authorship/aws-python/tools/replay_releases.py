#!/usr/bin/env python3
"""Replay configured historical SDK release tuples and aggregate evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# AWS Python historical maintenance replay",
        "",
        f"**Overall classification: `{summary['classification']}`**",
        "",
        "| Release | boto3 | botocore | s3transfer | Classification | Review reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for run in summary["runs"]:
        release = run["release"]
        reasons = ", ".join(run["manualReview"]["reasonCodes"]) or "none"
        lines.append(f"| {release['id']} | {release['boto3']} | {release['botocore']} | {release['s3transfer']} | {run['classification']} | {reasons} |")
    lines.extend([
        "",
        "An `automatic` result means the accepted semantic inputs required no edit and every requested gate passed. A `review-required` result is an intentional interruption for potential semantic or package-integration drift. An `invalid` result means the experiment could not classify the release safely.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--extensions-root", type=Path, required=True)
    parser.add_argument("--release", action="append", default=[])
    parser.add_argument("--source-cache", type=Path, default=Path(".work/maintenance-source-cache"))
    parser.add_argument("--work-root", type=Path, default=Path(".work/maintenance"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()

    experiment = read_json(args.experiment)
    configured = {item["id"]: item for item in experiment.get("releases", [])}
    selected = args.release or list(configured)
    unknown = sorted(set(selected) - set(configured))
    if unknown:
        parser.error(f"unknown release ids: {', '.join(unknown)}")
    if args.output.exists():
        parser.error(f"output directory already exists: {args.output}")
    args.output.mkdir(parents=True)

    runner = Path(__file__).with_name("run_release_maintenance.py")
    runs: list[dict[str, Any]] = []
    runner_exit_codes: dict[str, int] = {}
    for release_id in selected:
        command = [
            sys.executable,
            str(runner),
            "--experiment",
            str(args.experiment),
            "--release",
            release_id,
            "--extensions-root",
            str(args.extensions_root),
            "--source-cache",
            str(args.source_cache),
            "--work-root",
            str(args.work_root),
            "--output",
            str(args.output / release_id),
        ]
        if args.static_only:
            command.append("--static-only")
        completed = subprocess.run(command, check=False)
        runner_exit_codes[release_id] = completed.returncode
        result_path = args.output / release_id / "run.json"
        if not result_path.exists():
            runs.append(
                {
                    "release": configured[release_id],
                    "classification": "invalid",
                    "manualReview": {"reasonCodes": []},
                    "failure": {
                        "stage": "replay-runner",
                        "reason": "missing-run-result",
                        "diagnostics": f"single-release runner exited {completed.returncode} without run.json",
                    },
                }
            )
        else:
            runs.append(read_json(result_path))

    classifications = {run["classification"] for run in runs}
    if "invalid" in classifications:
        classification = "invalid"
        exit_code = 1
    elif "review-required" in classifications:
        classification = "review-required"
        exit_code = 2
    else:
        classification = "automatic"
        exit_code = 0
    summary = {
        "schemaVersion": 1,
        "experiment": experiment["id"],
        "completedAt": utc_now(),
        "classification": classification,
        "runnerExitCodes": runner_exit_codes,
        "runs": runs,
    }
    write_json(args.output / "summary.json", summary)
    (args.output / "summary.md").write_text(render_summary(summary), encoding="utf-8")
    print(f"overall classification: {classification}")
    print(f"summary: {args.output / 'summary.md'}")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
