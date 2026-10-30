"""Sequential delivery: one drone at a time along a static path (DEC-017).

Every drone waits at start (no capacity limit) until the previous one has
reached the end (no capacity limit), so no two drones are ever between the
hubs together. With path length ``L`` turns and ``K`` drones the makespan
is ``K * L``: always legal, rarely fast.
"""

from __future__ import annotations

from collections.abc import Sequence

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.model.map_graph import MapGraph
from fly_in.pathfinding.simple_dijkstra import entry_turns


def path_states(graph: MapGraph, path: Sequence[str]) -> list[DroneState]:
    """Expand a zone path into ``S_0 ..`` states without waiting."""
    states: list[DroneState] = [AtZone(path[0])]
    for before, after in zip(path, path[1:]):
        if entry_turns(graph, after) == 2:
            states.append(InTransit(before, after))
        states.append(AtZone(after))
    return states


def sequential_plans(
    graph: MapGraph, path: Sequence[str]
) -> list[list[DroneState]]:
    """Return one plan per drone; drone ``k`` departs at turn ``k * L``."""
    route = path_states(graph, path)
    length = len(route) - 1
    start: list[DroneState] = [AtZone(graph.start_hub.name)]
    return [
        start * (drone * length) + route for drone in range(graph.nb_drones)
    ]
