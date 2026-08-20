from pathlib import Path
from typing import Any, Protocol


class PutObjectClient(Protocol):
    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...


class ObjectWriter:
    def __init__(self, client: PutObjectClient) -> None:
        self._client = client

    def upload(self, bucket: str, key: str, source: Path) -> str:
        response = self._client.put_object(Bucket=bucket, Key=key, Body=source.read_bytes())
        return response["ETag"]

