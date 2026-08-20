#!/usr/bin/env python3
"""Validate an SDK release tuple against dependency ranges declared in source."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement


VERSION_PATTERN = re.compile(r'''__version__\s*=\s*['"]([^'"]+)['"]''')
PACKAGES = ("boto3", "botocore", "s3transfer")


def source_argument(value: str) -> tuple[str, Path]:
    package, separator, path = value.partition("=")
    if not separator or package not in PACKAGES or not path:
        raise argparse.ArgumentTypeError("source must be boto3=PATH, botocore=PATH, or s3transfer=PATH")
    return package, Path(path)


def source_version(source: Path, package: str) -> str:
    path = source / package / "__init__.py"
    match = VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: could not find __version__")
    return match.group(1)


def declared_requirements(source: Path) -> list[str]:
    path = source / "setup.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "requires" for target in targets):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{path}: requires must be a static list of strings")
        return value
    raise ValueError(f"{path}: could not find static requires declaration")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=source_argument, action="append", required=True)
    args = parser.parse_args()
    sources = dict(args.source)
    if set(sources) != set(PACKAGES) or len(sources) != len(args.source):
        parser.error("specify each of boto3, botocore, and s3transfer exactly once")

    versions = {package: source_version(sources[package], package) for package in PACKAGES}
    owner_requirements: dict[str, list[dict[str, Any]]] = {}
    for package in PACKAGES:
        relevant = []
        for value in declared_requirements(sources[package]):
            requirement = Requirement(value)
            if requirement.name not in versions:
                continue
            selected = versions[requirement.name]
            if requirement.specifier and selected not in requirement.specifier:
                raise ValueError(
                    f"{package} {versions[package]} requires {requirement}, "
                    f"but the release tuple selects {requirement.name} {selected}"
                )
            relevant.append(
                {
                    "dependency": requirement.name,
                    "selectedVersion": selected,
                    "requirement": str(requirement),
                }
            )
        owner_requirements[package] = relevant

    print("source-declared SDK release compatibility passed")
    print(json.dumps({"versions": versions, "ownerRequirements": owner_requirements}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
