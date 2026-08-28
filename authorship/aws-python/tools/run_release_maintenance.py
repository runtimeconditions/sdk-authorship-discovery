#!/usr/bin/env python3
"""Run one owner-aligned AWS Python SDK mapping maintenance experiment."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from serialization import read_document, write_yaml


EXIT_INVALID = 1
EXIT_REVIEW_REQUIRED = 2
REVIEW_CLASSIFICATIONS = {"extension-review-required", "sdk-review-required"}
VERSION_PATTERN = re.compile(r'''__version__\s*=\s*['"]([^'"]+)['"]''')
MAPPING_NAMES = {
    "boto3": "boto3.aws.s3",
    "botocore": "botocore.aws.s3",
    "s3transfer": "s3transfer.aws.s3",
}


class StageFailure(RuntimeError):
    def __init__(self, stage: str, classification: str, reason: str, diagnostics: str) -> None:
        super().__init__(f"{stage}: {reason}")
        self.stage = stage
        self.classification = classification
        self.reason = reason
        self.diagnostics = diagnostics


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_sha256(path: Path) -> str:
    value = copy.deepcopy(read_document(path))
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("distributionVersion", None)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def display_command(command: list[str]) -> str:
    return " ".join(command)


def execute(
    result: dict[str, Any],
    stage: str,
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    failure_classification: str = "invalid",
    failure_reason: str = "command-failed",
) -> str:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    duration = round(time.monotonic() - started, 3)
    record = {
        "name": stage,
        "status": "passed" if completed.returncode == 0 else "failed",
        "durationSeconds": duration,
        "command": display_command(command),
        "cwd": str(cwd) if cwd else None,
        "exitCode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    result["stages"].append(record)
    if completed.returncode != 0:
        diagnostics = "\n".join(
            value for value in (completed.stdout.strip(), completed.stderr.strip()) if value
        ) or f"exit code {completed.returncode}"
        raise StageFailure(stage, failure_classification, failure_reason, diagnostics)
    return completed.stdout


def git_revision(path: Path) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if commit.returncode != 0:
        return {"commit": None, "dirty": None}
    status = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "commit": commit.stdout.strip(),
        "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def source_version(source: Path, version_file: str) -> str:
    path = source / version_file
    match = VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: could not find __version__")
    return match.group(1)


def source_override(value: str) -> tuple[str, Path]:
    package, separator, path = value.partition("=")
    if not separator or package not in MAPPING_NAMES or not path:
        raise argparse.ArgumentTypeError("source must be boto3=PATH, botocore=PATH, or s3transfer=PATH")
    return package, Path(path).resolve()


def prepare_source(
    result: dict[str, Any],
    package: str,
    package_config: dict[str, Any],
    version: str,
    source_cache: Path,
    checkout_root: Path,
    supplied_source: Path | None,
) -> tuple[Path, str]:
    destination = checkout_root / f"{package}-{version}"
    if destination.exists():
        raise ValueError(f"source checkout already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    if supplied_source:
        if not supplied_source.is_dir():
            raise ValueError(f"supplied {package} source does not exist: {supplied_source}")
        commit = execute(
            result,
            f"resolve-{package}-source-commit",
            ["git", "-C", str(supplied_source), "rev-parse", "HEAD"],
        ).strip()
        execute(
            result,
            f"materialize-{package}-source",
            ["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(supplied_source), str(destination)],
        )
        execute(
            result,
            f"checkout-{package}-source",
            ["git", "-C", str(destination), "checkout", "--quiet", "--detach", commit],
        )
    else:
        mirror = source_cache / f"{package}.git"
        mirror.parent.mkdir(parents=True, exist_ok=True)
        if not mirror.exists():
            execute(
                result,
                f"initialize-{package}-source-cache",
                ["git", "init", "--quiet", "--bare", str(mirror)],
            )
            execute(
                result,
                f"configure-{package}-source-cache",
                ["git", "--git-dir", str(mirror), "remote", "add", "origin", package_config["repository"]],
            )
        tag_ref = f"refs/tags/{version}"
        execute(
            result,
            f"fetch-{package}-{version}",
            ["git", "--git-dir", str(mirror), "fetch", "--quiet", "--force", "--depth=1", "origin", f"{tag_ref}:{tag_ref}"],
        )
        commit = execute(
            result,
            f"resolve-{package}-{version}-commit",
            ["git", "--git-dir", str(mirror), "rev-list", "-n", "1", tag_ref],
        ).strip()
        execute(
            result,
            f"materialize-{package}-source",
            ["git", "--git-dir", str(mirror), "worktree", "add", "--quiet", "--detach", str(destination), commit],
        )

    actual_version = source_version(destination, package_config["versionFile"])
    if actual_version != version:
        raise StageFailure(
            f"verify-{package}-version",
            "invalid",
            "source-version-mismatch",
            f"tag {version!r} contains package version {actual_version!r}",
        )
    result["sources"][package] = {
        "repository": package_config["repository"],
        "tag": version,
        "version": actual_version,
        "commit": commit,
    }
    return destination, actual_version


def mapping_inventory(path: Path) -> dict[str, int]:
    mapping = read_document(path)
    python = mapping.get("python", {})
    resources = python.get("resources", [])
    calls = python.get("calls", [])
    return {
        "operations": len(mapping.get("operations", [])),
        "resources": len(resources),
        "resourceMembers": sum(
            len(item.get(field, []))
            for item in resources
            for field in ("actions", "waiters", "relations", "collections", "wrappers")
        ),
        "calls": len(calls),
        "entrypoints": sum(len(item.get("entrypoints", [])) for item in calls),
    }


def artifact_record(path: Path, baseline: Path | None) -> dict[str, Any]:
    raw_digest = sha256(path)
    semantic_digest = semantic_sha256(path)
    record: dict[str, Any] = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": raw_digest,
        "semanticSha256": semantic_digest,
        "inventory": mapping_inventory(path),
    }
    if baseline and baseline.exists():
        record["baseline"] = {
            "path": str(baseline),
            "sha256": sha256(baseline),
            "semanticSha256": semantic_sha256(baseline),
            "rawChanged": raw_digest != sha256(baseline),
            "semanticChanged": semantic_digest != semantic_sha256(baseline),
        }
    return record


def validate_generated_profile(
    result: dict[str, Any],
    fixture: str,
    generated: Path,
    expected: Path,
) -> None:
    stage = f"compare-profiler-profile-{fixture}"
    started = time.monotonic()
    if not expected.is_file():
        raise StageFailure(
            stage,
            "invalid",
            "expected-profiler-profile-missing",
            f"expected profile does not exist: {expected}",
        )
    try:
        generated_document = read_document(generated)
        expected_document = read_document(expected)
    except Exception as error:
        raise StageFailure(
            stage,
            "invalid",
            "profiler-profile-invalid",
            f"{type(error).__name__}: {error}",
        ) from error

    matches = generated_document == expected_document
    duration = round(time.monotonic() - started, 3)
    result["stages"].append(
        {
            "name": stage,
            "status": "passed" if matches else "failed",
            "durationSeconds": duration,
            "command": f"compare YAML documents {generated} {expected}",
            "cwd": None,
            "exitCode": 0 if matches else 1,
            "stdout": "",
            "stderr": "",
        }
    )
    result["artifacts"]["profiles"].append(
        {
            "fixture": fixture,
            "path": str(generated),
            "bytes": generated.stat().st_size,
            "sha256": sha256(generated),
            "expectedPath": str(expected),
            "expectedSha256": sha256(expected),
            "semanticMatch": matches,
        }
    )
    if not matches:
        difference = "".join(
            difflib.unified_diff(
                expected.read_text(encoding="utf-8").splitlines(keepends=True),
                generated.read_text(encoding="utf-8").splitlines(keepends=True),
                fromfile=str(expected),
                tofile=str(generated),
            )
        )
        raise StageFailure(
            stage,
            "invalid",
            "profiler-profile-drift",
            difference or "generated and expected YAML documents differ semantically",
        )


def render_report(result: dict[str, Any]) -> str:
    release = result["release"]
    lines = [
        f"# AWS Python mapping maintenance report: {release['id']}",
        "",
        "## Outcome",
        "",
        f"**Classification: `{result['classification']}`**",
        "",
    ]
    if result["classification"] == "automatic":
        lines.append("The accepted semantic inputs regenerated and passed every requested gate without a handwritten mapping change.")
    elif result["classification"] == "extension-review-required":
        lines.append("The SDK release cannot be aligned safely to the selected extension release. Extension stakeholders must review the focused API-semantic difference before SDK mapping acceptance continues.")
    elif result["classification"] == "sdk-review-required":
        lines.append("The extension remains sufficient, but an SDK-owned surface or package integration changed. An SDK mapping maintainer must review the focused reason below.")
    else:
        lines.append("The experiment could not classify the release safely. This is an automation or unsupported-input failure, not an accepted mapping update.")

    lines.extend([
        "",
        "## Release tuple",
        "",
        "| Package | Version | Upstream commit |",
        "| --- | --- | --- |",
    ])
    for package in ("boto3", "botocore", "s3transfer"):
        source = result.get("sources", {}).get(package, {})
        lines.append(f"| {package} | {release[package]} | `{source.get('commit', 'not resolved')}` |")

    lines.extend([
        "",
        "## Reproducibility",
        "",
        "| Input | Commit | Dirty during run |",
        "| --- | --- | --- |",
    ])
    for name in ("sdk", "extensions", "profiler"):
        revision = result.get("revisions", {}).get(name, {})
        lines.append(f"| {name} | `{revision.get('commit') or 'unavailable'}` | {revision.get('dirty')} |")

    artifacts = result.get("artifacts", {}).get("mappings", {})
    if artifacts:
        lines.extend([
            "",
            "## Generated mapping summary",
            "",
            "| Owner | Bytes | Semantic change from accepted baseline | SHA-256 |",
            "| --- | ---: | --- | --- |",
        ])
        for package in ("botocore", "s3transfer", "boto3"):
            artifact = artifacts.get(package)
            if not artifact:
                continue
            baseline = artifact.get("baseline", {})
            changed = baseline.get("semanticChanged", "not compared")
            lines.append(f"| {package} | {artifact['bytes']} | {changed} | `{artifact['sha256']}` |")

    profiles = result.get("artifacts", {}).get("profiles", [])
    if profiles:
        lines.extend([
            "",
            "## Profiler acceptance profiles",
            "",
            "| Application | Semantic match | SHA-256 |",
            "| --- | --- | --- |",
        ])
        for profile in profiles:
            lines.append(f"| {profile['fixture']} | {profile['semanticMatch']} | `{profile['sha256']}` |")

    lines.extend([
        "",
        "## Gates",
        "",
        "| Gate | Status | Duration (seconds) |",
        "| --- | --- | ---: |",
    ])
    for stage in result.get("stages", []):
        lines.append(f"| {stage['name']} | {stage['status']} | {stage['durationSeconds']} |")

    review = result["manualReview"]
    lines.extend([
        "",
        "## Human review record",
        "",
        f"- Requested: {review['requested']}",
        f"- Reason codes: {', '.join(review['reasonCodes']) if review['reasonCodes'] else 'none'}",
        f"- Disposition: {review['disposition'] or 'not recorded'}",
        f"- Minutes to understand: {review['minutesToUnderstand'] if review['minutesToUnderstand'] is not None else 'not recorded'}",
        f"- Minutes to edit: {review['minutesToEdit'] if review['minutesToEdit'] is not None else 'not recorded'}",
        f"- Minutes to review: {review['minutesToReview'] if review['minutesToReview'] is not None else 'not recorded'}",
    ])
    failure = result.get("failure")
    if failure:
        diagnostics = failure.get("diagnostics", "")[-4000:]
        lines.extend([
            "",
            "## Focused failure",
            "",
            f"- Stage: `{failure['stage']}`",
            f"- Reason: `{failure['reason']}`",
            "",
            "```text",
            diagnostics,
            "```",
        ])

    lines.extend([
        "",
        "## Interpretation",
        "",
        "This report measures maintenance behavior for the owner-aligned SDK mapping proposal. It does not declare profiler coverage, unresolved application observations, or downstream adapter policy.",
        "",
    ])
    return "\n".join(lines)


def finalize(result: dict[str, Any], output: Path) -> None:
    result["completedAt"] = utc_now()
    output.mkdir(parents=True, exist_ok=True)
    write_yaml(output / "run.yaml", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    sdk_root = Path(__file__).resolve().parents[3]
    experiment_path = args.experiment.resolve()
    experiment = read_document(experiment_path)
    releases = {item["id"]: item for item in experiment.get("releases", [])}
    if args.release_file:
        release_document = read_document(args.release_file.resolve())
        release = release_document.get("release", release_document)
        required_release_fields = {"id", "boto3", "botocore", "s3transfer"}
        missing_release_fields = sorted(required_release_fields - set(release))
        if missing_release_fields:
            raise ValueError(f"release file is missing fields: {', '.join(missing_release_fields)}")
    else:
        if args.release not in releases:
            raise ValueError(f"unknown release id {args.release!r}; choose from {', '.join(sorted(releases))}")
        release = releases[args.release]
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"output directory already exists: {output}")
    extensions_root = args.extensions_root.resolve()
    extension_root = extensions_root / experiment["extensionPath"]
    if not extension_root.is_dir():
        raise ValueError(f"extension source does not exist: {extension_root}")
    source_cache = args.source_cache.resolve()
    profiler_root = args.profiler_root.resolve() if args.profiler_root else None
    profiler_command = Path(sys.executable).with_name("runtimeconditions-python-profiler")
    run_work = args.work_root.resolve() / release["id"]
    checkout_root = run_work / "sources"
    if run_work.exists():
        raise ValueError(f"maintenance work directory already exists: {run_work}")
    run_work.mkdir(parents=True)
    output.mkdir(parents=True)

    supplied_sources = dict(args.source)
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "experiment": experiment["id"],
        "startedAt": utc_now(),
        "completedAt": None,
        "classification": "invalid",
        "release": release,
        "revisions": {
            "sdk": git_revision(sdk_root),
            "extensions": git_revision(extensions_root),
            "profiler": git_revision(profiler_root) if profiler_root else {"commit": None, "dirty": None},
        },
        "sources": {},
        "stages": [],
        "artifacts": {"mappings": {}, "wheels": [], "profiles": []},
        "manualReview": {
            "requested": False,
            "reasonCodes": [],
            "disposition": None,
            "minutesToUnderstand": None,
            "minutesToEdit": None,
            "minutesToReview": None,
        },
        "failure": None,
    }

    try:
        if not args.static_only:
            if profiler_root is None or not (profiler_root / "profiler.py").is_file():
                raise StageFailure(
                    "verify-profiler-source",
                    "invalid",
                    "profiler-source-missing",
                    "a full maintenance run requires --profiler-root pointing to the Python profiler source repository",
                )
            if not profiler_command.is_file():
                raise StageFailure(
                    "verify-profiler-command",
                    "invalid",
                    "profiler-command-missing",
                    f"a full maintenance run requires the installed profiler command at {profiler_command}",
                )
            missing_prerequisites = [
                module
                for module in ("setuptools", "wheel", "packaging", "jmespath", "dateutil", "urllib3", "six", "yaml", "jsonschema")
                if importlib.util.find_spec(module) is None
            ]
            if missing_prerequisites:
                raise StageFailure(
                    "verify-runner-prerequisites",
                    "invalid",
                    "runner-prerequisite-missing",
                    f"install the build prerequisites in the runner environment: {', '.join(missing_prerequisites)}",
                )
        sources: dict[str, Path] = {}
        versions: dict[str, str] = {}
        for package in ("boto3", "botocore", "s3transfer"):
            sources[package], versions[package] = prepare_source(
                result,
                package,
                experiment["packages"][package],
                release[package],
                source_cache,
                checkout_root,
                supplied_sources.get(package),
            )

        execute(
            result,
            "validate-release-compatibility",
            [
                sys.executable,
                str(sdk_root / "authorship/aws-python/tools/validate_source_dependencies.py"),
                "--source",
                f"boto3={sources['boto3']}",
                "--source",
                f"botocore={sources['botocore']}",
                "--source",
                f"s3transfer={sources['s3transfer']}",
            ],
            failure_reason="incompatible-release-tuple",
        )

        mappings_dir = output / "artifacts" / "mappings"
        mappings_dir.mkdir(parents=True)
        service_mapping = extension_root / "model/generated/s3-service-mapping.yaml"
        mapping_paths = {
            "botocore": mappings_dir / "botocore.aws.s3.yaml",
            "s3transfer": mappings_dir / "s3transfer.aws.s3.yaml",
            "boto3": mappings_dir / "boto3.aws.s3.yaml",
        }
        service_models = sources["botocore"] / "botocore/data/s3/2006-03-01"
        resource_model = sources["boto3"] / "boto3/data/s3/2006-03-01/resources-1.json"
        botocore_annotations = extension_root / "model/botocore-sdk-annotations.yaml"
        boto3_annotations = extension_root / "model/boto3-wrapper-annotations.yaml"
        transfer_annotations = extension_root / "model/s3transfer-semantic-annotations.yaml"

        execute(
            result,
            "validate-extension-alignment",
            [
                sys.executable,
                str(extension_root / "tools/validate_extension_alignment.py"),
                "--service-mapping",
                str(service_mapping),
                "--botocore-service-model",
                str(service_models / "service-2.json"),
                "--botocore-annotations",
                str(botocore_annotations),
            ],
            failure_classification="extension-review-required",
            failure_reason="extension-semantic-alignment-drift",
        )
        execute(
            result,
            "generate-owner-mappings",
            [
                sys.executable,
                str(extension_root / "tools/generate_owner_mappings.py"),
                "--service-mapping",
                str(service_mapping),
                "--botocore-service-model",
                str(service_models / "service-2.json"),
                "--paginator-model",
                str(service_models / "paginators-1.json"),
                "--waiter-model",
                str(service_models / "waiters-2.json"),
                "--resource-model",
                str(resource_model),
                "--botocore-annotations",
                str(botocore_annotations),
                "--boto3-wrappers",
                str(boto3_annotations),
                "--s3transfer-annotations",
                str(transfer_annotations),
                "--botocore-output",
                str(mapping_paths["botocore"]),
                "--boto3-output",
                str(mapping_paths["boto3"]),
                "--s3transfer-output",
                str(mapping_paths["s3transfer"]),
                "--botocore-version",
                versions["botocore"],
                "--boto3-version",
                versions["boto3"],
                "--s3transfer-version",
                versions["s3transfer"],
            ],
            failure_classification="sdk-review-required",
            failure_reason="owner-surface-drift",
        )
        execute(
            result,
            "validate-owner-mapping-graph",
            [
                sys.executable,
                str(extension_root / "tools/validate_owner_mappings.py"),
                "--mapping",
                str(mapping_paths["botocore"]),
                "--mapping",
                str(mapping_paths["s3transfer"]),
                "--mapping",
                str(mapping_paths["boto3"]),
                "--root-distribution",
                "boto3",
                "--root-mapping",
                "boto3.aws.s3",
                "--service-mapping",
                str(service_mapping),
            ],
            failure_reason="generated-reference-contract-failure",
        )
        execute(
            result,
            "validate-sdk-sources",
            [
                sys.executable,
                str(extension_root / "tools/validate_sdk_sources.py"),
                "--boto3-source",
                str(sources["boto3"]),
                "--botocore-source",
                str(sources["botocore"]),
                "--s3transfer-source",
                str(sources["s3transfer"]),
                "--botocore-annotations",
                str(botocore_annotations),
                "--boto3-annotations",
                str(boto3_annotations),
                "--s3transfer-annotations",
                str(transfer_annotations),
                "--botocore-mapping",
                str(mapping_paths["botocore"]),
                "--boto3-mapping",
                str(mapping_paths["boto3"]),
                "--s3transfer-mapping",
                str(mapping_paths["s3transfer"]),
            ],
            failure_classification="sdk-review-required",
            failure_reason="reviewed-sdk-surface-drift",
        )
        execute(
            result,
            "resolve-representative-mapping-paths",
            [
                sys.executable,
                str(sdk_root / "authorship/aws-python/tools/resolve_s3_examples.py"),
                "--boto3",
                str(mapping_paths["boto3"]),
                "--botocore",
                str(mapping_paths["botocore"]),
                "--s3transfer",
                str(mapping_paths["s3transfer"]),
            ],
            failure_reason="representative-resolution-failure",
        )

        for package, path in mapping_paths.items():
            baseline = extension_root / f"mappings/{package}/runtimeconditions.sdk-mapping.yaml"
            result["artifacts"]["mappings"][package] = artifact_record(path, baseline)

        if not args.static_only:
            wheels_dir = output / "artifacts" / "wheels"
            wheels_dir.mkdir(parents=True)
            for package in ("botocore", "s3transfer", "boto3"):
                package_config = experiment["packages"][package]
                execute(
                    result,
                    f"apply-{package}-package-data",
                    ["git", "-C", str(sources[package]), "apply", str(sdk_root / package_config["packageDataPatch"])],
                    failure_classification="sdk-review-required",
                    failure_reason="package-build-integration-drift",
                )
                execute(
                    result,
                    f"stage-{package}-mapping",
                    [
                        sys.executable,
                        str(sdk_root / "authorship/aws-python/tools/stage_distribution.py"),
                        "--source-root",
                        str(sources[package]),
                        "--distribution",
                        package,
                        "--version-file",
                        package_config["versionFile"],
                        "--index-path",
                        package_config["indexPath"],
                        "--mapping",
                        f"{mapping_paths[package]}={package_config['mappingDestination']}",
                    ],
                    failure_reason="mapping-staging-failure",
                )
                execute(
                    result,
                    f"build-{package}-wheel",
                    [sys.executable, "setup.py", "bdist_wheel", "--dist-dir", str(wheels_dir)],
                    cwd=sources[package],
                    failure_classification="sdk-review-required",
                    failure_reason="package-build-integration-drift",
                )

            wheel_paths = sorted(wheels_dir.glob("*.whl"))
            if len(wheel_paths) != 3:
                raise StageFailure(
                    "collect-wheels",
                    "invalid",
                    "unexpected-wheel-inventory",
                    f"expected three wheels, found {[path.name for path in wheel_paths]}",
                )
            result["artifacts"]["wheels"] = [
                {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
                for path in wheel_paths
            ]

            verification = run_work / "verification-site"
            verification.mkdir(parents=True)
            execute(
                result,
                "install-owner-wheels",
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-deps", "--target", str(verification), *[str(path) for path in wheel_paths]],
            )
            verification_env = os.environ.copy()
            verification_env["PYTHONPATH"] = os.pathsep.join(
                [str(verification), verification_env.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep)
            execute(
                result,
                "discover-installed-mapping-graph",
                [
                    sys.executable,
                    str(sdk_root / "authorship/aws-python/tools/discover_mappings.py"),
                    "--root-distribution",
                    "boto3",
                    "--root-mapping",
                    "boto3.aws.s3",
                ],
                env=verification_env,
                failure_reason="installed-mapping-discovery-failure",
            )
            execute(
                result,
                "validate-installed-runtime-surfaces",
                [
                    sys.executable,
                    str(sdk_root / "authorship/aws-python/tools/validate_runtime_surfaces.py"),
                    "--boto3",
                    str(mapping_paths["boto3"]),
                    "--botocore",
                    str(mapping_paths["botocore"]),
                    "--s3transfer",
                    str(mapping_paths["s3transfer"]),
                ],
                env=verification_env,
                failure_classification="sdk-review-required",
                failure_reason="installed-sdk-surface-drift",
            )
            execute(
                result,
                "check-installed-dependencies",
                [
                    sys.executable,
                    str(sdk_root / "authorship/aws-python/tools/validate_installed_dependencies.py"),
                    "--distribution",
                    "boto3",
                    "--distribution",
                    "botocore",
                    "--distribution",
                    "s3transfer",
                ],
                env=verification_env,
                failure_reason="resolved-dependency-graph-failure",
            )
            for project_value in experiment.get("applicationTests", []):
                project = sdk_root / project_value
                test_env = verification_env.copy()
                test_env["PYTHONPATH"] = os.pathsep.join(
                    [str(project / "src"), test_env["PYTHONPATH"]]
                )
                test_env["AWS_EC2_METADATA_DISABLED"] = "true"
                execute(
                    result,
                    f"test-application-{project.name}",
                    [sys.executable, "-m", "unittest", "discover", "-s", str(project / "tests")],
                    env=test_env,
                    failure_classification="sdk-review-required",
                    failure_reason="application-regression",
                )

            profiler_proof = experiment.get("profilerProof", {})
            expected_profiles = sdk_root / profiler_proof["expectedProfiles"]
            generated_profiles = output / "artifacts" / "profiles"
            generated_profiles.mkdir(parents=True)
            extension_version = read_document(mapping_paths["botocore"])["extension"]["version"]
            extension_release = extension_root / "releases" / str(extension_version)
            if not (extension_release / "runtimeconditions.extension.yaml").is_file():
                raise StageFailure(
                    "resolve-profiler-extension",
                    "invalid",
                    "profiler-extension-release-missing",
                    f"generated botocore mapping targets extension {extension_version}, but no release exists at {extension_release}",
                )
            profiler_env = verification_env.copy()
            profiler_env["PYTHONPATH"] = os.pathsep.join(
                [str(profiler_root), str(verification), profiler_env.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep)
            for project_value in experiment.get("applicationTests", []):
                project = sdk_root / project_value
                fixture = project.name
                generated_profile = generated_profiles / f"{fixture}.yaml"
                expected_profile = expected_profiles / f"{fixture}.yaml"
                execute(
                    result,
                    f"generate-profiler-profile-{fixture}",
                    [
                        str(profiler_command),
                        "generate",
                        "--project",
                        str(project),
                        "--package-path",
                        str(extension_release),
                        "--name",
                        f"{profiler_proof['profileNamePrefix']}{fixture}",
                        "--workload-uri",
                        f"{profiler_proof['workloadRepositoryUri'].rstrip('/')}/{project_value}",
                        "--workload-version",
                        str(profiler_proof["workloadVersion"]),
                        "--out",
                        str(generated_profile),
                    ],
                    env=profiler_env,
                    failure_reason="profiler-integration-failure",
                )
                validate_generated_profile(result, fixture, generated_profile, expected_profile)

        result["classification"] = "automatic"
    except StageFailure as error:
        result["classification"] = error.classification
        result["failure"] = {
            "stage": error.stage,
            "reason": error.reason,
            "diagnostics": error.diagnostics,
        }
        if error.classification in REVIEW_CLASSIFICATIONS:
            result["manualReview"]["requested"] = True
            result["manualReview"]["reasonCodes"].append(error.reason)
    except Exception as error:  # Preserve evidence for unexpected automation failures.
        result["classification"] = "invalid"
        result["failure"] = {
            "stage": "maintenance-runner",
            "reason": "unhandled-runner-failure",
            "diagnostics": f"{type(error).__name__}: {error}",
        }
    finally:
        finalize(result, output)

    print(f"classification: {result['classification']}")
    print(f"report: {output / 'report.md'}")
    print(f"machine result: {output / 'run.yaml'}")
    if result["classification"] == "automatic":
        return 0
    if result["classification"] in REVIEW_CLASSIFICATIONS:
        return EXIT_REVIEW_REQUIRED
    return EXIT_INVALID


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    release = parser.add_mutually_exclusive_group(required=True)
    release.add_argument("--release")
    release.add_argument("--release-file", type=Path)
    parser.add_argument("--extensions-root", type=Path, required=True)
    parser.add_argument("--profiler-root", type=Path)
    parser.add_argument("--source", type=source_override, action="append", default=[])
    parser.add_argument("--source-cache", type=Path, default=Path(".work/maintenance-source-cache"))
    parser.add_argument("--work-root", type=Path, default=Path(".work/maintenance"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    if len(dict(args.source)) != len(args.source):
        parser.error("each --source package may be specified only once")
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
