from typing import Any

from kubernetes import client, config, dynamic
from kubernetes.config.config_exception import ConfigException


def configure_client() -> None:
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()


def config_map_lifecycle(name: str, namespace: str, body: dict[str, Any]) -> tuple[Any, Any, Any, Any, Any]:
    configure_client()
    resource = dynamic.DynamicClient(client.ApiClient()).resources.get(api_version="v1", kind="ConfigMap")
    created = resource.create(body=body, namespace=namespace)
    current = resource.get(name=name, namespace=namespace)
    listed = resource.get(namespace=namespace)
    patched = resource.patch(body=body, name=name, namespace=namespace)
    deleted = resource.delete(name=name, namespace=namespace)
    return created, current, listed, patched, deleted
