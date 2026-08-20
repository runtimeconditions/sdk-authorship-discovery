import argparse
from pathlib import Path

from .storage import upload


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file with the boto3 S3 resource API")
    parser.add_argument("bucket")
    parser.add_argument("key")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(upload(args.bucket, args.key, args.source))


if __name__ == "__main__":
    main()

