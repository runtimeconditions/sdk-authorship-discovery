#!/usr/bin/env python3
"""Discover and verify an installed Kubernetes SDK mapping without importing Kubernetes."""

from __future__ import annotations

import argparse
import hashlib
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

from serialization import read_document


API_VERSION = "runtimeconditions.io/sdk-mapping/v1alpha1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: Any, expected: Any, description: str) -> None:
    if value != expected:
        raise ValueError(f"{description}: got {value!r}, expected {expected!r}")


def discover(distribution_name: str, mapping_name: str, extension_path: Path) -> dict[str, Any]:
    imported_before = "kubernetes" in sys.modules
    distribution = metadata.distribution(distribution_name)
    files = {str(path) for path in distribution.files or []}
    candidates = sorted(path for path in files if path.endswith("/runtimeconditions/index.yaml"))
    if len(candidates) != 1:
        raise ValueError(f"{distribution_name} {distribution.version}: expected one Runtime Conditions index, found {len(candidates)}")
    index_relative = candidates[0]
    index = read_document(Path(distribution.locate_file(index_relative)))
    require(index.get("apiVersion"), API_VERSION, "index apiVersion")
    require(index.get("kind"), "RuntimeConditionsSDKMappingIndex", "index kind")
    require(index.get("metadata", {}).get("distribution"), distribution_name, "index distribution")
    require(index.get("metadata", {}).get("distributionVersion"), distribution.version, "index version")
    entries = [item for item in index.get("mappings", []) if item.get("name") == mapping_name]
    if len(entries) != 1:
        raise ValueError(f"expected one installed mapping {mapping_name!r}, found {len(entries)}")
    entry = entries[0]
    relative = entry.get("path")
    if relative not in files:
        raise ValueError(f"indexed mapping is not installed: {relative!r}")
    mapping_path = Path(distribution.locate_file(relative))
    require(sha256(mapping_path), entry.get("sha256"), "mapping digest")
    mapping = read_document(mapping_path)
    require(mapping.get("apiVersion"), API_VERSION, "mapping apiVersion")
    require(mapping.get("kind"), "RuntimeConditionsSDKMapping", "mapping kind")
    require(mapping.get("metadata", {}).get("name"), mapping_name, "mapping name")
    require(mapping.get("metadata", {}).get("distribution"), distribution_name, "mapping distribution")
    require(mapping.get("metadata", {}).get("distributionVersion"), distribution.version, "mapping version")
    extension = read_document(extension_path)
    coordinates = mapping.get("extension", {})
    require(coordinates.get("id"), extension.get("metadata", {}).get("id"), "extension id")
    require(coordinates.get("version"), extension.get("metadata", {}).get("version"), "extension version")
    require(coordinates.get("semanticSha256"), extension.get("metadata", {}).get("semanticSha256"), "extension semantic digest")
    return {
        "distribution": {"name": distribution_name, "version": distribution.version},
        "index": index_relative,
        "mapping": {"name": mapping_name, "path": relative, "sha256": entry["sha256"]},
        "extension": coordinates,
        "sdkModulesImported": {"before": imported_before, "after": "kubernetes" in sys.modules},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", default="kubernetes")
    parser.add_argument("--mapping", default="kubernetes.api")
    parser.add_argument("--extension", type=Path, required=True)
    args = parser.parse_args()
    print(yaml.safe_dump(discover(args.distribution, args.mapping, args.extension), sort_keys=False, allow_unicode=True, width=4096), end="")


if __name__ == "__main__":
    main()
