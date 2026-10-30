"""Reservation: per-drone rules, capacity cache and atomic commit."""

import unittest

from map_builder import graph_from_text

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.pathfinding.reservation import Reservation

# start - a - end, plus start - r(restricted) - end.
MAP = """nb_drones: 3
start_hub: start 0 0
hub: a 1 0
hub: r 1 1 [zone=restricted]
hub: x 2 2 [zone=blocked]
end_hub: end 2 0
connection: start-a
connection: a-end
connection: start-r
connection: r-end
connection: a-x
"""

A_ROUTE: list[DroneState] = [AtZone("start"), AtZone("a"), AtZone("end")]
R_ROUTE: list[DroneState] = [
    AtZone("start"), InTransit("start", "r"), AtZone("r"), AtZone("end"),
]


class ReservationRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reservation = Reservation(graph_from_text(MAP))

    def assertRejected(self, plan: list[DroneState], reason: str) -> None:
        error = self.reservation.try_add(plan)
        self.assertIsNotNone(error)
        self.assertIn(reason, str(error))
        self.assertEqual(self.reservation.plans, ())

    def test_legal_routes_are_committed(self) -> None:
        self.assertIsNone(self.reservation.try_add(A_ROUTE))
        self.assertIsNone(self.reservation.try_add(R_ROUTE))
        self.assertEqual(len(self.reservation.plans), 2)

    def test_rejects_illegal_single_drone_plans(self) -> None:
        cases: list[tuple[list[DroneState], str]] = [
            ([], "empty"),
            ([AtZone("a"), AtZone("end")], "not at the start"),
            ([AtZone("start"), AtZone("a")], "not at the end"),
            ([AtZone("start"), AtZone("end")], "no connection"),
            ([AtZone("start"), AtZone("r"), AtZone("end")], "2 turn"),
            ([AtZone("start"), AtZone("a"), InTransit("a", "end"),
              AtZone("end")], "1 turn"),
            ([AtZone("start"), AtZone("a"), AtZone("x")], "blocked"),
            ([AtZone("start"), InTransit("start", "r"),
              InTransit("start", "r"), AtZone("r"), AtZone("end")],
             "must arrive"),
            ([AtZone("start"), AtZone("a"), AtZone("end"), AtZone("a"),
              AtZone("end")], "must not move"),
            ([AtZone("start"), InTransit("a", "end")], "does not start"),
        ]
        for plan, reason in cases:
            with self.subTest(plan=plan):
                self.assertRejected(plan, reason)

    def test_waiting_and_reentering_start_are_legal(self) -> None:
        plan: list[DroneState] = [
            AtZone("start"), AtZone("a"), AtZone("start"), AtZone("start"),
            AtZone("a"), AtZone("a"), AtZone("end"), AtZone("end"),
        ]
        self.assertIsNone(self.reservation.try_add(plan))


class ReservationCapacityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reservation = Reservation(graph_from_text(MAP))

    def test_cache_counts_zones_and_connections(self) -> None:
        self.assertIsNone(self.reservation.try_add(R_ROUTE))
        self.assertEqual(self.reservation.zone_occupancy(2, "r"), 1)
        self.assertEqual(self.reservation.zone_occupancy(1, "r"), 0)
        # start/end are never counted.
        self.assertEqual(self.reservation.zone_occupancy(0, "start"), 0)
        self.assertEqual(self.reservation.zone_occupancy(3, "end"), 0)
        key = ("r", "start")
        self.assertEqual(self.reservation.connection_usage(0, key), 1)
        # The forced arrival frees the connection in turn 1.
        self.assertEqual(self.reservation.connection_usage(1, key), 0)
        self.assertEqual(self.reservation.connection_usage(2, ("end", "r")),
                         1)

    def test_over_capacity_rejects_without_partial_commit(self) -> None:
        self.assertIsNone(self.reservation.try_add(A_ROUTE))
        error = self.reservation.try_add(A_ROUTE)
        self.assertIn("zone a over capacity at S_1", str(error))
        self.assertEqual(len(self.reservation.plans), 1)
        self.assertEqual(self.reservation.zone_occupancy(1, "a"), 1)
        self.assertEqual(
            self.reservation.connection_usage(0, ("a", "start")), 1)

    def test_vacated_zone_is_reusable_same_turn(self) -> None:
        # Single-file column: second drone enters a as the first leaves.
        self.assertIsNone(self.reservation.try_add(A_ROUTE))
        follower: list[DroneState] = [
            AtZone("start"), AtZone("start"), AtZone("a"), AtZone("end"),
        ]
        self.assertIsNone(self.reservation.try_add(follower))

    def test_restricted_queue_from_subject_example(self) -> None:
        # D2 starts crossing on the turn D1 arrives (Subject VII.3).
        self.assertIsNone(self.reservation.try_add(R_ROUTE))
        follower: list[DroneState] = [
            AtZone("start"), AtZone("start"), InTransit("start", "r"),
            AtZone("r"), AtZone("end"),
        ]
        error = self.reservation.try_add(follower)
        # r (capacity 1) is free again at S_3 because D1 left in turn 2.
        self.assertIsNone(error)

    def test_restricted_entry_while_connection_busy_is_rejected(self) -> None:
        graph = graph_from_text(MAP.replace(
            "[zone=restricted]", "[zone=restricted max_drones=2]"))
        reservation = Reservation(graph)
        self.assertIsNone(reservation.try_add(R_ROUTE))
        error = reservation.try_add(R_ROUTE)
        self.assertIn("connection r-start over capacity in turn 0",
                      str(error))
        self.assertEqual(len(reservation.plans), 1)

    def test_committed_plan_is_isolated_from_caller_list(self) -> None:
        plan = list(A_ROUTE)
        self.assertIsNone(self.reservation.try_add(plan))
        plan[1] = AtZone("start")
        self.assertEqual(self.reservation.plans[0][1], AtZone("a"))

    def test_link_capacity_is_shared_by_both_directions(self) -> None:
        graph = graph_from_text(
            "nb_drones: 2\nstart_hub: start 0 0\n"
            "hub: a 1 0 [max_drones=2]\nhub: b 2 0 [max_drones=2]\n"
            "end_hub: end 3 0\nconnection: start-a\n"
            "connection: a-b\nconnection: b-end\nconnection: start-b\n"
        )
        reservation = Reservation(graph)
        east: list[DroneState] = [
            AtZone("start"), AtZone("a"), AtZone("b"), AtZone("end")]
        west: list[DroneState] = [
            AtZone("start"), AtZone("b"), AtZone("a"), AtZone("b"),
            AtZone("end")]
        self.assertIsNone(reservation.try_add(east))
        self.assertIn("connection a-b", str(reservation.try_add(west)))


if __name__ == "__main__":
    unittest.main()
