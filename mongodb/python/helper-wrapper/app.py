import os
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


def orders_collection(client: MongoClient) -> Collection:
    return client["commerce"]["orders"]


def create_order(collection: Collection, order: dict[str, Any]) -> None:
    collection.insert_one(order)


def run(uri: str) -> None:
    client = MongoClient(uri)
    try:
        orders = orders_collection(client)
        create_order(orders, {"status": "pending", "total": 1250})
    finally:
        client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"])
