"""Static shortest turns to the end hub, ignoring other drones.

Used to detect an unreachable end (DEC-013), to build the sequential
fallback path (DEC-017), and as the admissible A* heuristic / lower bound.
"""

from __future__ import annotations

import heapq

from fly_in.model.map_data import ZoneType
from fly_in.model.map_graph import MapGraph


class NoPathError(ValueError):
    """No static route connects the start hub to the end hub."""

    def __init__(self) -> None:
        """Use the accepted user-facing message (DEC-013)."""
        super().__init__("No path from start to end.")


def entry_turns(graph: MapGraph, zone: str) -> int | None:
    """Return turns needed to enter ``zone``; ``None`` if it is blocked."""
    zone_type = graph.zone(zone).zone_type
    if zone_type is ZoneType.BLOCKED:
        return None
    return 2 if zone_type is ZoneType.RESTRICTED else 1


def turns_to_end(graph: MapGraph) -> dict[str, int]:
    """Return the fewest turns from each zone to the end; unreachable absent.

    Dijkstra runs backward from the end. Moving ``u -> v`` costs the entry
    turns of ``v``, so relaxing from ``v`` adds ``entry_turns(v)``.
    """
    end = graph.end_hub.name
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


def static_path(graph: MapGraph) -> list[str]:
    """Return one fewest-turn zone path from start to end.

    Among equally fast next steps a priority zone is taken first (DEC-020),
    then the smaller name for determinism.

    Raises:
        NoPathError: If the end is unreachable.
    """
    distance = turns_to_end(graph)
    zone = graph.start_hub.name
    if zone not in distance:
        raise NoPathError()
    path = [zone]
    while zone != graph.end_hub.name:
        steps = [
            neighbor for neighbor in graph.neighbors_for(zone)
            if neighbor in distance
            and entry_turns(graph, neighbor)
            == distance[zone] - distance[neighbor]
        ]
        zone = min(steps, key=lambda name: (
            graph.zone(name).zone_type is not ZoneType.PRIORITY, name))
        path.append(zone)
    return path
