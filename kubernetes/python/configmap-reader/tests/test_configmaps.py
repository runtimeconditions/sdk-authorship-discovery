import unittest
from types import SimpleNamespace
from unittest.mock import patch

from kubernetes.config.config_exception import ConfigException

from kubernetes_configmap_reader import read_config_map


class ConfigMapTest(unittest.TestCase):
    @patch("kubernetes_configmap_reader.configmaps.client.CoreV1Api")
    @patch("kubernetes_configmap_reader.configmaps.config.load_kube_config")
    @patch("kubernetes_configmap_reader.configmaps.config.load_incluster_config")
    def test_reads_config_map_with_generated_client(self, load_incluster_config, load_kube_config, core_v1_api) -> None:
        api = core_v1_api.return_value
        api.read_namespaced_config_map.return_value = SimpleNamespace(data={"mode": "production"})

        self.assertEqual(read_config_map("application-settings", "payments"), {"mode": "production"})
        load_incluster_config.assert_called_once_with()
        load_kube_config.assert_not_called()
        api.read_namespaced_config_map.assert_called_once_with(name="application-settings", namespace="payments")

    @patch("kubernetes_configmap_reader.configmaps.client.CoreV1Api")
    @patch("kubernetes_configmap_reader.configmaps.config.load_kube_config")
    @patch("kubernetes_configmap_reader.configmaps.config.load_incluster_config", side_effect=ConfigException("not in a cluster"))
    def test_falls_back_to_local_kubeconfig(self, load_incluster_config, load_kube_config, core_v1_api) -> None:
        core_v1_api.return_value.read_namespaced_config_map.return_value = SimpleNamespace(data=None)

        self.assertEqual(read_config_map("application-settings", "default"), {})
        load_incluster_config.assert_called_once_with()
        load_kube_config.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
