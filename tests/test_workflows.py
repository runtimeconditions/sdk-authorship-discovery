from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
EXPRESSION = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)
IMMUTABLE_ACTION = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def workflow_documents() -> list[tuple[Path, dict]]:
    documents = []
    for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
        documents.append((path, yaml.safe_load(path.read_text())))
    return documents


class WorkflowContractTest(unittest.TestCase):
    def test_embedded_bash_is_syntactically_valid(self) -> None:
        for path, workflow in workflow_documents():
            for job_name, job in workflow.get("jobs", {}).items():
                for index, step in enumerate(job.get("steps", []), start=1):
                    script = step.get("run")
                    if script is None:
                        continue
                    shell = step.get("shell", "bash")
                    if not str(shell).startswith("bash"):
                        continue
                    expanded = EXPRESSION.sub("GITHUB_EXPRESSION", script)
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=expanded,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                    label = step.get("name", f"step {index}")
                    self.assertEqual(
                        0,
                        completed.returncode,
                        f"{path.relative_to(ROOT)}:{job_name}:{label}: {completed.stderr.strip()}",
                    )

    def test_external_actions_are_pinned_to_commits(self) -> None:
        for path, workflow in workflow_documents():
            for job_name, job in workflow.get("jobs", {}).items():
                for index, step in enumerate(job.get("steps", []), start=1):
                    action = step.get("uses")
                    if action is None or action.startswith("./") or action.startswith("docker://"):
                        continue
                    label = step.get("name", f"step {index}")
                    self.assertRegex(
                        action,
                        IMMUTABLE_ACTION,
                        f"{path.relative_to(ROOT)}:{job_name}:{label} must pin an immutable commit",
                    )

    def test_pending_observation_summary_is_executable(self) -> None:
        workflow = yaml.safe_load((WORKFLOWS / "ongoing-releases.yml").read_text())
        steps = workflow["jobs"]["observe-compatible-root-graph"]["steps"]
        step = next(item for item in steps if item.get("name") == "Report observation awaiting review")
        observation_id = "ongoing-boto3-1.43.80-botocore-1.43.80-s3transfer-0.19.2"
        with tempfile.NamedTemporaryFile() as summary:
            environment = os.environ | {
                "GITHUB_STEP_SUMMARY": summary.name,
                "OBSERVATION_ID": observation_id,
                "PR_NUMBER": "4",
            }
            completed = subprocess.run(
                ["bash", "-eu", "-o", "pipefail", "-c", step["run"]],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            summary.seek(0)
            self.assertEqual(
                f"Observation {observation_id} is already awaiting review in pull request #4; "
                "the expensive maintenance proof was not repeated.\n",
                summary.read().decode(),
            )


if __name__ == "__main__":
    unittest.main()
