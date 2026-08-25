#!/usr/bin/env python3
"""Discover and recursively verify installed SDK mappings without SDK imports."""

from __future__ import annotations

import argparse
import hashlib
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable

from serialization import read_document, render_yaml


API_VERSION = "runtimeconditions.io/sdk-mapping/v1alpha1"
INDEX_KIND = "RuntimeConditionsSDKMappingIndex"
MAPPING_KIND = "RuntimeConditionsSDKMapping"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


class Registry:
    def __init__(self) -> None:
        self.mappings: dict[tuple[str, str], dict[str, Any]] = {}
        self.paths: dict[tuple[str, str], str] = {}
        self.distributions: dict[str, metadata.Distribution] = {}
        self.indexes: dict[str, str] = {}

    def load_distribution(self, name: str) -> None:
        if name in self.distributions:
            return
        distribution = metadata.distribution(name)
        files = {str(path) for path in distribution.files or []}
        index_candidates = sorted(path for path in files if path.endswith("/runtimeconditions/index.yaml"))
        if len(index_candidates) != 1:
            raise ValueError(
                f"{name} {distribution.version}: expected one runtimeconditions/index.yaml, "
                f"found {len(index_candidates)}"
            )
        index_relative = index_candidates[0]
        index = read_document(Path(distribution.locate_file(index_relative)))
        if index.get("apiVersion") != API_VERSION or index.get("kind") != INDEX_KIND:
            raise ValueError(f"{index_relative}: unsupported SDK mapping index")
        index_metadata = index.get("metadata", {})
        if index_metadata.get("distribution") != name:
            raise ValueError(f"{index_relative}: distribution identity mismatch")
        if index_metadata.get("distributionVersion") != distribution.version:
            raise ValueError(f"{index_relative}: installed version mismatch")

        self.distributions[name] = distribution
        self.indexes[name] = index_relative
        for entry in index.get("mappings", []):
            relative = entry.get("path")
            mapping_name = entry.get("name")
            if not isinstance(relative, str) or relative not in files:
                raise ValueError(f"{name}: indexed mapping is absent: {relative!r}")
            if not isinstance(mapping_name, str):
                raise ValueError(f"{name}: index mapping name must be a string")
            path = Path(distribution.locate_file(relative))
            if sha256(path) != entry.get("sha256"):
                raise ValueError(f"{relative}: mapping digest does not match index")
            mapping = read_document(path)
            if mapping.get("apiVersion") != API_VERSION or mapping.get("kind") != MAPPING_KIND:
                raise ValueError(f"{relative}: unsupported SDK mapping")
            mapping_metadata = mapping.get("metadata", {})
            if mapping_metadata.get("name") != mapping_name:
                raise ValueError(f"{relative}: mapping name does not match index")
            if mapping_metadata.get("distribution") != name:
                raise ValueError(f"{relative}: mapping distribution does not match index")
            if mapping_metadata.get("distributionVersion") != distribution.version:
                raise ValueError(f"{relative}: mapping version does not match installed version")
            key = (name, mapping_name)
            if key in self.mappings:
                raise ValueError(f"duplicate SDK mapping: {key}")
            self.mappings[key] = mapping
            self.paths[key] = relative

    def require(self, distribution: str, mapping: str) -> dict[str, Any]:
        self.load_distribution(distribution)
        key = (distribution, mapping)
        if key not in self.mappings:
            raise ValueError(f"missing SDK mapping: {key}")
        return self.mappings[key]


def member_names(mapping: dict[str, Any], member: str) -> set[str]:
    if member == "operation":
        values = mapping.get("operations", [])
    elif member == "waiter":
        values = mapping.get("python", {}).get("client", {}).get("waiterFactory", {}).get("items", [])
    elif member == "call":
        values = mapping.get("python", {}).get("calls", [])
    else:
        raise ValueError(member)
    return {item["name"] for item in values if isinstance(item, dict) and isinstance(item.get("name"), str)}


def target(reference: dict[str, Any]) -> tuple[str, str]:
    distribution = reference.get("distribution")
    mapping = reference.get("mapping")
    if not isinstance(distribution, str) or not isinstance(mapping, str):
        raise ValueError(f"invalid SDK mapping reference: {reference!r}")
    return distribution, mapping


def validate_references(registry: Registry, key: tuple[str, str]) -> None:
    mapping = registry.mappings[key]
    declared = {
        (item["distribution"], item["mapping"])
        for item in mapping.get("dependencies", [])
        if item.get("kind") == "sdkMapping"
    }
    for dependency in declared:
        registry.require(*dependency)
    used: set[tuple[str, str]] = set()
    for value in walk(mapping):
        for field, member in (("operationRef", "operation"), ("waiterRef", "waiter"), ("callRef", "call")):
            if field not in value:
                continue
            reference = value[field]
            reference_target = target(reference)
            target_mapping = registry.require(*reference_target)
            if reference.get(member) not in member_names(target_mapping, member):
                raise ValueError(f"{key}: unknown {member} reference: {reference}")
            if reference_target != key:
                used.add(reference_target)
    if used - declared:
        raise ValueError(f"{key}: undeclared SDK mapping dependencies: {sorted(used - declared)}")


def dependency_order(registry: Registry, root: tuple[str, str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    visiting: set[tuple[str, str]] = set()
    visited: set[tuple[str, str]] = set()

    def visit(current: tuple[str, str]) -> None:
        if current in visiting:
            raise ValueError(f"SDK mapping dependency cycle at {current}")
        if current in visited:
            return
        mapping = registry.require(*current)
        visiting.add(current)
        for dependency in mapping.get("dependencies", []):
            if dependency.get("kind") == "sdkMapping":
                visit((dependency["distribution"], dependency["mapping"]))
        visiting.remove(current)
        visited.add(current)
        validate_references(registry, current)
        result.append(current)

    visit(root)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-distribution", default="boto3")
    parser.add_argument("--root-mapping", default="boto3.aws.s3")
    args = parser.parse_args()

    registry = Registry()
    order = dependency_order(registry, (args.root_distribution, args.root_mapping))
    output = {
        "root": {"distribution": args.root_distribution, "mapping": args.root_mapping},
        "dependencyOrder": [
            {
                "distribution": distribution,
                "version": registry.distributions[distribution].version,
                "mapping": mapping,
                "path": registry.paths[(distribution, mapping)],
            }
            for distribution, mapping in order
        ],
        "sdkModulesImported": {
            distribution: distribution in sys.modules
            for distribution in sorted(registry.distributions)
        },
    }
    print(render_yaml(output), end="")


if __name__ == "__main__":
    main()
