from pathlib import Path

import boto3

from .settings import S3_SERVICE_NAME


def upload(bucket: str, key: str, source: Path, profile: str | None = None) -> str:
    session = boto3.Session(profile_name=profile)
    client = session.client(S3_SERVICE_NAME)
    response = client.put_object(Bucket=bucket, Key=key, Body=source.read_bytes())
    return response["ETag"]

