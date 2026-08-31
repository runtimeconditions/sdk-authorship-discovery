import unittest
from unittest.mock import patch

from kubernetes_dynamic_configmaps import config_map_lifecycle


class DynamicConfigMapTest(unittest.TestCase):
    @patch("kubernetes_dynamic_configmaps.configmaps.dynamic.DynamicClient")
    @patch("kubernetes_dynamic_configmaps.configmaps.client.ApiClient")
    @patch("kubernetes_dynamic_configmaps.configmaps.config.load_incluster_config")
    def test_uses_the_discovery_created_resource(self, load_incluster_config, api_client, dynamic_client) -> None:
        resource = dynamic_client.return_value.resources.get.return_value
        resource.create.return_value = "created"
        resource.get.side_effect = ["current", "listed"]
        resource.patch.return_value = "patched"
        resource.delete.return_value = "deleted"
        body = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "settings"}}

        result = config_map_lifecycle("settings", "payments", body)

        self.assertEqual(result, ("created", "current", "listed", "patched", "deleted"))
        dynamic_client.return_value.resources.get.assert_called_once_with(api_version="v1", kind="ConfigMap")
        resource.create.assert_called_once_with(body=body, namespace="payments")
        resource.get.assert_any_call(name="settings", namespace="payments")
        resource.get.assert_any_call(namespace="payments")


if __name__ == "__main__":
    unittest.main()
