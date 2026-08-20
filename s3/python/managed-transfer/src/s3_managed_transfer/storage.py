from pathlib import Path

import boto3


def upload(bucket: str, key: str, source: Path) -> None:
    client = boto3.client("s3")
    client.upload_file(str(source), bucket, key)
