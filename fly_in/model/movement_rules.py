"""Per-drone movement rules shared by plan validation (T01).

These functions look at one drone only. Capacity is a property of all drones
at the same time and is counted by the callers (Reservation, Simulation)
from ``occupied_zone`` and ``connection_used``.
"""

from __future__ import annotations

from collections.abc import Sequence

from fly_in.model.drone_state import AtZone, DroneState, InTransit
from fly_in.model.map_data import ZoneType
from fly_in.model.map_graph import MapGraph


def step_error(
    graph: MapGraph, before: DroneState, after: DroneState
) -> str | None:
    """Return why ``before -> after`` is illegal for one turn, or ``None``.

    Legal steps: wait in a zone, move to an adjacent normal/priority zone,
    enter the connection toward an adjacent restricted zone, and arrive from
    that connection on the very next turn. A drone at the end never moves.
    """
    if isinstance(before, InTransit):
        if after != AtZone(before.to_zone):
            return f"{before} must arrive at {before.to_zone} next turn"
        return None
    if after == before:
        return None
    if before.zone == graph.end_hub.name:
        return f"delivered drone at {before.zone} must not move"
    if isinstance(after, InTransit):
        if after.from_zone != before.zone:
            return f"{after} does not start from {before.zone}"
        target = after.to_zone
    else:
        target = after.zone
    if graph.connection_between(before.zone, target) is None:
        return f"no connection between {before.zone} and {target}"
    zone_type = graph.zone(target).zone_type
    if zone_type is ZoneType.BLOCKED:
        return f"{target} is blocked"
    is_restricted = zone_type is ZoneType.RESTRICTED
    if is_restricted != isinstance(after, InTransit):
        return (
            f"entering {target} takes {2 if is_restricted else 1} turn(s)"
        )
    return None


def plan_error(graph: MapGraph, plan: Sequence[DroneState]) -> str | None:
    """Return why a single-drone plan is illegal, or ``None``.

    ``plan[t]`` is the state ``S_t``. A plan starts at the start hub and ends
    at the end hub. Every later zone is reached through a connection, so the
    start check plus ``step_error`` also proves that every zone exists.
    """
    if not plan:
        return "empty plan"
    if plan[0] != AtZone(graph.start_hub.name):
        return f"plan starts at {plan[0]}, not at the start hub"
    for turn in range(len(plan) - 1):
        error = step_error(graph, plan[turn], plan[turn + 1])
        if error is not None:
            return f"turn {turn}: {error}"
    if plan[-1] != AtZone(graph.end_hub.name):
        return f"plan ends at {plan[-1]}, not at the end hub"
    return None


def occupied_zone(graph: MapGraph, state: DroneState) -> str | None:
    """Return the capacity-limited zone the state occupies, if any.

    Start and end have no capacity limit; a drone in transit occupies its
    connection, not a zone.
    """
    if isinstance(state, InTransit):
        return None
    if state.zone in (graph.start_hub.name, graph.end_hub.name):
        return None
    return state.zone


def connection_used(
    before: DroneState, after: DroneState
) -> tuple[str, str] | None:
    """Return the undirected connection key a legal step newly uses.

    A one-turn move and entering a restricted connection both count. The
    forced arrival off a connection adds nothing: the drone frees the
    connection that same turn (Subject VII.3, DEC-027).
    """
    if isinstance(before, InTransit):
        return None
    if isinstance(after, InTransit):
        return MapGraph.connection_key(after.from_zone, after.to_zone)
    if after.zone == before.zone:
        return None
    return MapGraph.connection_key(before.zone, after.zone)
