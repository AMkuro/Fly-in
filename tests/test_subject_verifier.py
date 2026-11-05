"""Check the checker with hand-written valid and invalid movement streams."""

import contextlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fly_in.model.map_graph import MapGraph
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder
from tools.verify_subject import (
    MovementVerifier, OPTIMUM_TURNS, SubjectVerifier, VerifierTimeout,
    performance_note,
)


class ReadmeVerifierTests(unittest.TestCase):
    """Check required README structure without arbitrary text length."""

    README = (
        "*This project has been created as part of the 42 "
        "curriculum by miwasaki*\n"
        "\n## Description\nX\n## Instructions\nX\n"
        "## Algorithm and Implementation Strategy\nX\n"
        "## Visual Representation\nX\n## Resources\nX\n"
        "### AI Usage\nX\n"
    )

    def check(self, text: str) -> None:
        """Run the real README checker against a temporary candidate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(text)
            SubjectVerifier(root).check_readme()

    def test_short_sections_are_valid(self) -> None:
        """One-character text must not trigger an invented length rule."""
        self.check(self.README)
        self.check(self.README.replace(
            "miwasaki*", "miwasaki, another-login*"
        ))
        first, rest = self.README.split("\n", 1)
        self.check(first.replace("*", "_") + "\n" + rest)

    def test_ai_usage_heading_name_is_not_required(self) -> None:
        """B2: only Resources content is required, not a heading name."""
        self.check(self.README.replace("### AI Usage\nX\n", ""))
        self.check(self.README.replace("### AI Usage", "### How AI helped"))

    def test_algorithm_and_visual_headings_are_not_fixed(self) -> None:
        """Subject VIII asks for that content, not for these heading names."""
        self.check(self.README.replace(
            "## Algorithm and Implementation Strategy", "## Implementation"
        ).replace("## Visual Representation", "## GUI"))
        self.check(self.README.replace(
            "## Algorithm and Implementation Strategy\nX\n", ""
        ).replace("## Visual Representation\nX\n", ""))

    def test_first_line_is_required(self) -> None:
        """Require the exact italicized sentence on the first line."""
        for text in (
            "", "\n" + self.README, self.README.replace("*", ""),
            self.README.replace("42 curriculum", "curriculum"),
            self.README.replace("miwasaki", "<login1>"),
        ):
            with self.subTest(text=text), self.assertRaisesRegex(
                ValueError, "attribution"
            ):
                self.check(text)

    def test_sections_and_real_content_are_required(self) -> None:
        """Reject missing headings and HTML-comment-only placeholders."""
        for text in (
            self.README.replace("## Instructions", "## Other"),
            self.README.replace(
                "## Description\nX", "## Description\n<!-- X -->"
            ),
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check(text)


class MovementVerifierTests(unittest.TestCase):
    """Keep scheduling expectations independent from any solver output."""

    def setUp(self) -> None:
        """Load a small graph with ordinary, restricted and blocked routes."""
        parsed = FlyInMapParser().load(
            "tests/fixtures/subject/mixed_zones.txt"
        )
        self.scenario = ScenarioBuilder().build(parsed)
        self.data = self.scenario.graph
        self.verifier = MovementVerifier(self.scenario)

    def widen(
        self, link_indexes: tuple[int, ...] = (), zone: str | None = None
    ) -> MovementVerifier:
        """Verify against a copied graph with capacity 2 where requested."""
        graph = self.data
        zones = dict(graph.zones)
        if zone is not None:
            zones[zone] = zones[zone].model_copy(update={"max_drones": 2})
        connections = [
            c.model_copy(update={"max_link_capacity": 2})
            if i in link_indexes else c
            for i, c in enumerate(graph.connections)
        ]
        scenario = replace(
            self.scenario, graph=MapGraph.from_models(zones, connections)
        )
        return MovementVerifier(scenario)

    def test_departures_free_capacity_on_same_turn(self) -> None:
        """Allow another drone into a zone vacated during the same turn."""
        output = "D1-a\nD1-end D2-a\nD2-end\n"
        self.assertEqual(self.verifier.verify(output), 3)

    def test_restricted_transit(self) -> None:
        """Require a connection token followed by arrival on the next turn."""
        output = "D1-start-r\nD1-r\nD1-end D2-start-r\nD2-r\nD2-end\n"
        self.assertEqual(self.verifier.verify(output), 5)

    def test_restricted_arrival_frees_link_this_turn(self) -> None:
        """A new restricted crossing may start during a forced arrival."""
        output = (
            "D1-start-r\n"
            "D1-r D2-start-r\n"
            "D1-end D2-r\n"
            "D2-end\n"
        )
        self.assertEqual(self.verifier.verify(output), 4)

    def test_restricted_connection_starts_still_obey_capacity(self) -> None:
        """Two new starts on a capacity-1 connection are not legal."""
        with self.assertRaisesRegex(ValueError, "connection capacity"):
            self.verifier.verify("D1-start-r D2-start-r\n")

    def test_connection_token_uses_travel_direction(self) -> None:
        """Traversal works when the map declares the edge in reverse order."""
        connections = [
            connection.model_copy(
                update={"name": "r-start", "a": "r", "b": "start"}
            ) if connection.name == "start-r" else connection
            for connection in self.data.connections
        ]
        scenario = replace(
            self.scenario,
            graph=MapGraph.from_models(self.data.zones, connections),
        )
        output = (
            "D1-start-r\n"
            "D1-r D2-start-r\n"
            "D1-end D2-r\n"
            "D2-end\n"
        )
        self.assertEqual(MovementVerifier(scenario).verify(output), 4)

    def test_legal_delayed_plan_is_not_rejected_by_turn_count(self) -> None:
        """Turn count is a metric, not a mandatory validity threshold."""
        output = (
            ("D1-a\nD1-start\n" * 4)
            + "D1-a\nD1-end D2-a\nD2-end\n"
        )
        self.assertEqual(self.verifier.verify(output), 11)

    def test_invalid_streams_are_rejected(self) -> None:
        """Reject malformed, incomplete and illegal movement sequences."""
        for output in (
            "", "Map loaded: 2 drones", "D1-a\n", "D3-a\n",
            "D1-a D1-a\n", "D1-end\n", "D1-b\n", "D1-r\n",
            "D1-start-r\n\n", "D1-start-r\nD1-end\n",
            "D1-a D2-a\n", "D1-start-r\nD1-r D2-start-r\n",
            "D1-a\nD1-end D2-a\nD1-a D2-end\n",
            "D1-a\nD1-end D2-a\nD2-end\n\n",
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.verifier.verify(output)

    def test_zone_capacity_is_independent_of_link_capacity(self) -> None:
        """A wider connection must not allow excess zone occupancy."""
        verifier = self.widen(link_indexes=(0,))
        with self.assertRaisesRegex(ValueError, "zone capacity"):
            verifier.verify("D1-a D2-a\n")

    def test_capacity_metadata_is_honored(self) -> None:
        """Allow concurrent traversal only when both capacities permit it."""
        verifier = self.widen(link_indexes=(0, 1), zone="a")
        output = "D1-a D2-a\nD1-end D2-end\n"
        self.assertEqual(verifier.verify(output), 2)

    def test_opposite_directions_share_one_link_capacity(self) -> None:
        """Subject VII.2: both directions count toward one connection."""
        crossing = "D1-a\nD1-start D2-a\nD1-a D2-end\nD1-end\n"
        with self.assertRaisesRegex(ValueError, "connection capacity"):
            self.verifier.verify(crossing)
        self.assertEqual(self.widen(link_indexes=(0,)).verify(crossing), 4)

    def test_forced_arrival_still_needs_zone_capacity(self) -> None:
        """A forced arrival into a zone still held by a drone is illegal."""
        stay = "D1-start-r\nD1-r D2-start-r\nD2-r\n"
        with self.assertRaisesRegex(ValueError, "zone capacity"):
            self.verifier.verify(stay)
        leave = "D1-start-r\nD1-r D2-start-r\nD1-end D2-r\nD2-end\n"
        self.assertEqual(self.verifier.verify(leave), 4)

    def test_end_zone_takes_several_arrivals_in_one_turn(self) -> None:
        """Subject VII.2: the end zone has no occupancy limit."""
        output = "D1-a D2-start-r\nD2-r\nD1-end D2-end\n"
        self.assertEqual(self.verifier.verify(output), 3)

    def test_listing_order_within_a_turn_is_irrelevant(self) -> None:
        """Subject VII.3: moves are simultaneous, not applied in order."""
        for second in ("D2-a D1-end", "D1-end D2-a"):
            with self.subTest(second=second):
                output = f"D1-a\n{second}\nD2-end\n"
                self.assertEqual(self.verifier.verify(output), 3)

    def test_illegal_tokens_and_connections_are_rejected(self) -> None:
        """Reject wrong direction, missing links, blocked and bad IDs."""
        for output, reason in (
            ("D1-start-b\n", "restricted"),
            ("D1-start-a\n", "restricted"),
            ("D1-r-start\n", "origin mismatch"),
            ("D1-a-end\n", "origin mismatch"),
            ("D1-start-end\n", "disconnected"),
            ("D1-start-r\nD1-start\n", "arrival required"),
            ("D0-a\n", "invalid token"),
            ("D01-a\n", "invalid token"),
        ):
            with self.subTest(output=output), self.assertRaisesRegex(
                ValueError, reason
            ):
                self.verifier.verify(output)

    def test_idle_turn_is_not_judged_by_shortness(self) -> None:
        """B5: a redundant all-wait line is legal; trailing ones are not."""
        self.assertEqual(
            self.verifier.verify("D1-a\n\nD1-end D2-a\nD2-end\n"), 4
        )
        with self.assertRaisesRegex(ValueError, "continues"):
            self.verifier.verify("D1-a\nD1-end D2-a\nD2-end\n\n")

    def test_only_sgr_colors_are_stripped(self) -> None:
        """B6: other control sequences and extra stdout stay invalid."""
        for output in (
            "\x1b[2JD1-a\n", "D1-a\x1b[K\n", "D1-a\r\r\n", "\x07D1-a\n",
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.verifier.verify(output)

    def test_turn_count_and_ansi_colors(self) -> None:
        """Count turns, while allowing terminal color escape sequences."""
        output = "\x1b[32mD1-a\x1b[0m\nD1-end D2-a\nD2-end\n"
        self.assertEqual(self.verifier.verify(output), 3)


class PerformanceReportTests(unittest.TestCase):
    """Optimum values come from Subject VII.6, typed in independently."""

    SUBJECT_TABLE = {
        "easy/01_linear_path.txt": 4, "easy/02_simple_fork.txt": 4,
        "easy/03_basic_capacity.txt": 4,
        "medium/01_dead_end_trap.txt": 8,
        "medium/02_circular_loop.txt": 10,
        "medium/03_priority_puzzle.txt": 6,
        "hard/01_maze_nightmare.txt": 13,
        "hard/02_capacity_hell.txt": 16,
        "hard/03_ultimate_challenge.txt": 26,
        "challenger/01_the_impossible_dream.txt": 43,
    }

    def test_optimum_table_matches_subject(self) -> None:
        """Guard against typos, and against the old 45-turn figure."""
        self.assertEqual(OPTIMUM_TURNS, self.SUBJECT_TABLE)

    def test_note_classifies_without_gating(self) -> None:
        """Hand-computed: 4 optimal, 5 is exactly +25%, 6 is over."""
        key = "easy/01_linear_path.txt"
        self.assertIn("optimal", performance_note(key, 4))
        self.assertIn("within 25%", performance_note(key, 5))
        self.assertIn("over 25%", performance_note(key, 6))
        self.assertIn("within 25%", performance_note(
            "challenger/01_the_impossible_dream.txt", 53))
        self.assertIn("over 25%", performance_note(
            "challenger/01_the_impossible_dream.txt", 54))
        self.assertIn("below reference", performance_note(key, 3))
        self.assertEqual(performance_note("subject/mixed_zones.txt", 99), "")


class StructureVerifierTests(unittest.TestCase):
    """Makefile lint command (III.2), unreachable report, optional map."""

    FLAGS = (
        "--warn-return-any --warn-unused-ignores --ignore-missing-imports "
        "--disallow-untyped-defs --check-untyped-defs"
    )
    LINT = (
        f"PY = python\nCHECK = flake8\n\nlint:\n\t$(PY) -m $(CHECK) .\n"
        f"\t$(PY) -m mypy . \\\n\t\t{FLAGS}\n"
        "\nlint-strict:\n\tflake8 .\n\tmypy . --strict\n"
    )

    def lint(self, makefile: str) -> None:
        """Run the real lint-rule check on a temporary Makefile."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Makefile").write_text(makefile)
            SubjectVerifier(root).check_lint_rule()

    def test_lint_rule_is_judged_on_expanded_commands(self) -> None:
        """Variables and continuations are fine; the real command counts."""
        self.lint(self.LINT)
        self.lint(self.LINT.replace("$(PY) -m $(CHECK) .", "flake8 ."))

    def test_lint_rule_that_does_not_run_the_tools_is_rejected(self) -> None:
        """Quoting, comments and lint-strict must not satisfy `lint`."""
        for old, new in (
            ("$(PY) -m $(CHECK) .", 'echo "flake8 ."'),
            ("$(PY) -m $(CHECK) .", "# flake8 ."),
            ("$(PY) -m $(CHECK) .", "$(PY) -m $(CHECK)"),
            ("$(PY) -m mypy .", 'printf "mypy ."'),
        ):
            with self.subTest(new=new), self.assertRaisesRegex(
                ValueError, "does not run"
            ):
                self.lint(self.LINT.replace(old, new, 1))
        with self.assertRaises(ValueError):
            self.lint("lint:\n\ttrue\n\nlint-strict:\n\tmypy . --strict\n")
        with self.assertRaisesRegex(ValueError, "make -n lint failed"):
            self.lint("other:\n\ttrue\n")

    def test_lint_rule_missing_flag_is_rejected(self) -> None:
        """Reject each missing mypy flag."""
        for flag in self.FLAGS.split():
            with self.subTest(flag=flag), self.assertRaisesRegex(
                ValueError, "lacks mypy flag"
            ):
                self.lint(self.LINT.replace(flag, "", 1))

    def unreachable(
        self, script: str, fixtures: Path | None = None
    ) -> None:
        """Run the check against a stub CLI instead of the real one."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fly-in.py").write_text(script)
            SubjectVerifier(root).check_unreachable(fixtures)

    def test_unreachable_report_is_required(self) -> None:
        """Accept only exit 1, the DEC-013 stderr line and empty stdout."""
        stub = (
            "import sys\nprint({out!r})\n"
            "print({msg!r}, file=sys.stderr)\nsys.exit({code})\n"
        )
        good = "Error: No path from start to end."
        self.unreachable(stub.format(out="", msg=good, code=1))
        for out, msg, code in (
            ("", good, 0), ("", good, 2), ("", "boom", 1), ("", "", 1),
            ("D1-x", good, 1),
        ):
            with self.subTest(out=out, msg=msg, code=code), (
                self.assertRaises(ValueError)
            ):
                self.unreachable(stub.format(out=out, msg=msg, code=code))

    def test_missing_unreachable_fixture_fails(self) -> None:
        """An empty fixture directory must not pass silently."""
        with tempfile.TemporaryDirectory() as empty, self.assertRaisesRegex(
            ValueError, "missing unreachable fixtures"
        ):
            self.unreachable("", Path(empty))

    def test_timeout_is_unverified_not_a_violation(self) -> None:
        """B7: a hang is reported as a timeout, never as a rule failure."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fly-in.py").write_text("import time\ntime.sleep(30)\n")
            with self.assertRaisesRegex(VerifierTimeout, "unverified"):
                SubjectVerifier(root, timeout=0.5).check_unreachable()
        self.assertFalse(issubclass(VerifierTimeout, ValueError))

    def files(self, names: tuple[str, ...], makefile: str) -> None:
        """Run the real root-file check on a temporary candidate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in names:
                (root / name).write_text("")
            (root / "Makefile").write_text(makefile)
            SubjectVerifier(root).check_files()

    def test_only_subject_root_files_are_required(self) -> None:
        """B3: requirements.txt/.flake8 are not Subject-mandated files."""
        base = ("README.md", "fly-in.py", ".gitignore")
        self.files(base, "install:\n\ttrue\n")
        self.files(base + ("requirements.txt",),
                   "install:\n\tpip install -r requirements.txt\n")
        for missing in base:
            with self.subTest(missing=missing), self.assertRaisesRegex(
                ValueError, "missing root file"
            ):
                self.files(tuple(n for n in base if n != missing),
                           "install:\n\ttrue\n")

    def test_file_named_by_makefile_must_exist(self) -> None:
        """B3: a dependency file the Makefile uses is still checked."""
        with self.assertRaisesRegex(ValueError, "requirements.txt"):
            self.files(("README.md", "fly-in.py", ".gitignore"),
                       "install:\n\tpip install -r requirements.txt\n")

    def test_real_cli_reports_unreachable(self) -> None:
        """Integration: the shipped CLI satisfies the DEC-013 contract."""
        SubjectVerifier(Path(__file__).resolve().parents[1]
                        ).check_unreachable()

    def test_challenger_is_optional(self) -> None:
        """A broken Challenger run warns and is not a mandatory case."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            maps = root / "maps"
            for category in ("easy", "medium", "hard", "challenger"):
                (maps / category).mkdir(parents=True)
                (maps / category / "x.txt").write_text("not a map\n")
            (root / "fly-in.py").write_text("raise SystemExit(1)\n")
            verifier = SubjectVerifier(root)
            names = {path.parent.name for path in verifier.mandatory_cases()}
            self.assertNotIn("challenger", names)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                verifier.check_challenger()
            self.assertIn("WARN optional x.txt", out.getvalue())
            with self.assertRaises(ValueError):
                verifier.check_movements()
