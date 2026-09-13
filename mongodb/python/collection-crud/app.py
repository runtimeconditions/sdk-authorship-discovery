import os

from pymongo import MongoClient


def run(uri: str) -> None:
    client = MongoClient(uri)
    try:
        orders = client["commerce"]["orders"]
        result = orders.insert_one({"status": "pending", "total": 1250})
        orders.find_one({"_id": result.inserted_id})
        orders.update_one({"_id": result.inserted_id}, {"$set": {"status": "paid"}})
        orders.delete_one({"_id": result.inserted_id})
    finally:
        client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"])
