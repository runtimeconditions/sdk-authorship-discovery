import argparse
from pathlib import Path

from .storage import upload


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file with a session-created boto3 S3 client")
    parser.add_argument("bucket")
    parser.add_argument("key")
    parser.add_argument("source", type=Path)
    parser.add_argument("--profile")
    args = parser.parse_args()
    print(upload(args.bucket, args.key, args.source, args.profile))


if __name__ == "__main__":
    main()

