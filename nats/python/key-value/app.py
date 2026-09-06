import nats
from nats.js.api import KeyValueConfig


async def run() -> None:
    client = await nats.connect()
    jetstream = client.jetstream()
    created = await jetstream.create_key_value(KeyValueConfig(bucket="SESSIONS"))
    await created.put("session", b"value")
    await created.get("session")
    await created.watch("session")
    await created.status()
    existing = await jetstream.key_value("CACHE")
    await existing.create("key", b"value")
    await existing.update("key", b"updated", 1)
    await existing.delete("key")
    await existing.purge("key")
    await existing.purge_deletes()
    await existing.keys()
    await existing.history("key")
    await existing.watchall()
    await jetstream.delete_key_value("CACHE")
