# Development and submission

This document defines **repeatable development, verification, and submission
procedures**. It is not a project status report. Do not record per-Issue
progress, temporary implementation gaps, pending design decisions, test
coverage snapshots, or resolved defects here. Follow the current sources of
truth identified in [Documentation and approval](#documentation).

## Branch and submission policy

`develop` is the development branch; `master` is reserved for reviewed
release/submission contents. `main` remains a separate branch; changing branch
roles requires an explicit decision.

Select submission contents using
[`submission-files.txt`](../submission-files.txt), rather than merging all
development history into `master`. The existence of a `master` snapshot does
not establish that the project is complete or verified.

CI is for verification only. It must not commit, push, publish warnings, or
release to `master` or the 42 submission repository automatically. A successful
check is evidence for review, not approval to submit.

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
explicit approval** before reaching `master`. This release-specific PR
requirement does not require PRs for every development change. CI success
alone does not approve a release.

Review and approve any update to the 42 submission repository separately from
the GitHub `master` release. The development, release, and 42 submission
repositories/branches are distinct trust boundaries.

<a id="unexpected-files-on-master"></a>

### Candidate content and repository enforcement

Before a release, compare the proposed `master` contents with
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
