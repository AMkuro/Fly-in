# Development and submission

`develop` is the development branch and GitHub default branch. `main` is retained
as historical data. `master` contains only the files selected by
[`submission-files.txt`](../submission-files.txt); do not merge development
history into it or edit it directly.

The initial `master` snapshot is explicitly **unverified**. It is created before
the project is complete at the repository owner's request. Its existence does
not mean the project is ready for evaluation. Later automated updates require
both CI jobs below to pass for the same develop revision.

## Checks

The workflow runs for pushes and pull requests to develop and supports manual
dispatch. No developer machine path or Subject PDF is needed in CI.

- **Quality**: Python 3.10 and 3.14, the existing `make install`, `make lint`, and
  `make test` commands. Tests run even if lint fails, to show both findings.
- **Subject submission gate**: exports the exact Git commit to a fresh directory,
  runs the existing lint target there, and runs the development-only verifier
  against the exported CLI. This job runs independently of Quality; the sync job
  requires both to pass. It does not fix the candidate or relax failing checks.

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
  attribution/AI disclosure. Content quality and English are reviewed manually.
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
Those remain peer-review items. Passing automation is necessary for syncing,
not a claim of complete Subject compliance.

## Automatic master updates

Only a successful push/manual run on `refs/heads/develop` can update master.
Pull requests have read-only workflow permissions and cannot publish. Write
permission is limited to the sync job. GitHub's workflow permission and event
semantics are documented in the
[official reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

The sync job exports the same immutable revision that passed the checks. It
checks the remote develop head to skip obsolete runs, serializes master updates,
and adds one commit to master's own history using a separate Git index. It does
not change the checkout or rewrite develop history. Pushes are fast-forward
only; a concurrent master change causes failure instead of being overwritten.
Identical exported contents cause no commit. Each generated commit records the
source develop SHA.

No branch-protection rules are installed by this setup. Maintainers can still
push manually, so enforcement here is the automated publication path, not an
access-control guarantee.

The migration audit and known baseline failures are in
[`submission-audit.md`](submission-audit.md).
