#!/usr/bin/env python3
"""Generate the Kubernetes Python SDK mapping from the verified surface and extension service mapping."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from serialization import read_document, write_yaml


MAPPING_API_VERSION = "runtimeconditions.io/sdk-mapping/v1alpha1"
MAPPING_KIND = "RuntimeConditionsSDKMapping"
HTTP_TO_VERB = {"post": "create", "put": "update", "patch": "patch"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def semantic_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(encoded)


def require(value: Any, expected: Any, description: str) -> None:
    if value != expected:
        raise ValueError(f"{description}: got {value!r}, expected {expected!r}")


def operation_index(service_mapping: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for operation in service_mapping.get("operations", []):
        name = operation.get("name")
        if not isinstance(name, str) or not name or name in result:
            raise ValueError(f"invalid or duplicate service operation name {name!r}")
        result[name] = operation
    return result


def extension_validator(extension: dict[str, Any]) -> Draft202012Validator:
    schemas = extension.get("spec", {}).get("schemas", [])
    matches = [item for item in schemas if item.get("id") == "kubernetes-api-interface"]
    if len(matches) != 1:
        raise ValueError("extension must contain exactly one kubernetes-api-interface schema")
    return Draft202012Validator(matches[0]["schema"])


def profile_condition(condition: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    return {"kind": condition["kind"], "interface": {"type": condition["interfaceType"], "operations": [operation]}}


def validate_condition(validator: Draft202012Validator, condition: dict[str, Any], operation: dict[str, Any], description: str) -> None:
    errors = sorted(validator.iter_errors(profile_condition(condition, operation)), key=lambda error: list(error.path))
    if errors:
        raise ValueError(f"{description}: condition does not align to the extension: {errors[0].message}")


def argument_binding(surface: dict[str, Any], argument: str) -> dict[str, Any]:
    binding = surface.get("arguments", {}).get(argument)
    if not isinstance(binding, dict):
        raise ValueError(f"{surface['generatorOperationId']}: missing public argument {argument!r}")
    if binding.get("required") is not True:
        raise ValueError(f"{surface['generatorOperationId']}: dynamic coordinate {argument!r} must be required")
    return {"argument": argument, "position": binding["position"], "keyword": binding["keyword"]}


def dynamic_resource_operation(surface: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    path = surface["path"]
    method = surface["method"]
    if method == "get":
        verb = "get" if "{name}" in path else "list"
    elif method == "delete":
        verb = "delete" if "{name}" in path else "deletecollection"
    elif method in HTTP_TO_VERB:
        verb = HTTP_TO_VERB[method]
    else:
        raise ValueError(f"{surface['generatorOperationId']}: unsupported dynamic resource HTTP method {method!r}")
    if "/namespaces/{namespace}/" in path:
        scope = "namespaced"
    elif "resource_plural" in surface["dynamicBindings"]:
        scope = "all_namespaces"
    else:
        scope = "cluster"
    tail = path.split("/{name}/", 1)[1] if "/{name}/" in path else ""
    subresource = tail.split("/", 1)[0] if tail else None
    operation: dict[str, Any] = {"verb": verb, "scope": scope}
    if subresource and not subresource.startswith("{"):
        operation["subresource"] = subresource
    dynamic = surface["dynamicBindings"]
    resource_field = "plural" if "plural" in dynamic else "resource_plural"
    bindings = {
        "apiGroup": argument_binding(surface, dynamic["group"]),
        "apiVersion": argument_binding(surface, dynamic["version"]),
        "resource": argument_binding(surface, dynamic[resource_field]),
    }
    return operation, bindings


def materialize_resource(operation: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]:
    result = dict(operation)
    samples = {"apiGroup": "widgets.example.io", "apiVersion": "v1alpha1", "resource": "widgets"}
    for field in bindings:
        result[field] = samples[field]
    return result


def dynamic_operation(surface: dict[str, Any], condition_kind: str, interface_type: str, validator: Draft202012Validator) -> dict[str, Any]:
    dynamic = surface["dynamicBindings"]
    condition = {"kind": condition_kind, "interfaceType": interface_type}
    symbol = next(item for item in surface["symbols"] if item["flavor"] == "sync")
    name = f"{symbol['class']}.{symbol['method']}"
    if not {"plural", "resource_plural"}.intersection(dynamic):
        path_variables = {field: argument_binding(surface, argument) for field, argument in sorted(dynamic.items())}
        operation = {"pathTemplate": surface["path"], "method": surface["method"]}
        materialized_path = surface["path"]
        for field in path_variables:
            materialized_path = materialized_path.replace("{" + field + "}", {"group": "widgets.example.io", "version": "v1alpha1"}.get(field, field))
        validate_condition(validator, condition, {"path": materialized_path, "method": surface["method"]}, name)
        return {
            "name": name,
            "endpoint": {"path": surface["path"], "method": surface["method"]},
            "conditionTemplate": {**condition, "operation": operation, "pathVariables": path_variables},
        }
    operation, bindings = dynamic_resource_operation(surface)
    validate_condition(validator, condition, materialize_resource(operation, bindings), name)
    return {
        "name": name,
        "endpoint": {"path": surface["path"], "method": surface["method"]},
        "conditionTemplate": {**condition, "operation": operation, "operationBindings": bindings},
    }


def condition_operation(record: dict[str, Any]) -> dict[str, Any]:
    if "conditions" in record:
        return record["conditions"][0]["operation"]
    template = record["conditionTemplate"]
    if "pathTemplate" in template["operation"]:
        return {"path": template["operation"]["pathTemplate"], "method": template["operation"]["method"]}
    return materialize_resource(template["operation"], template["operationBindings"])


def validate_condition_delegations(surface: dict[str, Any], methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    delegations = surface.get("python", {}).get("conditionDelegations", [])
    if not isinstance(delegations, list):
        raise ValueError("surface conditionDelegations must be a list")
    method_symbols = {
        (symbol["module"], symbol["class"], symbol["method"])
        for method in methods
        for symbol in method.get("symbols", [])
    }
    delegation_symbols: set[tuple[str, str, str]] = set()
    conditional_keywords = {
        method["conditionalOperation"]["when"]["argument"].get("keyword")
        for method in methods
        if "conditionalOperation" in method
    }
    identifiers: set[str] = set()
    for item in delegations:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError(f"invalid or duplicate condition delegation id {identifier!r}")
        identifiers.add(identifier)
        symbols = item.get("symbols")
        delegate = item.get("delegate")
        if not isinstance(symbols, list) or not symbols or not isinstance(delegate, dict):
            raise ValueError(f"{identifier}: symbols and delegate are required")
        for symbol in symbols:
            key = (symbol.get("module"), symbol.get("class"), symbol.get("method")) if isinstance(symbol, dict) else (None, None, None)
            if not all(isinstance(value, str) and value for value in key) or key in method_symbols or key in delegation_symbols:
                raise ValueError(f"{identifier}: invalid or duplicate delegation symbol {key}")
            delegation_symbols.add(key)
        activations = delegate.get("activateTargetConditionals")
        if not isinstance(activations, list) or not activations:
            raise ValueError(f"{identifier}: activateTargetConditionals are required")
        activated_keywords = {
            activation.get("argument", {}).get("keyword")
            for activation in activations
            if isinstance(activation, dict) and isinstance(activation.get("argument"), dict)
        }
        if not activated_keywords.intersection(conditional_keywords):
            raise ValueError(f"{identifier}: no target conditional can be activated by this delegation")
    return [{"id": item["id"], "symbols": item["symbols"], "delegate": item["delegate"]} for item in delegations]


def build_mapping(surface: dict[str, Any], service_mapping: dict[str, Any], extension: dict[str, Any]) -> dict[str, Any]:
    require(surface.get("kind"), "RuntimeConditionsPythonSDKSurfaceInventory", "surface kind")
    require(service_mapping.get("kind"), "RuntimeConditionsServiceMapping", "service mapping kind")
    require(extension.get("kind"), "RuntimeConditionsExtensionDefinition", "extension kind")
    owner = surface["metadata"]["owner"]
    extension_coordinates = service_mapping["extension"]
    require(extension_coordinates.get("id"), extension["metadata"]["id"], "extension id")
    require(extension_coordinates.get("version"), extension["metadata"]["version"], "extension version")
    require(extension_coordinates.get("semanticSha256"), extension["metadata"]["semanticSha256"], "extension semantic digest")
    require(surface["metadata"]["source"]["authoritativeInventory"]["semanticSha256"], service_mapping["metadata"]["sourceInventorySemanticSha256"], "authoritative inventory semantic digest")
    service_operations = operation_index(service_mapping)
    validator = extension_validator(extension)
    operations: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    operation_names: set[str] = set()
    for item in surface["surfaces"]:
        if item["classification"] == "authoritative":
            name = item["authoritative"]["operationId"]
            source_operation = service_operations.get(name)
            if not source_operation:
                raise ValueError(f"{item['generatorOperationId']}: authoritative operation {name!r} is absent from service mapping")
            record = {"name": name, "endpoint": source_operation["endpoint"], "conditions": source_operation["conditions"]}
            for condition in record["conditions"]:
                validate_condition(validator, condition, condition["operation"], name)
        elif item["classification"] == "sdk_injected_dynamic":
            record = dynamic_operation(item, "kubernetes", "api", validator)
            name = record["name"]
        else:
            raise ValueError(f"{item['generatorOperationId']}: unknown surface classification")
        if name in operation_names:
            raise ValueError(f"multiple Python surfaces target operation record {name!r}")
        operation_names.add(name)
        operations.append(record)
        method: dict[str, Any] = {
            "endpoint": {"path": item["path"], "method": item["method"]},
            "symbols": item["symbols"],
            "operationRef": {"distribution": owner["distribution"], "mapping": "kubernetes.api", "operation": name},
        }
        if "watchArgument" in item:
            base_operation = condition_operation(record)
            if base_operation.get("verb") == "list":
                watch_operation = {**base_operation, "verb": "watch"}
                condition = record["conditions"][0] if "conditions" in record else record["conditionTemplate"]
                validate_condition(validator, condition, watch_operation, f"{name} conditional watch")
                method["conditionalOperation"] = {
                    "when": {"argument": {"keyword": item["watchArgument"]}, "equals": True},
                    "operationOverride": {"verb": "watch"},
                }
        methods.append(method)
    operations.sort(key=lambda item: item["name"])
    methods.sort(key=lambda item: (item["symbols"][0]["module"], item["symbols"][0]["class"], item["symbols"][0]["method"]))
    delegations = validate_condition_delegations(surface, methods)
    python_mapping: dict[str, Any] = {"apiMethods": methods}
    if delegations:
        python_mapping["conditionDelegations"] = delegations
    body = {"operations": operations, "python": python_mapping}
    classifications = Counter("dynamic" if "conditionTemplate" in item else "authoritative" for item in operations)
    public_symbol_count = sum(len(item["symbols"]) for item in methods) + sum(len(item["symbols"]) for item in delegations)
    return {
        "apiVersion": MAPPING_API_VERSION,
        "kind": MAPPING_KIND,
        "metadata": {
            "name": "kubernetes.api",
            "distribution": owner["distribution"],
            "distributionVersion": owner["version"],
            "language": "python",
            "service": "kubernetes-api",
            "repository": owner["repository"],
            "revision": owner["revision"],
            "sourceSurfaceSemanticSha256": surface["metadata"]["semanticSha256"],
            "serviceMappingSemanticSha256": service_mapping["metadata"]["semanticSha256"],
            "operationCount": len(operations),
            "publicSymbolCount": public_symbol_count,
            "semanticSha256": semantic_sha256(body),
            "summary": {
                "operationRecords": dict(sorted(classifications.items())),
                "conditionalWatchMethods": sum("conditionalOperation" in item for item in methods),
                "conditionDelegations": len(delegations),
            },
        },
        "dependencies": [{"kind": "extension", **extension_coordinates}],
        "extension": extension_coordinates,
        **body,
    }


def review_markdown(mapping: dict[str, Any]) -> str:
    metadata = mapping["metadata"]
    summary = metadata["summary"]
    config_map = next(item for item in mapping["python"]["apiMethods"] if item["symbols"][0]["method"] == "read_namespaced_config_map")
    create_custom = next(item for item in mapping["operations"] if item["name"] == "CustomObjectsApi.create_namespaced_custom_object")
    dynamic_records = [item for item in mapping["operations"] if "conditionTemplate" in item]
    lines = [
        "# Kubernetes Python conforming mapping review",
        "",
        "**Classification: `accepted`**",
        "",
        "The verified Kubernetes Python 36.0.3 surface compiles into a mapping that targets one exact immutable Kubernetes API extension release.",
        "",
        "## Artifact",
        "",
        f"- Distribution: `{metadata['distribution']}=={metadata['distributionVersion']}`",
        f"- Mapping: `{metadata['name']}`",
        f"- Mapping semantic SHA-256: `{metadata['semanticSha256']}`",
        f"- Target extension: `{mapping['extension']['id']}`",
        f"- Target extension semantic SHA-256: `{mapping['extension']['semanticSha256']}`",
        f"- Operation records: {metadata['operationCount']} ({summary['operationRecords'].get('authoritative', 0)} authoritative and {summary['operationRecords'].get('dynamic', 0)} dynamic)",
        f"- Public sync/async symbols: {metadata['publicSymbolCount']}",
        f"- Conditional list-to-watch methods: {summary['conditionalWatchMethods']}",
        f"- Source-verified condition delegations: {summary['conditionDelegations']}",
        "",
        "## Representative typed-client join",
        "",
        f"`{config_map['symbols'][0]['class']}.{config_map['symbols'][0]['method']}` references `{config_map['operationRef']['operation']}`, which emits the accepted core/v1 namespaced ConfigMap `get` operation.",
        "",
        "## Dynamic method contract",
        "",
        f"The mapping contains {len(dynamic_records)} separate dynamic endpoint/method records. For example, `{create_custom['name']}` fixes `create` and `namespaced`; only API group, API version, and plural resource bind from that method's required arguments. No operation record contains a list of possible verbs, scopes, or subresources.",
        "",
        "## SDK-author review surface",
        "",
        "Generated typed-client records require no handwritten method table. Maintainers review the generator integration, the separate dynamic binding rule, one source-verified `Watch.stream` delegation annotation, future handwritten wrappers, and the concise release difference. The generated mapping YAML is not a line-by-line review surface.",
        "",
        "## Scope boundary",
        "",
        "This mapping conforms to the extension for the complete generated typed-client surface and the handwritten `Watch.stream` delegation. The wrapper contributes no generic Kubernetes condition: a profiler must resolve its callable argument, inherit that target's mapped condition, forward application arguments, and activate only a conditional argument declared by the target. `DynamicClient`, discovery-created `Resource` state, and other non-generated package behavior remain outside this mapping.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--service-mapping", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--mapping-output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    args = parser.parse_args()
    mapping = build_mapping(read_document(args.surface), read_document(args.service_mapping), read_document(args.extension))
    write_yaml(args.mapping_output, mapping)
    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    args.review_output.write_text(review_markdown(mapping), encoding="utf-8")
    print("classification: accepted")
    print(f"operations: {mapping['metadata']['operationCount']}")
    print(f"public symbols: {mapping['metadata']['publicSymbolCount']}")
    print(f"mapping semantic sha256: {mapping['metadata']['semanticSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
