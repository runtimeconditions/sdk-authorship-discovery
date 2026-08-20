from pathlib import Path

from .aws_clients import object_store_client


def upload(bucket: str, key: str, source: Path) -> str:
    client = object_store_client()
    response = client.put_object(Bucket=bucket, Key=key, Body=source.read_bytes())
    return response["ETag"]

