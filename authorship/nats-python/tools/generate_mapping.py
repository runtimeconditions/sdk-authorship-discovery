#!/usr/bin/env python3
"""Project reviewed NATS Python annotations into deterministic SDK metadata."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from serialization import read_document, write_yaml


@dataclass(frozen=True)
class Signature:
    parameters: tuple[str, ...]
    variadic_keywords: bool = False

    def argument(self, parameter: str) -> dict[str, Any]:
        if parameter in self.parameters:
            return {"position": self.parameters.index(parameter), "keyword": parameter}
        if self.variadic_keywords:
            return {"keyword": parameter}
        raise ValueError(f"parameter {parameter!r} does not exist in the pinned source signature")


class SourceIndex:
    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root.resolve()
        self.source_root = self.distribution_root / "src"
        self.modules: dict[str, ast.Module] = {}
        self.aliases: dict[str, str] = {}
        for path in sorted(self.source_root.rglob("*.py")):
            relative = path.relative_to(self.source_root)
            parts = list(relative.parts)
            if parts[-1] == "__init__.py":
                parts.pop()
            else:
                parts[-1] = Path(parts[-1]).stem
            module = ".".join(parts)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            self.modules[module] = tree
            package = module if path.name == "__init__.py" else module.rpartition(".")[0]
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    base = self._import_base(package, node.module or "", node.level)
                    for alias in node.names:
                        if alias.name != "*":
                            self.aliases[f"{module}.{alias.asname or alias.name}"] = f"{base}.{alias.name}" if base else alias.name

    def factory_signature(self, symbol: str) -> Signature:
        symbol = self.aliases.get(symbol, symbol)
        module, member = self._split_symbol(symbol)
        node = self._top_level(module, member)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return self._signature(node, receiver=False)
        if isinstance(node, ast.ClassDef):
            initializer = next((item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"), None)
            return self._signature(initializer, receiver=True) if initializer is not None else Signature(())
        raise ValueError(f"{symbol}: factory symbol is neither a function nor a class")

    def value_type_signature(self, symbol: str) -> Signature:
        symbol = self.aliases.get(symbol, symbol)
        module, member = self._split_symbol(symbol)
        node = self._top_level(module, member)
        if not isinstance(node, ast.ClassDef):
            raise ValueError(f"{symbol}: value type is not a class")
        fields = tuple(item.target.id for item in node.body if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name))
        if not fields:
            raise ValueError(f"{symbol}: value type has no declared dataclass fields")
        return Signature(fields)

    def method_signature(self, symbol: dict[str, Any]) -> Signature:
        module = symbol.get("module")
        class_name = symbol.get("class")
        method = symbol.get("method")
        if not all(isinstance(value, str) and value for value in (module, class_name, method)):
            raise ValueError(f"invalid Python method symbol {symbol!r}")
        class_node = self._top_level(module, class_name)
        if not isinstance(class_node, ast.ClassDef):
            raise ValueError(f"{module}.{class_name}: class does not exist")
        node = next((item for item in class_node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method), None)
        if node is None:
            raise ValueError(f"{module}.{class_name}.{method}: method does not exist")
        return self._signature(node, receiver=True)

    def public_methods(self, module: str, class_name: str) -> set[str]:
        node = self._top_level(module, class_name)
        if not isinstance(node, ast.ClassDef):
            raise ValueError(f"{module}.{class_name}: class does not exist")
        return {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_")}

    def _split_symbol(self, symbol: str) -> tuple[str, str]:
        candidates = [(module, symbol[len(module) + 1 :]) for module in self.modules if symbol.startswith(f"{module}.") and "." not in symbol[len(module) + 1 :]]
        if not candidates:
            raise ValueError(f"{symbol}: source symbol does not exist")
        return max(candidates, key=lambda item: len(item[0]))

    def _top_level(self, module: str, member: str) -> ast.AST:
        tree = self.modules.get(module)
        if tree is None:
            raise ValueError(f"{module}: source module does not exist")
        matches = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == member]
        if len(matches) != 1:
            raise ValueError(f"{module}.{member}: expected one source declaration, found {len(matches)}")
        return matches[0]

    def _signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef, receiver: bool) -> Signature:
        parameters = [item.arg for item in [*node.args.posonlyargs, *node.args.args]]
        if receiver and parameters and parameters[0] in {"self", "cls"}:
            parameters.pop(0)
        parameters.extend(item.arg for item in node.args.kwonlyargs)
        return Signature(tuple(parameters), node.args.kwarg is not None)

    def _import_base(self, package: str, module: str, level: int) -> str:
        if level == 0:
            return module
        parts = package.split(".") if package else []
        prefix = parts[: max(0, len(parts) - (level - 1))]
        if module:
            prefix.extend(module.split("."))
        return ".".join(prefix)


def semantic_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def method_id(prefix: str, method: str) -> str:
    return f"{prefix}-{'-'.join(part for part in method.split('_') if part)}"


def expand_calls(python: dict[str, Any]) -> list[dict[str, Any]]:
    calls = copy.deepcopy(python.get("calls", []))
    for group in python.get("callGroups", []):
        prefix = group["idPrefix"]
        common = {key: copy.deepcopy(value) for key, value in group.items() if key not in {"idPrefix", "methods", "symbols"}}
        base_symbol = group.get("symbols")
        if not isinstance(base_symbol, dict) or not isinstance(base_symbol.get("module"), str) or not isinstance(base_symbol.get("class"), str):
            raise ValueError(f"call group {prefix!r} must declare one module and class")
        for method in group.get("methods", []):
            if not isinstance(method, str) or not method:
                raise ValueError(f"call group {prefix!r} contains an invalid method")
            calls.append({"id": method_id(prefix, method), "symbols": [{**base_symbol, "method": method}], **copy.deepcopy(common)})
    return calls


def compile_binding(binding: Any, signature: Signature) -> Any:
    if not isinstance(binding, dict):
        raise ValueError("binding must be an object")
    result = copy.deepcopy(binding)
    if isinstance(result.get("anyOf"), list):
        result["anyOf"] = [compile_binding(item, signature) for item in result["anyOf"]]
    argument = result.get("argument")
    if isinstance(argument, dict) and "parameter" in argument:
        parameter = argument.pop("parameter")
        if not isinstance(parameter, str) or not parameter:
            raise ValueError("binding parameter must be a non-empty string")
        result["argument"] = {**signature.argument(parameter), **argument}
    return result


def compile_bindings(bindings: Any, signatures: list[Signature]) -> dict[str, Any]:
    if bindings is None:
        return {}
    if not isinstance(bindings, dict):
        raise ValueError("bindings must be an object")
    compiled: list[dict[str, Any]] = []
    for signature in signatures:
        compiled.append({field: compile_binding(binding, signature) for field, binding in bindings.items()})
    if any(candidate != compiled[0] for candidate in compiled[1:]):
        raise ValueError("one mapping record cannot compile to different bindings across its symbols")
    return compiled[0] if compiled else {}


def compile_operation_entries(record: dict[str, Any], signatures: list[Signature]) -> list[dict[str, Any]] | None:
    if "operationRef" in record and "operations" in record:
        raise ValueError(f"{record.get('id')}: cannot declare both operationRef and operations")
    if "operations" not in record:
        return None
    entries = record["operations"]
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{record.get('id')}: operations must be a non-empty list")
    result = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("operationRef"), str):
            raise ValueError(f"{record.get('id')}: invalid operation entry")
        compiled = {key: copy.deepcopy(value) for key, value in entry.items() if key != "operationBindings"}
        if "operationBindings" in entry:
            compiled["operationBindings"] = compile_bindings(entry["operationBindings"], signatures)
        result.append(compiled)
    return result


def operation_entries(record: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(record.get("operations"), list):
        return record["operations"]
    return [record] if isinstance(record.get("operationRef"), str) else []


def binding_references(binding: Any) -> tuple[set[str], set[str]]:
    state_fields: set[str] = set()
    value_fields: set[str] = set()
    if not isinstance(binding, dict):
        return state_fields, value_fields
    if isinstance(binding.get("state"), str):
        state_fields.add(binding["state"])
    argument = binding.get("argument")
    if isinstance(argument, dict) and isinstance(argument.get("field"), str):
        value_fields.add(argument["field"])
    for alternative in binding.get("anyOf", []):
        state, value = binding_references(alternative)
        state_fields.update(state)
        value_fields.update(value)
    return state_fields, value_fields


def validate_compiled_contract(python: dict[str, Any], operations: dict[str, dict[str, Any]]) -> None:
    value_fields = {field for value_type in python["valueTypes"] for field in value_type.get("fields", {})}
    producers: dict[str, list[set[str]]] = {}
    for record in [*python["factories"], *python["calls"]]:
        produced = record.get("produces")
        if not isinstance(produced, dict):
            continue
        state_type = produced.get("stateType")
        policy = produced.get("dependencyIdentity")
        if not isinstance(state_type, str) or not state_type or policy not in {"new", "inherit"}:
            raise ValueError(f"{record.get('id')}: produced state requires a stateType and new or inherit dependency identity")
        producers.setdefault(state_type, []).append(set(produced.get("bindings", {})))
    guaranteed_state_fields = {state_type: set.intersection(*field_sets) if field_sets else set() for state_type, field_sets in producers.items()}
    for record in [*python["factories"], *python["calls"]]:
        call_id = record.get("id")
        receiver_state = record.get("receiverState")
        if receiver_state is not None and receiver_state not in producers:
            raise ValueError(f"{call_id}: receiver state {receiver_state!r} has no producer")
        operation_areas = [entry.get("operationBindings", {}) for entry in operation_entries(record)]
        produced = record.get("produces")
        produced_bindings = produced.get("bindings", {}) if isinstance(produced, dict) else {}
        for area in [*operation_areas, produced_bindings]:
            for field, binding in area.items():
                state_refs, value_refs = binding_references(binding)
                if state_refs and not isinstance(receiver_state, str):
                    raise ValueError(f"{call_id}: binding {field!r} reads state without a receiver state")
                unavailable = state_refs - guaranteed_state_fields.get(receiver_state, set())
                if unavailable:
                    raise ValueError(f"{call_id}: binding {field!r} reads state fields not guaranteed by every producer: {sorted(unavailable)}")
                unknown_value_fields = value_refs - value_fields
                if unknown_value_fields:
                    raise ValueError(f"{call_id}: binding {field!r} reads undeclared typed-value fields {sorted(unknown_value_fields)}")
        for entry in operation_entries(record):
            operation_name = entry["operationRef"]
            operation = operations.get(operation_name)
            if operation is None:
                raise ValueError(f"{call_id}: unknown service operation {operation_name!r}")
            required = {field for condition in operation.get("conditions", []) for field in condition.get("bindings", {}).get("required", [])}
            optional = {field for condition in operation.get("conditions", []) for field in condition.get("bindings", {}).get("optional", [])}
            supplied = set(entry.get("operationBindings", {}))
            if not required <= supplied:
                raise ValueError(f"{call_id}: missing sources for required fields {sorted(required - supplied)}")
            if not supplied <= required | optional:
                raise ValueError(f"{call_id}: supplies fields absent from the service operation {sorted(supplied - required - optional)}")


def compile_python(annotations: dict[str, Any], source: SourceIndex, service_mapping: dict[str, Any]) -> dict[str, Any]:
    configured = annotations["python"]
    value_types = []
    for record in configured.get("valueTypes", []):
        symbols = record.get("symbols", [])
        signatures = [source.value_type_signature(symbol) for symbol in symbols]
        fields = compile_bindings(record.get("fields", {}), signatures)
        value_types.append({"id": record["id"], "symbols": symbols, "fields": fields})
    factories = []
    for record in configured.get("factories", []):
        signatures = [source.factory_signature(symbol) for symbol in record.get("symbols", [])]
        compiled = {key: copy.deepcopy(value) for key, value in record.items() if key not in {"operationBindings", "operations", "produces"}}
        if "operationBindings" in record:
            compiled["operationBindings"] = compile_bindings(record["operationBindings"], signatures)
        compiled_operations = compile_operation_entries(record, signatures)
        if compiled_operations is not None:
            compiled["operations"] = compiled_operations
        produced = record.get("produces")
        if isinstance(produced, dict):
            compiled["produces"] = {**{key: copy.deepcopy(value) for key, value in produced.items() if key != "bindings"}, "bindings": compile_bindings(produced.get("bindings", {}), signatures)}
        factories.append(compiled)
    operations = {record["name"]: record for record in service_mapping.get("operations", [])}
    calls = []
    seen_ids: set[str] = set()
    seen_symbols: set[tuple[str, str, str]] = set()
    for record in expand_calls(configured):
        call_id = record.get("id")
        if not isinstance(call_id, str) or not call_id or call_id in seen_ids:
            raise ValueError(f"invalid or duplicate call id {call_id!r}")
        seen_ids.add(call_id)
        symbols = record.get("symbols", [])
        signatures = [source.method_signature(symbol) for symbol in symbols]
        for symbol in symbols:
            key = (symbol["module"], symbol["class"], symbol["method"])
            if key in seen_symbols:
                raise ValueError(f"{call_id}: duplicate mapped symbol {'.'.join(key)}")
            seen_symbols.add(key)
        compiled = {key: copy.deepcopy(value) for key, value in record.items() if key not in {"operationBindings", "operations", "produces"}}
        if "operationBindings" in record:
            compiled["operationBindings"] = compile_bindings(record["operationBindings"], signatures)
        compiled_operations = compile_operation_entries(record, signatures)
        if compiled_operations is not None:
            compiled["operations"] = compiled_operations
        produced = record.get("produces")
        if isinstance(produced, dict):
            compiled["produces"] = {**{key: copy.deepcopy(value) for key, value in produced.items() if key != "bindings"}, "bindings": compile_bindings(produced.get("bindings", {}), signatures)}
        if "operationRef" not in compiled and "operations" not in compiled and "produces" not in compiled:
            raise ValueError(f"{call_id}: call must reference an operation, produce state, or both")
        calls.append(compiled)
    result = {"valueTypes": value_types, "factories": factories, "calls": calls}
    validate_compiled_contract(result, operations)
    return result


def validate_release(distribution_root: Path, metadata: dict[str, Any]) -> None:
    project = tomllib.loads((distribution_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project.get("name") != metadata.get("distribution") or project.get("version") != metadata.get("distributionVersion"):
        raise ValueError("pinned source distribution coordinates do not match annotations")
    repository = distribution_root
    while repository != repository.parent and not (repository / ".git").exists():
        repository = repository.parent
    if not (repository / ".git").exists():
        raise ValueError("pinned source is not inside a Git checkout")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, check=True, capture_output=True, text=True).stdout.strip()
    if revision != metadata.get("revision"):
        raise ValueError(f"pinned source revision {revision} does not match annotations")


def validate_authorities(annotations: dict[str, Any], extension: dict[str, Any], service_mapping: dict[str, Any]) -> None:
    configured_extension = annotations["extension"]
    for actual in (extension["metadata"], service_mapping["extension"]):
        for field in ("id", "version", "semanticSha256"):
            if configured_extension.get(field) != actual.get(field):
                raise ValueError(f"extension {field} mismatch")
    configured_service = annotations["serviceMapping"]
    if configured_service.get("name") != service_mapping.get("metadata", {}).get("name") or configured_service.get("semanticSha256") != service_mapping.get("metadata", {}).get("semanticSha256"):
        raise ValueError("service mapping coordinates do not match annotations")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--service-mapping", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    annotations = read_document(args.annotations)
    service_mapping = read_document(args.service_mapping)
    extension = read_document(args.extension)
    validate_authorities(annotations, extension, service_mapping)
    validate_release(args.source_root.resolve(), annotations["metadata"])
    python = compile_python(annotations, SourceIndex(args.source_root), service_mapping)
    body = {"operations": service_mapping["operations"], "python": python}
    metadata = annotations["metadata"]
    mapping = {
        "apiVersion": "runtimeconditions.io/sdk-mapping/v1alpha1",
        "kind": "RuntimeConditionsSDKMapping",
        "metadata": {**metadata, "language": "python", "callCount": len(python["calls"]), "semanticSha256": semantic_sha256(body)},
        "dependencies": [{"kind": "extension", **annotations["extension"]}, {"kind": "serviceMapping", **annotations["serviceMapping"]}],
        "extension": annotations["extension"],
        "operations": service_mapping["operations"],
        "python": python,
    }
    write_yaml(args.output, mapping)
    print(f"mapping: {metadata['name']}")
    print(f"calls: {len(python['calls'])}")
    print(f"semantic sha256: {mapping['metadata']['semanticSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
