import nats
from nats.js.api import ConsumerConfig, KeyValueConfig, StreamConfig


async def run() -> None:
    primary = await nats.connect()
    await primary.publish("events.created", b"created")
    await primary.subscribe("events.created")
    await primary.request("events.lookup", b"lookup")

    jetstream = primary.jetstream()
    stream = StreamConfig(name="ORDERS", subjects=["orders.*"])
    await jetstream.add_stream(stream)
    await jetstream.update_stream(name="ORDERS", subjects=["orders.*", "returns.*"])
    await jetstream.stream_info("ORDERS")
    await jetstream.publish("orders.created", b"created")

    consumer = ConsumerConfig(name="ORDERS_WORKER", deliver_subject="deliver.orders")
    await jetstream.add_consumer("ORDERS", consumer)
    await jetstream.consumer_info("ORDERS", "ORDERS_WORKER")
    await jetstream.subscribe_bind("ORDERS", consumer, "ORDERS_WORKER")
    await jetstream.delete_consumer("ORDERS", "ORDERS_WORKER")
    await jetstream.delete_stream("ORDERS")

    key_value = await jetstream.create_key_value(KeyValueConfig(bucket="SESSIONS"))
    await key_value.get("session")
    await key_value.put("session", b"value")
    await key_value.watch("session")
    await key_value.status()
    await jetstream.delete_key_value("SESSIONS")

    object_store = await jetstream.create_object_store("ASSETS")
    await object_store.get("logo")
    await object_store.put("logo", b"image")
    await object_store.watch()
    await object_store.status()
    await jetstream.delete_object_store("ASSETS")

    secondary = nats.NATS()
    await secondary.connect()
    await secondary.publish("audit.created", b"audit")
