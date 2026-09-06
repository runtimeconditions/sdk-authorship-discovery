import nats
from nats.js.api import StreamConfig


async def run() -> None:
    client = await nats.connect()
    jetstream = client.jetstream()
    config = StreamConfig(name="ORDERS", subjects=["orders.*"])
    await jetstream.add_stream(config)
    await jetstream.update_stream(name="ORDERS", subjects=["orders.*", "returns.*"])
    await jetstream.stream_info("ORDERS")
    await jetstream.publish("orders.created", b"created")
    await jetstream.publish_async("orders.updated", b"updated")
    await jetstream.delete_stream("ORDERS")
