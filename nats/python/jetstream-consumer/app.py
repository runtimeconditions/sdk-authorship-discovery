import nats
from nats.js.api import ConsumerConfig


async def run() -> None:
    client = await nats.connect()
    manager = client.jsm()
    config = ConsumerConfig(durable_name="ORDERS_WORKER", deliver_subject="deliver.orders")
    await manager.add_consumer("ORDERS", config)
    await manager.consumer_info("ORDERS", "ORDERS_WORKER")
    await manager.consumers_info("ORDERS")
    context = client.jetstream()
    await context.subscribe_bind("ORDERS", config, "ORDERS_WORKER")
    await manager.delete_consumer("ORDERS", "ORDERS_WORKER")
