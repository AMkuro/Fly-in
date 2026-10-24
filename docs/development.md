# Development and submission

`develop` is the development branch and GitHub default branch. `main`, `develop`
and `master` are retained; any change to the role of main is a separate decision.
`master` is for reviewed release/submission contents, selected using
[`submission-files.txt`](../submission-files.txt); do not merge development
history wholesale into it. CI performs verification only and never updates master.

The initial `master` snapshot is explicitly **unverified**. It is created before
the project is complete at the repository owner's request. Its existence does
not mean the project is ready for evaluation. CI success does not publish or
approve a release.

## Checks

The workflow runs for pushes and pull requests to develop and supports manual
dispatch. No developer machine path or Subject PDF is needed in CI.

- **Quality**: Python 3.10 and 3.14, the existing `make install`, `make lint`, and
  `make test` commands. Tests run even if lint fails, to show both findings.
- **Subject submission gate**: exports the exact Git commit to a fresh directory,
  runs the existing lint target there, and runs the development-only verifier
  against the exported CLI. This job runs independently of Quality. It does not
  fix the candidate or relax failing checks, and does not publish the candidate.

Use a working virtual environment for local checks. The Makefile's `PYTHON`
variable can point to an existing environment:

```sh
make test PYTHON=/path/to/venv/bin/python
make lint PYTHON=/path/to/venv/bin/python
/path/to/venv/bin/python -m tools.export_submission /tmp/fly-in-candidate
/path/to/venv/bin/python -m tools.verify_subject /tmp/fly-in-candidate
```

The export destination must not already exist. Exports use committed files, not
unstaged changes. The manifest is read from that same commit. Runtime sources,
dependencies, README and supplied input maps are retained; development tests,
tools, workflows and audit documents are excluded. Paths are preserved so Python
imports and Makefile defaults keep working. The Makefile and entry point are at
the root of the exported repository.

## Automated Subject coverage

The reference is the supplied Fly-in Subject: III (Python, types, docstrings,
Makefile), V (graph library restrictions), VII.2–VII.5 (occupancy, movement,
parsing and output), VII.7 (performance), VIII (README), X (deliverables).

The movement verifier uses parsed map facts but does not call the graph,
pathfinder or scheduler. Its own tests use hand-written valid and invalid
streams, independent of the application's output. The parser has a separate
contract suite so it is not trusted as its own input-validation oracle.

Checks include:

- Required root files, Makefile target names, nonempty README sections and the
  attribution/AI disclosure. The exact first-line sentence must be italicized
  with `*` or `_` and contain one or more login names. There is no minimum text
  length. HTML comments do not count as section content. Content quality and
  English are reviewed manually.
- Python syntax, class/function docstrings, and direct imports of known graph
  libraries. This is not a proof against dynamic imports or unlisted libraries.
- Invalid parser inputs: empty maps, missing or duplicate declarations, bad
  coordinates, metadata, capacities, endpoints and forward references.
- Exact movement tokens, known drone IDs and destinations, valid adjacency,
  no duplicated moves, and no movement after delivery.
- Blocked-zone exclusion, mandatory next-turn restricted arrival, zone capacity,
  and aggregate bidirectional connection capacity. Occupancy is checked after
  simultaneous departures. Restricted transit counts against the connection on
  both departure and arrival turns. The start is treated as an occupancy
  exception; the Subject's treatment of returning to start merits human review.
- All drones delivered, no output after completion, and a per-map process timeout.
- All supplied easy, medium and hard maps. General turn limits are respectively
  9, 30 and 59, following the Subject's general targets. The named per-map bonus
  targets and optional challenger record are not gates. A synthetic map also
  exercises normal, restricted and blocked routes.

CI does **not** prove optimality, priority preference, complete object-oriented
design, GUI usefulness, resource safety, or behavior for every possible graph.
Those remain peer-review items. Passing automation is evidence for review,
not release approval or a claim of complete Subject compliance.

## Verification-only CI

The [workflow](../.github/workflows/verify-and-sync.yml) retains develop push,
pull-request and manual-dispatch triggers, with only Quality and Subject
submission gate jobs. All workflow permissions are read-only and both checkouts
set `persist-credentials: false`. There is no publishing job, commit creation,
master push, warning-file publication or release dispatch path. Even when both
checks pass, neither push-triggered nor manual runs update master.

