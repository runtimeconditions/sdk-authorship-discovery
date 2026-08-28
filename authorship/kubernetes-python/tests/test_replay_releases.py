import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from replay_releases import review_markdown  # noqa: E402


class KubernetesPythonReleaseReplayTest(unittest.TestCase):
    def test_review_separates_final_compatibility_from_observed_maintenance(self):
        evidence = {
            "summary": {"releases": 1, "compatibleWithCurrentGenerator": 1, "incompatibleWithCurrentGenerator": 0, "observedAutomationRepairs": 1},
            "releases": [{"version": "36.0.0", "revision": "revision", "finalReplayResult": "compatible-with-current-generator", "operationRecords": 936, "syncSymbols": 936, "asyncSymbols": 0}],
            "observedMaintenance": [{"id": "repair", "description": "The initial replay failed.", "productionInterpretation": "An upstream integration would require maintainer review."}],
        }

        review = review_markdown(evidence)

        self.assertIn("not a chronological simulation", review)
        self.assertIn("1 authored integration-tooling repair", review)
        self.assertIn("does not prove zero-touch production maintenance", review)
        self.assertNotIn("Classification: `automatic`", review)


if __name__ == "__main__":
    unittest.main()
