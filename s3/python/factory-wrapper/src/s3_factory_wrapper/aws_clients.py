from typing import Any

import boto3


def object_store_client() -> Any:
    return boto3.client("s3")

