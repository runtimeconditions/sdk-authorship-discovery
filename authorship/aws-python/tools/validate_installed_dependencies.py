#!/usr/bin/env python3
"""Validate the installed dependency closure rooted at selected distributions."""

from __future__ import annotations

import argparse
from importlib import metadata
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from serialization import render_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", action="append", required=True)
    args = parser.parse_args()

    resolved: dict[str, dict[str, Any]] = {}
    visiting: set[str] = set()

    def visit(requested_name: str) -> None:
        name = canonicalize_name(requested_name)
        if name in resolved or name in visiting:
            return
        visiting.add(name)
        try:
            distribution = metadata.distribution(requested_name)
        except metadata.PackageNotFoundError as error:
            raise ValueError(f"required distribution is not installed: {requested_name}") from error

        requirements = []
        for value in distribution.requires or []:
            requirement = Requirement(value)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            try:
                dependency = metadata.distribution(requirement.name)
            except metadata.PackageNotFoundError as error:
                raise ValueError(f"{distribution.metadata['Name']} {distribution.version} requires missing {requirement}") from error
            if requirement.specifier and dependency.version not in requirement.specifier:
                raise ValueError(
                    f"{distribution.metadata['Name']} {distribution.version} requires {requirement}, "
                    f"but {dependency.metadata['Name']} {dependency.version} is installed"
                )
            requirements.append(
                {
                    "name": dependency.metadata["Name"],
                    "version": dependency.version,
                    "requirement": str(requirement),
                }
            )
            visit(requirement.name)

        visiting.remove(name)
        resolved[name] = {
            "name": distribution.metadata["Name"],
            "version": distribution.version,
            "requirements": sorted(requirements, key=lambda item: canonicalize_name(item["name"])),
        }

    for distribution_name in args.distribution:
        visit(distribution_name)

    print("selected installed dependency graph passed")
    print(render_yaml({"roots": args.distribution, "distributions": resolved}), end="")


if __name__ == "__main__":
    main()
