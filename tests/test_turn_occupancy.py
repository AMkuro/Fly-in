"""Check the per-turn drone grouping used by the viewer (no Tk needed)."""

import unittest
from pathlib import Path

from fly_in.model.drone_state import AtZone, InTransit
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder
from fly_in.pathfinding.scheduler import Scheduler
from fly_in.rendering.turn_occupancy import TurnOccupancy
from fly_in.simulation.simulation import Simulator
from map_builder import scenario_from_text

RESTRICTED = (
    "nb_drones: 2\n"
    "start_hub: start 0 0\n"
    "hub: r 1 0 [zone=restricted]\n"
    "end_hub: end 2 0\n"
    "connection: start-r\n"
    "connection: r-end\n"
)


class TurnOccupancyTests(unittest.TestCase):
    """Groups are by place at the end of the turn, whatever the direction."""

    def setUp(self) -> None:
        """Build the restricted-zone map graph."""
        self.graph = scenario_from_text(RESTRICTED).graph

    def test_at_zone_and_in_transit_are_grouped(self) -> None:
        """List ids per zone and per connection, ascending."""
        occupancy = TurnOccupancy.from_state(
            (InTransit("start", "r"), AtZone("start")), self.graph
        )
        self.assertEqual(occupancy.zone_ids("start"), (2,))
        self.assertEqual(occupancy.connection_ids("start-r"), (1,))
        self.assertEqual(occupancy.zone_ids("end"), ())
        self.assertEqual(occupancy.connection_ids("r-end"), ())

    def test_restricted_exit_and_simultaneous_entry(self) -> None:
        """Count who is on the connection in each confirmed state only.

        S_t: D1 is on start-r. In S_t+1 D1 has arrived and D2 has entered:
        the connection holds one drone in both states, never two.
        """
        before = TurnOccupancy.from_state(
            (InTransit("start", "r"), AtZone("start")), self.graph
        )
        after = TurnOccupancy.from_state(
            (AtZone("r"), InTransit("start", "r")), self.graph
        )
        self.assertEqual(before.connection_ids("start-r"), (1,))
        self.assertEqual(after.connection_ids("start-r"), (2,))
        self.assertEqual(after.zone_ids("r"), (1,))

    def test_both_directions_share_one_connection(self) -> None:
        """Merge opposite travel directions into the same connection."""
        occupancy = TurnOccupancy.from_state(
            (InTransit("start", "r"), InTransit("r", "start")), self.graph
        )
        self.assertEqual(occupancy.connection_ids("start-r"), (1, 2))

    def test_delivered_drones_stay_at_end(self) -> None:
        """A delivered drone is simply AtZone(end)."""
        occupancy = TurnOccupancy.from_state(
            (AtZone("end"), AtZone("end")), self.graph
        )
        self.assertEqual(occupancy.zone_ids("end"), (1, 2))

    def test_missing_connection_is_rejected(self) -> None:
        """Do not hide an impossible history."""
        with self.assertRaises(ValueError):
            TurnOccupancy.from_state(
                (InTransit("start", "end"), AtZone("start")), self.graph
            )

    def test_every_drone_is_in_exactly_one_place_each_turn(self) -> None:
        """Hold on real histories: counts add up to nb_drones at every S_t."""
        for name in (
            "maps/easy/01_linear_path.txt",
            "maps/medium/02_circular_loop.txt",
            "maps/medium/03_priority_puzzle.txt",
        ):
            with self.subTest(map=name):
                path = Path(name)
                scenario = ScenarioBuilder().build(
                    FlyInMapParser().load(str(path))
                )
                history = Simulator(scenario).run(
                    Scheduler(scenario).schedule()
                )
                for turn, state in enumerate(history.states):
                    occupancy = TurnOccupancy.from_state(
                        state, scenario.graph
                    )
                    ids = sorted(
                        i
                        for group in (
                            *occupancy.zone_drones.values(),
                            *occupancy.connection_drones.values(),
                        )
                        for i in group
                    )
                    self.assertEqual(
                        ids, list(range(1, scenario.nb_drones + 1)), turn
                    )
                last = TurnOccupancy.from_state(
                    history.states[-1], scenario.graph
                )
                self.assertEqual(
                    len(last.zone_ids(scenario.end_name)), scenario.nb_drones
                )


if __name__ == "__main__":
    unittest.main()
