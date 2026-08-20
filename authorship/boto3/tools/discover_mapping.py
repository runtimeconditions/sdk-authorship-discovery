#!/usr/bin/env python3
"""Discover packaged Runtime Conditions metadata without importing boto3."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib import metadata
from pathlib import Path
from typing import Any


API_VERSION = "runtimeconditions.io/v1alpha1"
INDEX_KIND = "RuntimeConditionsSDKMappingIndexCandidate"
INDEX_PATH = "boto3/runtimeconditions/index.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", default="boto3")
    args = parser.parse_args()

    distribution = metadata.distribution(args.distribution)
    installed_files = {str(path) for path in distribution.files or []}
    if INDEX_PATH not in installed_files:
        raise ValueError(f"{args.distribution} {distribution.version} does not contain {INDEX_PATH}")

    index_path = Path(distribution.locate_file(INDEX_PATH))
    index = read_json(index_path)
    if index.get("apiVersion") != API_VERSION or index.get("kind") != INDEX_KIND:
        raise ValueError(f"{index_path}: unsupported Runtime Conditions index")

    index_metadata = index.get("metadata", {})
    if index_metadata.get("distribution") != args.distribution:
        raise ValueError("index distribution does not match installed distribution")
    if index_metadata.get("distributionVersion") != distribution.version:
        raise ValueError("index version does not match installed distribution")

    results = []
    for entry in index.get("mappings", []):
        mapping_relative = entry.get("path")
        if not isinstance(mapping_relative, str) or mapping_relative not in installed_files:
            raise ValueError(f"indexed mapping is absent from installed distribution: {mapping_relative!r}")
        mapping_path = Path(distribution.locate_file(mapping_relative))
        actual_digest = sha256(mapping_path)
        if actual_digest != entry.get("sha256"):
            raise ValueError(f"{mapping_relative}: mapping digest does not match index")
        mapping = read_json(mapping_path)
        results.append(
            {
                "service": entry.get("service"),
                "path": mapping_relative,
                "sha256": actual_digest,
                "extension": entry.get("extension", {}).get("id"),
                "clientOperations": len(mapping.get("python", {}).get("clientOperations", [])),
                "resourceActions": len(mapping.get("python", {}).get("resourceActions", [])),
            }
        )

    output = {
        "distribution": args.distribution,
        "version": distribution.version,
        "index": INDEX_PATH,
        "sdkImported": args.distribution in sys.modules,
        "mappings": results,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
