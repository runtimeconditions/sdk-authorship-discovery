import nats


async def run() -> None:
    client = await nats.connect()
    await client.publish("events.created", b"created")
    await client.subscribe("events.created")
    await client.request("events.lookup", b"lookup")
