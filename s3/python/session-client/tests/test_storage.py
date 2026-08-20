import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import boto3
from botocore.stub import Stubber

from s3_session_client import upload


class UploadTest(unittest.TestCase):
    def test_uploads_with_session_client(self) -> None:
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        session = Mock()
        session.client.return_value = client
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "event.json")
            source.write_bytes(b"payload")
            with Stubber(client) as stubber:
                stubber.add_response(
                    "put_object",
                    {"ETag": '"test-etag"'},
                    {"Bucket": "example-bucket", "Key": "event.json", "Body": b"payload"},
                )
                with patch("s3_session_client.storage.boto3.Session", return_value=session):
                    self.assertEqual(upload("example-bucket", "event.json", source, "dev"), '"test-etag"')
        session.client.assert_called_once_with("s3")


if __name__ == "__main__":
    unittest.main()

