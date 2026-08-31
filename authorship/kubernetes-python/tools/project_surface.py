#!/usr/bin/env python3
"""Project a Kubernetes Python release into a statically verified SDK surface inventory."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from serialization import read_document, write_yaml


SURFACE_API_VERSION = "runtimeconditions.io/python-sdk-surface/v1alpha1"
SURFACE_KIND = "RuntimeConditionsPythonSDKSurfaceInventory"
HTTP_METHODS = ("delete", "get", "head", "options", "patch", "post", "put", "trace")
DYNAMIC_PATH_FIELDS = {"group", "version", "plural", "resource_plural"}
ANNOTATION_API_VERSION = "runtimeconditions.io/sdk-authoring/v1alpha1"
ANNOTATION_KIND = "RuntimeConditionsPythonSDKAnnotations"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def semantic_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(encoded)


def string_subscript(node: ast.AST, container: str) -> str | None:
    if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name) or node.value.id != container:
        return None
    if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
        return node.slice.value
    return None


def call_api_endpoint(function: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, str]:
    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "call_api"
    ]
    if len(calls) != 1 or len(calls[0].args) < 2:
        raise ValueError(f"{function.name}: expected exactly one call_api invocation with path and method")
    path, method = calls[0].args[:2]
    if not isinstance(path, ast.Constant) or not isinstance(path.value, str) or not isinstance(method, ast.Constant) or not isinstance(method.value, str):
        raise ValueError(f"{function.name}: call_api path and method must be string literals")
    return path.value, method.value.lower()


def function_bindings(function: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[dict[str, str], dict[str, str]]:
    path_bindings: dict[str, str] = {}
    query_bindings: dict[str, str] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = string_subscript(node.targets[0], "path_params")
            source = string_subscript(node.value, "local_var_params")
            if target and source:
                path_bindings[target] = source
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and isinstance(node.func.value, ast.Name) and node.func.value.id == "query_params" and len(node.args) == 1 and isinstance(node.args[0], ast.Tuple) and len(node.args[0].elts) == 2:
            key_node, value_node = node.args[0].elts
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                source = string_subscript(value_node, "local_var_params")
                if source:
                    query_bindings[key_node.value] = source
    return dict(sorted(path_bindings.items())), dict(sorted(query_bindings.items()))


def public_arguments(function: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, dict[str, Any]]:
    positional = [*function.args.posonlyargs, *function.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    default_offset = len(positional) - len(function.args.defaults)
    result: dict[str, dict[str, Any]] = {}
    posonly_count = max(0, len(function.args.posonlyargs) - (1 if function.args.posonlyargs and function.args.posonlyargs[0].arg in {"self", "cls"} else 0))
    for position, argument in enumerate(positional):
        binding: dict[str, Any] = {"position": position}
        if position >= posonly_count:
            binding["keyword"] = argument.arg
        binding["required"] = position < default_offset
        result[argument.arg] = binding
    for argument, default in zip(function.args.kwonlyargs, function.args.kw_defaults):
        result[argument.arg] = {"keyword": argument.arg, "required": default is None}
    return dict(sorted(result.items()))


def class_function(tree: ast.Module, class_name: str, method_name: str, source_path: Path) -> tuple[ast.ClassDef, ast.FunctionDef | ast.AsyncFunctionDef]:
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    if len(classes) != 1:
        raise ValueError(f"{source_path}: expected one class {class_name!r}")
    functions = [node for node in classes[0].body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name]
    if len(functions) != 1:
        raise ValueError(f"{source_path}: expected one method {class_name}.{method_name}")
    return classes[0], functions[0]


def helper_return_strings(class_node: ast.ClassDef, helper_name: str, source_path: Path) -> set[str]:
    helpers = [node for node in class_node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == helper_name]
    if len(helpers) != 1:
        raise ValueError(f"{source_path}: expected one helper {class_node.name}.{helper_name}")
    values = {node.value.value for node in ast.walk(helpers[0]) if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}
    if not values:
        raise ValueError(f"{source_path}: helper {class_node.name}.{helper_name} returns no string literals")
    return values


def validate_condition_delegation(source_root: Path, item: dict[str, Any]) -> dict[str, Any]:
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("condition delegation id is required")
    symbols = item.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise ValueError(f"{identifier}: symbols are required")
    delegate = item.get("delegate")
    if not isinstance(delegate, dict):
        raise ValueError(f"{identifier}: delegate is required")
    callable_binding = delegate.get("callableArgument")
    forwarded = delegate.get("forwardedArguments")
    activations = delegate.get("activateTargetConditionals")
    if not isinstance(callable_binding, dict) or not isinstance(forwarded, dict) or not isinstance(activations, list) or not activations:
        raise ValueError(f"{identifier}: callableArgument, forwardedArguments, and activateTargetConditionals are required")
    expected_position = callable_binding.get("position")
    expected_keyword = callable_binding.get("keyword")
    positional_forward = forwarded.get("positional")
    if not isinstance(expected_position, int) or not isinstance(expected_keyword, str) or not isinstance(positional_forward, dict) or forwarded.get("keywords") is not True:
        raise ValueError(f"{identifier}: unsupported delegation argument binding")
    activation_keywords: set[str] = set()
    for activation in activations:
        argument = activation.get("argument") if isinstance(activation, dict) else None
        keyword = argument.get("keyword") if isinstance(argument, dict) else None
        if not isinstance(keyword, str) or not keyword or activation.get("equals") is not True:
            raise ValueError(f"{identifier}: each target conditional activation must set one keyword to true")
        activation_keywords.add(keyword)
    source_proofs: list[dict[str, Any]] = []
    for symbol in symbols:
        if not isinstance(symbol, dict) or not all(isinstance(symbol.get(field), str) and symbol.get(field) for field in ("module", "class", "method")):
            raise ValueError(f"{identifier}: invalid Python symbol")
        source_path = source_root / Path(*symbol["module"].split(".")).with_suffix(".py")
        if not source_path.is_file():
            raise ValueError(f"{identifier}: source module is absent: {source_path}")
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        class_node, function = class_function(tree, symbol["class"], symbol["method"], source_path)
        positional = [*function.args.posonlyargs, *function.args.args]
        if positional and positional[0].arg in {"self", "cls"}:
            positional = positional[1:]
        if expected_position >= len(positional) or positional[expected_position].arg != expected_keyword:
            raise ValueError(f"{identifier}: callable argument does not match {symbol['class']}.{symbol['method']} source")
        vararg = function.args.vararg.arg if function.args.vararg else None
        kwarg = function.args.kwarg.arg if function.args.kwarg else None
        if positional_forward.get("fromPosition") != expected_position + 1 or not vararg or not kwarg:
            raise ValueError(f"{identifier}: forwarded argument declaration does not match wrapper signature")
        delegated_calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == expected_keyword
            and any(isinstance(argument, ast.Starred) and isinstance(argument.value, ast.Name) and argument.value.id == vararg for argument in node.args)
            and any(keyword.arg is None and isinstance(keyword.value, ast.Name) and keyword.value.id == kwarg for keyword in node.keywords)
        ]
        if not delegated_calls:
            raise ValueError(f"{identifier}: wrapper does not forward *{vararg} and **{kwarg} to {expected_keyword}")
        selector_helpers: dict[str, str] = {}
        for node in ast.walk(function):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name) or not isinstance(node.value, ast.Call):
                continue
            if isinstance(node.value.func, ast.Attribute) and isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == "self" and len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Name) and node.value.args[0].id == expected_keyword:
                selector_helpers[node.targets[0].id] = node.value.func.attr
        assigned_selectors: set[str] = set()
        for node in ast.walk(function):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Subscript) or not isinstance(node.targets[0].value, ast.Name) or node.targets[0].value.id != kwarg:
                continue
            if isinstance(node.targets[0].slice, ast.Name) and node.targets[0].slice.id in selector_helpers and isinstance(node.value, ast.Constant) and node.value.value is True:
                assigned_selectors.add(node.targets[0].slice.id)
        if len(assigned_selectors) != 1:
            raise ValueError(f"{identifier}: wrapper does not source-provenly select and enable a delegated target argument")
        source_keywords = helper_return_strings(class_node, selector_helpers[next(iter(assigned_selectors))], source_path)
        if source_keywords != activation_keywords:
            raise ValueError(f"{identifier}: annotated target conditionals {sorted(activation_keywords)} differ from source {sorted(source_keywords)}")
        source_proofs.append({"path": source_path.relative_to(source_root).as_posix(), "sha256": sha256_file(source_path)})
    return {"id": identifier, "symbols": symbols, "delegate": delegate, "sourceProofs": source_proofs}


def condition_delegations(source_root: Path, annotations_path: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if annotations_path is None:
        return [], None
    document = read_document(annotations_path)
    if document.get("apiVersion") != ANNOTATION_API_VERSION or document.get("kind") != ANNOTATION_KIND:
        raise ValueError("invalid Python SDK annotation document")
    if document.get("metadata", {}).get("distribution") != "kubernetes":
        raise ValueError("Python SDK annotations target a different distribution")
    authored = document.get("python", {}).get("conditionDelegations")
    if not isinstance(authored, list):
        raise ValueError("Python SDK annotations must contain conditionDelegations")
    validated = [validate_condition_delegation(source_root, item) for item in authored]
    identifiers = [item["id"] for item in validated]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Python SDK annotations contain duplicate condition delegation ids")
    coordinates = {"path": annotations_path.name, "sha256": sha256_file(annotations_path), "semanticSha256": semantic_sha256(document)}
    return validated, coordinates


def module_source(source_root: Path, module: str) -> Path:
    path = source_root / Path(*module.split("."))
    source = path.with_suffix(".py")
    if source.is_file():
        return source
    package = path / "__init__.py"
    if package.is_file():
        return package
    raise ValueError(f"source module is absent: {module}")


def method_arguments(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    arguments = [argument.arg for argument in (*function.args.posonlyargs, *function.args.args)]
    return arguments[1:] if arguments and arguments[0] in {"self", "cls"} else arguments


def validate_stateful_resource_flow(source_root: Path, item: dict[str, Any]) -> dict[str, Any]:
    identifier = item.get("id")
    constructors = item.get("constructorSymbols")
    producer = item.get("producer")
    implementation = item.get("implementation")
    methods = item.get("methods")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("stateful resource flow id is required")
    if not isinstance(constructors, list) or not constructors or any(not isinstance(symbol, str) or not symbol for symbol in constructors):
        raise ValueError(f"{identifier}: constructorSymbols are required")
    if not isinstance(producer, dict) or producer.get("memberPath") != ["resources", "get"] or not isinstance(producer.get("selectorArguments"), dict) or not isinstance(producer.get("producesState"), str):
        raise ValueError(f"{identifier}: unsupported state producer")
    if set(producer["selectorArguments"]) != {"apiVersion", "group", "kind"}:
        raise ValueError(f"{identifier}: producer must bind API version, group, and kind")
    if not isinstance(implementation, dict) or not isinstance(methods, list) or not methods:
        raise ValueError(f"{identifier}: implementation and methods are required")

    source_paths: set[Path] = set()
    parsed: dict[str, tuple[ast.Module, ast.ClassDef]] = {}
    for role in ("client", "discoverer", "resourceProxy"):
        symbol = implementation.get(role)
        if not isinstance(symbol, dict) or not isinstance(symbol.get("module"), str) or not isinstance(symbol.get("class"), str):
            raise ValueError(f"{identifier}: invalid {role} implementation symbol")
        source_path = module_source(source_root, symbol["module"])
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == symbol["class"]]
        if len(classes) != 1:
            raise ValueError(f"{identifier}: expected one {symbol['class']} class in {source_path}")
        parsed[role] = tree, classes[0]
        source_paths.add(source_path)

    client_symbol = implementation["client"]
    _, constructor = class_function(parsed["client"][0], client_symbol["class"], "__init__", module_source(source_root, client_symbol["module"]))
    if not any(isinstance(node, ast.FunctionDef) and node.decorator_list and any(isinstance(decorator, ast.Name) and decorator.id == "property" for decorator in node.decorator_list) and node.name == "resources" and any(isinstance(child, ast.Return) and isinstance(child.value, ast.Attribute) and child.value.attr == "__discoverer" for child in ast.walk(node)) for node in parsed["client"][1].body):
        raise ValueError(f"{identifier}: DynamicClient.resources no longer exposes its discoverer")
    if method_arguments(constructor)[:1] != ["client"]:
        raise ValueError(f"{identifier}: DynamicClient constructor signature changed")

    discoverer_symbol = implementation["discoverer"]
    _, discoverer_get = class_function(parsed["discoverer"][0], discoverer_symbol["class"], discoverer_symbol["method"], module_source(source_root, discoverer_symbol["module"]))
    forwards_search = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "self" and node.func.attr == "search" and any(keyword.arg is None and isinstance(keyword.value, ast.Name) and keyword.value.id == discoverer_get.args.kwarg.arg for keyword in node.keywords) for node in ast.walk(discoverer_get)) if discoverer_get.args.kwarg else False
    if not forwards_search:
        raise ValueError(f"{identifier}: Discoverer.get no longer forwards its selectors to search")

    proxy_symbol = implementation["resourceProxy"]
    _, proxy = class_function(parsed["resourceProxy"][0], proxy_symbol["class"], proxy_symbol["method"], module_source(source_root, proxy_symbol["module"]))
    proxy_source = ast.dump(proxy, include_attributes=False)
    if "Name(id='partial'" not in proxy_source or "attr='client'" not in proxy_source:
        raise ValueError(f"{identifier}: Resource proxy no longer binds DynamicClient methods")
    _, path_function = class_function(parsed["resourceProxy"][0], proxy_symbol["class"], "path", module_source(source_root, proxy_symbol["module"]))
    path_tests = [ast.dump(node.test, include_attributes=False) for node in ast.walk(path_function) if isinstance(node, ast.If)]
    if not any(test == "Name(id='name', ctx=Load())" for test in path_tests) or not any(test == "BoolOp(op=And(), values=[Attribute(value=Name(id='self', ctx=Load()), attr='namespaced', ctx=Load()), Name(id='namespace', ctx=Load())])" for test in path_tests):
        raise ValueError(f"{identifier}: Resource.path no longer derives collection and namespaced paths from argument truthiness")

    expected_verbs = {
        "get": {"get", "list"},
        "create": {"create"},
        "delete": {"delete", "deletecollection"},
        "replace": {"update"},
        "patch": {"patch"},
        "server_side_apply": {"patch"},
        "watch": {"watch"},
    }
    seen_methods: set[str] = set()
    for method in methods:
        name = method.get("method") if isinstance(method, dict) else None
        operation_entries = method.get("operations") if isinstance(method, dict) else None
        if name not in expected_verbs or name in seen_methods or not isinstance(operation_entries, list) or not operation_entries:
            raise ValueError(f"{identifier}: invalid or duplicate stateful method {name!r}")
        seen_methods.add(name)
        if {operation.get("verb") for operation in operation_entries if isinstance(operation, dict)} != expected_verbs[name]:
            raise ValueError(f"{identifier}: {name} operations differ from source-proven behavior")
        if name == "get":
            expected = [
                {"when": {"argument": {"position": 0, "keyword": "name"}, "provided": True}, "verb": "get", "scopeMode": "resource"},
                {"otherwise": True, "verb": "list", "scopeMode": "collection"},
            ]
            if operation_entries != expected:
                raise ValueError(f"{identifier}: get branch rules differ from Resource.path behavior")
        if name == "delete":
            expected = [
                {"when": {"argument": {"position": 0, "keyword": "name"}, "provided": True}, "verb": "delete", "scopeMode": "resource"},
                {
                    "when": {
                        "any": [
                            {"argument": {"position": 3, "keyword": "label_selector"}, "provided": True},
                            {"argument": {"position": 4, "keyword": "field_selector"}, "provided": True},
                        ]
                    },
                    "verb": "deletecollection",
                    "scopeMode": "collection",
                },
            ]
            if operation_entries != expected:
                raise ValueError(f"{identifier}: delete branch rules differ from its required selectors")
        _, function = class_function(parsed["client"][0], client_symbol["class"], name, module_source(source_root, client_symbol["module"]))
        arguments = method_arguments(function)
        if not arguments or arguments[0] != "resource":
            raise ValueError(f"{identifier}: DynamicClient.{name} no longer receives a resource first")
        namespace = method.get("namespaceArgument")
        if not isinstance(namespace, dict) or not isinstance(namespace.get("position"), int) or namespace.get("keyword") != "namespace":
            raise ValueError(f"{identifier}: {name} namespace binding is invalid")
        public_arguments = arguments[1:]
        position = namespace["position"]
        if position >= len(public_arguments) or public_arguments[position] != "namespace":
            raise ValueError(f"{identifier}: {name} namespace binding differs from source")
        if name == "watch":
            delegated = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "stream" and node.args and isinstance(node.args[0], ast.Attribute) and isinstance(node.args[0].value, ast.Name) and node.args[0].value.id == "resource" and node.args[0].attr == "get" for node in ast.walk(function))
            if not delegated:
                raise ValueError(f"{identifier}: DynamicClient.watch no longer delegates to resource.get")
        else:
            requests = [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "self" and node.func.attr == "request"]
            if len(requests) != 1 or not requests[0].args or not isinstance(requests[0].args[0], ast.Constant):
                raise ValueError(f"{identifier}: DynamicClient.{name} no longer makes one literal request")
            if name == "delete":
                function_source = ast.dump(function, include_attributes=False)
                if not all(f"Name(id='{argument}', ctx=Load())" in function_source for argument in ("name", "label_selector", "field_selector")) or "Raise(" not in function_source:
                    raise ValueError(f"{identifier}: DynamicClient.delete no longer enforces name or collection selectors")
    if seen_methods != set(expected_verbs):
        raise ValueError(f"{identifier}: stateful method inventory is incomplete")

    return {
        "id": identifier,
        "constructorSymbols": constructors,
        "producer": producer,
        "methods": methods,
        "sourceProofs": [
            {"path": path.relative_to(source_root).as_posix(), "sha256": sha256_file(path)}
            for path in sorted(source_paths)
        ],
    }


def stateful_resource_flows(source_root: Path, annotations_path: Path | None) -> list[dict[str, Any]]:
    if annotations_path is None:
        return []
    document = read_document(annotations_path)
    authored = document.get("python", {}).get("statefulResourceFlows", [])
    if not isinstance(authored, list):
        raise ValueError("Python SDK annotations statefulResourceFlows must be a list")
    validated = [validate_stateful_resource_flow(source_root, item) for item in authored]
    identifiers = [item["id"] for item in validated]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Python SDK annotations contain duplicate stateful resource flow ids")
    return validated


def parse_generated_directory(source_root: Path, relative_directory: Path, flavor: str) -> dict[tuple[str, str], dict[str, Any]]:
    directory = source_root / relative_directory
    if not directory.is_dir():
        raise ValueError(f"missing generated {flavor} API directory: {directory}")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for source_path in sorted(directory.glob("*_api.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for class_node in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            functions = {
                node.name: node
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for function_name, function in sorted(functions.items()):
                if not function_name.endswith("_with_http_info"):
                    continue
                method_name = function_name.removesuffix("_with_http_info")
                if method_name not in functions:
                    raise ValueError(f"{source_path}: missing public wrapper {method_name}")
                arguments = public_arguments(functions[method_name])
                endpoint = call_api_endpoint(function)
                if endpoint in result:
                    raise ValueError(f"duplicate generated {flavor} endpoint {endpoint}")
                path_bindings, query_bindings = function_bindings(function)
                module = ".".join(source_path.relative_to(source_root).with_suffix("").parts)
                result[endpoint] = {
                    "flavor": flavor,
                    "module": module,
                    "class": class_node.name,
                    "method": method_name,
                    "arguments": arguments,
                    "pathBindings": path_bindings,
                    "queryBindings": query_bindings,
                }
    if not result:
        raise ValueError(f"generated {flavor} API directory contains no public operations")
    return result


def processed_operations(model: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    if model.get("swagger") != "2.0":
        raise ValueError("Python generator input must be Swagger 2.0")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(model.get("paths", {})):
        path_item = model["paths"][path]
        for method in HTTP_METHODS:
            if method not in path_item:
                continue
            operation = path_item[method]
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ValueError(f"{method.upper()} {path}: missing operationId")
            result[(path, method)] = {
                "operationId": operation_id,
                "tags": operation.get("tags", []),
            }
    return result


def normalize_path(path: str) -> str:
    if path != "/":
        return path.rstrip("/")
    return path


def authoritative_index(inventory: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for operation in inventory.get("operations", []):
        key = (normalize_path(operation["path"]), operation["method"])
        if key in result:
            raise ValueError(f"authoritative inventory contains normalized endpoint collision {key}")
        result[key] = operation
    return result


def placeholders(path: str) -> list[str]:
    return re.findall(r"\{([^{}]+)\}", path)


def build_surface(
    source_root: Path,
    authoritative_inventory_path: Path,
    repository: str,
    revision: str,
    version: str,
    annotations_path: Path | None = None,
) -> dict[str, Any]:
    processed_path = source_root / "scripts/swagger.json"
    unprocessed_path = source_root / "kubernetes/swagger.json.unprocessed"
    processed_model = read_document(processed_path)
    unprocessed_model = read_document(unprocessed_path)
    authoritative_inventory = read_document(authoritative_inventory_path)
    delegations, annotation_coordinates = condition_delegations(source_root, annotations_path)
    stateful_flows = stateful_resource_flows(source_root, annotations_path)
    processed = processed_operations(processed_model)
    flavor_directories = {"sync": Path("kubernetes/client/api"), "async": Path("kubernetes/aio/client/api")}
    symbol_sets = {
        flavor: parse_generated_directory(source_root, directory, flavor)
        for flavor, directory in flavor_directories.items()
        if (source_root / directory).is_dir()
    }
    if not symbol_sets:
        raise ValueError("SDK source contains neither a synchronous nor asynchronous generated API surface")
    endpoints = set(processed)
    for flavor, symbols in symbol_sets.items():
        if set(symbols) != endpoints:
            missing = sorted(endpoints - set(symbols))
            extra = sorted(set(symbols) - endpoints)
            raise ValueError(f"{flavor} generated source differs from generator input: missing={missing[:5]} extra={extra[:5]}")
    authoritative = authoritative_index(authoritative_inventory)
    surfaces: list[dict[str, Any]] = []
    for endpoint in sorted(endpoints, key=lambda item: (processed[item]["operationId"], item[0], item[1])):
        path, method = endpoint
        processed_operation = processed[endpoint]
        available_symbols = [symbol_sets[flavor][endpoint] for flavor in ("sync", "async") if flavor in symbol_sets]
        primary = available_symbols[0]
        for symbol in available_symbols[1:]:
            if primary["arguments"] != symbol["arguments"] or primary["pathBindings"] != symbol["pathBindings"] or primary["queryBindings"] != symbol["queryBindings"]:
                raise ValueError(f"generated flavor bindings differ for {method.upper()} {path}")
        entry: dict[str, Any] = {
            "generatorOperationId": processed_operation["operationId"],
            "path": path,
            "method": method,
            "symbols": [{key: value for key, value in symbol.items() if key not in {"arguments", "pathBindings", "queryBindings"}} for symbol in available_symbols],
        }
        if primary["arguments"]:
            entry["arguments"] = primary["arguments"]
        if primary["pathBindings"]:
            entry["pathBindings"] = primary["pathBindings"]
        if "watch" in primary["queryBindings"]:
            entry["watchArgument"] = primary["queryBindings"]["watch"]
        dynamic_fields = sorted(DYNAMIC_PATH_FIELDS.intersection(placeholders(path)))
        if dynamic_fields:
            missing_bindings = sorted(set(dynamic_fields) - set(primary["pathBindings"]))
            if missing_bindings:
                raise ValueError(f"{processed_operation['operationId']}: dynamic path fields lack source bindings: {missing_bindings}")
            entry["classification"] = "sdk_injected_dynamic"
            entry["dynamicBindings"] = {field: primary["pathBindings"][field] for field in dynamic_fields}
            surfaces.append(entry)
            continue
        authoritative_operation = authoritative.get((normalize_path(path), method))
        if not authoritative_operation:
            raise ValueError(f"{processed_operation['operationId']}: no authoritative endpoint for {method.upper()} {path}")
        entry["classification"] = "authoritative"
        entry["authoritative"] = {
            "operationId": authoritative_operation["operationId"],
            "projection": authoritative_operation["projection"],
        }
        if processed_operation["operationId"] != authoritative_operation["operationId"]:
            entry["authoritative"]["generatorRenamedOperation"] = True
        if "watch" in primary["queryBindings"] and authoritative_operation["projection"].get("verb") == "list":
            entry["conditionalProjection"] = {
                "when": {"argument": primary["queryBindings"]["watch"], "equals": True},
                "projection": {**authoritative_operation["projection"], "verb": "watch"},
            }
        surfaces.append(entry)

    classifications = Counter(surface["classification"] for surface in surfaces)
    generator_operation_ids = Counter(surface["generatorOperationId"] for surface in surfaces)
    watch_capable = sum("watchArgument" in surface for surface in surfaces)
    conditional_watch = sum("conditionalProjection" in surface for surface in surfaces)
    renamed = sum(bool(surface.get("authoritative", {}).get("generatorRenamedOperation")) for surface in surfaces)
    normalized_path_joins = sum(
        surface["classification"] == "authoritative"
        and surface["path"] != next(operation["path"] for operation in authoritative_inventory["operations"] if operation["operationId"] == surface["authoritative"]["operationId"])
        for surface in surfaces
    )
    source_metadata = {
        "authoritativeSnapshot": {
            "path": "kubernetes/swagger.json.unprocessed",
            "sha256": sha256_file(unprocessed_path),
            "semanticSha256": semantic_sha256(unprocessed_model),
        },
        "generatorInput": {
            "path": "scripts/swagger.json",
            "sha256": sha256_file(processed_path),
            "semanticSha256": semantic_sha256(processed_model),
        },
        "authoritativeInventory": {
            "semanticSha256": authoritative_inventory["metadata"]["semanticSha256"],
            "sourceSemanticSha256": authoritative_inventory["metadata"]["source"]["semanticSha256"],
        },
    }
    if annotation_coordinates:
        source_metadata["sdkAnnotations"] = annotation_coordinates
    semantic_body: dict[str, Any] = {"surfaces": surfaces}
    if delegations or stateful_flows:
        semantic_body["python"] = {}
        if delegations:
            semantic_body["python"]["conditionDelegations"] = delegations
        if stateful_flows:
            semantic_body["python"]["statefulResourceFlows"] = stateful_flows
    result = {
        "apiVersion": SURFACE_API_VERSION,
        "kind": SURFACE_KIND,
        "metadata": {
            "name": "kubernetes-python",
            "status": "investigation",
            "owner": {
                "repository": repository,
                "revision": revision,
                "distribution": "kubernetes",
                "version": version,
            },
            "source": source_metadata,
            "surfaceCount": len(surfaces),
            "semanticSha256": semantic_sha256(semantic_body),
            "summary": {
                "classifications": dict(sorted(classifications.items())),
                "syncSymbols": len(symbol_sets.get("sync", {})),
                "asyncSymbols": len(symbol_sets.get("async", {})),
                "operationIdRenames": renamed,
                "duplicateGeneratorOperationIds": sum(count > 1 for count in generator_operation_ids.values()),
                "endpointsUsingDuplicateGeneratorOperationIds": sum(count for count in generator_operation_ids.values() if count > 1),
                "normalizedPathJoins": normalized_path_joins,
                "watchCapableMethods": watch_capable,
                "conditionalWatchProjections": conditional_watch,
                "conditionDelegations": len(delegations),
                "statefulResourceFlows": len(stateful_flows),
            },
        },
        "surfaces": surfaces,
    }
    if delegations or stateful_flows:
        result["python"] = {}
        if delegations:
            result["python"]["conditionDelegations"] = delegations
        if stateful_flows:
            result["python"]["statefulResourceFlows"] = stateful_flows
    return result


def review_markdown(surface: dict[str, Any]) -> str:
    metadata = surface["metadata"]
    summary = metadata["summary"]
    source = metadata["source"]
    representative = next(item for item in surface["surfaces"] if item["generatorOperationId"] == "readNamespacedConfigMap")
    dynamic = [item for item in surface["surfaces"] if item["classification"] == "sdk_injected_dynamic"]
    dynamic_resources = [item for item in dynamic if {"plural", "resource_plural"}.intersection(item.get("dynamicBindings", {}))]
    dynamic_discovery = len(dynamic) - len(dynamic_resources)
    dynamic_watch = sum("watchArgument" in item for item in dynamic_resources)
    delegations = surface.get("python", {}).get("conditionDelegations", [])
    stateful_flows = surface.get("python", {}).get("statefulResourceFlows", [])
    representative_symbols = " and ".join(f"`{item['module']}.{item['class']}.{item['method']}`" for item in representative["symbols"])
    lines = [
        "# Kubernetes Python 36.0.3 SDK surface review",
        "",
        "**Classification: `investigation`**",
        "",
        "The complete transformed generator input joins statically to both generated Python API surfaces and feeds the conforming SDK mapping bound to the immutable Kubernetes API extension release. This report remains the lower-level SDK-authorship inventory rather than the mapping review surface.",
        "",
        "## Owner",
        "",
        f"- Repository: `{metadata['owner']['repository']}`",
        f"- Revision: `{metadata['owner']['revision']}`",
        f"- Distribution: `{metadata['owner']['distribution']}=={metadata['owner']['version']}`",
        "",
        "## Exact inputs",
        "",
        f"- Retained authoritative snapshot SHA-256: `{source['authoritativeSnapshot']['sha256']}`",
        f"- Retained authoritative snapshot semantic SHA-256: `{source['authoritativeSnapshot']['semanticSha256']}`",
        f"- Transformed generator input SHA-256: `{source['generatorInput']['sha256']}`",
        f"- Transformed generator input semantic SHA-256: `{source['generatorInput']['semanticSha256']}`",
        f"- Target authoritative inventory semantic SHA-256: `{source['authoritativeInventory']['semanticSha256']}`",
        "",
        "## Generated surface",
        "",
        f"- Generator operations: {metadata['surfaceCount']}",
        f"- Synchronous public methods: {summary['syncSymbols']}",
        f"- Asynchronous public methods: {summary['asyncSymbols']}",
        f"- Authoritative endpoint joins: {summary['classifications'].get('authoritative', 0)}",
        f"- SDK-injected dynamic endpoint/method records: {summary['classifications'].get('sdk_injected_dynamic', 0)} ({len(dynamic_resources)} custom-resource records and {dynamic_discovery} discovery record)",
        f"- Generator operation-ID renames: {summary['operationIdRenames']}",
        f"- Reused generator operation IDs: {summary['duplicateGeneratorOperationIds']} names across {summary['endpointsUsingDuplicateGeneratorOperationIds']} endpoints",
        f"- Joins requiring normalized trailing-slash equivalence: {summary['normalizedPathJoins']}",
        f"- Methods exposing a `watch` argument: {summary['watchCapableMethods']}",
        f"- Statically derived list-to-watch conditional projections: {summary['conditionalWatchProjections']}",
        f"- Source-verified handwritten condition delegations: {summary['conditionDelegations']}",
        f"- Source-verified stateful resource flows: {summary['statefulResourceFlows']}",
        "",
        "## Representative join",
        "",
        f"{representative_symbols} join through transformed operation `{representative['generatorOperationId']}` and `{representative['method'].upper()} {representative['path']}` to authoritative operation `{representative['authoritative']['operationId']}`.",
        "",
        "## SDK-owned review surface",
        "",
        f"The {summary['classifications'].get('authoritative', 0)} generated endpoint mappings and {summary['syncSymbols'] + summary['asyncSymbols']} generated public symbols require no handwritten method table. The generator or adjacent build step can emit them from the retained processed model and generated source verification. Reused transformed operation IDs confirm that endpoint plus owning class must remain part of SDK identity.",
        "",
        f"The focused SDK-owned semantic surface contains {len(dynamic_resources)} distinct custom-resource method records, {dynamic_discovery} API-discovery method record, {len(delegations)} source-verified handwritten condition delegation, {len(stateful_flows)} source-verified stateful resource flow, and any future wrappers or aliases absent from the processed model. These records must not collapse into one operation with combinatorial verb, scope, or subresource choices: each public SDK method determines one fixed base verb, scope, and optional subresource, while the {dynamic_watch} list methods have one explicit source-proven `watch=true` override and only resource coordinates such as group, version, and plural resource bind from method arguments. `Watch.stream` contributes no standalone Kubernetes condition; it delegates to the mapped callable and activates only a conditional argument declared by that target. The stateful flow describes one discovery-produced Resource object and seven source-verified methods; its built-in resource catalog remains deterministic generated data rather than a handwritten SDK table. A record must not emit a concrete resource requirement when application source leaves required coordinates unresolved.",
        "",
        "## Accepted validation boundary",
        "",
        "The real-profiler application proof is recorded separately from this source inventory. Literal built-in GVK selectors resolve through the extension-generated authoritative catalog, while an unmodeled CRD remains unresolved unless application source independently proves its plural resource and scope. Dynamic subresources, ResourceList fan-out, and constructor-only discovery traffic remain explicit boundaries.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--authoritative-inventory", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sdk-annotations", type=Path)
    parser.add_argument("--surface-output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    args = parser.parse_args()
    surface = build_surface(
        args.source_root,
        args.authoritative_inventory,
        args.repository,
        args.revision,
        args.version,
        args.sdk_annotations,
    )
    write_yaml(args.surface_output, surface)
    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    args.review_output.write_text(review_markdown(surface), encoding="utf-8")
    print("classification: investigation")
    print(f"generator operations: {surface['metadata']['surfaceCount']}")
    print(f"sync symbols: {surface['metadata']['summary']['syncSymbols']}")
    print(f"async symbols: {surface['metadata']['summary']['asyncSymbols']}")
    print(f"authoritative joins: {surface['metadata']['summary']['classifications'].get('authoritative', 0)}")
    print(f"dynamic operations: {surface['metadata']['summary']['classifications'].get('sdk_injected_dynamic', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
