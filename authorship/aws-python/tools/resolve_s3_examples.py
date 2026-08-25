#!/usr/bin/env python3
"""Resolve representative boto3 S3 surfaces through nested owner mappings."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from serialization import read_document, render_yaml


def one(values: list[dict[str, Any]], description: str) -> dict[str, Any]:
    if len(values) != 1:
        raise ValueError(f"expected one {description}, found {len(values)}")
    return values[0]


def operation(mapping: dict[str, Any], name: str) -> dict[str, Any]:
    return one([item for item in mapping["operations"] if item["name"] == name], f"operation {name}")


def resource(mapping: dict[str, Any], name: str) -> dict[str, Any]:
    return one([item for item in mapping["python"]["resources"] if item["name"] == name], f"resource {name}")


def condition_summary(botocore: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return operation(botocore, name)["conditions"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boto3", type=Path, required=True)
    parser.add_argument("--botocore", type=Path, required=True)
    parser.add_argument("--s3transfer", type=Path, required=True)
    args = parser.parse_args()

    boto3 = read_document(args.boto3)
    botocore = read_document(args.botocore)
    transfer = read_document(args.s3transfer)

    client_method = one(
        [item for item in botocore["python"]["client"]["methods"] if item["method"] == "put_object"],
        "botocore put_object method",
    )
    direct_operation = client_method["operation"]

    bucket = resource(boto3, "Bucket")
    resource_action = one(
        [item for item in bucket["actions"] if item["method"] == "put_object"],
        "Bucket.put_object action",
    )
    resource_operation = resource_action["operationRef"]["operation"]

    resource_waiter = one(
        [item for item in bucket["waiters"] if item["method"] == "wait_until_exists"],
        "Bucket.wait_until_exists waiter",
    )
    waiter_name = resource_waiter["waiterRef"]["waiter"]
    waiter = one(
        [
            item
            for item in botocore["python"]["client"]["waiterFactory"]["items"]
            if item["name"] == waiter_name
        ],
        f"botocore waiter {waiter_name}",
    )

    upload_wrapper = one(
        [item for item in bucket["wrappers"] if item["method"] == "upload_file"],
        "Bucket.upload_file wrapper",
    )
    call_name = upload_wrapper["callRef"]["call"]
    transfer_call = one(
        [item for item in transfer["python"]["calls"] if item["name"] == call_name],
        f"s3transfer call {call_name}",
    )
    upload_paths = []
    for implementation in transfer_call["implementations"]:
        paths = implementation.get("executionPaths")
        if paths:
            for path in paths:
                names = [item["operationRef"]["operation"] for item in path["operationRefs"]]
                upload_paths.append(
                    {
                        "implementation": implementation["name"],
                        "path": path["name"],
                        "operations": names,
                        "conditionKinds": sorted(
                            {
                                condition["kind"]
                                for name in names
                                for condition in condition_summary(botocore, name)
                            }
                        ),
                    }
                )
        else:
            names = [item["operationRef"]["operation"] for item in implementation["operationRefs"]]
            upload_paths.append(
                {
                    "implementation": implementation["name"],
                    "path": "single-path",
                    "operations": names,
                    "conditionKinds": sorted(
                        {
                            condition["kind"]
                            for name in names
                            for condition in condition_summary(botocore, name)
                        }
                    ),
                }
            )

    result = {
        "directClient": {
            "chain": ["boto3.client('s3')", "botocore.client.s3.put_object", direct_operation],
            "conditions": condition_summary(botocore, direct_operation),
        },
        "resourceAction": {
            "chain": ["boto3.resource('s3')", "ServiceResource.Bucket", "Bucket.put_object", resource_operation],
            "conditions": condition_summary(botocore, resource_operation),
        },
        "resourceWaiter": {
            "chain": [
                "boto3.resource('s3')",
                "ServiceResource.Bucket",
                "Bucket.wait_until_exists",
                f"botocore waiter {waiter_name}",
                waiter["operation"],
            ],
            "conditions": condition_summary(botocore, waiter["operation"]),
        },
        "managedTransfer": {
            "chain": [
                "boto3.resource('s3')",
                "ServiceResource.Bucket",
                "Bucket.upload_file",
                f"s3transfer call {call_name}",
                "execution path selected by transfer implementation",
                "botocore operations",
            ],
            "executionPaths": upload_paths,
        },
    }
    print(render_yaml(result), end="")


if __name__ == "__main__":
    main()
