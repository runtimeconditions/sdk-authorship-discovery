import os
from typing import Any

from pymongo import MongoClient
from pymongo.client_session import ClientSession


def transfer(client: MongoClient, source: str, destination: str, amount: int) -> None:
    accounts = client["billing"]["accounts"]
    ledger = client["billing"]["ledger"]

    def apply(session: ClientSession) -> Any:
        accounts.update_one({"account": source}, {"$inc": {"balance": -amount}}, session=session)
        accounts.update_one({"account": destination}, {"$inc": {"balance": amount}}, session=session)
        return ledger.insert_one({"source": source, "destination": destination, "amount": amount}, session=session)

    with client.start_session() as session:
        session.with_transaction(apply)


def run(uri: str) -> None:
    client = MongoClient(uri)
    try:
        transfer(client, "checking", "savings", 250)
    finally:
        client.close()


if __name__ == "__main__":
    run(os.environ["MONGODB_URI"])
