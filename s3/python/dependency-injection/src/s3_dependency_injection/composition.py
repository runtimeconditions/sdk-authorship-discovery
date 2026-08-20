import boto3

from .storage import ObjectWriter


def build_writer() -> ObjectWriter:
    return ObjectWriter(boto3.client("s3"))

