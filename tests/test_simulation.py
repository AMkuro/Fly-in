"""Simulation: independent validation, StateHistory and CLI lines."""

import unittest

from map_builder import scenario_from_text

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.simulation.simulation import SimulationError, Simulator

LINEAR = """nb_drones: 2
start_hub: start 0 0
hub: a 1 0
hub: b 2 0
end_hub: end 3 0
connection: start-a
connection: a-b
connection: b-end
"""

# Subject VII.3 example: two drones queueing for a restricted connection.
RESTRICTED = """nb_drones: 2
start_hub: start 0 0
hub: r 1 0 [zone=restricted]
end_hub: end 2 0
connection: r-start
connection: r-end
"""


def column(delay: int) -> list[DroneState]:
    """Linear route after waiting ``delay`` turns at start."""
    waiting: list[DroneState] = [AtZone("start")] * (delay + 1)
    return waiting + [AtZone("a"), AtZone("b"), AtZone("end")]


class SimulationTests(unittest.TestCase):
    def test_linear_column_history_and_output(self) -> None:
        scenario = scenario_from_text(LINEAR)
        history = Simulator(scenario).run([column(0), column(1)])
        self.assertEqual(history.makespan, 4)
        self.assertEqual(history.states[0],
                         (AtZone("start"), AtZone("start")))
        self.assertEqual(history.states[4], (AtZone("end"), AtZone("end")))
        self.assertEqual(history.lines(), [
            "D1-a",
            "D1-b D2-a",
            "D1-end D2-b",
            "D2-end",
        ])

    def test_restricted_queue_matches_subject_example(self) -> None:
        scenario = scenario_from_text(RESTRICTED)
        first: list[DroneState] = [
            AtZone("start"), InTransit("start", "r"), AtZone("r"),
            AtZone("end")]
        second: list[DroneState] = [
            AtZone("start"), AtZone("start"), InTransit("start", "r"),
            AtZone("r"), AtZone("end")]
        history = Simulator(scenario).run([first, second])
        # Connection is printed in travel order even if declared r-start.
        self.assertEqual(history.lines(), [
            "D1-start-r",
            "D1-r D2-start-r",
            "D1-end D2-r",
            "D2-end",
        ])

    def test_rejects_capacity_conflicts(self) -> None:
        scenario = scenario_from_text(LINEAR)
        with self.assertRaisesRegex(SimulationError, "zone a holds 2"):
            Simulator(scenario).run([column(0), column(0)])

    def test_rejects_illegal_plan_with_drone_id(self) -> None:
        scenario = scenario_from_text(LINEAR)
        stuck: list[DroneState] = [AtZone("start"), AtZone("a")]
        with self.assertRaisesRegex(SimulationError, "D2: .*end hub"):
            Simulator(scenario).run([column(0), stuck])

    def test_rejects_wrong_plan_count(self) -> None:
        scenario = scenario_from_text(LINEAR)
        with self.assertRaisesRegex(SimulationError, "expected 2 plans"):
            Simulator(scenario).run([column(0)])

    def test_history_is_immutable(self) -> None:
        scenario = scenario_from_text(LINEAR)
        history = Simulator(scenario).run([column(0), column(1)])
        self.assertIsInstance(history.states, tuple)
        self.assertIsInstance(history.states[0], tuple)


if __name__ == "__main__":
    unittest.main()
