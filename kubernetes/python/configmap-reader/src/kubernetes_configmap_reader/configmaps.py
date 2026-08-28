from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


def configure_client() -> None:
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()


def read_config_map(name: str, namespace: str) -> dict[str, str]:
    configure_client()
    response = client.CoreV1Api().read_namespaced_config_map(name=name, namespace=namespace)
    return dict(response.data or {})
