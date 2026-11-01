"""Input contracts, source positions, and parser-to-model integration."""

import itertools
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fly_in.model.connection_model import Connection
from fly_in.model.scenario import Scenario
from fly_in.model.zone_model import Zone, ZoneType
from fly_in.parse import FlyInMapParser, MapParseError
from fly_in.parse.scenario_builder import ScenarioBuilder
from fly_in.parse.declaration_parser import DeclarationParser
from fly_in.parse.map_reader import MapReader
from fly_in.pathfinding.static_distance import NoPathError, static_path


class ParserContractTests(unittest.TestCase):
    """Check Subject requirements and explicitly adopted input restrictions."""

    MAP = (
        "nb_drones: 2\nstart_hub: start 0 0\nend_hub: end 1 0\n"
        "connection: start-end\n"
    )

    def setUp(self) -> None:
        """Give each test an isolated input file."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "map.txt"

    def load(self, text: str) -> Scenario:
        """Read inline input through the public file-based API."""
        self.path.write_text(text, encoding="utf-8")
        parsed = FlyInMapParser().load(str(self.path))
        return ScenarioBuilder().build(parsed)

    def check_error(self, text: str, line: int | None, *causes: str) -> str:
        """Require a parser error at an exact line (or none) and cause."""
        with self.assertRaises(MapParseError) as caught:
            self.load(text)
        error = caught.exception
        self.assertEqual(error.line_number, line)
        prefix = "" if line is None else f"line {line}: "
        self.assertTrue(str(error).startswith(prefix))
        self.assertEqual(str(error).startswith("line "), line is not None)
        for cause in causes:
            self.assertIn(cause, str(error))
        return str(error)

    def test_package_exports_only_loading_and_input_errors(self) -> None:
        """The package API excludes submodules, parsing helpers, and models."""
        namespace: dict[str, object] = {}
        exec("from fly_in.parse import *", namespace)
        exports = {name for name in namespace if not name.startswith("_")}
        self.assertEqual(exports, {"FlyInMapParser", "MapParseError"})
        self.assertIs(namespace["FlyInMapParser"], FlyInMapParser)
        self.assertIs(namespace["MapParseError"], MapParseError)

    def test_reader_leaves_key_classification_to_parser(self) -> None:
        """Reader accepts unknown keys; declaration parsing rejects them."""
        text = "# header\ncustom: opaque payload\n\n"
        self.path.write_text(text)
        numbered_lines = MapReader().read(str(self.path))
        self.assertEqual(numbered_lines, [(2, "custom", "opaque payload")])
        known_line = MapReader.parse_key_value_line(5, "nb_drones: 2")
        self.assertEqual(known_line, (5, "nb_drones", "2"))
        self.assertIs(type(known_line[1]), str)
        self.check_error(text, 2, "unknown declaration", "custom")

    def test_syntax_and_local_value_errors(self) -> None:
        """Cover P02-P07 and V01-V07 without relying on Pydantic wording."""
        cases = (
            ("P02", self.MAP.replace("nb_drones: 2\n", "")
             + "nb_drones: 2\n", 1, "first meaningful"),
            ("P03", self.MAP.replace("nb_drones:", "unknown:"),
             1, "unknown declaration"),
            ("P04", "nb_drones 2\n", 1, "syntax"),
            ("P04-empty-key", ": 2\n", 1, "key"),
            ("P04-empty-value", "nb_drones:\n", 1, "value"),
            ("P05-short", self.MAP.replace("end 1 0", "end 1"),
             3, "syntax"),
            ("P05-long", self.MAP.replace("end 1 0", "end 1 0 extra"),
             3, "syntax"),
            ("P05-count", self.MAP.replace("nb_drones: 2", "nb_drones: 2 3"),
             1, "one integer"),
            ("V01", self.MAP.replace("nb_drones: 2", "nb_drones: 0"),
             1, "nb_drones"),
            ("V02", self.MAP.replace("end 1 0", "bad-name 1 0"),
             3, "name"),
            ("V02-space", self.MAP.replace("end 1 0", "end name 1 0"),
             3, "syntax"),
            ("V03", self.MAP.replace("end 1 0", "end 1.0 0"),
             3, "x"),
            ("V04", self.MAP.replace("end 1 0", "end 1 0 [zone=urgent]"),
             3, "zone"),
            ("V05", self.MAP.replace("end 1 0", "end 1 0 [max_drones=0]"),
             3, "max_drones"),
            ("V06", self.MAP.replace(
                "start-end", "start-end [max_link_capacity=0]"),
             4, "max_link_capacity"),
            ("V07", self.MAP.replace("end 1 0", "end 1 0 [color=two words]"),
             3, "metadata"),
            ("V08", self.MAP.replace("end 1 0", "end 1 0 [color=0]"),
             3, "digits"),
        )
        for requirement, text, line, cause in cases:
            with self.subTest(requirement=requirement):
                message = self.check_error(text, line, cause)
                self.assertNotIn("zone_type", message)
                self.assertNotIn("zones.", message)
        for body in ("start", "-end", "start-", "start-end-extra",
                     "start--end", "start -end"):
            with self.subTest(requirement="P07", body=body):
                self.check_error(self.MAP.replace("start-end", body), 4)

    def test_metadata_syntax_and_restrictions(self) -> None:
        """Cover P06, M01-M03, including duplicates with identical values."""
        invalid = (
            "[", "]", "][", "[color=red", "color=red]",
            "[color=red] trailing", "[] []", "[[color=red]]",
            "[color]", "[=red]", "[color=]",
            "[zone=normal zone=normal]", "[zone=normal zone=blocked]",
            "[color=red max_drones=2 color=red]", "[unknown=x]",
            "[name=other]", "[x=2]", "[y=2]", "[line_number=2]",
            "[zone_type=normal]",
            "[max_link_capacity=2]",
        )
        for metadata in invalid:
            with self.subTest(metadata=metadata):
                self.check_error(
                    self.MAP.replace("end 1 0", f"end 1 0 {metadata}"), 3
                )
        for metadata in (
            "[max_link_capacity=1 max_link_capacity=1]", "[unknown=x]",
            "[zone=normal]", "[color=red]", "[max_drones=1]",
            "[name=other]", "[a=other]", "[b=other]",
        ):
            with self.subTest(connection_metadata=metadata):
                self.check_error(self.MAP.replace(
                    "start-end", f"start-end {metadata}"
                ), 4)

    def test_ordered_declaration_constraints(self) -> None:
        """Cover S01-S06 and G01, including both duplicate positions."""
        for declaration, first in (
            ("nb_drones: 3", 1), ("start_hub: other 2 0", 2),
            ("end_hub: other 2 0", 3), ("hub: end 2 0", 3),
            ("connection: start-end", 4),
            ("connection: end-start [max_link_capacity=2]", 4),
        ):
            with self.subTest(declaration=declaration):
                self.check_error(
                    self.MAP + declaration + "\n", 5,
                    "duplicate", f"first defined on line {first}",
                )
        self.check_error(
            "nb_drones: 1\nhub: A 1 0\nstart_hub: A 0 0\n"
            "end_hub: B 2 0\n", 3, "first defined on line 2",
        )
        self.check_error(
            "nb_drones: 1\nconnection: A-B\nstart_hub: A 0 0\n"
            "end_hub: B 1 0\n", 2, "before connection",
        )
        self.check_error(
            "nb_drones: 1\nstart_hub: A 0 0\nconnection: A-B\n"
            "end_hub: B 1 0\n", 3, "B", "before connection",
        )
        self.check_error(self.MAP.replace("start-end", "start-missing"),
                         4, "missing", "before connection")
        self.check_error(self.MAP.replace("start-end", "start-start"),
                         4, "self-loop")

    def test_coordinate_uniqueness_includes_special_hubs(self) -> None:
        """G02 compares integer values for every kind of Zone."""
        self.check_error(self.MAP.replace("end 1 0", "end +00 -0"),
                         3, "coordinates", "first defined on line 2")
        for zone_type in ZoneType:
            with self.subTest(zone_type=zone_type):
                self.check_error(
                    self.MAP + f"hub: other 01 +00 [zone={zone_type.value}]\n",
                    5, "coordinates", "first defined on line 3",
                )
        self.check_error(
            "nb_drones: 1\nhub: X -01 -2\nstart_hub: A 0 0\n"
            "end_hub: B -1 -02\n", 4,
            "coordinates", "first defined on line 2",
        )

    def test_strict_integer_lexing_in_every_numeric_field(self) -> None:
        """N01 is applied before numeric conversion at all input sites."""
        for token in ("1.0", "2e3", "1_000", "0x10", "0b10", "１２", "١",
                      "+", "-", "--1", "1x"):
            variants = (
                (self.MAP.replace("nb_drones: 2", f"nb_drones: {token}"), 1),
                (self.MAP.replace("end 1 0", f"end {token} 0"), 3),
                (self.MAP.replace("end 1 0", f"end 1 {token}"), 3),
                (self.MAP.replace(
                    "end 1 0", f"end 1 0 [max_drones={token}]"), 3),
                (self.MAP.replace(
                    "start-end", f"start-end [max_link_capacity={token}]"), 4),
            )
            for text, line in variants:
                with self.subTest(token=token, line=line, text=text):
                    self.check_error(text, line, "ASCII decimal integer")
        for token in ("0", "-0", "-1"):
            with self.subTest(nonpositive=token):
                self.check_error(self.MAP.replace(
                    "nb_drones: 2", f"nb_drones: {token}"
                ), 1, "nb_drones")
                for name, line in (("start", 2), ("end", 3)):
                    suffix = "0 0" if name == "start" else "1 0"
                    self.check_error(self.MAP.replace(
                        f"{name} {suffix}",
                        f"{name} {suffix} [max_drones={token}]",
                    ), line, "max_drones")
                self.check_error(self.MAP.replace(
                    "start-end", f"start-end [max_link_capacity={token}]"
                ), 4, "max_link_capacity")

    def test_valid_values_defaults_and_metadata_order(self) -> None:
        """Accept signs, leading zeros, empty metadata, and all zone types."""
        data = self.load(
            "# comment\nnb_drones: +002\nstart_hub: 東京 -000 +00 []\n"
            "hub: middle -01 -02 [max_drones=+003]\n"
            "end_hub: goal:2 +003 -04 [max_drones=1 color=custom_color]\n"
            "connection: middle-東京 []\n"
            "connection: middle-goal:2 [max_link_capacity=+002]\n"
        )
        self.assertEqual(FlyInMapParser().load(str(self.path)).nb_drones, 2)
        middle = data.graph.zones["middle"]
        self.assertEqual((middle.x, middle.y), (-1, -2))
        self.assertEqual(list(data.graph.zones), ["東京", "goal:2", "middle"])
        self.assertEqual(data.graph.zones["東京"].zone_type, ZoneType.NORMAL)
        self.assertEqual(data.graph.zones["東京"].max_drones, 1)
        self.assertIsNone(data.graph.zones["東京"].color)
        self.assertNotIn("max_drones", data.graph.zones["東京"].model_fields_set)
        self.assertIn(
            "max_drones", data.graph.zones["goal:2"].model_fields_set
        )
        self.assertEqual(data.graph.connections[0].max_link_capacity, 1)
        self.assertNotIn("max_link_capacity",
                         data.graph.connections[0].model_fields_set)
        graph = data.graph
        edge = graph.connection_between("東京", "middle")
        self.assertIs(edge, data.graph.connections[0])
        self.assertEqual(data.graph.connections[0].name, "middle-東京")
        for kind in ZoneType:
            self.assertEqual(self.load(self.MAP.replace(
                "end 1 0", f"end 1 0 [zone={kind.value}]"
            )).graph.zones["end"].zone_type, kind)
        for tags in itertools.permutations(
            ("zone=priority", "color=arbitrary_word", "max_drones=2")
        ):
            zone = self.load(self.MAP.replace(
                "end 1 0", f"end 1 0 [{' '.join(tags)}]"
            )).graph.zones["end"]
            self.assertEqual((zone.zone_type, zone.color, zone.max_drones),
                             (ZoneType.PRIORITY, "arbitrary_word", 2))
        count = 2 ** 100
        self.path.write_text(self.MAP.replace(
            "nb_drones: 2", f"nb_drones: {count}"
        ))
        self.assertEqual(
            FlyInMapParser().load(str(self.path)).nb_drones, count
        )

    def test_empty_and_missing_declarations_have_no_line(self) -> None:
        """Absent declarations have no source line to report."""
        for text in ("", "# comment\n\n", "\n \n"):
            self.check_error(text, None, "empty")
        self.check_error("nb_drones: 1\n# trailing\n\n", None,
                         "missing", "start_hub", "end_hub")
        self.check_error("nb_drones: 1\nstart_hub: A 0 0", None,
                         "missing", "end_hub")
        self.check_error("nb_drones: 1\nend_hub: B 1 0\n", None,
                         "missing", "start_hub")
        self.check_error(
            "# header\n\nnb_drones: 1\nstart_hub: A 0 0\n"
            "# middle\n\nend_hub: B nope 0\n", 7, "x",
        )
        self.check_error(
            "\nnb_drones: 1\n# gap\nstart_hub: A 0 0\n"
            "end_hub: B 1 0\n\nhub: A 2 0\n", 7,
            "first defined on line 4",
        )
        for separator in ("\n", "\r\n", "\r"):
            self.path.write_bytes(separator.join((
                "# header", "", "nb_drones: 1", "start_hub: A 0 0",
                "end_hub: B x 0", "",
            )).encode())
            with self.assertRaises(MapParseError) as caught:
                FlyInMapParser().load(str(self.path))
            self.assertEqual(caught.exception.line_number, 5)

    def test_file_errors_and_decoding(self) -> None:
        """Report decoding failures for the file without a line number."""
        with self.assertRaisesRegex(FileNotFoundError, "Map file not found"):
            FlyInMapParser().load(str(self.path))
        with self.assertRaisesRegex(OSError, "Could not read"):
            FlyInMapParser().load(str(self.path.parent))
        self.path.write_bytes(b"nb_drones: 1\n# comment\n\xff\n")
        with self.assertRaises(ValueError) as caught:
            FlyInMapParser().load(str(self.path))
        self.assertNotIsInstance(caught.exception, MapParseError)
        self.assertIn("UTF-8", str(caught.exception))
        self.assertIn(str(self.path), str(caught.exception))
        self.assertNotIn("line ", str(caught.exception))
        result = subprocess.run(
            [sys.executable, "fly-in.py", str(self.path)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Configuration error: Could not decode map file",
                      result.stderr)
        self.assertNotIn("line ", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_models_are_reused_without_parser_information(self) -> None:
        """Preserve validated instances and discard parser provenance."""
        zones: list[Zone] = []
        connections: list[Connection] = []
        validate_zone = Zone.model_validate
        validate_connection = Connection.model_validate

        def record_zone(values: object) -> Zone:
            zone = validate_zone(values)
            zones.append(zone)
            return zone

        def record_connection(values: object) -> Connection:
            connection = validate_connection(values)
            connections.append(connection)
            return connection

        with patch("fly_in.parse.map_parser.Zone.model_validate",
                   side_effect=record_zone), patch(
            "fly_in.parse.map_parser.Connection.model_validate",
            side_effect=record_connection,
        ):
            data = self.load(self.MAP)
        for zone in zones:
            self.assertIs(data.graph.zones[zone.name], zone)
            self.assertNotIn("line_number", zone.model_dump())
        self.assertIs(data.graph.connections[0], connections[0])
        self.assertNotIn("line_number", connections[0].model_dump())
        self.assertFalse(hasattr(data, "declarations"))

    def test_splitting_leaves_value_validation_to_the_caller(self) -> None:
        """Syntax helpers keep raw values for subsequent model validation."""
        parser = DeclarationParser()
        zone = parser.parse_zone(7, "A 1.0 0 [zone=unknown max_drones=-1]")
        self.assertEqual(zone["x"], "1.0")
        self.assertEqual(zone["metadata"], {
            "zone": "unknown", "max_drones": "-1",
        })
        connection = parser.parse_connection(8, "A-A [max_link_capacity=0]")
        self.assertEqual(connection["a"], connection["b"])
        self.assertEqual(connection["metadata"], {"max_link_capacity": "0"})

    def test_unsolvable_maps_are_input_valid(self) -> None:
        """Only pathfinding rejects blocked or disconnected routes."""
        for links in ("connection: A-C\nconnection: C-B\n", ""):
            data = self.load(
                "nb_drones: 2\nstart_hub: A 0 0\nend_hub: B 2 0\n"
                "hub: C 1 0 [zone=blocked]\n" + links
            )
            with self.assertRaises(NoPathError):
                static_path(data)
            result = subprocess.run(
                [sys.executable, "fly-in.py", str(self.path)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr,
                             "Error: No path from start to end.\n")

    def test_local_errors_precede_whole_map_validation(self) -> None:
        """A later local error is allowed to precede an earlier duplicate."""
        self.check_error(
            self.MAP + "nb_drones: 3\nhub: X 3 0 [zone=unknown]\n",
            6, "zone",
        )

    def test_start_end_capacities_are_validated_but_not_enforced(self) -> None:
        """Accept positive metadata without limiting hub occupancy."""
        self.load(self.MAP.replace(
            "start 0 0", "start 0 0 [max_drones=1]"
        ).replace("end 1 0", "end 1 0 [max_drones=1]"))
        result = subprocess.run(
            [sys.executable, "fly-in.py", str(self.path)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.split()), {"D1-end", "D2-end"})

    def test_cli_source_errors_are_concise(self) -> None:
        """Preserve stderr and exit code without configuration tracebacks."""
        for text, line, cause in (
            ("", None, "empty"),
            ("nb_drones: 1\n# trailing\n", None, "missing"),
            (self.MAP.replace("end 1 0", "end 0 0"), 3, "coordinates"),
            (self.MAP.replace("end 1 0", "end 1 0 ]color=red["),
             3, "metadata"),
        ):
            self.path.write_text(text)
            result = subprocess.run(
                [sys.executable, "fly-in.py", str(self.path)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            where = "" if line is None else f"line {line}: "
            self.assertIn(f"Configuration error: {where}", result.stderr)
            self.assertIn(cause, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
