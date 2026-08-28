#!/usr/bin/env python3
"""Stage the generated mapping and index into a Kubernetes Python source tree."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

from serialization import read_document, write_yaml


API_VERSION = "runtimeconditions.io/sdk-mapping/v1alpha1"
MAPPING_KIND = "RuntimeConditionsSDKMapping"
INDEX_KIND = "RuntimeConditionsSDKMappingIndex"
VERSION_PATTERN = re.compile(r'''CLIENT_VERSION\s*=\s*['"]([^'"]+)['"]''')
MAPPING_DESTINATION = Path("kubernetes/runtimeconditions/mappings/kubernetes-api.yaml")
INDEX_DESTINATION = Path("kubernetes/runtimeconditions/index.yaml")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: Any, expected: Any, description: str) -> None:
    if value != expected:
        raise ValueError(f"{description}: got {value!r}, expected {expected!r}")


def source_version(source: Path) -> str:
    setup = source / "setup.py"
    match = VERSION_PATTERN.search(setup.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{setup}: could not find CLIENT_VERSION")
    return match.group(1)


def stage(source: Path, mapping_path: Path) -> dict[str, Any]:
    version = source_version(source)
    mapping = read_document(mapping_path)
    require(mapping.get("apiVersion"), API_VERSION, "mapping apiVersion")
    require(mapping.get("kind"), MAPPING_KIND, "mapping kind")
    metadata = mapping.get("metadata", {})
    require(metadata.get("distribution"), "kubernetes", "mapping distribution")
    require(metadata.get("distributionVersion"), version, "mapping distribution version")
    require(metadata.get("language"), "python", "mapping language")
    target = source / MAPPING_DESTINATION
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mapping_path, target)
    index = {
        "apiVersion": API_VERSION,
        "kind": INDEX_KIND,
        "metadata": {"distribution": "kubernetes", "distributionVersion": version, "language": "python"},
        "mappings": [
            {
                "name": metadata["name"],
                "service": metadata["service"],
                "path": MAPPING_DESTINATION.as_posix(),
                "sha256": sha256(target),
            }
        ],
    }
    write_yaml(source / INDEX_DESTINATION, index)
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args()
    index = stage(args.source_root.resolve(), args.mapping.resolve())
    print(f"distribution: kubernetes {index['metadata']['distributionVersion']}")
    print(f"mapping: {index['mappings'][0]['name']}")
    print(f"mapping sha256: {index['mappings'][0]['sha256']}")
    print(f"staged index: {INDEX_DESTINATION.as_posix()}")


if __name__ == "__main__":
    main()
