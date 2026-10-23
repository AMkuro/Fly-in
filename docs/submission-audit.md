# Fly-in submission automation audit

Date: 2026-10-23 JST.

## Scope and evidence

Audit the **mechanism**, not rewrite the drone program to pass it. Existing
implementation, README, requirements and Makefile are preserved from develop
commit `26651a3` (the separately authorized blocked-zone fix). Failures found by
the new checks remain failures.

Sources inspected live:

- Owner-provided Fly-in Subject at
  `/Users/miwasaki/42Tokyo/pdf/Fly-in/en.subject.pdf`, chapters III, V, VII, VIII, X.
  Embedded text was read locally with `pdftotext`; the PDF is not uploaded.
- [Codexion's workflow](https://github.com/AMkuro/Codexion/blob/develop/.github/workflows/sync-master.yml),
  inspected blob `757939a160a1d58fe084895a65b7c17f0e365583`.
- Codexion default branch `develop`, and its `main`/`master` branches, confirmed
  through GitHub metadata and branch queries.
- Fly-in initially had only remote `main` at
  `6c50f3748710425cf3afc8f0185c1b0d92c71ab1`. Current development work is moved
  to develop without deleting main or rewriting its history.

## Judgment

**Reuse the development-to-submission projection pattern, with changes.**
Codexion's C file selection and Norminette/build commands are not applicable
to Fly-in. Keeping an independent submission history is suitable; copying the
workflow verbatim would not establish Python or drone-simulation compliance.

| Codexion finding | Fly-in treatment |
| --- | --- |
| C/header glob selection and compiler checks | Explicit Python/runtime manifest and Subject-derived verification |
| Tests run only in the development checkout | Lint and execute the exported candidate as well |
| Write permission declared for the whole workflow | Read-only checks; write only in the publishing job |
| No explicit obsolete-source check | Compare the verified source SHA to remote develop before publishing |
| No independent movement validity check | Replay output against timing, occupancy and delivery constraints |
| Hard-coded README line deletion | Preserve the submitted README byte for byte |
| In-place checkout/removal to build submission | Read committed blobs; construct submission commits with an isolated index |
| No proof of complete Subject coverage | Document automated coverage and human-review limitations explicitly |

The allowlist is a repository policy, not a Subject-specified list of extensions.
The Subject requires a working Python submission and a root README/Makefile;
package paths are retained. The root-placement wording and the broader manual
requirements still require peer review. Tests stay on develop, matching III.3's
statement that test programs are not submitted or graded.

## Baseline failures to preserve and report

The project is incomplete. Publishing a bootstrap master does not change this.

| Check | Existing result / evidence |
| --- | --- |
| Movement output, VII.5 | CLI prints a map summary, not movement tokens; verification must fail |
| README, VIII | Description, Instructions, Algorithm, Visual Representation and Resources contain placeholders |
| Types, III/V | Existing `map_view.py` calls have mypy errors involving Canvas kwargs/font/anchor types |
| Docstrings, III | `FlyInApp` and `MapParseError.__init__` lack docstrings |
| Empty input, VII.4 | Raw builder indexes an empty list instead of producing a parser ValueError |
| Connection ordering, VII.4 | Existing parser accepts connections before endpoint declarations |
| Routing/scheduling/visual simulation, VII | Still absent; CI must not infer them from static GUI code |

No fixes to those existing files are included in this automation change.

## Validation evidence

The development-only verifier accepts hand-written legal streams and rejects
invalid tokens, unknown drones, duplicate moves, blocked entry, illegal jumps,
direct/late restricted arrivals, link/zone overflow and incomplete delivery.
Export tests exercise real temporary Git repositories, uncommitted/untracked
file exclusion, existing-destination refusal and symlink rejection.

Full local output is preserved in
[`verification-results.md`](verification-results.md).

The initial run confirms that verifier/export self-tests and the existing
blocked-zone regression pass. Subject parser contracts fail for empty input
and forward references. Full lint fails on the existing GUI type errors.
The Subject gate rejects the placeholder README and summary-only CLI. These
are findings in the existing implementation, not reasons to modify it here.

GitHub Actions results will be recorded after the workflow is published.
