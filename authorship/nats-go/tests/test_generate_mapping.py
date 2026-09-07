from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml


AUTHORSHIP_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = AUTHORSHIP_ROOT.parents[1]
WORKSPACE_ROOT = SDK_ROOT.parent
GENERATOR = AUTHORSHIP_ROOT / "tools/generate_mapping.py"
ANNOTATIONS = AUTHORSHIP_ROOT / "annotations/go.yaml"
SERVICE_MAPPING = WORKSPACE_ROOT / "extensions/nats-service/model/generated/nats-service-mapping.yaml"
EXTENSION = WORKSPACE_ROOT / "extensions/nats-service/releases/0.1.0/runtimeconditions.extension.yaml"
PYTHON_ANNOTATIONS = SDK_ROOT / "authorship/nats-python/annotations/python.yaml"


def read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} did not contain an object")
    return value


class GenerateMappingTests(unittest.TestCase):
    def run_generator(self, annotations: dict[str, Any], service_mapping: dict[str, Any] | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]:
        with tempfile.TemporaryDirectory(prefix="runtimeconditions-nats-go-generator-") as temporary:
            root = Path(temporary)
            annotations_path = root / "annotations.yaml"
            service_mapping_path = root / "service-mapping.yaml"
            output_path = root / "mapping.yaml"
            annotations_path.write_text(yaml.safe_dump(annotations, sort_keys=False), encoding="utf-8")
            service_mapping_path.write_text(yaml.safe_dump(service_mapping or read_yaml(SERVICE_MAPPING), sort_keys=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--annotations",
                    str(annotations_path),
                    "--service-mapping",
                    str(service_mapping_path),
                    "--extension",
                    str(EXTENSION),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            output = read_yaml(output_path) if output_path.exists() else None
            return result, output

    def test_resolves_operation_references_from_the_service_mapping(self) -> None:
        annotations = read_yaml(ANNOTATIONS)
        service_mapping = read_yaml(SERVICE_MAPPING)
        result, output = self.run_generator(annotations, service_mapping)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(output)
        assert output is not None
        self.assertNotIn("conditionTemplate", ANNOTATIONS.read_text(encoding="utf-8"))
        self.assertNotRegex(ANNOTATIONS.read_text(encoding="utf-8"), r"[&*][A-Za-z_]")
        self.assertIn({"kind": "serviceMapping", **annotations["serviceMapping"]}, output["dependencies"])
        operations = {operation["name"]: operation for operation in service_mapping["operations"]}
        conditioned_calls = 0
        for call in output["go"]["calls"]:
            operation_ref = call.get("operationRef")
            if operation_ref is None:
                self.assertIn("produces", call)
                self.assertNotIn("conditionTemplate", call)
                continue
            conditioned_calls += 1
            condition = operations[operation_ref]["conditions"][0]
            self.assertEqual(
                call["conditionTemplate"],
                {"kind": condition["kind"], "interfaceType": condition["interfaceType"], "operation": condition["operation"]},
            )
        self.assertEqual(conditioned_calls, 86)

    def test_go_and_python_reference_one_service_authority(self) -> None:
        go_annotations = read_yaml(ANNOTATIONS)
        python_annotations = read_yaml(PYTHON_ANNOTATIONS)
        service_mapping = read_yaml(SERVICE_MAPPING)
        self.assertEqual(go_annotations["serviceMapping"], python_annotations["serviceMapping"])
        canonical = {operation["name"] for operation in service_mapping["operations"]}
        go_references = {
            record["operationRef"]
            for area in ("calls", "callGroups")
            for record in go_annotations["go"].get(area, [])
            if "operationRef" in record
        }
        python_references: set[str] = set()
        for area in ("factories", "calls", "callGroups"):
            for record in python_annotations["python"].get(area, []):
                if "operationRef" in record:
                    python_references.add(record["operationRef"])
                python_references.update(entry["operationRef"] for entry in record.get("operations", []) if "operationRef" in entry)
        self.assertEqual(go_references, canonical)
        self.assertEqual(canonical - python_references, {"consumer.update"})
        self.assertTrue(go_references & python_references)

    def test_rejects_an_unknown_service_operation(self) -> None:
        annotations = copy.deepcopy(read_yaml(ANNOTATIONS))
        annotations["go"]["calls"][0]["operationRef"] = "connection.unknown"
        result, output = self.run_generator(annotations)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(output)
        self.assertIn("unknown service operation", result.stderr)

    def test_rejects_a_missing_required_binding(self) -> None:
        annotations = copy.deepcopy(read_yaml(ANNOTATIONS))
        publish = next(call for call in annotations["go"]["calls"] if call["id"] == "core-publish")
        publish["operationBindings"] = {}
        result, output = self.run_generator(annotations)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(output)
        self.assertIn("missing sources for required fields", result.stderr)

    def test_rejects_a_stale_service_mapping_digest(self) -> None:
        annotations = copy.deepcopy(read_yaml(ANNOTATIONS))
        annotations["serviceMapping"]["semanticSha256"] = "stale"
        result, output = self.run_generator(annotations)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(output)
        self.assertIn("service mapping coordinates do not match annotations", result.stderr)

    def test_rejects_an_authored_condition_template(self) -> None:
        annotations = copy.deepcopy(read_yaml(ANNOTATIONS))
        connect = annotations["go"]["calls"][0]
        connect["conditionTemplate"] = {"kind": "nats", "interfaceType": "service", "operation": {"resource": "connection", "action": "connect"}}
        result, output = self.run_generator(annotations)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(output)
        self.assertIn("authoring input must use operationRef", result.stderr)


if __name__ == "__main__":
    unittest.main()
