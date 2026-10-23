"""Exercise export policy in a disposable Git repository."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SubmissionExportTests(unittest.TestCase):
    """Check exported contents, revision pinning and unsafe file rejection."""

    def test_export_uses_committed_allowlisted_files(self) -> None:
        """Exclude development/untracked files and never overwrite output."""
        self._check_export(symlink=False)

    def test_export_rejects_symlinks(self) -> None:
        """Do not leak a symlink target into a submission."""
        self._check_export(symlink=True)

    def _check_export(self, symlink: bool) -> None:
        """Run the real exporter against a bounded temporary repository."""
        exporter = Path("tools/export_submission.py").resolve()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for key, value in (
                ("user.name", "Test"), ("user.email", "test@example.com"),
            ):
                subprocess.run(
                    ["git", "-C", str(root), "config", key, value], check=True
                )
            (root / "submission-files.txt").write_text(
                "README.md\nfly_in/**/*.py\n"
            )
            (root / "README.md").write_text("committed version")
            (root / "fly_in").mkdir()
            if symlink:
                (root / "fly_in/app.py").symlink_to("../README.md")
            else:
                (root / "fly_in/app.py").write_text("# runtime\n")
            (root / "tests").mkdir()
            (root / "tests/private.py").write_text("# development\n")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-qm", "fixture"],
                check=True,
            )
            (root / "README.md").write_text("uncommitted version")
            (root / "secret.txt").write_text("not tracked")
            output = Path(directory) / "export"
            command = [sys.executable, str(exporter), str(output)]
            result = subprocess.run(
                command, cwd=root, capture_output=True, text=True
            )
            if symlink:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
                return
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (output / "README.md").read_text(), "committed version"
            )
            self.assertEqual(
                {
                    p.relative_to(output).as_posix()
                    for p in output.rglob("*") if p.is_file()
                },
                {"README.md", "fly_in/app.py"},
            )
            result = subprocess.run(
                command, cwd=root, capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)
