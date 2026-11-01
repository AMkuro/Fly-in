"""Space-time A* Planner and whole-plan Scheduler retries."""

import unittest
from collections.abc import Mapping
from pathlib import Path

from map_builder import scenario_from_text

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder
from fly_in.pathfinding.planner import SearchParams, SpaceTimePlanner
from fly_in.pathfinding.reservation import Reservation
from fly_in.pathfinding.scheduler import makespan, plan_all, schedule
from fly_in.pathfinding.static_distance import NoPathError, StaticDistance
from fly_in.simulation.simulation import simulate

ROOT = Path(__file__).resolve().parent.parent

# Subject VII.6 optimum turns for the shipped maps.
OPTIMUM = {
    "easy/01_linear_path.txt": 4,
    "easy/02_simple_fork.txt": 4,
    "easy/03_basic_capacity.txt": 4,
    "medium/01_dead_end_trap.txt": 8,
    "medium/02_circular_loop.txt": 10,
    "medium/03_priority_puzzle.txt": 6,
    "hard/01_maze_nightmare.txt": 13,
    "hard/02_capacity_hell.txt": 16,
    "hard/03_ultimate_challenge.txt": 26,
    "challenger/01_the_impossible_dream.txt": 43,
}

LINEAR = """nb_drones: 2
start_hub: start 0 0
hub: a 1 0
end_hub: end 2 0
connection: start-a
connection: a-end
"""


def planner_inputs(text: str) -> tuple[Reservation, Mapping[str, int]]:
    scenario = scenario_from_text(text)
    return Reservation(scenario), StaticDistance(scenario).turns_to_end


def plan_drone(
    reservation: Reservation,
    distance: Mapping[str, int],
    deadline: int,
    params: SearchParams,
) -> list[DroneState] | None:
    """Plan one drone with a planner built for this call."""
    return SpaceTimePlanner(reservation, distance, params).plan(deadline)


class PlannerTests(unittest.TestCase):
    def test_lone_drone_takes_static_shortest_route(self) -> None:
        reservation, distance = planner_inputs(LINEAR)
        plan = plan_drone(reservation, distance, 10, SearchParams())
        self.assertEqual(plan, [AtZone("start"), AtZone("a"), AtZone("end")])

    def test_waits_for_committed_drone(self) -> None:
        reservation, distance = planner_inputs(LINEAR)
        first = plan_drone(reservation, distance, 10, SearchParams())
        assert first is not None
        self.assertIsNone(reservation.try_add(first))
        second = plan_drone(reservation, distance, 10, SearchParams())
        self.assertEqual(second, [
            AtZone("start"), AtZone("start"), AtZone("a"), AtZone("end")])

    def test_deadline_too_early_returns_none(self) -> None:
        reservation, distance = planner_inputs(LINEAR)
        self.assertIsNone(plan_drone(reservation, distance, 1, SearchParams()))

    def test_restricted_entry_is_followed_by_forced_arrival(self) -> None:
        reservation, distance = planner_inputs(
            "nb_drones: 1\nstart_hub: start 0 0\n"
            "hub: r 1 0 [zone=restricted]\nend_hub: end 2 0\n"
            "connection: start-r\nconnection: r-end\n")
        plan = plan_drone(reservation, distance, 10, SearchParams())
        self.assertEqual(plan, [
            AtZone("start"), InTransit("start", "r"), AtZone("r"),
            AtZone("end")])

    def test_priority_preferred_on_equal_arrival(self) -> None:
        reservation, distance = planner_inputs(
            "nb_drones: 1\nstart_hub: start 0 0\nhub: a 1 0\n"
            "hub: p 1 1 [zone=priority]\nend_hub: end 2 0\n"
            "connection: start-a\nconnection: start-p\n"
            "connection: a-end\nconnection: p-end\n")
        for seed in range(5):
            with self.subTest(seed=seed):
                plan = plan_drone(reservation, distance, 10,
                                  SearchParams(seed=seed))
                assert plan is not None
                self.assertEqual(plan[1], AtZone("p"))


class SchedulerTests(unittest.TestCase):
    def test_unreachable_end_raises(self) -> None:
        scenario = scenario_from_text(
            "nb_drones: 1\nstart_hub: start 0 0\n"
            "hub: wall 1 0 [zone=blocked]\nend_hub: end 2 0\n"
            "connection: start-wall\nconnection: wall-end\n")
        with self.assertRaises(NoPathError):
            schedule(scenario)

    def test_zero_attempts_keeps_sequential_fallback(self) -> None:
        scenario = scenario_from_text(LINEAR)
        self.assertEqual(makespan(schedule(scenario, attempts=0)), 4)
        self.assertEqual(makespan(schedule(scenario)), 3)

    def test_shipped_maps_reach_subject_optimum(self) -> None:
        for name, optimum in OPTIMUM.items():
            with self.subTest(map=name):
                parsed = FlyInMapParser().load(str(ROOT / "maps" / name))
                scenario = ScenarioBuilder().build(parsed)
                plans = schedule(scenario)
                history = simulate(scenario, plans)
                self.assertEqual(history.makespan, optimum)

    def test_reservation_accepts_every_planner_result(self) -> None:
        # A rejection would silently drop attempts; make it visible here.
        for name in OPTIMUM:
            with self.subTest(map=name):
                parsed = FlyInMapParser().load(str(ROOT / "maps" / name))
                scenario = ScenarioBuilder().build(parsed)
                plans = plan_all(
                    scenario, StaticDistance(scenario).turns_to_end, 10_000,
                    SearchParams(),
                )
                self.assertIsNotNone(plans)

    def test_scheduled_plans_are_one_per_drone(self) -> None:
        scenario = scenario_from_text(LINEAR)
        plans: list[list[DroneState]] = schedule(scenario)
        self.assertEqual(len(plans), 2)


if __name__ == "__main__":
    unittest.main()
