"""Whole-input validation remains separate from graph construction."""

import tempfile
import unittest
from pathlib import Path

from fly_in.model.map_parse_error import MapParseError
from fly_in.model.parsed_map import ParsedMap
from fly_in.parse import FlyInMapParser
from fly_in.parse.map_validator import MapValidator


class MapValidatorTests(unittest.TestCase):
    def test_global_constraints_are_checked_after_parsing(self) -> None:
        """Validate relationships after parsing each local object."""
        base = (
            "nb_drones: 1\nstart_hub: A 0 0\nend_hub: B 1 0\n"
            "connection: A-B\n"
        )
        cases = (
            (base + "hub: A 2 0\n", 5, "duplicate zone"),
            (base.replace("A-B", "A-missing"), 4, "before connection"),
            (base + "connection: B-A\n", 5, "duplicate connection"),
            ("nb_drones: 1\n", None, "missing required"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.txt"
            for text, line, cause in cases:
                with self.subTest(cause=cause):
                    path.write_text(text, encoding="utf-8")
                    parsed = FlyInMapParser().load(str(path))
                    self.assertIsInstance(parsed, ParsedMap)
                    with self.assertRaises(MapParseError) as caught:
                        MapValidator(parsed).validate()
                    self.assertEqual(caught.exception.line_number, line)
                    self.assertIn(cause, str(caught.exception))
