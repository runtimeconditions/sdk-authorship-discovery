from typing import Any

from kubernetes import client, dynamic


def list_ingress_routes(namespace: str) -> Any:
    resource = dynamic.DynamicClient(client.ApiClient()).resources.get(api_version="apps.example.com/v1", kind="IngressRoute")
    return resource.get(namespace=namespace)
