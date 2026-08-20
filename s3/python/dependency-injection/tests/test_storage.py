import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.stub import Stubber

from s3_dependency_injection import build_writer


class ObjectWriterTest(unittest.TestCase):
    def test_uploads_with_injected_client(self) -> None:
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "event.json")
            source.write_bytes(b"payload")
            with Stubber(client) as stubber:
                stubber.add_response(
                    "put_object",
                    {"ETag": '"test-etag"'},
                    {"Bucket": "example-bucket", "Key": "event.json", "Body": b"payload"},
                )
                with patch("s3_dependency_injection.composition.boto3.client", return_value=client):
                    writer = build_writer()
                    self.assertEqual(writer.upload("example-bucket", "event.json", source), '"test-etag"')


if __name__ == "__main__":
    unittest.main()
