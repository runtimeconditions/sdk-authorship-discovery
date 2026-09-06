import nats
from nats.js.api import ObjectMeta


async def run() -> None:
    client = await nats.connect()
    jetstream = client.jetstream()
    created = await jetstream.create_object_store("ASSETS")
    await created.put("logo", b"image")
    await created.get("logo")
    await created.get_info("logo")
    await created.list()
    await created.update_meta("logo", ObjectMeta(name="logo"))
    await created.delete("logo")
    await created.watch()
    await created.status()
    existing = await jetstream.object_store("ARCHIVE")
    await existing.get("record")
    await jetstream.delete_object_store("ARCHIVE")
