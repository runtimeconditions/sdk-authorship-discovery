#!/usr/bin/env python3
"""Resolve directly constructed Kubernetes Python API calls through an installed or local mapping."""

from __future__ import annotations

import argparse
import ast
import copy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from serialization import read_document, write_yaml


def symbol_index(mapping: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for method in mapping.get("python", {}).get("apiMethods", []):
        for symbol in method.get("symbols", []):
            key = (symbol["class"], symbol["method"])
            existing = result.get(key)
            if existing and existing != method:
                raise ValueError(f"ambiguous Python SDK symbol {key}")
            result[key] = method
    return result


def operation_index(mapping: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {item["name"]: item for item in mapping.get("operations", [])}
    if len(result) != len(mapping.get("operations", [])):
        raise ValueError("mapping contains duplicate operation records")
    return result


def direct_constructor_symbol(call: ast.Call) -> tuple[str, str] | None:
    if not isinstance(call.func, ast.Attribute) or not isinstance(call.func.value, ast.Call):
        return None
    constructor = call.func.value.func
    if not isinstance(constructor, ast.Attribute):
        return None
    return constructor.attr, call.func.attr


def call_argument(call: ast.Call, binding: dict[str, Any]) -> ast.AST | None:
    position = binding.get("position")
    if isinstance(position, int) and position < len(call.args):
        return call.args[position]
    keyword = binding.get("keyword")
    for item in call.keywords:
        if item.arg == keyword:
            return item.value
    return None


def string_argument(call: ast.Call, binding: dict[str, Any]) -> str | None:
    value = call_argument(call, binding)
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def resolve_template(call: ast.Call, template: dict[str, Any]) -> dict[str, Any] | None:
    operation = copy.deepcopy(template["operation"])
    if "pathTemplate" in operation:
        path = operation.pop("pathTemplate")
        for variable, binding in template.get("pathVariables", {}).items():
            value = string_argument(call, binding)
            if value is None:
                return None
            path = path.replace("{" + variable + "}", value)
        operation["path"] = path
        return operation
    for field, binding in template.get("operationBindings", {}).items():
        value = string_argument(call, binding)
        if value is None:
            return None
        operation[field] = value
    return operation


def resolve_method(call: ast.Call, method: dict[str, Any], operations: dict[str, dict[str, Any]]) -> tuple[str, str, dict[str, Any]] | None:
    reference = method["operationRef"]
    record = operations.get(reference["operation"])
    if not record:
        raise ValueError(f"unknown operation reference {reference}")
    if "conditions" in record:
        condition = record["conditions"][0]
        operation = copy.deepcopy(condition["operation"])
    else:
        condition = record["conditionTemplate"]
        operation = resolve_template(call, condition)
        if operation is None:
            return None
    conditional = method.get("conditionalOperation")
    if conditional:
        predicate = call_argument(call, conditional["when"]["argument"])
        if isinstance(predicate, ast.Constant) and predicate.value is conditional["when"]["equals"]:
            operation.update(conditional["operationOverride"])
        elif predicate is not None and not isinstance(predicate, ast.Constant):
            return None
    return condition["kind"], condition["interfaceType"], operation


def profile_for_sources(mapping: dict[str, Any], extension: dict[str, Any], sources: list[Path], name: str, workload_uri: str) -> dict[str, Any]:
    symbols = symbol_index(mapping)
    operations = operation_index(mapping)
    resolved: list[tuple[str, str, dict[str, Any]]] = []
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            symbol = direct_constructor_symbol(node)
            method = symbols.get(symbol) if symbol else None
            if method:
                condition = resolve_method(node, method, operations)
                if condition and condition not in resolved:
                    resolved.append(condition)
    schema = next(item["schema"] for item in extension["spec"]["schemas"] if item["id"] == "kubernetes-api-interface")
    validator = Draft202012Validator(schema)
    conditions = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for kind, interface_type, operation in resolved:
        grouped.setdefault((kind, interface_type), []).append(operation)
    for (kind, interface_type), grouped_operations in sorted(grouped.items()):
        condition = {"kind": kind, "interface": {"type": interface_type, "operations": grouped_operations}}
        errors = sorted(validator.iter_errors(condition), key=lambda error: list(error.path))
        if errors:
            raise ValueError(f"resolved condition does not align to extension: {errors[0].message}")
        conditions.append(condition)
    return {
        "apiVersion": "runtimeconditions.io/v1alpha1",
        "kind": "RuntimeConditionsProfile",
        "metadata": {"name": name},
        "workload": {"uri": workload_uri},
        "extensions": [extension["metadata"]["id"]] if conditions else [],
        "conditions": conditions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--workload-uri", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    profile = profile_for_sources(read_document(args.mapping), read_document(args.extension), args.source, args.name, args.workload_uri)
    write_yaml(args.output, profile)
    print(f"conditions: {len(profile['conditions'])}")


if __name__ == "__main__":
    main()
