"""Static shortest path, unreachable detection and sequential fallback."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from map_builder import graph_from_text

from fly_in.model.drone_state import AtZone, InTransit
from fly_in.pathfinding.fallback import path_states, sequential_plans
from fly_in.pathfinding.simple_dijkstra import (
    NoPathError,
    static_path,
    turns_to_end,
)
from fly_in.simulation.simulation import simulate

ROOT = Path(__file__).resolve().parent.parent

# Two equally fast branches (a normal, p priority) and a slower restricted r.
FORK = """nb_drones: 3
start_hub: start 0 0
hub: a 1 0
hub: p 1 1 [zone=priority]
hub: r 1 2 [zone=restricted]
end_hub: end 2 0
connection: start-a
connection: start-p
connection: start-r
connection: a-end
connection: p-end
connection: r-end
"""

BLOCKED = """nb_drones: 1
start_hub: start 0 0
hub: wall 1 0 [zone=blocked]
end_hub: end 2 0
connection: start-wall
connection: wall-end
"""


class StaticPathTests(unittest.TestCase):
    def test_distances_use_entry_cost(self) -> None:
        distance = turns_to_end(graph_from_text(FORK))
        self.assertEqual(distance["start"], 2)
        self.assertEqual(distance["r"], 1)
        self.assertEqual(distance["end"], 0)

    def test_priority_wins_equal_arrival(self) -> None:
        self.assertEqual(static_path(graph_from_text(FORK)),
                         ["start", "p", "end"])

    def test_restricted_route_when_it_is_the_only_one(self) -> None:
        graph = graph_from_text(
            "nb_drones: 1\nstart_hub: start 0 0\n"
            "hub: r 1 0 [zone=restricted]\nend_hub: end 2 0\n"
            "connection: start-r\nconnection: r-end\n")
        path = static_path(graph)
        self.assertEqual(path_states(graph, path), [
            AtZone("start"), InTransit("start", "r"), AtZone("r"),
            AtZone("end")])

    def test_blocked_zone_makes_end_unreachable(self) -> None:
        with self.assertRaisesRegex(NoPathError, "No path from start"):
            static_path(graph_from_text(BLOCKED))


class SequentialFallbackTests(unittest.TestCase):
    def test_makespan_is_drones_times_path_length(self) -> None:
        graph = graph_from_text(FORK)
        plans = sequential_plans(graph, static_path(graph))
        history = simulate(graph, plans)
        self.assertEqual(history.makespan, 3 * 2)
        self.assertEqual(plans[1][:3], [AtZone("start")] * 3)


class CliTests(unittest.TestCase):
    def run_cli(self, text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.txt"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "fly-in.py"), str(path)],
                capture_output=True, text=True, cwd=ROOT, check=False)

    def test_unreachable_map_reports_error(self) -> None:
        result = self.run_cli(BLOCKED)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Error: No path from start to end.\n")

    def test_prints_one_line_per_turn(self) -> None:
        result = self.run_cli(
            "nb_drones: 2\nstart_hub: start 0 0\nhub: a 1 0\n"
            "end_hub: end 2 0\nconnection: start-a\nconnection: a-end\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(),
                         ["D1-a", "D1-end D2-a", "D2-end"])


if __name__ == "__main__":
    unittest.main()
