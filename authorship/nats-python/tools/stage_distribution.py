#!/usr/bin/env python3
"""Stage generated Runtime Conditions metadata into a local nats-py source distribution."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tomllib
from pathlib import Path

from serialization import read_document, write_yaml


MAPPING_DESTINATION = Path("src/nats/runtimeconditions/mappings/nats-service.yaml")
INDEX_DESTINATION = Path("src/nats/runtimeconditions/index.yaml")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    mapping_path = args.mapping.resolve()
    mapping = read_document(mapping_path)
    project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    metadata = mapping["metadata"]
    if project.get("name") != metadata.get("distribution") or project.get("version") != metadata.get("distributionVersion"):
        raise ValueError("mapping coordinates do not match the staged Python distribution")
    target = source / MAPPING_DESTINATION
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mapping_path, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    index = {
        "apiVersion": "runtimeconditions.io/sdk-mapping/v1alpha1",
        "kind": "RuntimeConditionsSDKMappingIndex",
        "metadata": {"distribution": metadata["distribution"], "distributionVersion": metadata["distributionVersion"], "language": "python"},
        "mappings": [{"name": metadata["name"], "service": metadata["service"], "path": "runtimeconditions/mappings/nats-service.yaml", "sha256": digest}],
    }
    write_yaml(source / INDEX_DESTINATION, index)
    print(f"distribution: {metadata['distribution']} {metadata['distributionVersion']}")
    print(f"mapping sha256: {digest}")
    print(f"staged index: {INDEX_DESTINATION.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
