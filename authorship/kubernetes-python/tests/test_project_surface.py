import sys
import tempfile
import unittest
from pathlib import Path

import yaml


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from project_surface import build_surface  # noqa: E402


GENERATED_SOURCE = '''class CoreV1Api:
    def read_namespaced_config_map(self, name, namespace, **kwargs):
        return self.read_namespaced_config_map_with_http_info(name, namespace, **kwargs)

    def read_namespaced_config_map_with_http_info(self, name, namespace, **kwargs):
        local_var_params = locals()
        path_params = {}
        path_params["name"] = local_var_params["name"]
        path_params["namespace"] = local_var_params["namespace"]
        query_params = []
        return self.api_client.call_api("/api/v1/namespaces/{namespace}/configmaps/{name}", "GET", path_params, query_params)
'''


class PythonSurfaceProjectionTest(unittest.TestCase):
    def test_joins_generated_sync_and_async_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            for relative in ("kubernetes/client/api", "kubernetes/aio/client/api"):
                target = source_root / relative
                target.mkdir(parents=True)
                (target / "core_v1_api.py").write_text(GENERATED_SOURCE, encoding="utf-8")
            (source_root / "scripts").mkdir()
            processed = {
                "swagger": "2.0",
                "paths": {
                    "/api/v1/namespaces/{namespace}/configmaps/{name}": {
                        "get": {"operationId": "readNamespacedConfigMap", "tags": ["core_v1"]}
                    }
                },
            }
            (source_root / "scripts/swagger.json").write_text(__import__("json").dumps(processed), encoding="utf-8")
            (source_root / "kubernetes/swagger.json.unprocessed").write_text(__import__("json").dumps(processed), encoding="utf-8")
            inventory_path = source_root / "inventory.yaml"
            inventory_path.write_text(
                yaml.safe_dump(
                    {
                        "metadata": {"semanticSha256": "inventory", "source": {"semanticSha256": "source"}},
                        "operations": [
                            {
                                "operationId": "readCoreV1NamespacedConfigMap",
                                "path": "/api/v1/namespaces/{namespace}/configmaps/{name}",
                                "method": "get",
                                "projection": {"form": "resource", "verb": "get", "apiGroup": "", "apiVersion": "v1", "resource": "configmaps", "scope": "namespaced"},
                            }
                        ],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            surface = build_surface(source_root, inventory_path, "https://example.test/python.git", "revision", "1.0.0")
        self.assertEqual(surface["metadata"]["surfaceCount"], 1)
        self.assertEqual(surface["metadata"]["summary"]["syncSymbols"], 1)
        self.assertEqual(surface["metadata"]["summary"]["asyncSymbols"], 1)
        entry = surface["surfaces"][0]
        self.assertEqual(entry["authoritative"]["operationId"], "readCoreV1NamespacedConfigMap")
        self.assertEqual(entry["symbols"][0]["method"], "read_namespaced_config_map")
        self.assertEqual(entry["arguments"]["name"], {"position": 0, "keyword": "name", "required": True})
        self.assertEqual(entry["arguments"]["namespace"], {"position": 1, "keyword": "namespace", "required": True})
        self.assertEqual(entry["pathBindings"], {"name": "name", "namespace": "namespace"})


if __name__ == "__main__":
    unittest.main()
