import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.stub import Stubber

from s3_dynamic_service import upload


class UploadTest(unittest.TestCase):
    def test_uploads_when_runtime_service_is_s3(self) -> None:
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
                with patch("s3_dynamic_service.storage.boto3.client", return_value=client) as create_client:
                    self.assertEqual(upload("s3", "example-bucket", "event.json", source), '"test-etag"')
        create_client.assert_called_once_with("s3")


if __name__ == "__main__":
    unittest.main()

