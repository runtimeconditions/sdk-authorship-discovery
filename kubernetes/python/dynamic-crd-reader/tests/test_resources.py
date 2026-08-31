import unittest
from unittest.mock import patch

from kubernetes_dynamic_crd_reader import list_ingress_routes


class DynamicCustomResourceTest(unittest.TestCase):
    @patch("kubernetes_dynamic_crd_reader.resources.dynamic.DynamicClient")
    @patch("kubernetes_dynamic_crd_reader.resources.client.ApiClient")
    def test_uses_live_discovery_for_the_custom_resource(self, api_client, dynamic_client) -> None:
        resource = dynamic_client.return_value.resources.get.return_value
        resource.get.return_value = ["ingress-route"]

        self.assertEqual(list_ingress_routes("payments"), ["ingress-route"])
        dynamic_client.return_value.resources.get.assert_called_once_with(api_version="apps.example.com/v1", kind="IngressRoute")
        resource.get.assert_called_once_with(namespace="payments")


if __name__ == "__main__":
    unittest.main()
