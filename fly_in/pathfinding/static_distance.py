"""Static shortest turns to the end hub, ignoring other drones.

Used to detect an unreachable end, to build the sequential
fallback path, and as the admissible A* heuristic / lower bound.
``StaticDistance`` runs the search once and shares the result.
"""

from __future__ import annotations

import heapq
from collections.abc import Mapping
from types import MappingProxyType

from fly_in.model.scenario import Scenario
from fly_in.model.zone_model import ZoneType


class NoPathError(ValueError):
    """No static route connects the start hub to the end hub."""

    def __init__(self) -> None:
        """Use the user-facing message required for an unreachable end."""
        super().__init__("No path from start to end.")


class StaticDistance:
    """Fewest turns to the end for one scenario, searched exactly once.

    Other drones are ignored. ``turns_to_end`` and ``path()`` read the same
    result, so nothing is recomputed after construction.
    """

    def __init__(self, scenario: Scenario) -> None:
        """Run the backward search from the end of ``scenario``."""
        self._scenario = scenario
        self.turns_to_end: Mapping[str, int] = MappingProxyType(
            self._search()
        )

    def _search(self) -> dict[str, int]:
        """Return the fewest turns from each zone to the end.

        Dijkstra runs backward from the end. Moving ``u -> v`` costs the
        entry turns of ``v``, so relaxing from ``v`` adds
        ``Zone.entry_turns`` of ``v``. A zone's value therefore excludes the
        cost of entering that zone itself.

        Zones with no route to the end are absent. A blocked zone next to a
        reachable zone is present but never expanded, so no route passes
        through it; a presence in the result does not mean the zone can be
        entered.
        """
        graph = self._scenario.graph
        end = self._scenario.end_name
        distance = {end: 0}
        queue = [(0, end)]
        while queue:
            turns, zone = heapq.heappop(queue)
            if turns > distance[zone]:
                continue
            cost = graph.zone(zone).entry_turns
            if cost is None:
                continue
            for neighbor in graph.neighbors_for(zone):
                candidate = turns + cost
                if candidate < distance.get(neighbor, candidate + 1):
                    distance[neighbor] = candidate
                    heapq.heappush(queue, (candidate, neighbor))
        return distance

    def path(self) -> list[str]:
        """Return one fewest-turn zone path from start to end.

        Among equally fast next steps, a priority zone is taken first,
        then the larger name for determinism.

        Raises:
            NoPathError: If the end is unreachable.
        """
        graph = self._scenario.graph
        distance = self.turns_to_end
        zone = self._scenario.start_name
        if zone not in distance:
            raise NoPathError()
        path = [zone]
        while zone != self._scenario.end_name:
            steps = [
                neighbor
                for neighbor in graph.neighbors_for(zone)
                if neighbor in distance
                and graph.zone(neighbor).entry_turns
                == distance[zone] - distance[neighbor]
            ]
            zone = max(
                steps,
                key=lambda name: (
                    graph.zone(name).zone_type is ZoneType.PRIORITY,
                    name,
                ),
            )
            path.append(zone)
        return path
