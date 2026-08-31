import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
WORKSPACE = ROOT.parents[2]
sys.path.insert(0, str(TOOLS))

from generate_mapping import build_mapping  # noqa: E402
from serialization import read_document  # noqa: E402


class KubernetesPythonMappingGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surface = read_document(ROOT / "results/python-36.0.3-surface.yaml")
        cls.service_mapping = read_document(WORKSPACE / "extensions/kubernetes-api/model/generated/kubernetes-service-mapping.yaml")
        cls.extension = read_document(WORKSPACE / "extensions/kubernetes-api/releases/0.1.0/runtimeconditions.extension.yaml")
        cls.mapping = build_mapping(cls.surface, cls.service_mapping, cls.extension)

    def test_complete_surface_maps_to_exact_extension(self):
        self.assertEqual(self.mapping["metadata"]["operationCount"], 944)
        self.assertEqual(self.mapping["metadata"]["publicSymbolCount"], 1875)
        self.assertEqual(self.mapping["metadata"]["summary"]["operationRecords"], {"authoritative": 908, "dynamic": 28, "stateful": 8})
        self.assertEqual(self.mapping["metadata"]["summary"]["conditionDelegations"], 1)
        self.assertEqual(self.mapping["metadata"]["summary"]["statefulResourceFlows"], 1)
        self.assertEqual(self.mapping["metadata"]["summary"]["statefulResourceCatalogEntries"], 95)
        self.assertEqual(self.mapping["extension"]["semanticSha256"], self.extension["metadata"]["semanticSha256"])

    def test_config_map_method_references_authoritative_condition(self):
        method = next(item for item in self.mapping["python"]["apiMethods"] if item["symbols"][0]["method"] == "read_namespaced_config_map")
        self.assertEqual(method["operationRef"]["operation"], "readCoreV1NamespacedConfigMap")
        operation = next(item for item in self.mapping["operations"] if item["name"] == method["operationRef"]["operation"])
        self.assertEqual(operation["conditions"][0]["operation"], {"verb": "get", "apiGroup": "", "apiVersion": "v1", "resource": "configmaps", "scope": "namespaced"})

    def test_dynamic_methods_are_distinct_scalar_templates(self):
        dynamic = [item for item in self.mapping["operations"] if "conditionTemplate" in item and "endpoint" in item]
        self.assertEqual(len(dynamic), 28)
        self.assertEqual(len({item["name"] for item in dynamic}), 28)
        create = next(item for item in dynamic if item["name"] == "CustomObjectsApi.create_namespaced_custom_object")
        self.assertEqual(create["conditionTemplate"]["operation"], {"verb": "create", "scope": "namespaced"})
        self.assertEqual(create["conditionTemplate"]["operationBindings"]["resource"], {"argument": "plural", "position": 3, "keyword": "plural"})
        for item in dynamic:
            operation = item["conditionTemplate"]["operation"]
            self.assertIsInstance(operation.get("verb", operation.get("method")), str)
            self.assertNotIsInstance(operation.get("scope"), list)
            self.assertNotIsInstance(operation.get("subresource"), list)

    def test_dynamic_client_flow_uses_distinct_state_bound_operations(self):
        flows = self.mapping["python"]["statefulResourceFlows"]
        self.assertEqual(len(flows), 1)
        flow = flows[0]
        self.assertEqual(flow["producer"]["memberPath"], ["resources", "get"])
        self.assertEqual(len(flow["producer"]["catalog"]), 95)
        config_map = next(item for item in flow["producer"]["catalog"] if item["selector"] == {"apiGroup": "", "apiVersion": "v1", "kind": "ConfigMap"})
        self.assertEqual(config_map["state"]["resource"], "configmaps")
        self.assertTrue(config_map["state"]["namespaced"])
        operations = [item for item in self.mapping["operations"] if item["name"].startswith("DynamicResource.")]
        self.assertEqual(len(operations), 8)
        self.assertEqual({item["conditionTemplate"]["operation"]["verb"] for item in operations}, {"create", "delete", "deletecollection", "get", "list", "patch", "update", "watch"})
        list_operation = next(item for item in operations if item["name"] == "DynamicResource.list")
        self.assertEqual(list_operation["conditionTemplate"]["scopeResolution"], {"stateField": "namespaced", "cases": [{"equals": False, "value": "cluster"}, {"equals": True, "argumentProvided": {"provided": "namespaced", "omitted": "all_namespaces"}}]})
        get = next(item for item in flow["methods"] if item["method"] == "get")
        self.assertEqual([item["operationRef"]["operation"] for item in get["operations"]], ["DynamicResource.get", "DynamicResource.list"])
        self.assertEqual(get["scopeArgument"], {"position": 1, "keyword": "namespace"})
        delete = next(item for item in flow["methods"] if item["method"] == "delete")
        self.assertNotIn("otherwise", delete["operations"][1])
        self.assertEqual({item["argument"]["keyword"] for item in delete["operations"][1]["when"]["any"]}, {"label_selector", "field_selector"})

    def test_list_watch_is_one_reviewed_override_not_a_choice_list(self):
        method = next(item for item in self.mapping["python"]["apiMethods"] if item["symbols"][0]["method"] == "list_namespaced_config_map")
        self.assertEqual(method["conditionalOperation"], {"when": {"argument": {"keyword": "watch"}, "equals": True}, "operationOverride": {"verb": "watch"}})

    def test_watch_stream_delegates_instead_of_declaring_a_generic_condition(self):
        delegations = self.mapping["python"]["conditionDelegations"]
        self.assertEqual(len(delegations), 1)
        watch = delegations[0]
        self.assertEqual(watch["symbols"], [{"module": "kubernetes.watch.watch", "class": "Watch", "method": "stream"}])
        self.assertNotIn("operationRef", watch)
        self.assertEqual(watch["delegate"]["callableArgument"], {"position": 0, "keyword": "func"})
        self.assertEqual({item["argument"]["keyword"] for item in watch["delegate"]["activateTargetConditionals"]}, {"watch", "follow"})

    def test_extension_digest_mismatch_fails_closed(self):
        extension = copy.deepcopy(self.extension)
        extension["metadata"]["semanticSha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "extension semantic digest"):
            build_mapping(self.surface, self.service_mapping, extension)


if __name__ == "__main__":
    unittest.main()
