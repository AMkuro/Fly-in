"""Exercise the release-candidate planner in a disposable Git repository."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path("tools/prepare_submission.py").resolve()
ROOT = TOOL.parents[1]


class ReleaseCandidateTests(unittest.TestCase):
    """Check what is planned, refused and built, without any remote."""

    def setUp(self) -> None:
        """Create a repository with an old main and a newer develop."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.write("README.md", "old readme")
        self.write("app/stale.py", "# only on main\n")
        self.write("notes.txt", "unexpected on main")
        self.git("add", ".")
        self.git("commit", "-qm", "old release")
        self.git("checkout", "-q", "-b", "develop")
        self.git("rm", "-q", "app/stale.py", "notes.txt")
        self.write("submission-files.txt", "README.md\napp/**/*.py\n")
        self.write("README.md", "new readme")
        self.write("app/run.py", "# runtime\n")
        self.write("tests_private.py", "# development only\n")
        self.git("add", ".")
        self.git("commit", "-qm", "new work")
        self.source = self.git("rev-parse", "HEAD")

    def git(self, *args: str) -> str:
        """Run git in the fixture repository."""
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def write(self, name: str, text: str) -> None:
        """Write one file of the fixture repository."""
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the real tool in the fixture repository."""
        return subprocess.run(
            [sys.executable, str(TOOL), *args], cwd=self.repo,
            capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
                 "PYTHONPATH": str(ROOT)},
        )

    def plan_command(self, source: str) -> subprocess.CompletedProcess[str]:
        """Run ``plan`` for a source commit against main and develop."""
        return self.tool("plan", "--source", source, "--base", "main",
                         "--develop", "develop")

    def plan(self, source: str = "") -> tuple[str, str]:
        """Return the plan text and its hash for the source commit."""
        result = self.plan_command(source or self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        digest = next(line for line in result.stdout.splitlines()
                      if "plan hash" in line).split("`")[1]
        return result.stdout, digest

    def commit(self, digest: str) -> subprocess.CompletedProcess[str]:
        """Build the candidate commit with an approved plan hash."""
        return self.tool("commit", "--source", self.source, "--base",
                         "main", "--develop", "develop",
                         "--approve", digest, "--message", "candidate")

    def test_plan_lists_every_kind_of_change(self) -> None:
        """Added, modified and deleted files are reported separately."""
        text, _ = self.plan()
        for expected in (
            "### Added (1)", "`app/run.py`",
            "### Modified (1)", "`README.md`",
            "### Deleted: removed from develop (1)", "`app/stale.py`",
            "### Deleted: UNEXPECTED, not allowed by the manifest (1)",
            "`notes.txt`",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("tests_private.py", text)

    def test_plan_hash_is_reproducible_and_follows_content(self) -> None:
        """The same inputs give the same hash; new content changes it."""
        self.assertEqual(self.plan()[1], self.plan()[1])
        self.write("README.md", "changed again")
        self.git("commit", "-qam", "again")
        newer = self.git("rev-parse", "HEAD")
        self.assertNotEqual(self.plan()[1], self.plan(newer)[1])

    def test_plan_ignores_uncommitted_work(self) -> None:
        """A dirty working tree cannot change the plan."""
        before = self.plan()[1]
        self.write("README.md", "uncommitted")
        self.write("app/extra.py", "# untracked\n")
        self.assertEqual(self.plan()[1], before)

    def test_source_outside_develop_is_refused(self) -> None:
        """Only commits that belong to develop's history can be released."""
        self.git("checkout", "-q", "-b", "side", "main")
        self.write("README.md", "side")
        self.git("commit", "-qam", "side")
        result = self.plan_command(self.git("rev-parse", "HEAD"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("not part of the history", result.stderr)

    def test_commit_needs_the_approved_hash(self) -> None:
        """A wrong or stale hash builds nothing."""
        before = self.git("rev-parse", "main")
        result = self.commit("0" * 64)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plan changed", result.stderr)
        self.assertEqual(self.git("rev-parse", "main"), before)

    def test_commit_builds_exactly_the_selection_on_top_of_main(self) -> None:
        """The tree is the manifest's files; no ref is created or moved."""
        base = self.git("rev-parse", "main")
        refs = self.git("for-each-ref")
        result = self.commit(self.plan()[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        built = result.stdout.strip()
        self.assertEqual(self.git("rev-parse", f"{built}^"), base)
        self.assertEqual(
            self.git("ls-tree", "-r", "--name-only", built).split("\n"),
            ["README.md", "app/run.py"],
        )
        self.assertEqual(self.git("show", f"{built}:README.md"), "new readme")
        self.assertEqual(self.git("for-each-ref"), refs)

    def test_approval_is_void_after_main_moves(self) -> None:
        """If the release branch advanced, the old approval is refused."""
        digest = self.plan()[1]
        self.git("checkout", "-q", "main")
        self.write("extra.txt", "another release")
        self.git("add", ".")
        self.git("commit", "-qm", "main moved")
        self.git("checkout", "-q", "develop")
        result = self.commit(digest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plan changed", result.stderr)

    def test_nothing_to_release_is_refused(self) -> None:
        """A candidate equal to main is not turned into an empty PR."""
        built = self.commit(self.plan()[1]).stdout.strip()
        self.git("branch", "-f", "main", built)
        result = self.commit(self.plan()[1])
        self.assertEqual(result.returncode, 1)
        self.assertIn("already has this content", result.stderr)

    def test_same_candidate_is_recognised(self) -> None:
        """Two builds of one plan share tree and parent; others differ."""
        digest = self.plan()[1]
        first = self.commit(digest).stdout.strip()
        second = self.commit(digest).stdout.strip()
        self.assertEqual(self.tool("same", first, second).returncode, 0)
        self.git("checkout", "-q", "main")
        self.write("README.md", "different")
        self.git("commit", "-qam", "other")
        other = self.git("rev-parse", "HEAD")
        self.assertEqual(self.tool("same", first, other).returncode, 1)

    def test_symlink_in_source_is_refused(self) -> None:
        """A symlink cannot enter a release candidate."""
        (self.repo / "app/link.py").symlink_to("../README.md")
        self.git("add", ".")
        self.git("commit", "-qm", "link")
        result = self.plan_command(self.git("rev-parse", "HEAD"))
        self.assertNotEqual(result.returncode, 0)

    def test_later_develop_commits_do_not_change_the_plan(self) -> None:
        """The source SHA is fixed; develop moving on is not part of it."""
        before = self.plan()[1]
        self.write("README.md", "work after the release source")
        self.write("app/new_feature.py", "# later work\n")
        self.git("add", ".")
        self.git("commit", "-qm", "later work on develop")
        self.assertEqual(self.plan()[1], before)
        built = self.commit(before).stdout.strip()
        self.assertEqual(
            self.git("show", f"{built}:README.md"), "new readme"
        )
        self.assertNotIn("new_feature", self.git("ls-tree", "-r", built))

    def verify(self, head: str) -> subprocess.CompletedProcess[str]:
        """Run ``verify`` for a branch head against the fixed source."""
        return self.tool("verify", "--source", self.source, "--head", head,
                         "--base", "main", "--develop", "develop")

    def test_verify_accepts_the_built_candidate(self) -> None:
        """The branch that was built passes the check before merging."""
        built = self.commit(self.plan()[1]).stdout.strip()
        result = self.verify(built)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_verify_refuses_a_head_that_changed_after_review(self) -> None:
        """A later commit on the release branch cannot pass unnoticed."""
        built = self.commit(self.plan()[1]).stdout.strip()
        self.git("checkout", "-q", "-b", "release", built)
        self.write("README.md", "edited after review")
        self.git("commit", "-qam", "late edit")
        late = self.verify("release")
        self.assertEqual(late.returncode, 1)
        self.assertIn("does not hold exactly", late.stderr)
        self.git("reset", "-q", "--hard", built)
        self.write("app/extra.py", "# smuggled\n")
        self.git("add", ".")
        self.git("commit", "-q", "--amend", "-m", "amended")
        amended = self.verify("release")
        self.assertEqual(amended.returncode, 1)
        self.assertIn("does not hold exactly", amended.stderr)

    def test_verify_refuses_when_main_moved_since(self) -> None:
        """A branch built on an older main is not the current candidate."""
        built = self.commit(self.plan()[1]).stdout.strip()
        self.git("checkout", "-q", "main")
        self.write("other.txt", "another change on main")
        self.git("add", ".")
        self.git("commit", "-qm", "main moved")
        self.git("checkout", "-q", "develop")
        result = self.verify(built)
        self.assertEqual(result.returncode, 1)
        self.assertIn("make a new plan", result.stderr)
