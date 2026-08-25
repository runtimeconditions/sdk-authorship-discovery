#!/usr/bin/env python3
"""Supplementary runtime check for packaged AWS Python SDK public surfaces."""

from __future__ import annotations

import argparse
import importlib
import inspect
from pathlib import Path
from typing import Any

from serialization import read_document


class OptionalDependencyMissing(Exception):
    pass


def resolve_symbol(symbol: str) -> Any:
    parts = symbol.split(".")
    for boundary in range(len(parts), 0, -1):
        try:
            value: Any = importlib.import_module(".".join(parts[:boundary]))
        except ModuleNotFoundError as error:
            candidate = ".".join(parts[:boundary])
            if error.name and not candidate.startswith(error.name):
                raise OptionalDependencyMissing(error.name) from error
            continue
        for part in parts[boundary:]:
            value = getattr(value, part)
        return value
    raise ValueError(f"cannot resolve symbol: {symbol}")


def validate_binding(symbol: str, function: Any, bindings: dict[str, Any]) -> None:
    parameters = list(inspect.signature(function).parameters)
    if parameters and parameters[0] in {"self", "cls"}:
        parameters = parameters[1:]
    for logical_name, binding in bindings.items():
        position = binding["position"]
        keyword = binding["keyword"]
        if position >= len(parameters) or parameters[position] != keyword:
            raise ValueError(
                f"{symbol}: {logical_name} expected {keyword!r} at {position}, "
                f"runtime signature is {parameters}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boto3", type=Path, required=True)
    parser.add_argument("--botocore", type=Path, required=True)
    parser.add_argument("--s3transfer", type=Path, required=True)
    args = parser.parse_args()

    boto3_mapping = read_document(args.boto3)
    botocore_mapping = read_document(args.botocore)
    transfer_mapping = read_document(args.s3transfer)

    import boto3

    connection = {
        "region_name": "us-east-1",
        "endpoint_url": "https://s3.invalid",
        "aws_access_key_id": "runtimeconditions-validation",
        "aws_secret_access_key": "runtimeconditions-validation",
    }
    client = boto3.client("s3", **connection)
    client_model = botocore_mapping["python"]["client"]
    for item in client_model["methods"]:
        if not hasattr(client, item["method"]):
            raise ValueError(f"runtime S3 client is missing {item['method']}")
    for item in client_model["paginatorFactory"]["items"]:
        client.get_paginator(item["name"])
    for item in client_model["waiterFactory"]["items"]:
        client.get_waiter(item["name"])

    service = boto3.resource("s3", **connection)
    resource_models = [boto3_mapping["python"]["serviceResource"]]
    resource_models.extend(boto3_mapping["python"]["resources"])
    checked_members = 0
    for item in resource_models:
        if item["name"] == "ServiceResource":
            instance = service
        else:
            constructor = getattr(service, item["name"])
            identifiers = [
                1 if identifier.get("type") == "integer" else "runtimeconditions-validation"
                for identifier in item["identifiers"]
            ]
            instance = constructor(*identifiers)
        cls = type(instance)
        for field, name_field in (
            ("actions", "method"),
            ("waiters", "method"),
            ("relations", "member"),
            ("collections", "member"),
            ("wrappers", "method"),
        ):
            for member in item[field]:
                member_name = member[name_field]
                if not hasattr(cls, member_name):
                    raise ValueError(f"runtime {item['name']} is missing {field} member {member_name}")
                checked_members += 1

    boto3_transfer_wrappers = 0
    for wrapper in boto3_mapping["python"]["transferClassWrappers"]:
        function = resolve_symbol(wrapper["symbol"])
        validate_binding(wrapper["symbol"], function, wrapper["arguments"])
        context = wrapper.get("receiverContext")
        if context:
            constructor = resolve_symbol(context["constructor"])
            validate_binding(
                context["constructor"], constructor.__init__, context.get("arguments", {})
            )
        boto3_transfer_wrappers += 1

    transfer_entrypoints = 0
    skipped_entrypoints: list[str] = []
    for call in transfer_mapping["python"]["calls"]:
        for entrypoint in call["entrypoints"]:
            try:
                function = resolve_symbol(entrypoint["symbol"])
            except OptionalDependencyMissing as error:
                if not entrypoint["symbol"].startswith("s3transfer.crt."):
                    raise
                skipped_entrypoints.append(f"{entrypoint['symbol']} ({error})")
                continue
            validate_binding(entrypoint["symbol"], function, entrypoint["arguments"])
            context = entrypoint.get("receiverContext")
            if context:
                constructor = resolve_symbol(context["constructor"])
                validate_binding(
                    context["constructor"], constructor.__init__, context.get("arguments", {})
                )
            transfer_entrypoints += 1

    print("packaged SDK runtime surface validation passed")
    print(f"  client methods: {len(client_model['methods'])}")
    print(f"  paginators: {len(client_model['paginatorFactory']['items'])}")
    print(f"  waiters: {len(client_model['waiterFactory']['items'])}")
    print(f"  resource classes: {len(resource_models)}")
    print(f"  resource members: {checked_members}")
    print(f"  boto3 transfer-class wrappers: {boto3_transfer_wrappers}")
    print(f"  s3transfer entrypoints: {transfer_entrypoints}")
    print(f"  optional entrypoints source-validated only: {len(skipped_entrypoints)}")
    for entrypoint in skipped_entrypoints:
        print(f"    {entrypoint}")


if __name__ == "__main__":
    main()
