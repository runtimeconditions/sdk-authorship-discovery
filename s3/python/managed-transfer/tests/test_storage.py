import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.stub import ANY, Stubber

from s3_managed_transfer import upload


class UploadTest(unittest.TestCase):
    def test_uploads_through_s3transfer(self) -> None:
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
            aws_session_token="testing",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "event.json")
            source.write_bytes(b"payload")
            with Stubber(client) as stubber:
                stubber.add_response(
                    "put_object",
                    {"ETag": '"test-etag"'},
                    {
                        "Bucket": "example-bucket",
                        "Key": "event.json",
                        "Body": ANY,
                        "ChecksumAlgorithm": "CRC32",
                    },
                )
                with patch("s3_managed_transfer.storage.boto3.client", return_value=client):
                    self.assertIsNone(upload("example-bucket", "event.json", source))


if __name__ == "__main__":
    unittest.main()
