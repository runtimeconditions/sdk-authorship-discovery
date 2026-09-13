import os
from io import BytesIO

from gridfs import GridFSBucket
from pymongo import MongoClient


def run(uri: str) -> None:
    client = MongoClient(uri)
    try:
        bucket = GridFSBucket(client["media"], bucket_name="assets")
        file_id = bucket.upload_from_stream("logo.svg", BytesIO(b"<svg></svg>"))
        downloaded = BytesIO()
        bucket.download_to_stream(file_id, downloaded)
        bucket.delete(file_id)
    finally:
        client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"])
