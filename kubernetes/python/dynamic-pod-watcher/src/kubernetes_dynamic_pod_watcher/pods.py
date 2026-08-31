from collections.abc import Iterator
from typing import Any

from kubernetes import client, dynamic


def pod_events(namespace: str) -> Iterator[dict[str, Any]]:
    resource = dynamic.DynamicClient(client.ApiClient()).resources.get(api_version="v1", kind="Pod")
    return resource.watch(namespace=namespace, timeout=30)
