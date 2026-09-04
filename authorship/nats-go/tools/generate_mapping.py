#!/usr/bin/env python3
"""Generate and validate the NATS Go SDK mapping from reviewed annotations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from serialization import read_document, write_yaml


def semantic_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def method_id(prefix: str, method: str) -> str:
    words: list[str] = []
    start = 0
    for index in range(1, len(method)):
        if method[index].isupper() and (method[index - 1].islower() or (index + 1 < len(method) and method[index + 1].islower())):
            words.append(method[start:index].lower())
            start = index
    words.append(method[start:].lower())
    return f"{prefix}-{'-'.join(words)}"


def expanded_calls(go: dict[str, Any]) -> list[dict[str, Any]]:
    calls = copy.deepcopy(go.get("calls", []))
    for group in go.get("callGroups", []):
        prefix = group["idPrefix"]
        methods = group["methods"]
        common = {key: copy.deepcopy(value) for key, value in group.items() if key not in {"idPrefix", "methods"}}
        symbol = common.pop("symbol")
        if "receiver" not in symbol or "function" in symbol or "method" in symbol:
            raise ValueError(f"call group {prefix!r} must identify one receiver and no function or method")
        for method in methods:
            if not isinstance(method, str) or not method:
                raise ValueError(f"call group {prefix!r} contains an invalid method")
            call = copy.deepcopy(common)
            call["id"] = method_id(prefix, method)
            call["symbol"] = {**symbol, "method": method}
            calls.append(call)
    return calls


def validate_argument_source(call_id: str, label: str, argument: Any) -> None:
    if not isinstance(argument, dict):
        raise ValueError(f"{call_id}: {label}.argument must be an object")
    parameter = argument.get("parameter")
    position = argument.get("position")
    if (parameter is None) == (position is None):
        raise ValueError(f"{call_id}: {label}.argument requires exactly one of parameter or position")
    if parameter is not None and (not isinstance(parameter, str) or not parameter):
        raise ValueError(f"{call_id}: {label}.argument.parameter must be a non-empty string")
    if position is not None and (not isinstance(position, int) or isinstance(position, bool) or position < 0):
        raise ValueError(f"{call_id}: {label}.argument.position must be a non-negative integer")
    if "field" in argument and (not isinstance(argument["field"], str) or not argument["field"]):
        raise ValueError(f"{call_id}: {label}.argument.field must be a non-empty string")
    unexpected = set(argument) - {"parameter", "position", "field"}
    if unexpected:
        raise ValueError(f"{call_id}: {label}.argument has unsupported fields {sorted(unexpected)}")


def validate_value_source(call_id: str, label: str, source: Any) -> None:
    if not isinstance(source, dict):
        raise ValueError(f"{call_id}: {label} must be an object")
    if ("argument" in source) == ("state" in source):
        raise ValueError(f"{call_id}: {label} requires exactly one of argument or state")
    if "argument" in source:
        validate_argument_source(call_id, label, source["argument"])
    elif not isinstance(source["state"], str) or not source["state"]:
        raise ValueError(f"{call_id}: {label}.state must be a non-empty string")
    if "optional" in source and not isinstance(source["optional"], bool):
        raise ValueError(f"{call_id}: {label}.optional must be a boolean")
    unexpected = set(source) - {"argument", "state", "optional"}
    if unexpected:
        raise ValueError(f"{call_id}: {label} has unsupported fields {sorted(unexpected)}")


def validate_call_structure(call: dict[str, Any]) -> tuple[str, str, str, str]:
    call_id = call["id"]
    symbol = call.get("symbol")
    if not isinstance(symbol, dict) or not isinstance(symbol.get("package"), str) or not symbol["package"]:
        raise ValueError(f"{call_id}: symbol.package is required")
    function = symbol.get("function", "")
    receiver = symbol.get("receiver", "")
    method = symbol.get("method", "")
    if bool(function) == bool(method) or (method and not receiver) or (function and receiver):
        raise ValueError(f"{call_id}: symbol must identify exactly one function or receiver method")
    for name, source in call.get("operationBindings", {}).items():
        validate_value_source(call_id, f"operationBindings.{name}", source)
    argument_state = call.get("argumentState")
    if argument_state is not None:
        if not isinstance(argument_state, dict) or not isinstance(argument_state.get("stateType"), str) or not argument_state["stateType"]:
            raise ValueError(f"{call_id}: argumentState.stateType is required")
        validate_argument_source(call_id, "argumentState", argument_state.get("argument"))
    produces = call.get("produces")
    if produces is not None:
        if not isinstance(produces, dict) or not isinstance(produces.get("stateType"), str) or not produces["stateType"]:
            raise ValueError(f"{call_id}: produces.stateType is required")
        if produces.get("dependencyIdentity", "") not in {"", "new", "inherit"}:
            raise ValueError(f"{call_id}: unsupported produces.dependencyIdentity {produces.get('dependencyIdentity')!r}")
        for name, source in produces.get("bindings", {}).items():
            validate_value_source(call_id, f"produces.bindings.{name}", source)
    return symbol["package"], function, receiver, method


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    annotations = read_document(args.annotations)
    extension = read_document(args.extension)
    configured = annotations["extension"]
    actual = extension["metadata"]
    for field in ("id", "version", "semanticSha256"):
        if configured.get(field) != actual.get(field):
            raise ValueError(f"extension {field} mismatch: annotation {configured.get(field)!r}, release {actual.get(field)!r}")
    schema = extension["spec"]["schemas"][0]["schema"]
    validator = Draft202012Validator(schema)
    calls = expanded_calls(annotations["go"])
    seen: set[str] = set()
    seen_symbols: dict[tuple[str, str, str, str], str] = {}
    for call in calls:
        call_id = call.get("id")
        if not isinstance(call_id, str) or not call_id or call_id in seen:
            raise ValueError(f"invalid or duplicate call id {call_id!r}")
        seen.add(call_id)
        symbol_key = validate_call_structure(call)
        if symbol_key in seen_symbols:
            raise ValueError(f"{call_id}: symbol duplicates call {seen_symbols[symbol_key]!r}")
        seen_symbols[symbol_key] = call_id
        template = call.get("conditionTemplate")
        if template is None:
            if "produces" not in call:
                raise ValueError(f"{call_id}: a call must emit a condition, produce state, or both")
            continue
        operation = dict(template["operation"])
        for field in call.get("operationBindings", {}):
            operation.setdefault(field, ["runtimeconditions-validation-placeholder"] if field == "subjects" else "runtimeconditions-validation-placeholder")
        candidate = {"kind": template["kind"], "interface": {"type": template["interfaceType"], "operations": [operation]}}
        errors = list(validator.iter_errors(candidate))
        if errors:
            raise ValueError(f"{call_id}: invalid condition template: {errors[0].message}")
    metadata = annotations["metadata"]
    go_body = {"calls": calls}
    mapping = {
        "apiVersion": "runtimeconditions.io/sdk-mapping/v1alpha1",
        "kind": "RuntimeConditionsSDKMapping",
        "metadata": {
            "name": metadata["name"],
            "module": metadata["module"],
            "moduleVersion": metadata["moduleVersion"],
            "language": "go",
            "service": metadata["service"],
            "repository": metadata["repository"],
            "revision": metadata["revision"],
            "callCount": len(calls),
            "semanticSha256": semantic_sha256(go_body),
        },
        "dependencies": [{"kind": "extension", **configured}],
        "extension": configured,
        "go": go_body,
    }
    write_yaml(args.output, mapping)
    print(f"mapping: {metadata['name']}")
    print(f"calls: {len(calls)}")
    print(f"semantic sha256: {mapping['metadata']['semanticSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
