"""Sequential delivery: one drone at a time along a static path.

Every drone waits at start (no capacity limit) until the previous one has
reached the end (no capacity limit), so no two drones are ever between the
hubs together. With path length ``L`` turns and ``K`` drones the completion
turn is ``K * L``: always legal, rarely fast.
"""

from __future__ import annotations

from collections.abc import Sequence

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.model.scenario import Scenario


class SequentialFallback:
    """One legal plan per drone, delivered one after another."""

    def __init__(self, scenario: Scenario, path: Sequence[str]) -> None:
        """Bind the scenario and the zone path every drone follows."""
        self._scenario = scenario
        self._path = path

    def route(self) -> list[DroneState]:
        """Expand the zone path into ``S_0 ..`` states without waiting."""
        graph = self._scenario.graph
        states: list[DroneState] = [AtZone(self._path[0])]
        for before, after in zip(self._path, self._path[1:]):
            if graph.zone(after).entry_turns == 2:
                states.append(InTransit(before, after))
            states.append(AtZone(after))
        return states

    def plans(self) -> list[list[DroneState]]:
        """Return one plan per drone; drone ``k`` departs at ``k * L``."""
        route = self.route()
        length = len(route) - 1
        start: list[DroneState] = [AtZone(self._scenario.start_name)]
        return [
            start * (drone * length) + route
            for drone in range(self._scenario.nb_drones)
        ]
