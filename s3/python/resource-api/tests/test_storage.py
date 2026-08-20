import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.stub import Stubber

from s3_resource_api import upload


class UploadTest(unittest.TestCase):
    def test_uploads_with_resource_api(self) -> None:
        resource = boto3.resource(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "event.json")
            source.write_bytes(b"payload")
            with Stubber(resource.meta.client) as stubber:
                stubber.add_response(
                    "put_object",
                    {"ETag": '"test-etag"'},
                    {"Bucket": "example-bucket", "Key": "event.json", "Body": b"payload"},
                )
                with patch("s3_resource_api.storage.boto3.resource", return_value=resource):
                    self.assertEqual(upload("example-bucket", "event.json", source), "event.json")


if __name__ == "__main__":
    unittest.main()
