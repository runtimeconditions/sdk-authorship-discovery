#!/usr/bin/env python3
"""Record one completed ongoing SDK maintenance observation as durable repository evidence."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from serialization import read_document, write_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()

    state = read_document(args.state)
    candidate = read_document(args.candidate)
    run = read_document(args.run)
    if run["release"] != candidate["release"]:
        raise ValueError("maintenance run release does not match resolved candidate")
    if run["classification"] == "invalid":
        raise ValueError("invalid automation outcomes cannot advance the observation state")

    destination = args.evidence_root / candidate["release"]["id"]
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.run, destination / "run.yaml")
    shutil.copy2(args.report, destination / "report.md")
    write_yaml(destination / "candidate.yaml", candidate)

    repository_root = args.state.resolve().parents[2]
    try:
        evidence_path = str(destination.resolve().relative_to(repository_root))
    except ValueError:
        evidence_path = str(destination.resolve())

    observations = state.setdefault("observations", [])
    if any(item["key"] == candidate["key"] for item in observations):
        raise ValueError(f"observation already recorded: {candidate['key']}")
    observations.append(
        {
            "key": candidate["key"],
            "release": candidate["release"],
            "extension": candidate["extension"],
            "classification": run["classification"],
            "completedAt": run["completedAt"],
            "evidence": evidence_path,
        }
    )
    state["latestUpstream"] = candidate["upstream"]
    state["latestObservation"] = observations[-1]
    write_yaml(args.state, state)
    print(f"recorded: {candidate['release']['id']}")
    print(f"classification: {run['classification']}")


if __name__ == "__main__":
    main()
