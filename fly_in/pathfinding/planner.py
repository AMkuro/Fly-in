"""Reservation-aware space-time A* for one drone.

A search node is ``(state, t)``: the drone is in ``state`` at ``S_t``.
Each step costs one turn, so ``g = t`` and ``f = t + h`` where ``h`` is the
static fewest turns to the end (admissible: other drones only add delay).
The first goal popped is therefore the earliest legal arrival given the
committed plans. Ties on ``f`` are broken by more priority zones entered,
then by a congestion score and a seeded random order that the
Scheduler varies between attempts.
"""

from __future__ import annotations

import heapq
import itertools
import random
from collections.abc import Mapping
from dataclasses import dataclass

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.model.zone_model import ZoneType
from fly_in.model.map_graph import MapGraph
from fly_in.pathfinding.reservation import Reservation
from fly_in.pathfinding.static_distance import entry_turns

Node = tuple[DroneState, int]
QueueItem = tuple[int, int, int, float, int, Node, Node | None]


@dataclass(frozen=True)
class SearchParams:
    """Planner knobs the Scheduler changes between attempts.

    ``congestion_weight`` adds the committed usage of every zone and
    connection the drone uses to the tie-break score (route dispersion).
    ``seed`` reorders candidates that are otherwise equal.
    """

    congestion_weight: int = 0
    seed: int = 0


def plan_drone(
    reservation: Reservation,
    distance: Mapping[str, int],
    deadline: int,
    params: SearchParams,
) -> list[DroneState] | None:
    """Return the earliest legal plan arriving by ``deadline``, or ``None``.

    ``distance`` is ``StaticDistance.turns_to_end`` of the same scenario.
    The reservation is only read; committing the plan is the caller's job.
    """
    scenario = reservation.scenario
    goal = AtZone(scenario.end_name)
    start: Node = (AtZone(scenario.start_name), 0)
    rng = random.Random(params.seed)
    order = itertools.count()
    queue: list[QueueItem] = [(
        _heuristic(start[0], distance), 0, 0, rng.random(), next(order),
        start, None,
    )]
    parent: dict[Node, Node | None] = {}
    while queue:
        _, priorities, congestion, _, _, node, previous = heapq.heappop(queue)
        if node in parent:
            continue
        parent[node] = previous
        state, turn = node
        if state == goal:
            return _rebuild(parent, node)
        for after, gained, crowd in _successors(reservation, state, turn):
            child: Node = (after, turn + 1)
            if child in parent or _unreachable(after, distance):
                continue
            estimate = turn + 1 + _heuristic(after, distance)
            if estimate > deadline:
                continue
            heapq.heappush(queue, (
                estimate,
                priorities - gained,
                congestion + params.congestion_weight * crowd,
                rng.random(),
                next(order),
                child,
                node,
            ))
    return None


def _unreachable(state: DroneState, distance: Mapping[str, int]) -> bool:
    """Return whether the end cannot be reached from ``state`` at all."""
    zone = state.to_zone if isinstance(state, InTransit) else state.zone
    return zone not in distance


def _heuristic(state: DroneState, distance: Mapping[str, int]) -> int:
    """Static fewest turns to the end; a transit still needs its arrival."""
    if isinstance(state, InTransit):
        return 1 + distance[state.to_zone]
    return distance[state.zone]


def _successors(
    reservation: Reservation, state: DroneState, turn: int
) -> list[tuple[DroneState, int, int]]:
    """Return ``(next_state, priority_entered, crowd)`` legal at ``turn``.

    Capacity is checked against committed plans plus this drone: a zone at
    ``S_(turn+1)`` and a connection used in move ``turn``.
    """
    if isinstance(state, InTransit):
        arrival = AtZone(state.to_zone)
        if not _zone_has_room(reservation, arrival.zone, turn + 1):
            return []
        return [(arrival, 0, _zone_crowd(reservation, arrival, turn + 1))]
    graph = reservation.graph
    result: list[tuple[DroneState, int, int]] = []
    if _zone_has_room(reservation, state.zone, turn + 1):
        result.append((state, 0, _zone_crowd(reservation, state, turn + 1)))
    for neighbor in graph.neighbors_for(state.zone):
        turns = entry_turns(graph, neighbor)
        key = MapGraph.connection_key(state.zone, neighbor)
        link_used = reservation.connection_usage(turn, key)
        if turns is None or link_used >= reservation.connection_capacity(key):
            continue
        if turns == 2:
            result.append((InTransit(state.zone, neighbor), 0, link_used))
            continue
        if not _zone_has_room(reservation, neighbor, turn + 1):
            continue
        after = AtZone(neighbor)
        is_priority = graph.zone(neighbor).zone_type is ZoneType.PRIORITY
        crowd = link_used + _zone_crowd(reservation, after, turn + 1)
        result.append((after, int(is_priority), crowd))
    return result


def _zone_has_room(reservation: Reservation, zone: str, turn: int) -> bool:
    """Return whether one more drone fits in ``zone`` at ``S_turn``."""
    scenario = reservation.scenario
    if zone in (scenario.start_name, scenario.end_name):
        return True
    used = reservation.zone_occupancy(turn, zone)
    return used < reservation.zone_capacity(zone)


def _zone_crowd(reservation: Reservation, state: AtZone, turn: int) -> int:
    """Return committed drones sharing the zone at ``S_turn``."""
    return reservation.zone_occupancy(turn, state.zone)


def _rebuild(parent: dict[Node, Node | None], goal: Node) -> list[DroneState]:
    """Follow parent links back to ``S_0`` and return ``plan[t]``."""
    plan: list[DroneState] = []
    node: Node | None = goal
    while node is not None:
        plan.append(node[0])
        node = parent[node]
    plan.reverse()
    return plan
