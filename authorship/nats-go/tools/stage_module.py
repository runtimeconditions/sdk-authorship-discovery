#!/usr/bin/env python3
"""Stage generated Runtime Conditions metadata into a local NATS Go module source tree."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path

from serialization import read_document, write_yaml


MODULE_DESTINATION = Path("runtimeconditions/mappings/nats-service.yaml")
INDEX_DESTINATION = Path("runtimeconditions/index.yaml")


def module_path(source: Path) -> str:
    match = re.search(r"(?m)^module\s+(\S+)\s*$", (source / "go.mod").read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{source / 'go.mod'}: module directive not found")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    mapping_path = args.mapping.resolve()
    mapping = read_document(mapping_path)
    metadata = mapping["metadata"]
    if module_path(source) != metadata["module"]:
        raise ValueError("mapping module does not match staged Go module")
    target = source / MODULE_DESTINATION
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mapping_path, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    index = {
        "apiVersion": "runtimeconditions.io/sdk-mapping/v1alpha1",
        "kind": "RuntimeConditionsSDKMappingIndex",
        "metadata": {"module": metadata["module"], "moduleVersion": metadata["moduleVersion"], "language": "go"},
        "mappings": [{"name": metadata["name"], "service": metadata["service"], "path": MODULE_DESTINATION.as_posix(), "sha256": digest}],
    }
    write_yaml(source / INDEX_DESTINATION, index)
    print(f"module: {metadata['module']} {metadata['moduleVersion']}")
    print(f"mapping sha256: {digest}")
    print(f"staged index: {INDEX_DESTINATION.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
