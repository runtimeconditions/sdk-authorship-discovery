#!/usr/bin/env python3
"""Stage a generated Runtime Conditions mapping into a boto3 source tree."""

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
INDEX_PATH = Path("boto3/runtimeconditions/index.json")
SERVICE_DIRECTORY = Path("boto3/runtimeconditions/services")
VERSION_PATTERN = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boto3_version(source: Path) -> str:
    init = source / "boto3/__init__.py"
    match = VERSION_PATTERN.search(init.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{init}: could not find boto3 version")
    return match.group(1)


def require(value: Any, expected: Any, description: str) -> None:
    if value != expected:
        raise ValueError(f"{description}: got {value!r}, expected {expected!r}")


def validate_mapping(mapping: dict[str, Any], version: str) -> tuple[str, str, int, int, int]:
    require(mapping.get("apiVersion"), API_VERSION, "mapping apiVersion")
    require(mapping.get("kind"), MAPPING_KIND, "mapping kind")

    metadata = mapping.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("mapping metadata must be an object")
    require(metadata.get("sdk"), "boto3", "mapping SDK")
    require(metadata.get("language"), "python", "mapping language")
    require(metadata.get("boto3Version"), version, "mapping boto3 version")
    service = metadata.get("service")
    if not isinstance(service, str) or not service:
        raise ValueError("mapping service must be a non-empty string")

    extension = mapping.get("extension")
    if not isinstance(extension, dict) or not isinstance(extension.get("id"), str):
        raise ValueError("mapping extension.id must be a string")

    python = mapping.get("python")
    if not isinstance(python, dict):
        raise ValueError("mapping python section must be an object")
    require(python.get("package"), "boto3", "mapping Python package")

    factories = python.get("clientFactories")
    operations = python.get("clientOperations")
    resources = python.get("resourceActions")
    if not isinstance(factories, list) or not factories:
        raise ValueError("mapping must contain at least one client factory")
    if not isinstance(operations, list) or not operations:
        raise ValueError("mapping must contain client operations")
    if not isinstance(resources, list):
        raise ValueError("mapping resourceActions must be an array")

    methods = [item.get("method") for item in operations if isinstance(item, dict)]
    if len(methods) != len(operations) or any(not isinstance(method, str) or not method for method in methods):
        raise ValueError("every client operation must have a method")
    if len(set(methods)) != len(methods):
        raise ValueError("client operation methods must be unique")

    return service, extension["id"], len(factories), len(operations), len(resources)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boto3-source", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args()

    source = args.boto3_source.resolve()
    mapping_path = args.mapping.resolve()
    version = boto3_version(source)
    mapping = read_json(mapping_path)
    service, extension_id, factory_count, operation_count, resource_count = validate_mapping(mapping, version)

    target = source / SERVICE_DIRECTORY / f"{service}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mapping_path, target)
    digest = sha256(target)

    index = {
        "apiVersion": API_VERSION,
        "kind": INDEX_KIND,
        "metadata": {
            "distribution": "boto3",
            "distributionVersion": version,
            "language": "python",
        },
        "mappings": [
            {
                "service": service,
                "path": target.relative_to(source).as_posix(),
                "sha256": digest,
                "extension": {"id": extension_id},
            }
        ],
    }
    write_json(source / INDEX_PATH, index)

    condition_count = sum(
        len(operation.get("conditions", []))
        for operation in mapping["python"]["clientOperations"]
        if isinstance(operation, dict)
    )
    print(f"distribution: boto3 {version}")
    print(f"service: {service}")
    print(f"extension: {extension_id}")
    print(f"client factories: {factory_count}")
    print(f"client operations: {operation_count}")
    print(f"condition templates: {condition_count}")
    print(f"resource actions: {resource_count}")
    print(f"mapping sha256: {digest}")
    print(f"staged index: {INDEX_PATH.as_posix()}")
    print(f"staged mapping: {target.relative_to(source).as_posix()}")


if __name__ == "__main__":
    main()
