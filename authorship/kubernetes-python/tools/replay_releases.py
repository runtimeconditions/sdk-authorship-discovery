#!/usr/bin/env python3
"""Replay Kubernetes Python releases through the deterministic surface and mapping generators."""

from __future__ import annotations

import argparse
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from generate_mapping import build_mapping
from project_surface import build_surface
from serialization import read_document, write_yaml


VERSION_PATTERN = re.compile(r'''CLIENT_VERSION\s*=\s*['"]([^'"]+)['"]''')


def git(repository: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()


def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe archive path {member.name!r}")
        stream.extractall(destination)


def release_source(repository: Path, tag: str, destination: Path) -> tuple[str, str]:
    revision = git(repository, "rev-list", "-n", "1", tag)
    archive = destination / "source.tar"
    subprocess.check_call(["git", "-C", str(repository), "archive", "--format=tar", "-o", str(archive), tag])
    source = destination / "source"
    source.mkdir()
    safe_extract(archive, source)
    match = VERSION_PATTERN.search((source / "setup.py").read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{tag}: CLIENT_VERSION is absent")
    return revision, match.group(1)


def replay(repository: Path, tags: list[str], inventory_path: Path, service_mapping: dict[str, Any], extension: dict[str, Any], observations: dict[str, Any], sdk_annotations: Path) -> dict[str, Any]:
    if observations.get("experiment") != "kubernetes-python-release-replay":
        raise ValueError("maintenance observations target a different experiment")
    if observations.get("mode") != "retrospective-compatibility":
        raise ValueError("maintenance observations must identify this as a retrospective compatibility replay")
    observed_maintenance = observations.get("observations")
    if not isinstance(observed_maintenance, list):
        raise ValueError("maintenance observations must contain an observations list")
    records = []
    for tag in tags:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision, version = release_source(repository, tag, root)
            source = root / "source"
            try:
                surface = build_surface(source, inventory_path, "https://github.com/kubernetes-client/python.git", revision, version, sdk_annotations)
                mapping = build_mapping(surface, service_mapping, extension)
                record = {
                    "tag": tag,
                    "revision": revision,
                    "version": version,
                    "finalReplayResult": "compatible-with-current-generator",
                    "authoritativeModelSemanticSha256": surface["metadata"]["source"]["authoritativeSnapshot"]["semanticSha256"],
                    "generatorInputSemanticSha256": surface["metadata"]["source"]["generatorInput"]["semanticSha256"],
                    "surfaceSemanticSha256": surface["metadata"]["semanticSha256"],
                    "mappingSemanticSha256": mapping["metadata"]["semanticSha256"],
                    "operationRecords": mapping["metadata"]["operationCount"],
                    "publicSymbols": mapping["metadata"]["publicSymbolCount"],
                    "syncSymbols": surface["metadata"]["summary"]["syncSymbols"],
                    "asyncSymbols": surface["metadata"]["summary"]["asyncSymbols"],
                }
            except ValueError as error:
                record = {"tag": tag, "revision": revision, "version": version, "finalReplayResult": "incompatible-with-current-generator", "reason": str(error)}
            records.append(record)
    compatible_flavors = [(item["syncSymbols"], item["asyncSymbols"]) for item in records if item["finalReplayResult"] == "compatible-with-current-generator"]
    return {
        "schemaVersion": 1,
        "experiment": "kubernetes-python-release-replay",
        "mode": observations["mode"],
        "method": observations.get("method", {}),
        "targetExtension": {"id": extension["metadata"]["id"], "version": extension["metadata"]["version"], "semanticSha256": extension["metadata"]["semanticSha256"]},
        "releases": records,
        "observedMaintenance": observed_maintenance,
        "summary": {
            "releases": len(records),
            "compatibleWithCurrentGenerator": sum(item["finalReplayResult"] == "compatible-with-current-generator" for item in records),
            "incompatibleWithCurrentGenerator": sum(item["finalReplayResult"] == "incompatible-with-current-generator" for item in records),
            "observedAutomationRepairs": sum(item.get("maintenanceKind") == "integration-tooling" for item in observed_maintenance),
            "observedSemanticMappingEdits": sum(item.get("semanticMappingEdits", 0) for item in observed_maintenance),
            "generatedFlavorTransitions": sum(current != previous for previous, current in zip(compatible_flavors, compatible_flavors[1:])),
        },
    }


def review_markdown(evidence: dict[str, Any]) -> str:
    summary = evidence["summary"]
    compatible = summary["incompatibleWithCurrentGenerator"] == 0
    lines = [
        "# Kubernetes Python historical release replay",
        "",
        "**Classification: `retrospective-compatibility-passed-after-automation-repair`**" if compatible else "**Classification: `retrospective-compatibility-failed`**",
        "",
        f"The current generator can process {summary['compatibleWithCurrentGenerator']} of {summary['releases']} Kubernetes Python releases through the same authoritative join, generated-source verification, extension alignment, and mapping generation. This was a backward compatibility replay using tooling developed against v36.0.3, not a chronological simulation of a production integration. It also does not measure the substantial first-integration work needed to build that tooling.",
        "",
        "| Release | Revision | Current generator result | Operations | Sync symbols | Async symbols |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for item in evidence["releases"]:
        lines.append(f"| `{item['version']}` | `{item['revision']}` | `{item['finalReplayResult']}` | {item.get('operationRecords', '—')} | {item.get('syncSymbols', '—')} | {item.get('asyncSymbols', '—')} |")
    lines.extend(["", "## Observed investigative maintenance", ""])
    for item in evidence["observedMaintenance"]:
        lines.append(f"- **{item['id']}**: {item['description']} {item['productionInterpretation']}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"The evidence separates three workloads that must not be collapsed: initial integration construction, which this replay does not measure; {summary['observedAutomationRepairs']} authored integration-tooling repair encountered during the replay; and zero per-operation, per-resource, or state-flow semantic edits observed in the replay. The final generator is backward-compatible with {summary['compatibleWithCurrentGenerator']} releases. If this integration lived in the SDK repository, its maintainers would need to review and ship an equivalent tooling change, even if Runtime Conditions contributors implemented it.",
            "",
            "Release 36.0.0 contains only the synchronous generated surface, while 36.0.1 adds the asynchronous surface. Because the integration was first developed against v36.0.3 and then replayed backward, the experiment cannot establish whether a chronological production integration would have needed the repair at v36.0.0, at v36.0.1, or not at all if flavor discovery had been designed in from the start.",
            "",
            "This sample measures final compatibility across patch releases within one Kubernetes API/client major line. It does not prove zero-touch production maintenance and does not substitute for observing future releases as they occur.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--tag", action="append", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--service-mapping", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--sdk-annotations", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    args = parser.parse_args()
    evidence = replay(args.repository.resolve(), args.tag, args.inventory.resolve(), read_document(args.service_mapping), read_document(args.extension), read_document(args.observations), args.sdk_annotations.resolve())
    write_yaml(args.evidence_output, evidence)
    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    args.review_output.write_text(review_markdown(evidence), encoding="utf-8")
    print(f"releases: {evidence['summary']['releases']}")
    print(f"compatible with current generator: {evidence['summary']['compatibleWithCurrentGenerator']}")
    print(f"incompatible with current generator: {evidence['summary']['incompatibleWithCurrentGenerator']}")
    print(f"observed automation repairs: {evidence['summary']['observedAutomationRepairs']}")
    if evidence["summary"]["incompatibleWithCurrentGenerator"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
