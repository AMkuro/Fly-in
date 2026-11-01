"""Static shortest turns to the end hub, ignoring other drones.

Used to detect an unreachable end, to build the sequential
fallback path, and as the admissible A* heuristic / lower bound.
"""

from __future__ import annotations

import heapq

from fly_in.model.map_graph import MapGraph
from fly_in.model.scenario import Scenario
from fly_in.model.zone_model import ZoneType


class NoPathError(ValueError):
    """No static route connects the start hub to the end hub."""

    def __init__(self) -> None:
        """Use the user-facing message required for an unreachable end."""
        super().__init__("No path from start to end.")


def entry_turns(graph: MapGraph, zone: str) -> int | None:
    """Return turns needed to enter ``zone``; ``None`` if it is blocked."""
    zone_type = graph.zone(zone).zone_type
    if zone_type is ZoneType.BLOCKED:
        return None
    return 2 if zone_type is ZoneType.RESTRICTED else 1


def turns_to_end(scenario: Scenario) -> dict[str, int]:
    """Return the fewest turns from each zone to the end.

    Dijkstra runs backward from the end. Moving ``u -> v`` costs the entry
    turns of ``v``, so relaxing from ``v`` adds ``entry_turns(v)``. A zone's
    value therefore excludes the cost of entering that zone itself.

    Zones with no route to the end are absent. A blocked zone next to a
    reachable zone is present but never expanded, so no route passes through
    it; a presence in the result does not mean the zone can be entered.
    """
    graph = scenario.graph
    end = scenario.end_name
    distance = {end: 0}
    queue = [(0, end)]
    while queue:
        turns, zone = heapq.heappop(queue)
        if turns > distance[zone]:
            continue
        cost = entry_turns(graph, zone)
        if cost is None:
            continue
        for neighbor in graph.neighbors_for(zone):
            candidate = turns + cost
            if candidate < distance.get(neighbor, candidate + 1):
                distance[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return distance


def static_path(scenario: Scenario) -> list[str]:
    """Return one fewest-turn zone path from start to end.

    Among equally fast next steps, a priority zone is taken first,
    then the smaller name for determinism.

    Raises:
        NoPathError: If the end is unreachable.
    """
    graph = scenario.graph
    distance = turns_to_end(scenario)
    zone = scenario.start_name
    if zone not in distance:
        raise NoPathError()
    path = [zone]
    while zone != scenario.end_name:
        steps = [
            neighbor
            for neighbor in graph.neighbors_for(zone)
            if neighbor in distance
            and entry_turns(graph, neighbor)
            == distance[zone] - distance[neighbor]
        ]
        zone = min(
            steps,
            key=lambda name: (
                graph.zone(name).zone_type is not ZoneType.PRIORITY,
                name,
            ),
        )
        path.append(zone)
    return path
