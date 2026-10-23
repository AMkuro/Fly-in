"""Check the checker with hand-written valid and invalid movement streams."""

import tempfile
import unittest
from pathlib import Path

from fly_in.parse.map_parser import FlyInMapParser
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
        self.data = FlyInMapParser().load(
            Path("tests/fixtures/subject/mixed_zones.txt")
        )

    def test_departures_free_capacity_on_same_turn(self) -> None:
        """Allow another drone into a zone vacated during the same turn."""
        output = "D1-a\nD1-end D2-a\nD2-end\n"
        self.assertEqual(MovementVerifier(self.data).verify(output, 3), 3)

    def test_restricted_transit(self) -> None:
        """Require a connection token followed by arrival on the next turn."""
        output = "D1-start-r\nD1-r\nD1-end D2-start-r\nD2-r\nD2-end\n"
        self.assertEqual(MovementVerifier(self.data).verify(output, 5), 5)

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
                MovementVerifier(self.data).verify(output, 12)

    def test_zone_capacity_is_independent_of_link_capacity(self) -> None:
        """A wider connection must not allow excess zone occupancy."""
        self.data.connections[0].max_link_capacity = 2
        with self.assertRaisesRegex(ValueError, "zone capacity"):
            MovementVerifier(self.data).verify("D1-a D2-a\n", 12)

    def test_capacity_metadata_is_honored(self) -> None:
        """Allow concurrent traversal only when both capacities permit it."""
        self.data.connections[0].max_link_capacity = 2
        self.data.connections[1].max_link_capacity = 2
        self.data.zones["a"].max_drones = 2
        output = "D1-a D2-a\nD1-end D2-end\n"
        self.assertEqual(MovementVerifier(self.data).verify(output, 2), 2)

    def test_turn_limit_and_ansi_colors(self) -> None:
        """Count turns, while allowing terminal color escape sequences."""
        output = "\x1b[32mD1-a\x1b[0m\nD1-end D2-a\nD2-end\n"
        self.assertEqual(MovementVerifier(self.data).verify(output, 3), 3)
        with self.assertRaisesRegex(ValueError, "turn limit"):
            MovementVerifier(self.data).verify(output, 2)
