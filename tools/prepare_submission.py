"""Plan and build a release-candidate commit for the release branch.

The candidate is made from the blobs of one pinned ``develop`` commit,
selected by ``submission-files.txt`` through ``SubmissionExport``, on top of
the current head of the release branch. Nothing here pushes or merges.

``plan`` only reads. It lists what would be added, changed and deleted and
prints a hash of that plan. ``commit`` builds the candidate only when it is
given the same hash, so a deletion (or any other change) must be reviewed
first, and a changed plan is refused instead of being applied silently.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from tools.export_submission import SubmissionExport

Entries = dict[str, tuple[str, str]]


@dataclass(frozen=True)
class Plan:
    """What a release candidate changes on the release branch."""

    source: str
    base: str
    manifest: str
    added: Entries
    modified: Entries
    deleted: list[str]
    unexpected: list[str]
    unchanged: int

    @property
    def empty(self) -> bool:
        """Tell whether the release branch already equals the candidate."""
        return not (self.added or self.modified or self.deleted)


def git(*args: str, env: dict[str, str] | None = None,
        data: bytes | None = None) -> str:
    """Run one git command and return its output; failures raise."""
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, input=data,
        env=env,
    ).stdout.decode().strip()


def tree_entries(commit: str) -> Entries:
    """Return ``path -> (mode, blob)`` of every file of one commit."""
    entries: Entries = {}
    out = subprocess.check_output(["git", "ls-tree", "-rz", commit])
    for entry in filter(None, out.split(b"\0")):
        meta, raw = entry.split(b"\t", 1)
        mode, _, blob = meta.decode().split()
        entries[raw.decode()] = (mode, blob)
    return entries


def resolve(ref: str) -> str:
    """Return the commit that a ref names."""
    return git(
        "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"
    )


class ReleaseCandidate:
    """The difference between one source commit and the release branch."""

    def __init__(self, source: str, base: str, develop: str) -> None:
        """Pin the source and base commits; the source must be on develop."""
        self.exporter = SubmissionExport(source)
        self.source = self.exporter.commit
        self.base = resolve(base)
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", self.source,
             resolve(develop)],
            capture_output=True,
        )
        if ancestor.returncode != 0:
            raise ValueError(
                f"{self.source} is not part of the history of {develop}"
            )

    def candidate(self) -> Entries:
        """Return ``path -> (mode, blob)`` of the files to release."""
        return {p: (m, b) for p, b, m in self.exporter.select()}

    def current(self) -> Entries:
        """Return ``path -> (mode, blob)`` of the release branch head."""
        return tree_entries(self.base)

    def plan(self) -> Plan:
        """Describe the change from the release head to the candidate."""
        new, old = self.candidate(), self.current()
        added = sorted(new.keys() - old.keys())
        deleted = sorted(old.keys() - new.keys())
        modified = sorted(
            p for p in new.keys() & old.keys() if new[p] != old[p]
        )
        patterns = self.exporter.patterns()
        unexpected = [
            p for p in deleted
            if not any(SubmissionExport.matches(p, q) for q in patterns)
        ]
        return Plan(
            source=self.source,
            base=self.base,
            manifest=git("rev-parse", f"{self.source}:submission-files.txt"),
            added={p: new[p] for p in added},
            modified={p: new[p] for p in modified},
            deleted=deleted,
            unexpected=unexpected,
            unchanged=len(new) - len(added) - len(modified),
        )

    @staticmethod
    def digest(plan: Plan) -> str:
        """Hash the plan, so approving it approves exactly this change."""
        text = json.dumps(asdict(plan), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def render(plan: Plan, digest: str) -> str:
        """Write the plan as Markdown for a person to review."""
        def section(title: str, names: list[str]) -> list[str]:
            """List the paths of one kind of change."""
            body = [f"- `{n}`" for n in names] or ["- (none)"]
            return [f"### {title} ({len(names)})", *body, ""]

        return "\n".join([
            f"- source commit (develop): `{plan.source}`",
            f"- release branch head (base): `{plan.base}`",
            f"- unchanged files: {plan.unchanged}",
            f"- plan hash: `{digest}`", "",
            *section("Added", sorted(plan.added)),
            *section("Modified", sorted(plan.modified)),
            *section(
                "Deleted: removed from develop",
                [p for p in plan.deleted if p not in plan.unexpected],
            ),
            *section(
                "Deleted: UNEXPECTED, not allowed by the manifest",
                plan.unexpected,
            ),
        ])

    def build(self, approved: str, message: str) -> str:
        """Create the candidate commit on top of the base; do not push."""
        plan = self.plan()
        if self.digest(plan) != approved:
            raise ValueError("The plan changed; review it again.")
        if plan.empty:
            raise ValueError("The release branch already has this content.")
        new = self.candidate()
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ,
                   "GIT_INDEX_FILE": str(Path(directory) / "index")}
            git("read-tree", "--empty", env=env)
            lines = "".join(
                f"{mode} {blob}\t{path}\n"
                for path, (mode, blob) in sorted(new.items())
            )
            git("update-index", "--add", "--index-info", env=env,
                data=lines.encode())
            tree = git("write-tree", env=env)
        env = {
            "GIT_AUTHOR_NAME": "Fly-in release",
            "GIT_COMMITTER_NAME": "Fly-in release",
            "GIT_AUTHOR_EMAIL": "noreply@github.com",
            "GIT_COMMITTER_EMAIL": "noreply@github.com",
            **os.environ,
        }
        commit = git("commit-tree", tree, "-p", self.base, "-m", message,
                     env=env)
        built = tree_entries(commit)
        if built != new:
            raise ValueError("The candidate does not match the selection.")
        return commit

    def verify_head(self, head: str) -> None:
        """Refuse unless ``head`` is exactly this candidate on top of main.

        Run it just before merging: it shows that the branch still holds the
        files of the source commit and nothing else, as one commit whose
        parent is the current head of the release branch.
        """
        commit = resolve(head)
        if tree_entries(commit) != self.candidate():
            raise ValueError(
                f"{head} does not hold exactly the candidate of {self.source}"
            )
        parents = git("rev-list", "--parents", "-n", "1", commit).split()[1:]
        if parents != [self.base]:
            raise ValueError(
                f"{head} is not one commit on top of the current "
                f"{self.base}; make a new plan"
            )


def same_candidate(first: str, second: str) -> bool:
    """Tell whether two commits have the same tree and the same parents."""
    def shape(commit: str) -> tuple[str, list[str]]:
        """Return the tree and the parent commits of one commit."""
        parents = git("rev-list", "--parents", "-n", "1", commit).split()[1:]
        return git("rev-parse", f"{commit}^{{tree}}"), parents

    return shape(first) == shape(second)


def main() -> int:
    """Plan or build a candidate; report a refusal as a failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    same = sub.add_parser("same")
    same.add_argument("first")
    same.add_argument("second")
    for name in ("plan", "commit", "verify"):
        item = sub.add_parser(name)
        item.add_argument("--source", required=True)
        item.add_argument("--base", default="origin/main")
        item.add_argument("--develop", default="origin/develop")
        if name == "plan":
            item.add_argument("--out", type=Path)
        elif name == "verify":
            item.add_argument("--head", required=True)
        else:
            item.add_argument("--approve", required=True)
            item.add_argument("--message", required=True)
    args = parser.parse_args()
    try:
        if args.command == "same":
            return int(not same_candidate(args.first, args.second))
        release = ReleaseCandidate(args.source, args.base, args.develop)
        if args.command == "commit":
            print(release.build(args.approve, args.message))
            return 0
        if args.command == "verify":
            release.verify_head(args.head)
            print(f"{args.head} holds exactly the candidate "
                  f"of {release.source}")
            return 0
        plan = release.plan()
        digest = release.digest(plan)
        text = release.render(plan, digest)
        print(text)
        if args.out is not None:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / "plan.md").write_text(text)
            (args.out / "plan.hash").write_text(digest + "\n")
        return 0
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"Release candidate refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