The workflow filename is retained to avoid unrelated renaming. Earlier audit
and verification records describe the retired sync mechanism, not current CI.
Changes take effect on GitHub only after this revision is pushed. Older workflow
revisions or already-running jobs are not changed by this local edit; an old
manual run must not be used to publish a release.

## Reviewed releases

Release policy: release at version changes or important milestones. A release
candidate must go through a PR with human code review and explicit approval
before it reaches master. This release-specific PR requirement does not require
PRs for every development change. CI success alone does not authorize a release.
The GitHub submission branch and the 42 intranet repository remain separate;
42 submission also requires human review and approval.

Candidate creation and the PR-based release mechanism are **not implemented**
by this change. A later task must define how selected files become a reviewable
candidate, how its source revision and verification evidence are recorded, and
how the approved candidate is applied without importing development-only files.
The current PR checks target develop, not master; release-PR validation is also
part of that later task. No automatic PR creation or release workflow is added.

<a id="unexpected-files-on-master"></a>

[`tools/export_submission.py`](../tools/export_submission.py) and the manifest
remain available for exporting committed candidate files. The existing
[`tools/prepare_submission.py`](../tools/prepare_submission.py) is retained but
is not called by CI. Its old warning text describes retired automation and must
be reviewed before reusing that helper in a future release mechanism. It does
not itself commit or push. CI no longer creates or clears `SUBMISSION_WARNING.md`.

`.flake8` remains shared lint configuration in the manifest, not cache data.

### Policy versus GitHub enforcement

On 2026-10-24 JST, read-only GitHub API queries for master returned
`404 Branch not protected` from the branch-protection endpoint and an empty
list from the applicable branch-rules endpoint. PR review is therefore an
operational requirement, **not confirmed technical enforcement** against direct
pushes or bypasses. Repository settings were not changed. Recheck protection and
rulesets, including approval and bypass settings, before establishing releases.

The historical migration audit and baseline failures remain in
[`submission-audit.md`](submission-audit.md).

<a id="documentation"></a>

## Documentation and approval

- [`AGENTS.md`](../AGENTS.md) is the canonical source for Agent behavior and
  approval boundaries. Human code review and separate approval are required
  before changes reach master or the 42 submission repository. The release
  policy above requires a reviewed, explicitly approved PR; verification-only
  CI neither publishes nor enforces repository branch protection.
- [`architecture.md`](architecture.md) owns current responsibilities and
  accepted shared contracts; [`decisions.md`](decisions.md) owns decision IDs,
  conclusions, approval evidence and rationale. This document owns development,
  verification and submission procedures. [`README.md`](../README.md) owns
  user-facing execution and evaluation explanations and must remain useful in
  the exported submission, where development documents are absent. Executable
  settings remain in Makefile, workflow and submission manifest; link to them
  rather than maintaining a second configuration list.
- The supplied Subject remains authoritative for requirements. The development
  verifier may contain an unapproved Connection-capacity interpretation; its
  departure/arrival counting above describes existing behavior, not a settled
  specification. Detailed auditing is deferred; see DEC-002 in the decision index.
- Update architecture for responsibility, shared-contract or implementation-state
  changes; decisions for newly approved or superseded judgments; this document
  for procedure changes; README for user-visible changes. Update affected code
  and documents in the same change unit. If using a PR, include both in that PR;
  a PR is not mandatory for every change. The change author checks related links
  and stale descriptions; humans approve design changes. Internal changes with
  no documentation impact need no document edit.
- Issues own discussion and unresolved progress once a topic is transferred;
  the decision index then links to the Issue without copying progress. Record
  an explicit human approval reference when formalizing a decision; closing an
  Issue alone is not approval. Projects, if used, own progress and priority only.
  Preserve superseded rationale with a successor link and update current
  contracts together.
- [Handoffs](../.agent/handoffs/2026-10-23-design-context.md), audit and verification
  records are historical evidence, not current specifications or current test
  results. Preserve their original content; reference them for provenance.
  Create a handoff only when unfinished context is needed to resume work, and
  link to canonical decisions rather than duplicating them. Before completing a
  change, check relative links, approval states, affected references and diff scope.
