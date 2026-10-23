"""Exercise the actual publication shell script against a local bare remote."""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class WorkflowSyncTests(unittest.TestCase):
    """Test initial creation, no-op publication and stale-source rejection."""

    @staticmethod
    def git(root: Path, *args: str) -> str:
        """Execute Git only in a disposable repository."""
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True,
            stderr=subprocess.PIPE,
        ).strip()

    def test_sync_script(self) -> None:
        """Use the workflow's real shell instead of duplicating its logic."""
        workflow = Path(".github/workflows/verify-and-sync.yml").read_text()
        script = textwrap.dedent(workflow.split("        run: |\n", 1)[1])
        exporter = Path("tools/export_submission.py").resolve()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed, remote, runner = root / "seed", root / "remote", root / "run"
            seed.mkdir()
            self.git(seed, "init", "-q", "-b", "develop")
            self.git(seed, "config", "user.name", "Test")
            self.git(seed, "config", "user.email", "test@example.com")
            (seed / "submission-files.txt").write_text("README.md\n")
            (seed / "README.md").write_text("first candidate\n")
            (seed / "private.txt").write_text("development only\n")
            self.git(seed, "add", ".")
            self.git(seed, "commit", "-qm", "fixture")
            subprocess.run(
                ["git", "clone", "-q", "--bare", str(seed), str(remote)],
                check=True,
            )
            subprocess.run(
                ["git", "clone", "-q", str(remote), str(runner)], check=True
            )
            source = self.git(runner, "rev-parse", "HEAD")

            def publish(label: str, sha: str) -> str:
                """Prepare a candidate and run the unchanged workflow shell."""
                temp = root / label
                temp.mkdir()
                subprocess.run(
                    [sys.executable, str(exporter), str(temp / "submission"),
                     "--ref", sha], cwd=runner, check=True,
                    stdout=subprocess.PIPE,
                )
                result = subprocess.run(
                    ["bash", "-euo", "pipefail", "-c", script], cwd=runner,
                    env={
                        **os.environ, "RUNNER_TEMP": str(temp),
                        "GITHUB_WORKSPACE": str(runner), "GITHUB_SHA": sha,
                    },
                    capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            publish("first", source)
            first = self.git(remote, "rev-parse", "master")
            self.assertEqual(
                self.git(remote, "ls-tree", "--name-only", "master"),
                "README.md",
            )
            self.assertEqual(
                self.git(remote, "show", "master:README.md"), "first candidate"
            )
            self.assertIn("already match", publish("same", source))
            self.assertEqual(self.git(remote, "rev-parse", "master"), first)

            (runner / "README.md").write_text("second candidate\n")
            self.git(runner, "add", "README.md")
            self.git(runner, "commit", "-qm", "second")
            self.git(runner, "push", "origin", "develop")
            second_source = self.git(runner, "rev-parse", "HEAD")
            self.assertIn("skipping stale", publish("stale", source))
            self.assertEqual(self.git(remote, "rev-parse", "master"), first)
            publish("second", second_source)
            second = self.git(remote, "rev-parse", "master")
            self.assertNotEqual(first, second)
            self.assertEqual(self.git(remote, "rev-parse", "master^"), first)
            self.assertEqual(
                self.git(remote, "show", "master:README.md"),
                "second candidate",
            )
            self.assertEqual(self.git(runner, "status", "--porcelain"), "")
