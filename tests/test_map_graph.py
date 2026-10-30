"""Regression checks for maps containing blocked zones."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fly_in.model.map_graph import MapGraph
from fly_in.parse.map_parser import FlyInMapParser


class MapGraphTests(unittest.TestCase):
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
                data = FlyInMapParser().load(path)
                graph = MapGraph.from_map_data(data)

                self.assertEqual(dict(graph.zones), data.zones)
                self.assertEqual(graph.start_hub, data.zones["start"])
                self.assertEqual(graph.end_hub, data.zones["end"])
                self.assertEqual(graph.connections, tuple(data.connections))
                self.assertEqual(len(graph.connections_by_name), 4)
                self.assertEqual(len(graph.connections_by_key), 4)
                for connection in data.connections:
                    self.assertEqual(
                        graph.connection(connection.name), connection
                    )
                    self.assertEqual(
                        graph.connection_between(connection.b, connection.a),
                        connection,
                    )
                    for a, b in (
                        (connection.a, connection.b),
                        (connection.b, connection.a),
                    ):
                        self.assertIn(connection, graph.connections_for(a))
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
                data = FlyInMapParser().load(path)
                graph = MapGraph.from_map_data(data)
                self.assertEqual(dict(graph.zones), data.zones)
                self.assertEqual(graph.connections, tuple(data.connections))
