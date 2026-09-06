#!/usr/bin/env python3
"""Run NATS Python fixtures through the real profiler and compare reviewed profiles."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from serialization import read_document


FIXTURES = ("core-messaging", "jetstream-publisher", "jetstream-consumer", "key-value", "object-store", "complete-service")


def run(command: list[str], *, cwd: Path, environment: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def operation_forms(condition: dict[str, Any]) -> set[tuple[str, str]]:
    return {(operation["resource"], operation["action"]) for operation in condition["interface"]["operations"]}


def validate_complete_fixture(profile: dict[str, Any], service_mapping: dict[str, Any]) -> None:
    conditions = profile.get("conditions", [])
    if len(conditions) != 2:
        raise ValueError(f"complete-service: expected two independently identified NATS conditions, found {len(conditions)}")
    expected = {(condition["operation"]["resource"], condition["operation"]["action"]) for item in service_mapping["operations"] for condition in item["conditions"]}
    expected.remove(("consumer", "update"))
    missing = expected - operation_forms(conditions[0])
    if missing:
        raise ValueError(f"complete-service: primary dependency does not exercise supported operation forms {sorted(missing)}")
    secondary = conditions[1]["interface"]["operations"]
    if secondary != [{"resource": "connection", "action": "connect"}, {"resource": "subject", "action": "publish", "subject": "audit.created"}]:
        raise ValueError("complete-service: calls on the second connection were not kept in a separate Condition")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiler-root", type=Path, required=True)
    parser.add_argument("--sdk-source", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--fixtures-root", type=Path, required=True)
    parser.add_argument("--extensions-root", type=Path, required=True)
    parser.add_argument("--expected-root", type=Path, required=True)
    args = parser.parse_args()
    profiler_root = args.profiler_root.resolve()
    sdk_source = args.sdk_source.resolve()
    mapping = args.mapping.resolve()
    fixtures_root = args.fixtures_root.resolve()
    extensions_root = args.extensions_root.resolve()
    expected_root = args.expected_root.resolve()
    for required in (profiler_root, sdk_source / "pyproject.toml", mapping, extensions_root, expected_root):
        if not required.exists():
            raise ValueError(f"required path does not exist: {required}")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(profiler_root), environment.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    tools_root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="runtimeconditions-nats-python-") as temporary:
        temporary_root = Path(temporary)
        staged_source = temporary_root / "nats-py"
        shutil.copytree(sdk_source, staged_source)
        run([sys.executable, str(tools_root / "stage_distribution.py"), "--source-root", str(staged_source), "--mapping", str(mapping)], cwd=tools_root, environment=environment)
        for fixture in FIXTURES:
            fixture_root = fixtures_root / fixture
            compile((fixture_root / "app.py").read_text(encoding="utf-8"), str(fixture_root / "app.py"), "exec")
            actual_path = temporary_root / f"{fixture}.yaml"
            run(
                [
                    sys.executable,
                    "-c",
                    "from runtimeconditions_profiler.cli import main; raise SystemExit(main())",
                    "generate",
                    "--project",
                    str(fixture_root),
                    "--name",
                    f"nats-python-{fixture}",
                    "--workload-uri",
                    f"https://github.com/runtimeconditions/sdk-authorship-discovery/tree/main/nats/python/{fixture}",
                    "--workload-version",
                    "0.1.0",
                    "--package-path",
                    str(staged_source),
                    "--package-path",
                    str(extensions_root / "nats-service/releases/0.1.0"),
                    "--no-installed-sdk-mappings",
                    "--out",
                    str(actual_path),
                ],
                cwd=fixture_root,
                environment=environment,
            )
            actual = read_document(actual_path)
            expected = read_document(expected_root / f"{fixture}.yaml")
            if actual != expected:
                raise ValueError(f"{fixture}: real-profiler output differs from the reviewed profile")
            if fixture == "complete-service":
                validate_complete_fixture(actual, read_document(extensions_root / "nats-service/model/generated/nats-service-mapping.yaml"))
            print(f"{fixture}: syntax valid, profile valid, reviewed output matched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
