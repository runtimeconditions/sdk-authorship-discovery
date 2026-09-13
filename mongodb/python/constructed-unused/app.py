import os

from pymongo import MongoClient


def build_client(uri: str) -> MongoClient:
    return MongoClient(uri, connect=False)


def run(uri: str) -> None:
    client = build_client(uri)
    client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"])
