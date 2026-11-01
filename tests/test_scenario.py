"""Endpoint and fleet settings can vary independently of graph topology."""

import unittest

from map_builder import scenario_from_text

from fly_in.model.drone_state import AtZone
from fly_in.model.movement_rules import occupied_zone
from fly_in.model.scenario import Scenario
from fly_in.pathfinding.scheduler import schedule
from fly_in.pathfinding.static_distance import StaticDistance
from fly_in.simulation.simulation import simulate

MAP = (
    "nb_drones: 2\nstart_hub: A 0 0\nhub: B 1 0\nend_hub: C 2 0\n"
    "connection: A-B\nconnection: B-C\n"
)


class ScenarioTests(unittest.TestCase):
    """Keep endpoint roles and fleet size outside graph topology."""

    def test_same_graph_supports_different_settings(self) -> None:
        """Route and simulate another fleet without rebuilding the graph."""
        forward = scenario_from_text(MAP)
        backward = Scenario(forward.graph, "C", "A", 3)
        self.assertIs(backward.graph, forward.graph)
        self.assertEqual(StaticDistance(forward).path(), ["A", "B", "C"])
        self.assertEqual(StaticDistance(backward).path(), ["C", "B", "A"])
        plans = schedule(backward, attempts=0)
        self.assertEqual(len(plans), 3)
        self.assertEqual(simulate(backward, plans).makespan, 6)

    def test_unlimited_capacity_follows_the_scenario(self) -> None:
        """Changing the start role changes which zone is capacity-exempt."""
        first = scenario_from_text(MAP)
        second = Scenario(first.graph, "B", "C", 2)
        self.assertIsNone(occupied_zone(first, AtZone("A")))
        self.assertEqual(occupied_zone(second, AtZone("A")), "A")
        self.assertEqual(occupied_zone(first, AtZone("B")), "B")
        self.assertIsNone(occupied_zone(second, AtZone("B")))
