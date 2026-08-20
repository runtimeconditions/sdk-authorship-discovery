"""Dependency-injected boto3 S3 client scenario."""

from .composition import build_writer
from .storage import ObjectWriter

__all__ = ["ObjectWriter", "build_writer"]

