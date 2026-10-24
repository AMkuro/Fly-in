"""Guard the verification-only workflow against automatic publication."""

import re
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    """Keep CI triggers and checks while allowing no publication steps."""

    # shortcut: fixed YAML layout, use a YAML parser if formatting expands.
    WORKFLOW = Path(".github/workflows/verify-and-sync.yml")

    def test_verification_triggers(self) -> None:
        """Run checks on develop pushes, pull requests and manual dispatch."""
        workflow = self.WORKFLOW.read_text()
        for event in ("push", "pull_request"):
            self.assertIn(
                f"  {event}:\n    branches: [develop]\n", workflow
            )
        self.assertIn("  workflow_dispatch:\n", workflow)
        self.assertIn("python: ['3.10', '3.14']", workflow)

    def test_only_verification_jobs_and_commands(self) -> None:
        """Reject added jobs, actions or commands outside the check policy."""
        workflows = set(Path(".github/workflows").glob("*"))
        self.assertEqual(workflows, {self.WORKFLOW})
        workflow = self.WORKFLOW.read_text()
        jobs = workflow.split("\njobs:\n", 1)[1]
        self.assertEqual(
            re.findall(r"^  ([\w-]+):$", jobs, re.MULTILINE),
            ["quality", "subject"],
        )
        # Only these single-line checks may execute; no publication shell.
        self.assertCountEqual(
            re.findall(r"^[ \t]*(?:- )?run: (.+)$", jobs, re.MULTILINE),
            [
                "make install", "make lint", "make test", "make install",
                '.venv/bin/python -m tools.export_submission '
                '"$RUNNER_TEMP/submission"',
                'make -C "$RUNNER_TEMP/submission" lint '
                'PYTHON="$GITHUB_WORKSPACE/.venv/bin/python"',
                '.venv/bin/python -m tools.verify_subject '
                '"$RUNNER_TEMP/submission"',
            ],
        )
        self.assertCountEqual(
            re.findall(r"^[ \t]*- uses: (.+)$", jobs, re.MULTILINE),
            ["actions/checkout@v7", "actions/setup-python@v7"] * 2,
        )

    def test_read_only_permissions(self) -> None:
        """Deny job permission overrides and persisted checkout credentials."""
        workflow = self.WORKFLOW.read_text()
        self.assertIn("\npermissions:\n  contents: read\n", workflow)
        self.assertEqual(
            re.findall(r"^[ \t]*permissions:.*$", workflow, re.MULTILINE),
            ["permissions:"],
        )
        self.assertNotIn("${{ secrets.", workflow)
        self.assertEqual(workflow.count("persist-credentials: false"), 2)
