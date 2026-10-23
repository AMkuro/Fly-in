"""Build a submission index, preserving master if unexpected files exist."""

import argparse
import json
import os
import subprocess
from pathlib import Path

from tools.export_submission import SubmissionExport

WARNING_FILE = "SUBMISSION_WARNING.md"


def prepare(candidate: Path, parent: str) -> str:
    """Prepare an isolated index and report submit or warning mode."""
    if not os.environ.get("GIT_INDEX_FILE"):
        raise ValueError("An isolated GIT_INDEX_FILE is required")
    source = SubmissionExport("HEAD")
    patterns = source.patterns()
    if (candidate / WARNING_FILE).exists():
        raise ValueError(f"{WARNING_FILE} is reserved for submission warnings")
    paths: list[str] = []
    if parent:
        paths = [
            path.decode() for path in subprocess.check_output(
                ["git", "ls-tree", "-rz", "--name-only", parent]
            ).split(b"\0") if path
        ]
    extras = sorted(
        path for path in paths if path != WARNING_FILE
        and not any(source.matches(path, pattern) for pattern in patterns)
    )
    if extras:
        subprocess.run(["git", "read-tree", parent], check=True)
        warning = (
            "# Submission warning\n\n"
            "Automatic submission update was stopped. Unexpected files from\n"
            "master have been preserved unchanged:\n\n"
            + "\n".join(
                f"- {json.dumps(path, ensure_ascii=False)}" for path in extras
            )
            + "\n\nReview before submission. Remove unwanted files\n"
            "from master, or include required runtime files in\n"
            "develop's manifest. A later passing CI run removes this warning\n"
            "when no unexpected files remain. This file is managed by CI.\n"
        )
        blob = subprocess.check_output(
            ["git", "hash-object", "-w", "--stdin"],
            input=warning.encode(),
        ).decode().strip()
        subprocess.run(
            ["git", "update-index", "--add", "--cacheinfo",
             "100644", blob, WARNING_FILE], check=True,
        )
        return "warning"
    subprocess.run(["git", "read-tree", "--empty"], check=True)
    git_dir = subprocess.check_output(
        ["git", "rev-parse", "--absolute-git-dir"], text=True
    ).strip()
    subprocess.run(
        ["git", "add", "--all", "."], cwd=candidate,
        env={**os.environ, "GIT_DIR": git_dir}, check=True,
    )
    return "submit"


def main() -> None:
    """Prepare the index; the caller handles committing and pushing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--parent", default="")
    args = parser.parse_args()
    print(prepare(args.candidate, args.parent))


if __name__ == "__main__":
    main()
