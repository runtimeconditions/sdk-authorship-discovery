import os

from pymongo import MongoClient


def run(uri: str, database_name: str, collection_name: str) -> None:
    client = MongoClient(uri)
    try:
        collection = client.get_database(database_name).get_collection(collection_name)
        collection.find_one({"enabled": True})
    finally:
        client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"], os.environ["MONGODB_DATABASE"], os.environ["MONGODB_COLLECTION"])
