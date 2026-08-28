from collections.abc import Iterator
from typing import Any

from kubernetes import client, config, watch
from kubernetes.config.config_exception import ConfigException


def configure_client() -> None:
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()


def pod_events(namespace: str) -> Iterator[dict[str, Any]]:
    configure_client()
    api = client.CoreV1Api()
    watcher = watch.Watch()
    return watcher.stream(api.list_namespaced_pod, namespace=namespace, timeout_seconds=30)
