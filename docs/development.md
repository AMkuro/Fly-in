# Development and submission

This document defines **repeatable development, verification, and submission
procedures**. It is not a project status report. Do not record per-Issue
progress, temporary implementation gaps, pending design decisions, test
coverage snapshots, or resolved defects here. Follow the current sources of
truth identified in [Documentation and approval](#documentation).

## Branch and submission policy

| Branch | Role |
|---|---|
| `develop` | Development, tests and verification (the default branch). |
| `main` | Reviewed release and submission candidate. |
| `master` | Old release branch. Not used for new releases. |
| `archive/legacy-main-20261105` | Preserved history of the old `main`. |

Select submission contents using
[`submission-files.txt`](../submission-files.txt), rather than merging all
development history into `main`: a release is a snapshot of the selected files
of one `develop` commit, added on top of the existing history of `main`. The
existence of a snapshot on `main` does not establish that the project is
complete or verified.

The verification workflow is for verification only. It must not commit, push,
publish warnings, or release to `main` or the 42 submission repository
automatically. A successful check is evidence for review, not approval to
submit. Changing branch roles requires an explicit decision.

## Local checks and candidate export

Use a working virtual environment. The commands and targets available in a
particular revision are defined by the [Makefile](../Makefile) and tool sources;
check them before running. The project's development and candidate-check
workflow can be invoked as follows:

```sh
make install
make lint PYTHON=/path/to/venv/bin/python
make test PYTHON=/path/to/venv/bin/python
/path/to/venv/bin/python -m tools.export_submission /tmp/fly-in-candidate
/path/to/venv/bin/python -m tools.verify_subject /tmp/fly-in-candidate
```

The export destination must not already exist. Export a **committed revision**,
not an uncommitted working tree. Review the selected files against
[`submission-files.txt`](../submission-files.txt) and inspect the exported
candidate independently from the development checkout.

A development-only verifier is not the Subject and does not approve a design
interpretation. Before relying on any verification result, compare the
verifier's actual rules with the current
[accepted contracts](architecture.md) and
[decision record](decisions.md). Check its coverage and behavior in
[`tools/verify_subject.py`](../tools/verify_subject.py) and the
[tests](../tests); track discrepancies and their resolution in the relevant
Issues. Do not transcribe the verifier's current behavior or defect status into
this manual.

Passing automation does not by itself prove optimality, priority preference,
complete object-oriented design, GUI usefulness, resource safety, or correctness
for every possible graph. Those require appropriate review and additional
evidence.

## Verification-only CI

The [GitHub Actions workflow](../.github/workflows/verify-and-sync.yml) is the
source of truth for configured jobs, triggers, Python versions, and checks.
Review the workflow itself rather than maintaining a duplicate list of its
current configuration here.

CI changes must preserve the verification-only boundary:
- Do not grant a workflow publishing or submission authority through a test run.
- Keep workflow permissions as restricted as practicable; avoid persisting
  credentials in checkouts used for untrusted changes.
- Review any changes to candidate selection, permissions, and release behavior
  separately from ordinary test additions.

Older [audit records](submission-audit.md) document historical configurations,
not current CI behavior. The project's actual verification state and remaining
work belong in the relevant Issues.

## Reviewed releases

At version changes or important milestones, prepare a reviewable release
candidate from an explicitly identified source revision. The release process
must make the selected files and verification evidence inspectable.

A release candidate must pass through a PR with **human code review and
explicit approval** before reaching `main`. This release-specific PR
requirement does not require PRs for every development change. CI success
alone does not approve a release.

Review and approve any update to the 42 submission repository separately from
the GitHub `main` release. The development, release, and 42 submission
repositories/branches are distinct trust boundaries.

### Release candidate workflow

The workflow [`release-candidate.yml`](../.github/workflows/release-candidate.yml)
is started by hand (`workflow_dispatch`) from `develop`, and a push never
starts it. It is separate from the verification workflow.

1. **Dry run.** Run it with `source_sha` set to the full SHA of the `develop`
   commit to release. The commit must belong to `develop`'s history. With
   read-only permissions it runs `make lint` and `make test` on that commit,
   exports the files of the manifest, checks the export, and prints the
   **plan**: the files added, modified and deleted on `main`, and a plan hash.
2. **Review the plan.** Files that are on `main` but not allowed by the
   manifest are listed as *UNEXPECTED*. They are only deleted if the plan that
   lists them is approved in the next step.
3. **Publish.** Run it again with the same `source_sha` and
   `approved_plan_hash` set to the reviewed hash. Only this run has write
   permission (`contents`, `pull-requests`). It builds one commit on top of
   `main` from the blobs of the source commit, pushes it as `release/<12 hex
   of the SHA>` without force, and opens a PR into `main`. The plan depends
   on the source SHA, the manifest and the head of `main`. Later commits on
   `develop` are not part of it and never enter the candidate. If the manifest
   or `main` changed, the hash no longer matches and nothing is pushed.
4. **Review and merge by hand.** The PR lists the source SHA, the candidate
   commit, the changed files, the checks that ran and what was not verified.
   **Before merging, check the branch again**: run the workflow with the
   same `source_sha` and `verify_branch` set to the `release/*` branch (or run
   `python -m tools.prepare_submission verify --source <sha> --head
   origin/release/<12 hex>` locally). It must pass: it shows that the branch
   holds exactly the files of the source commit, as one commit on top of the
   current `main`. If the branch received any other commit, or `main` moved,
   make a new plan and approve it again. Merge (squash only) only after reading
   the diff. Nothing merges it automatically.
5. Submitting to the 42 repository is a separate operation.

Rerun and failure behavior: the same source and plan produce the same tree; an
existing `release/*` branch with the same tree and parent is reused, one with
different content stops the run, and a second open release PR is refused. No
step rewrites history. Deleting a stale `release/*` branch or closing a PR is
done by a person.

Settings the workflow relies on (check them, they are not changed by code):
Actions may create pull requests (repository setting *Allow GitHub Actions to
create and approve pull requests*; if it is off, the branch is still pushed
and the job summary gives the compare link and the PR text so that a person
opens the PR); the `release` environment may be given
required reviewers to gate the publish job; the ruleset *Protect release
branch* on `main` stays active.

What re-verifies a release PR: nothing, after it is open. GitHub's rule is
that events caused by `GITHUB_TOKEN` start no workflow run, except that a
`pull_request` event (opened, synchronize, reopened) from such a PR creates
runs that wait for a person to approve them. In this repository that does not
help: the verification workflow only runs for pull requests into `develop`, and
the candidate branch carries no workflow files. The ruleset on `main` requires
no status check and no approving review. The checks that exist are the ones in
the run that opened the PR (linked in its body) and the manual check before
merging described above; a change to the branch after review must be approved
again.

<a id="unexpected-files-on-main"></a>

### Candidate content and repository enforcement

Before a release, compare the proposed `main` contents with
[`submission-files.txt`](../submission-files.txt) and examine unexpected files.
Development-only tests, audit records, and tooling must not be included unless
explicitly selected and reviewed.

PR review is a **required policy**, but documentation alone does not enforce it.
Inspect the actual GitHub branch protection, rulesets, bypass permissions,
workflow configuration, and release-PR checks before releasing. Do not infer
technical enforcement from a historical audit.

<a id="documentation"></a>

## Documentation and approval

Maintain a single source of truth for each type of information:

| Information | Canonical location |
|---|---|
| Agent behavior, permissions, and approval boundaries | [`AGENTS.md`](../AGENTS.md) |
| Current implementation responsibilities and accepted shared contracts | [`architecture.md`](architecture.md) |
| Design decisions, status of acceptance, rationale, and human approval evidence | [`decisions.md`](decisions.md) |
| Work progress, unresolved questions, implementation/Subject mismatches, verification results, and acceptance criteria | Relevant GitHub Issues |
| Development, verification, and release **procedures** | This document |
| User-facing use, output, and evaluation instructions | [`README.md`](../README.md) |
| Executable build/check/release configuration | [Makefile](../Makefile), [workflow](../.github/workflows/verify-and-sync.yml), and [submission manifest](../submission-files.txt) |

The supplied Subject is authoritative for project requirements. Neither the
verifier, passing tests, historical notes, nor an Issue closure substitutes
for explicit human approval of a project-specific design decision.

- Update `AGENTS.md` **only** when the Agent behavior policy or document-routing
  rules change. Do not add project status or individual design conclusions.
- Update this document **only** when a development, verification, release, or
  documentation **procedure** changes. Do not add progress updates, open/closed
  issue counts, temporary failures, or descriptions of what a particular test
  suite currently accepts.
- Update `architecture.md` when responsibilities, accepted shared contracts,
  or implementation state changes; update `decisions.md` for approved,
  superseded, or rejected judgments; update relevant Issues for work progress
  and discrepancies. Update [`README.md`](../README.md) for user-facing changes.
- When documentation changes are necessary, keep affected canonical documents
  consistent with the code change. Review relative links and stale references.
  A PR is not mandatory for every development change, but a release PR requires
  human review and explicit approval.
- [Handoffs](../.agent/handoffs/2026-10-23-design-context.md) and audit records
  are historical evidence, not the current implementation or specification.
  Preserve provenance without copying historical status into procedure manuals.
