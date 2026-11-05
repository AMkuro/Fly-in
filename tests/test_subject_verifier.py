"""Check the checker with hand-written valid and invalid movement streams."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fly_in.model.map_graph import MapGraph
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder
from tools.verify_subject import MovementVerifier, SubjectVerifier


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
            self.README.replace("### AI Usage", "### Other"),
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

    def test_turn_count_and_ansi_colors(self) -> None:
        """Count turns, while allowing terminal color escape sequences."""
        output = "\x1b[32mD1-a\x1b[0m\nD1-end D2-a\nD2-end\n"
        self.assertEqual(self.verifier.verify(output), 3)
