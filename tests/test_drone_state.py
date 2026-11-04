"""Unit checks for the two drone physical states."""

import dataclasses
import unittest

from fly_in.model.drone_state import AtZone, DroneState, InTransit


def describe(state: DroneState) -> str:
    """Branch on the state kind the way later consumers are expected to."""
    match state:
        case AtZone(zone):
            return f"at {zone}"
        case InTransit(from_zone, to_zone):
            return f"{from_zone}->{to_zone}"
    raise AssertionError(f"unexpected state {state!r}")


class DroneStateTests(unittest.TestCase):
    def test_fields_hold_zone_names(self) -> None:
        self.assertEqual(AtZone("hub").zone, "hub")
        transit = InTransit("hub", "roof")
        self.assertEqual(transit.from_zone, "hub")
        self.assertEqual(transit.to_zone, "roof")

    def test_kinds_are_distinguishable(self) -> None:
        self.assertEqual(describe(AtZone("a")), "at a")
        self.assertEqual(describe(InTransit("a", "b")), "a->b")
        self.assertNotIsInstance(AtZone("a"), InTransit)
        self.assertNotIsInstance(InTransit("a", "b"), AtZone)

    def test_value_equality_and_direction(self) -> None:
        self.assertEqual(AtZone("a"), AtZone("a"))
        self.assertNotEqual(AtZone("a"), AtZone("b"))
        self.assertEqual(InTransit("a", "b"), InTransit("a", "b"))
        self.assertNotEqual(InTransit("a", "b"), InTransit("b", "a"))
        self.assertEqual(len({AtZone("a"), AtZone("a"), InTransit("a", "b")}),
                         2)

    def test_states_are_immutable(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
            AtZone("a").zone = "b"  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            InTransit("a", "b").to_zone = "c"  # type: ignore[misc]

    def test_rejects_states_no_map_can_contain(self) -> None:
        for name in ("", "a-b", "a b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                AtZone(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                InTransit(name, "z")
            with self.subTest(name=name), self.assertRaises(ValueError):
                InTransit("z", name)
        with self.assertRaises(ValueError):
            InTransit("a", "a")

    def test_plan_example_with_restricted_move(self) -> None:
        # start -> r (restricted, 2 turns) -> end; index t is S_t.
        plan: list[DroneState] = [
            AtZone("start"),
            InTransit("start", "r"),
            AtZone("r"),
            AtZone("end"),
        ]
        self.assertEqual([describe(state) for state in plan],
                         ["at start", "start->r", "at r", "at end"])
        self.assertEqual(plan[-1], AtZone("end"))

    def test_state_is_abstract_and_both_kinds_derive_from_it(self) -> None:
        with self.assertRaises(TypeError):
            DroneState()  # type: ignore[abstract]
        self.assertIsInstance(AtZone("a"), DroneState)
        self.assertIsInstance(InTransit("a", "b"), DroneState)

    def test_destination_and_settle_turns(self) -> None:
        at_zone, transit = AtZone("a"), InTransit("a", "b")
        self.assertEqual((at_zone.destination, at_zone.settle_turns), ("a", 0))
        self.assertEqual((transit.destination, transit.settle_turns), ("b", 1))

    def test_resident_zone_is_none_only_in_transit(self) -> None:
        self.assertEqual(AtZone("a").resident_zone, "a")
        self.assertIsNone(InTransit("a", "b").resident_zone)

    def test_travel_zones_follow_travel_order(self) -> None:
        self.assertEqual(AtZone("a").travel_zones, ("a",))
        self.assertEqual(InTransit("a", "b").travel_zones, ("a", "b"))
        self.assertEqual(InTransit("b", "a").travel_zones, ("b", "a"))

    def test_travel_zones_end_at_destination(self) -> None:
        for state in (AtZone("a"), InTransit("a", "b")):
            with self.subTest(state=state):
                self.assertEqual(state.travel_zones[-1], state.destination)


if __name__ == "__main__":
    unittest.main()
