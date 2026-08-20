import argparse
from pathlib import Path

from .composition import build_writer


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a file through a dependency-injected boto3 S3 client")
    parser.add_argument("bucket")
    parser.add_argument("key")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(build_writer().upload(args.bucket, args.key, args.source))


if __name__ == "__main__":
    main()

