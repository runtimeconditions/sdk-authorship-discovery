import argparse
from pathlib import Path

from .storage import upload


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file with boto3's managed S3 transfer")
    parser.add_argument("bucket")
    parser.add_argument("key")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    upload(args.bucket, args.key, args.source)


if __name__ == "__main__":
    main()
