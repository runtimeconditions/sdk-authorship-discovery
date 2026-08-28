import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
WORKSPACE = ROOT.parents[2]
sys.path.insert(0, str(TOOLS))

from resolve_application import profile_for_sources  # noqa: E402
from serialization import read_document  # noqa: E402


class KubernetesApplicationResolutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping = read_document(ROOT / "mappings/runtimeconditions.sdk-mapping.yaml")
        cls.extension = read_document(WORKSPACE / "extensions/kubernetes-api/releases/0.1.0/runtimeconditions.extension.yaml")

    def profile(self, source_text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.py"
            source.write_text(source_text, encoding="utf-8")
            return profile_for_sources(self.mapping, self.extension, [source], "fixture", "https://example.test/fixture")

    def test_resolves_unchanged_config_map_reader(self):
        source = WORKSPACE / "sdk/kubernetes/python/configmap-reader/src/kubernetes_configmap_reader/configmaps.py"
        profile = profile_for_sources(self.mapping, self.extension, [source], "kubernetes-configmap-reader", "https://github.com/runtimeconditions/sdk-authorship-discovery/tree/main/kubernetes/python/configmap-reader")
        self.assertEqual(profile["extensions"], [self.extension["metadata"]["id"]])
        self.assertEqual(profile["conditions"], [{"kind": "kubernetes", "interface": {"type": "api", "operations": [{"verb": "get", "apiGroup": "", "apiVersion": "v1", "resource": "configmaps", "scope": "namespaced"}]}}])

    def test_client_construction_and_configuration_emit_nothing(self):
        profile = self.profile("from kubernetes import client, config\nconfig.load_kube_config()\nclient.CoreV1Api()\n")
        self.assertEqual(profile["extensions"], [])
        self.assertEqual(profile["conditions"], [])

    def test_dynamic_literal_coordinates_resolve_one_fixed_operation(self):
        profile = self.profile("from kubernetes import client\nclient.CustomObjectsApi().create_namespaced_custom_object('widgets.example.io', 'v1alpha1', 'payments', 'widgets', {})\n")
        self.assertEqual(profile["conditions"][0]["interface"]["operations"], [{"verb": "create", "scope": "namespaced", "apiGroup": "widgets.example.io", "apiVersion": "v1alpha1", "resource": "widgets"}])

    def test_unresolved_dynamic_coordinates_emit_nothing(self):
        profile = self.profile("from kubernetes import client\ndef create(group):\n    client.CustomObjectsApi().create_cluster_custom_object(group, 'v1', 'widgets', {})\n")
        self.assertEqual(profile["conditions"], [])


if __name__ == "__main__":
    unittest.main()
