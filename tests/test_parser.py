"""Subject VII.4 parser contract and CLI error handling checks."""

import subprocess
import sys
import tempfile
import unittest
from itertools import permutations
from pathlib import Path

from fly_in.model.map_data import MapData, ZoneType
from fly_in.parse.map_parser import FlyInMapParser


class ParserTests(unittest.TestCase):
    """Reject malformed input without unhandled exceptions."""

    MAP = (
        "nb_drones: 2\nstart_hub: start 0 0\nend_hub: end 1 0\n"
        "connection: start-end\n"
    )

    def test_invalid_inputs(self) -> None:
        """Cover missing/duplicate fields, bad metadata and forward links."""
        for text in (
            "", "# comments only\n",
            self.MAP.replace("nb_drones: 2", "nb_drones: 0"),
            self.MAP.replace("nb_drones: 2", "nb_drones: x"),
            self.MAP.replace("start_hub: start 0 0\n", ""),
            self.MAP.replace("end_hub: end 1 0\n", ""),
            self.MAP.replace("end 1 0", "start 1 0"),
            self.MAP.replace("end 1 0", "end 1.5 0"),
            self.MAP.replace("end 1 0", "end 1 0 [zone=invalid]"),
            self.MAP.replace("end 1 0", "end 1 0 [max_drones=0]"),
            self.MAP.replace("end 1 0", "end 1 0 [zone=normal"),
            self.MAP.replace("start-end", "start-unknown"),
            self.MAP.replace("start-end", "start-start"),
            self.MAP.replace("start-end", "start-end [max_link_capacity=0]"),
            self.MAP + "connection: end-start\n",
            self.MAP + "nb_drones: 3\n",
            "nb_drones: 2\nconnection: start-end\n"
            "start_hub: start 0 0\nend_hub: end 1 0\n",
        ):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as d:
                path = Path(d) / "invalid.txt"
                path.write_text(text)
                with self.assertRaises(ValueError):
                    FlyInMapParser().load(path)
                result = subprocess.run(
                    [sys.executable, "fly-in.py", str(path)],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("Configuration error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def load_text(self, text: str) -> MapData:
        """Parse one temporary UTF-8 map through the public API."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.txt"
            path.write_text(text, encoding="utf-8")
            return FlyInMapParser().load(path)

    def assert_invalid(self, text: str, message: str) -> None:
        """Require the same useful error from the parser and CLI."""
        with self.assertRaisesRegex(ValueError, message):
            self.load_text(text)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.txt"
            path.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "fly-in.py", str(path)],
                capture_output=True, text=True, timeout=10,
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Configuration error:", result.stderr)
        self.assertRegex(result.stderr, message)
        self.assertNotIn("Traceback", result.stderr)

    def test_no_declarations(self) -> None:
        """Explain inputs with no meaningful line without inventing a line."""
        for text in ("", "\n \t\n", "# comment\n\n# more\n"):
            with self.subTest(text=text):
                self.assert_invalid(text, "no map declarations")

    def test_declaration_order(self) -> None:
        """Only the count is first; connections need prior endpoints."""
        for text, message in (
            ("hub: a 0 0\n" + self.MAP, "line 1: first meaningful"),
            ("nb_drones: 2\nconnection: start-end\n"
             "start_hub: start 0 0\nend_hub: end 1 0\n",
             "line 2:.*'start'.*before"),
            ("nb_drones: 2\nstart_hub: start 0 0\n"
             "connection: start-end\nend_hub: end 1 0\n",
             "line 3:.*'end'.*before"),
            (self.MAP.replace("start-end", "start-missing"),
             "line 4:.*unknown zone 'missing'"),
        ):
            with self.subTest(text=text):
                self.assert_invalid(text, message)
        data = self.load_text(
            "# comment\n\nnb_drones: 2\nhub: a 0 0\n"
            "end_hub: end 1 0\nconnection: a-end\n"
            "start_hub: start 0 0\nconnection: start-a\n"
        )
        self.assertEqual(len(data.connections), 2)
        self.assertEqual(data.zones["a"].line_number, 4)

    def test_singletons_and_duplicate_names(self) -> None:
        """Identify missing fields and the later duplicate source line."""
        for declaration in ("nb_drones: 2", "start_hub: start 0 0",
                            "end_hub: end 1 0"):
            key = declaration.split(":")[0]
            with self.subTest(key=key):
                self.assert_invalid(
                    self.MAP + declaration + "\n",
                    f"line 5: duplicate {key}.*line [123]",
                )
        for key in ("start_hub", "end_hub"):
            text = "\n".join(
                line for line in self.MAP.splitlines()
                if not line.startswith(key + ":")
                and not line.startswith("connection:")
            )
            with self.subTest(key=key):
                self.assert_invalid(text, f"missing.*{key}")
        for text, line, first in (
            (self.MAP + "hub: start 2 2\n", 5, 2),
            ("nb_drones: 2\nhub: a 0 0\nstart_hub: a 1 0\n"
             "end_hub: end 2 0\n", 3, 2),
            (self.MAP.replace("end 1 0", "start 1 0"), 3, 2),
        ):
            with self.subTest(text=text):
                self.assert_invalid(
                    text, f"line {line}: duplicate zone.*line {first}"
                )
        self.assert_invalid(
            self.MAP + "connection: end-start\n",
            "line 5: duplicate connection.*line 4",
        )

    def test_integer_boundaries(self) -> None:
        """Reject decimal spellings rather than silently coercing integers."""
        for value in ("0", "-1", "1.0", "1.5", "x", "1e2"):
            for original, replacement, line, field in (
                ("nb_drones: 2", f"nb_drones: {value}", 1, "nb_drones"),
                ("end 1 0", f"end 1 0 [max_drones={value}]",
                 3, "max_drones"),
                ("start-end", f"start-end [max_link_capacity={value}]",
                 4, "max_link_capacity"),
            ):
                with self.subTest(value=value, field=field):
                    self.assert_invalid(
                        self.MAP.replace(original, replacement),
                        f"line {line}:.*{field}",
                    )
        for coordinate in ("1.0", "1.5", "1e2", "x"):
            for values in (f"{coordinate} 0", f"0 {coordinate}"):
                with self.subTest(values=values):
                    self.assert_invalid(
                        self.MAP.replace("end 1 0", f"end {values}"),
                        "line 3:.*integer",
                    )
        data = self.load_text(self.MAP.replace(
            "nb_drones: 2", "nb_drones: " + "9" * 100
        ).replace("end 1 0", "end -12 +34 [max_drones=999999999999]"))
        self.assertEqual(data.nb_drones, int("9" * 100))
        self.assertEqual((data.zones["end"].x, data.zones["end"].y),
                         (-12, 34))

    def test_metadata_syntax_and_scope(self) -> None:
        """Reject malformed brackets, duplicate keys and unsupported fields."""
        for metadata in (
            "[zone=normal", "zone=normal]", "]zone=normal[",
            "[[zone=normal]]", "[zone=normal] [color=red]",
            "[zone=normal] trailing", "[zone]", "[=normal]", "[zone=]",
            "[zone=normal zone=blocked]", "[color=red color=red]",
            "[zone=invalid]", "[unknown=x]", "[max_link_capacity=2]",
            "[zone_type=blocked]", "[name=overwritten]",
        ):
            with self.subTest(metadata=metadata):
                self.assert_invalid(
                    self.MAP.replace("end 1 0", f"end 1 0 {metadata}"),
                    "line 3:",
                )
        for metadata in ("[max_drones=2]", "[zone=normal]", "[color=red]",
                         "[max_link_capacity=1 max_link_capacity=2]"):
            with self.subTest(metadata=metadata):
                self.assert_invalid(
                    self.MAP.replace("start-end", f"start-end {metadata}"),
                    "line 4:",
                )

    def test_metadata_defaults_and_order(self) -> None:
        """Keep arbitrary single-word colors, all zone types and defaults."""
        data = self.load_text(self.MAP)
        self.assertEqual(data.zones["end"].zone_type, ZoneType.NORMAL)
        self.assertIsNone(data.zones["end"].color)
        self.assertEqual(data.zones["end"].max_drones, 1)
        self.assertEqual(data.connections[0].max_link_capacity, 1)
        for zone_type in ZoneType:
            for order in permutations((
                f"zone={zone_type.value}", "color=任意色", "max_drones=2"
            )):
                tags = " ".join(order)
                with self.subTest(tags=tags):
                    data = self.load_text(self.MAP.replace(
                        "end 1 0", f"end 1 0 [{tags}] # comment"
                    ).replace("start-end", "start-end [max_link_capacity=3]"))
                    self.assertEqual(data.zones["end"].zone_type, zone_type)
                    self.assertEqual(data.zones["end"].color, "任意色")
                    self.assertEqual(data.zones["end"].max_drones, 2)
                    self.assertEqual(data.connections[0].max_link_capacity, 3)
        self.load_text(self.MAP.replace("end 1 0", "end 1 0 []"))

    def test_names_and_line_syntax(self) -> None:
        """Preserve non-ASCII names and reject broken names and payloads."""
        data = self.load_text(self.MAP.replace(
            ": start ", ": 始点_1 "
        ).replace(": end ", ": 終点.2 ").replace("start-end", "始点_1-終点.2"))
        self.assertIn("始点_1", data.zones)
        for text, message in (
            (self.MAP.replace("end 1 0", "bad-name 1 0"), "line 3:"),
            (self.MAP.replace("end 1 0", "bad name 1 0"), "line 3:"),
            (self.MAP.replace("end 1 0", "1 0"), "line 3:"),
            (self.MAP.replace("start-end", "-end"), "line 4:"),
            (self.MAP.replace("start-end", "start-"), "line 4:"),
            (self.MAP.replace("start-end", "start end"), "line 4:"),
            (self.MAP.replace("start-end", "start-start"), "line 4:"),
            (self.MAP + "invalid\n", "line 5:.*syntax"),
            (self.MAP + "other: value\n", "line 5:.*unknown key"),
            (self.MAP + ": value\n", "line 5:.*key must not be empty"),
            (self.MAP + "hub:\n", "line 5:.*value must not be empty"),
        ):
            with self.subTest(text=text):
                self.assert_invalid(text, message)

    def test_count_line_preserves_physical_line_number(self) -> None:
        """Report counts after comments using the physical source line."""
        self.assert_invalid(
            "# comment\n\n" + self.MAP.replace("nb_drones: 2", "nb_drones: 0"),
            "line 3:.*nb_drones",
        )

    def test_file_errors(self) -> None:
        """Keep file and decoding failures inside the CLI error boundary."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.txt"
            with self.assertRaises(FileNotFoundError):
                FlyInMapParser().load(path)
            for content in (None, b"\xff\xfe"):
                if content is not None:
                    path.write_bytes(content)
                    with self.assertRaises(UnicodeDecodeError):
                        FlyInMapParser().load(path)
                result = subprocess.run(
                    [sys.executable, "fly-in.py", str(path)],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("Configuration error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
