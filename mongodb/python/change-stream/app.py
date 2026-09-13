import os

from pymongo import MongoClient


def run(uri: str) -> None:
    client = MongoClient(uri)
    try:
        stock = client["inventory"]["stock"]
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}]
        with stock.watch(pipeline, full_document="updateLookup") as changes:
            for change in changes:
                print(change)
    finally:
        client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"])
