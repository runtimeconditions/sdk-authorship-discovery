from pathlib import Path

import boto3


def upload(bucket: str, key: str, source: Path) -> str:
    resource = boto3.resource("s3")
    uploaded_object = resource.Bucket(bucket).put_object(Key=key, Body=source.read_bytes())
    return uploaded_object.key
