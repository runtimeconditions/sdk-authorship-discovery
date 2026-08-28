import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from serialization import read_document  # noqa: E402
from stage_distribution import stage  # noqa: E402


class KubernetesDistributionStagingTest(unittest.TestCase):
    def test_stages_version_aligned_mapping_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "setup.py").write_text('CLIENT_VERSION = "36.0.3"\n', encoding="utf-8")
            index = stage(source, ROOT / "mappings/runtimeconditions.sdk-mapping.yaml")
            self.assertEqual(index["metadata"]["distributionVersion"], "36.0.3")
            mapping_path = source / index["mappings"][0]["path"]
            self.assertTrue(mapping_path.is_file())
            installed_index = read_document(source / "kubernetes/runtimeconditions/index.yaml")
            self.assertEqual(installed_index, index)


if __name__ == "__main__":
    unittest.main()
