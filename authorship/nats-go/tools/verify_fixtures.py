#!/usr/bin/env python3
"""Run the NATS fixtures through a real Go profiler and compare their profiles."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from serialization import read_document


FIXTURES = ("complete-service", "core-messaging", "jetstream-consumer", "jetstream-publisher", "key-value", "object-store")


def run(command: list[str], *, cwd: Path, environment: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def operations(condition: dict[str, Any]) -> list[dict[str, Any]]:
    return condition["interface"]["operations"]


def validate_complete_fixture(profile: dict[str, Any], extension_model: dict[str, Any]) -> None:
    conditions = profile.get("conditions", [])
    if len(conditions) != 2:
        raise ValueError(f"complete-service: expected two independently identified NATS conditions, found {len(conditions)}")
    primary, secondary = conditions
    expected_forms = {(resource, action) for resource, form in extension_model["operationForms"].items() for action in form["actions"]}
    actual_forms = {(operation["resource"], operation["action"]) for operation in operations(primary)}
    missing = sorted(expected_forms - actual_forms)
    if missing:
        raise ValueError(f"complete-service: primary dependency does not exercise extension operations {missing}")
    expected_secondary = [
        {"resource": "connection", "action": "connect"},
        {"resource": "subject", "action": "publish", "subject": "audit.created"},
    ]
    if operations(secondary) != expected_secondary:
        raise ValueError("complete-service: calls on the second connection were not kept in a separate dependency condition")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiler", type=Path, required=True)
    parser.add_argument("--sdk-source", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--fixtures-root", type=Path, required=True)
    parser.add_argument("--extensions-root", type=Path, required=True)
    parser.add_argument("--expected-root", type=Path, required=True)
    args = parser.parse_args()
    profiler = args.profiler.resolve()
    sdk_source = args.sdk_source.resolve()
    mapping = args.mapping.resolve()
    fixtures_root = args.fixtures_root.resolve()
    extensions_root = args.extensions_root.resolve()
    expected_root = args.expected_root.resolve()
    for required in (profiler, sdk_source / "go.mod", mapping, extensions_root, expected_root):
        if not required.exists():
            raise ValueError(f"required path does not exist: {required}")

    tools_root = Path(__file__).resolve().parent
    base_environment = os.environ.copy()
    base_environment.setdefault("GOPROXY", "off")
    run([sys.executable, str(tools_root / "stage_module.py"), "--source-root", str(sdk_source), "--mapping", str(mapping)], cwd=tools_root, environment=base_environment)

    with tempfile.TemporaryDirectory(prefix="runtimeconditions-nats-fixtures-") as temporary:
        temporary_root = Path(temporary)
        workspace = temporary_root / "go.work"
        workspace_environment = base_environment | {"GOWORK": str(workspace), "GOCACHE": str(temporary_root / "go-cache")}
        fixture_paths = [fixtures_root / fixture for fixture in FIXTURES]
        run(["go", "work", "init", *(str(path) for path in fixture_paths)], cwd=temporary_root, environment=base_environment | {"GOWORK": "off"})
        run(["go", "work", "edit", "-replace", f"github.com/nats-io/nats.go={sdk_source}"], cwd=temporary_root, environment=workspace_environment)
        for fixture, fixture_path in zip(FIXTURES, fixture_paths, strict=True):
            run(["go", "test", "."], cwd=fixture_path, environment=workspace_environment)
            actual_path = temporary_root / f"{fixture}.yaml"
            run(
                [
                    str(profiler),
                    "-dir",
                    str(fixture_path),
                    "-name",
                    f"nats-{fixture}",
                    "-workload-uri",
                    f"https://github.com/runtimeconditions/sdk-authorship-discovery/tree/main/nats/go/{fixture}",
                    "-workload-version",
                    "0.1.0",
                    "-extensions-root",
                    str(extensions_root),
                    "-require-go-packages",
                    "-out",
                    str(actual_path),
                ],
                cwd=fixture_path,
                environment=workspace_environment,
            )
            actual = read_document(actual_path)
            expected = read_document(expected_root / f"{fixture}.yaml")
            if actual != expected:
                raise ValueError(f"{fixture}: real-profiler output differs from the reviewed profile")
            if fixture == "complete-service":
                validate_complete_fixture(actual, read_document(extensions_root / "nats-service/model/runtimeconditions.yaml"))
            print(f"{fixture}: compiled, profile valid, reviewed output matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
