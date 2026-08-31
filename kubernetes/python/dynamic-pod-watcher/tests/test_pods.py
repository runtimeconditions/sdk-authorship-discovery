import unittest
from unittest.mock import patch

from kubernetes_dynamic_pod_watcher import pod_events


class DynamicPodWatcherTest(unittest.TestCase):
    @patch("kubernetes_dynamic_pod_watcher.pods.dynamic.DynamicClient")
    @patch("kubernetes_dynamic_pod_watcher.pods.client.ApiClient")
    def test_watches_the_discovery_created_resource(self, api_client, dynamic_client) -> None:
        events = iter([{"type": "ADDED"}])
        resource = dynamic_client.return_value.resources.get.return_value
        resource.watch.return_value = events

        self.assertIs(pod_events("payments"), events)
        dynamic_client.return_value.resources.get.assert_called_once_with(api_version="v1", kind="Pod")
        resource.watch.assert_called_once_with(namespace="payments", timeout=30)


if __name__ == "__main__":
    unittest.main()
