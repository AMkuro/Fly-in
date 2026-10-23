"""Check the checker with hand-written valid and invalid movement streams."""

import unittest
from pathlib import Path

from fly_in.parse.map_parser import FlyInMapParser
from tools.verify_subject import MovementVerifier


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
