"""Regression checks for maps containing blocked zones."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fly_in.model.connection_model import Connection
from fly_in.model.map_graph import MapGraph
from fly_in.model.parsed_map import ParsedMap
from fly_in.model.zone_model import Zone
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder


class MapGraphTests(unittest.TestCase):
    def test_topology_does_not_require_execution_roles(self) -> None:
        """An empty graph can exist independently of a scenario."""
        graph = MapGraph.from_models({}, [])
        self.assertEqual(dict(graph.zones), {})
        self.assertEqual(graph.connections, ())

    def check_parsed_objects(self, parsed: ParsedMap) -> MapGraph:
        """Require graph construction to retain the parsed model instances."""
        graph = ScenarioBuilder().build(parsed).graph
        self.assertFalse(hasattr(graph, "nb_drones"))
        for _, _, value in parsed.declarations:
            if isinstance(value, Zone):
                self.assertIs(graph.zones[value.name], value)
            elif isinstance(value, Connection):
                self.assertIs(
                    graph.connection_between(value.a, value.b), value
                )
        return graph

    def test_blocked_zones_preserve_topology(self) -> None:
        for blocked in ((), ("a",), ("b",), ("a", "b"), ("start",), ("end",)):
            with (
                self.subTest(blocked=blocked),
                tempfile.TemporaryDirectory() as directory,
            ):
                lines = ["nb_drones: 2"]
                for prefix, name, x in (
                    ("start_hub", "start", 0),
                    ("end_hub", "end", 3),
                    ("hub", "a", 1),
                    ("hub", "b", 2),
                ):
                    metadata = " [zone=blocked]" if name in blocked else ""
                    lines.append(f"{prefix}: {name} {x} 0{metadata}")
                lines.extend((
                    "connection: start-a",
                    "connection: a-b",
                    "connection: b-end",
                    "connection: start-end",
                ))
                path = Path(directory) / "map.txt"
                path.write_text("\n".join(lines), encoding="utf-8")
                parsed = FlyInMapParser().load(str(path))
                graph = self.check_parsed_objects(parsed)

                self.assertEqual(set(graph.zones), {"start", "end", "a", "b"})
                self.assertFalse(hasattr(graph, "start_hub"))
                self.assertFalse(hasattr(graph, "end_hub"))
                self.assertEqual(len(graph.connections), 4)
                for connection in graph.connections:
                    self.assertEqual(
                        graph.connection_between(connection.b, connection.a),
                        connection,
                    )
                    for a, b in (
                        (connection.a, connection.b),
                        (connection.b, connection.a),
                    ):
                        self.assertIn(b, graph.neighbors_for(a))
                result = subprocess.run(
                    [sys.executable, "fly-in.py", str(path)],
                    capture_output=True, text=True, timeout=10,
                )
                if "end" in blocked:
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(
                        result.stderr, "Error: No path from start to end.\n"
                    )
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(result.stdout.startswith("D1-"))

    def test_provided_maps_build_graphs(self) -> None:
        paths = sorted(Path("maps").glob("*/*.txt"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path):
                self.check_parsed_objects(FlyInMapParser().load(str(path)))
