import os

from pymongo import MongoClient


def run(analytics_uri: str, operational_uri: str) -> None:
    analytics = MongoClient(analytics_uri)
    operational = MongoClient(operational_uri)
    try:
        analytics["warehouse"]["events"].insert_one({"type": "order.created"})
        operational["commerce"]["orders"].find_one({"status": "pending"})
    finally:
        analytics.close()
        operational.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_ANALYTICS_URI"], os.environ["MONGODB_OPERATIONAL_URI"])
