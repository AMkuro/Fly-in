"""Guard the workflows: verification only, release by hand and reviewed."""

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
        self.assertEqual(
            workflows, {self.WORKFLOW, ReleaseWorkflowTests.WORKFLOW}
        )
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


class ReleaseWorkflowTests(unittest.TestCase):
    """Keep release-candidate creation manual, minimal and non-merging."""

    # shortcut: text checks on a fixed layout, as for the verification file.
    WORKFLOW = Path(".github/workflows/release-candidate.yml")

    def setUp(self) -> None:
        """Read the release workflow and split it into its two jobs."""
        self.text = self.WORKFLOW.read_text()
        self.jobs = self.text.split("\njobs:\n", 1)[1]
        self.publish = self.jobs.split("\n  publish:\n", 1)[1]
        self.candidate = self.jobs.split("\n  publish:\n", 1)[0]

    def test_only_a_manual_trigger(self) -> None:
        """A push or pull request must never start a release."""
        header = self.text.split("\npermissions:\n", 1)[0]
        self.assertEqual(
            re.findall(r"^  ([a-z_]+):$", header.split("\non:\n", 1)[1],
                       re.MULTILINE)[:1],
            ["workflow_dispatch"],
        )
        for forbidden in ("push:", "pull_request", "schedule:",
                          "workflow_run", "repository_dispatch"):
            self.assertNotIn(forbidden, header)

    def test_two_jobs_and_least_privilege(self) -> None:
        """Only the publish job writes, and only what a release PR needs."""
        self.assertEqual(
            re.findall(r"^  ([\w-]+):$", self.jobs, re.MULTILINE),
            ["candidate", "publish"],
        )
        self.assertIn("\npermissions:\n  contents: read\n", self.text)
        self.assertEqual(
            re.findall(r"^[ \t]*permissions:.*$", self.text, re.MULTILINE),
            ["permissions:", "    permissions:"],
        )
        self.assertNotIn("write", self.candidate)
        self.assertEqual(
            re.findall(r"^      ([\w-]+): write$", self.publish,
                       re.MULTILINE),
            ["contents", "pull-requests"],
        )
        self.assertIn("    environment: release\n", self.publish)

    def test_runs_only_for_trusted_develop(self) -> None:
        """Both jobs refuse any ref other than develop."""
        self.assertEqual(
            self.text.count("github.ref == 'refs/heads/develop'"), 2
        )
        self.assertIn("inputs.approved_plan_hash != ''", self.publish)

    def test_no_persisted_credentials_or_secrets(self) -> None:
        """Checkouts keep no token; only the run's own token is used."""
        self.assertEqual(
            self.text.count("actions/checkout@v7"),
            self.text.count("persist-credentials: false"),
        )
        self.assertNotIn("${{ secrets.", self.text)
        self.assertEqual(self.text.count("github.token"), 1)

    def test_inputs_never_reach_a_shell_directly(self) -> None:
        """Inputs are passed through env, not pasted into scripts."""
        for line in self.text.splitlines():
            if "${{ inputs." in line:
                self.assertRegex(line, r"^\s+[A-Z_]+: \$\{\{ inputs\.\w+ \}\}$"
                                 r"|^    if: .*inputs\.approved_plan_hash")

    def test_never_forces_merges_or_bypasses(self) -> None:
        """No force push, merge, admin override or auto-merge exists."""
        for forbidden in ("--force", "--force-with-lease", " -f ", "+refs",
                          "pr merge", "--admin", "auto-merge", "--squash",
                          "master"):
            self.assertNotIn(forbidden, self.text)
        pushes = re.findall(r"push origin (\S+)", self.text)
        self.assertEqual(pushes, ['"${COMMIT}:refs/heads/${BRANCH}"'])
        self.assertEqual(self.text.count("git -c"), 1)
