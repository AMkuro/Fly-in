"""Per-drone movement rules shared by plan validation.

``MovementRules`` looks at one drone only. Capacity is a property of all
drones at the same time and is counted by the callers (Reservation,
Simulation) from ``occupied_zone`` and ``connection_used``.
"""

from __future__ import annotations

from collections.abc import Sequence

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.model.zone_model import ZoneType
from fly_in.model.connection_model import Connection
from fly_in.model.scenario import Scenario


class MovementRules:
    """The legal moves of one drone on the map of one scenario."""

    def __init__(self, scenario: Scenario) -> None:
        """Bind the scenario whose map and hubs the rules refer to."""
        self._scenario = scenario

    def step_error(self, before: DroneState, after: DroneState) -> str | None:
        """Return why ``before -> after`` is illegal for one turn, or None.

        Legal steps: wait in a zone, move to an adjacent normal/priority
        zone, enter the connection toward an adjacent restricted zone, and
        arrive from that connection on the very next turn. A drone at the
        end never moves.
        """
        scenario = self._scenario
        graph = scenario.graph
        if isinstance(before, InTransit):
            if after != AtZone(before.to_zone):
                return f"{before} must arrive at {before.to_zone} next turn"
            return None
        if after == before:
            return None
        if before.destination == scenario.end_name:
            return f"delivered drone at {before.destination} must not move"
        if isinstance(after, InTransit):
            if after.from_zone != before.destination:
                return f"{after} does not start from {before.destination}"
        target = after.destination
        if graph.connection_between(before.destination, target) is None:
            return f"no connection between {before.destination} and {target}"
        zone_type = graph.zone(target).zone_type
        if zone_type is ZoneType.BLOCKED:
            return f"{target} is blocked"
        is_restricted = zone_type is ZoneType.RESTRICTED
        if is_restricted != isinstance(after, InTransit):
            return (
                f"entering {target} takes {2 if is_restricted else 1} "
                "turn(s)"
            )
        return None

    def plan_error(self, plan: Sequence[DroneState]) -> str | None:
        """Return why a single-drone plan is illegal, or ``None``.

        ``plan[t]`` is the state ``S_t``. A plan starts at the start hub and
        ends at the end hub. Every later zone is reached through a
        connection, so the start check plus ``step_error`` also proves that
        every zone exists.
        """
        scenario = self._scenario
        if not plan:
            return "empty plan"
        if plan[0] != AtZone(scenario.start_name):
            return f"plan starts at {plan[0]}, not at the start hub"
        for turn in range(len(plan) - 1):
            error = self.step_error(plan[turn], plan[turn + 1])
            if error is not None:
                return f"turn {turn}: {error}"
        if plan[-1] != AtZone(scenario.end_name):
            return f"plan ends at {plan[-1]}, not at the end hub"
        return None

    def occupied_zone(self, state: DroneState) -> str | None:
        """Return the capacity-limited zone the state occupies, if any.

        Start and end have no capacity limit; a drone in transit occupies
        its connection, not a zone.
        """
        zone = state.resident_zone
        if zone in (self._scenario.start_name, self._scenario.end_name):
            return None
        return zone

    @staticmethod
    def connection_used(
        before: DroneState, after: DroneState
    ) -> tuple[str, str] | None:
        """Return the undirected connection key a legal step newly uses.

        A one-turn move and entering a restricted connection both count. The
        forced arrival off a connection adds nothing: the drone frees the
        connection that same turn (Subject VII.3).
        """
        if isinstance(before, InTransit):
            return None
        if isinstance(after, InTransit):
            return Connection.key(after.from_zone, after.to_zone)
        if after.destination == before.destination:
            return None
        return Connection.key(before.destination, after.destination)
