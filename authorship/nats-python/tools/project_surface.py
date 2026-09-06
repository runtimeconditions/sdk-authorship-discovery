#!/usr/bin/env python3
"""Classify the pinned nats-py public surface against generated mappings and reviewed policy."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from generate_mapping import SourceIndex
from serialization import read_document, write_yaml


def classified_methods(scope: dict[str, Any], category: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for group in scope.get(category, []):
        reason = group.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError(f"{scope['module']}.{scope['class']}: {category} group has no reason")
        for method in group.get("methods", []):
            if method in result:
                raise ValueError(f"{scope['module']}.{scope['class']}.{method}: duplicate {category} classification")
            result[method] = reason
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = SourceIndex(args.source_root)
    mapping = read_document(args.mapping)
    policy = read_document(args.policy)
    mapped: dict[tuple[str, str], set[str]] = {}
    for call in mapping.get("python", {}).get("calls", []):
        for symbol in call.get("symbols", []):
            mapped.setdefault((symbol["module"], symbol["class"]), set()).add(symbol["method"])
    scopes = []
    totals = {"public": 0, "mapped": 0, "excluded": 0, "deferred": 0, "unclassified": 0}
    for scope in policy.get("scopes", []):
        module = scope["module"]
        class_name = scope["class"]
        public = source.public_methods(module, class_name)
        mapped_methods = mapped.get((module, class_name), set())
        excluded = classified_methods(scope, "exclusions")
        deferred = classified_methods(scope, "deferred")
        overlaps = (mapped_methods & set(excluded)) | (mapped_methods & set(deferred)) | (set(excluded) & set(deferred))
        if overlaps:
            raise ValueError(f"{module}.{class_name}: methods have conflicting classifications {sorted(overlaps)}")
        classified = mapped_methods | set(excluded) | set(deferred)
        unknown = classified - public
        if unknown:
            raise ValueError(f"{module}.{class_name}: classifications reference absent methods {sorted(unknown)}")
        unclassified = public - classified
        record = {
            "module": module,
            "class": class_name,
            "publicMethods": sorted(public),
            "mapped": sorted(mapped_methods),
            "excluded": [{"method": method, "reason": excluded[method]} for method in sorted(excluded)],
            "deferred": [{"method": method, "reason": deferred[method]} for method in sorted(deferred)],
            "unclassified": sorted(unclassified),
        }
        scopes.append(record)
        totals["public"] += len(public)
        totals["mapped"] += len(mapped_methods)
        totals["excluded"] += len(excluded)
        totals["deferred"] += len(deferred)
        totals["unclassified"] += len(unclassified)
    report = {
        "apiVersion": "runtimeconditions.io/sdk-authorship-evidence/v1alpha1",
        "kind": "RuntimeConditionsSDKSurfaceClassification",
        "metadata": {"distribution": mapping["metadata"]["distribution"], "distributionVersion": mapping["metadata"]["distributionVersion"], "mappingSemanticSha256": mapping["metadata"]["semanticSha256"]},
        "summary": totals,
        "scopes": scopes,
    }
    write_yaml(args.output, report)
    if totals["unclassified"]:
        raise ValueError(f"{totals['unclassified']} public methods remain unclassified")
    print(f"public methods: {totals['public']}")
    print(f"mapped: {totals['mapped']}")
    print(f"excluded: {totals['excluded']}")
    print(f"deferred: {totals['deferred']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
