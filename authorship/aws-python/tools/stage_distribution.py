#!/usr/bin/env python3
"""Stage generated SDK mappings into a Python distribution source tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


API_VERSION = "runtimeconditions.io/v1alpha1"
INDEX_KIND = "RuntimeConditionsSDKMappingIndexCandidate"
MAPPING_KIND = "RuntimeConditionsSDKMappingCandidate"
VERSION_PATTERN = re.compile(r'''__version__\s*=\s*['"]([^'"]+)['"]''')


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_version(source: Path, relative_version_file: Path) -> str:
    version_file = source / relative_version_file
    match = VERSION_PATTERN.search(version_file.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{version_file}: could not find __version__")
    return match.group(1)


def parse_mapping_argument(value: str) -> tuple[Path, Path]:
    source, separator, destination = value.partition("=")
    if not separator or not source or not destination:
        raise argparse.ArgumentTypeError("mapping must be SOURCE=DESTINATION")
    target = Path(destination)
    if target.is_absolute() or ".." in target.parts:
        raise argparse.ArgumentTypeError("mapping destination must be a safe relative path")
    return Path(source), target


def require(value: Any, expected: Any, description: str) -> None:
    if value != expected:
        raise ValueError(f"{description}: got {value!r}, expected {expected!r}")


def validate_mapping(mapping: dict[str, Any], distribution: str, version: str) -> dict[str, str]:
    require(mapping.get("apiVersion"), API_VERSION, "mapping apiVersion")
    require(mapping.get("kind"), MAPPING_KIND, "mapping kind")
    metadata = mapping.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("mapping metadata must be an object")
    require(metadata.get("distribution"), distribution, "mapping distribution")
    require(metadata.get("distributionVersion"), version, "mapping distribution version")
    require(metadata.get("language"), "python", "mapping language")
    for field in ("name", "service"):
        if not isinstance(metadata.get(field), str) or not metadata[field]:
            raise ValueError(f"mapping metadata.{field} must be a non-empty string")
    return {"name": metadata["name"], "service": metadata["service"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--version-file", type=Path, required=True)
    parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--mapping", type=parse_mapping_argument, action="append", required=True)
    args = parser.parse_args()

    source = args.source_root.resolve()
    version = source_version(source, args.version_file)
    index_path = args.index_path
    if index_path.is_absolute() or ".." in index_path.parts:
        raise ValueError("index path must be a safe relative path")

    entries = []
    identities: set[str] = set()
    for mapping_source, mapping_destination in args.mapping:
        mapping_source = mapping_source.resolve()
        mapping = read_json(mapping_source)
        identity = validate_mapping(mapping, args.distribution, version)
        if identity["name"] in identities:
            raise ValueError(f"duplicate mapping name: {identity['name']}")
        identities.add(identity["name"])

        target = source / mapping_destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mapping_source, target)
        entries.append(
            {
                **identity,
                "path": mapping_destination.as_posix(),
                "sha256": sha256(target),
            }
        )

    index = {
        "apiVersion": API_VERSION,
        "kind": INDEX_KIND,
        "metadata": {
            "distribution": args.distribution,
            "distributionVersion": version,
            "language": "python",
        },
        "mappings": sorted(entries, key=lambda item: item["name"]),
    }
    write_json(source / index_path, index)

    print(f"distribution: {args.distribution} {version}")
    print(f"mappings: {len(entries)}")
    for entry in index["mappings"]:
        print(f"  {entry['name']} ({entry['service']}): {entry['sha256']}")
    print(f"staged index: {index_path.as_posix()}")


if __name__ == "__main__":
    main()
