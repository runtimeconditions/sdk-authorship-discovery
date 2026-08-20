from pathlib import Path
from typing import Any

import boto3


def client_for(service_name: str) -> Any:
    return boto3.client(service_name)


def upload(service_name: str, bucket: str, key: str, source: Path) -> str:
    client = client_for(service_name)
    response = client.put_object(Bucket=bucket, Key=key, Body=source.read_bytes())
    return response["ETag"]

