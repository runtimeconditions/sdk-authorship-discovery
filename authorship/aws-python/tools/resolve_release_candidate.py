#!/usr/bin/env python3
"""Resolve the newest upstream-compatible AWS SDK for Python observation tuple."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version
from serialization import read_document, write_yaml


PACKAGES = ("boto3", "botocore", "s3transfer")
TAG_PATTERN = re.compile(r"refs/tags/(.+)$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def execute(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or f"{' '.join(command)} failed")
    return completed.stdout


def stable_tags(repository: str) -> dict[Version, str]:
    tags: dict[Version, str] = {}
    for line in execute(["git", "ls-remote", "--tags", "--refs", repository]).splitlines():
        match = TAG_PATTERN.search(line)
        if not match:
            continue
        tag = match.group(1)
        candidate = tag[1:] if tag.startswith("v") else tag
        try:
            version = Version(candidate)
        except InvalidVersion:
            continue
        if version.is_prerelease or version.is_devrelease:
            continue
        existing = tags.get(version)
        if existing is None or (existing.startswith("v") and not tag.startswith("v")):
            tags[version] = tag
    if not tags:
        raise ValueError(f"no stable version tags found in {repository}")
    return tags


def ensure_mirror(cache: Path, package: str, repository: str) -> Path:
    mirror = cache / f"{package}.git"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    if not mirror.exists():
        execute(["git", "init", "--quiet", "--bare", str(mirror)])
        execute(["git", "--git-dir", str(mirror), "remote", "add", "origin", repository])
    return mirror


def source_file(cache: Path, package: str, repository: str, tag: str, path: str) -> str:
    mirror = ensure_mirror(cache, package, repository)
    tag_ref = f"refs/tags/{tag}"
    execute(["git", "--git-dir", str(mirror), "fetch", "--quiet", "--force", "--depth=1", "origin", f"{tag_ref}:{tag_ref}"])
    return execute(["git", "--git-dir", str(mirror), "show", f"{tag_ref}:{path}"])


def declared_requirements(setup_source: str, source_name: str) -> list[Requirement]:
    tree = ast.parse(setup_source, filename=source_name)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "requires" for target in targets):
            continue
        values = ast.literal_eval(node.value)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"{source_name}: requires must be a static list of strings")
        return [Requirement(value) for value in values]
    raise ValueError(f"{source_name}: could not find static requires declaration")


def select_latest(tags: dict[Version, str], requirement: Requirement, preferred: Optional[Version] = None) -> tuple[Version, str]:
    compatible = [(version, tag) for version, tag in tags.items() if version in requirement.specifier]
    if not compatible:
        raise ValueError(f"no upstream tag satisfies {requirement}")
    if preferred is not None and preferred in tags and preferred in requirement.specifier:
        return preferred, tags[preferred]
    return max(compatible, key=lambda item: item[0])


def observation_key(release: dict[str, str], extension: dict[str, str]) -> str:
    return "|".join([release[package] for package in PACKAGES] + [extension["id"], extension["semanticSha256"]])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--extensions-root", type=Path, required=True)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    experiment = read_document(args.experiment)
    state = read_document(args.state)
    packages = experiment["packages"]
    tag_sets = {package: stable_tags(packages[package]["repository"]) for package in PACKAGES}
    floor = Version(state["rootReleaseFloor"])
    observed_root_versions = {
        Version(item["release"]["boto3"])
        for item in state.get("observations", [])
        if "release" in item and "boto3" in item["release"]
    }
    unseen_root_versions = sorted(version for version in tag_sets["boto3"] if version > floor and version not in observed_root_versions)
    boto3_version = unseen_root_versions[0] if unseen_root_versions else max(tag_sets["boto3"])
    boto3_tag = tag_sets["boto3"][boto3_version]
    setup_source = source_file(args.source_cache, "boto3", packages["boto3"]["repository"], boto3_tag, "setup.py")
    requirements = {requirement.name: requirement for requirement in declared_requirements(setup_source, f"boto3 {boto3_version} setup.py")}
    missing = sorted({"botocore", "s3transfer"} - set(requirements))
    if missing:
        raise ValueError(f"boto3 {boto3_version} does not declare expected dependencies: {', '.join(missing)}")
    botocore_version, botocore_tag = select_latest(tag_sets["botocore"], requirements["botocore"], preferred=boto3_version)
    s3transfer_version, s3transfer_tag = select_latest(tag_sets["s3transfer"], requirements["s3transfer"])

    service_mapping = read_document(args.extensions_root / experiment["extensionPath"] / "model/generated/s3-service-mapping.yaml")
    extension = service_mapping["extension"]
    release = {
        "id": f"ongoing-boto3-{boto3_version}-botocore-{botocore_version}-s3transfer-{s3transfer_version}",
        "boto3": str(boto3_version),
        "botocore": str(botocore_version),
        "s3transfer": str(s3transfer_version),
        "role": "ongoing-compatible-root-graph",
    }
    key = observation_key(release, extension)
    observed_keys = {item["key"] for item in state.get("observations", [])}
    result = {
        "schemaVersion": 1,
        "experiment": experiment["id"],
        "resolvedAt": utc_now(),
        "hasCandidate": key not in observed_keys,
        "selectionReason": "next-unobserved-boto3-release" if unseen_root_versions else "latest-compatible-graph-or-extension-change",
        "unobservedRootReleaseCount": len(unseen_root_versions),
        "key": key,
        "release": release,
        "tags": {
            "boto3": boto3_tag,
            "botocore": botocore_tag,
            "s3transfer": s3transfer_tag,
        },
        "declaredByRoot": {
            "botocore": str(requirements["botocore"]),
            "s3transfer": str(requirements["s3transfer"]),
        },
        "extension": {
            "id": extension["id"],
            "version": extension["version"],
            "semanticSha256": extension["semanticSha256"],
            "serviceMappingSemanticSha256": service_mapping["metadata"]["semanticSha256"],
        },
        "upstream": {
            package: {"latestStable": str(max(tags)), "stableTagCount": len(tags)}
            for package, tags in tag_sets.items()
        },
    }
    write_yaml(args.output, result)
    print(f"candidate: {result['hasCandidate']}")
    print(f"release: {release['id']}")
    print(f"extension: {extension['id']}")


if __name__ == "__main__":
    main()
