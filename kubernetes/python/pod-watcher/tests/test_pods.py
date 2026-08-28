import unittest
from unittest.mock import patch

from kubernetes_pod_watcher import pod_events


class PodWatcherTest(unittest.TestCase):
    @patch("kubernetes_pod_watcher.pods.watch.Watch")
    @patch("kubernetes_pod_watcher.pods.client.CoreV1Api")
    @patch("kubernetes_pod_watcher.pods.config.load_incluster_config")
    def test_delegates_the_generated_list_method_to_watch(self, load_incluster_config, core_v1_api, watch_class) -> None:
        api = core_v1_api.return_value
        events = iter([{"type": "ADDED"}])
        watch_class.return_value.stream.return_value = events

        self.assertIs(pod_events("payments"), events)
        load_incluster_config.assert_called_once_with()
        watch_class.return_value.stream.assert_called_once_with(api.list_namespaced_pod, namespace="payments", timeout_seconds=30)


if __name__ == "__main__":
    unittest.main()
