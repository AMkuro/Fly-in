"""Committed single-drone plans plus a sparse capacity cache (DEC-027/028).

The committed plans are the source of truth. ``zone_occupancy[t][zone]`` is
the number of drones in ``zone`` at state ``S_t``; ``connection_usage[t]
[key]`` is the usage of the undirected connection during the move
``S_t -> S_(t+1)``. Missing keys mean 0. After a plan ends, its drone stays
at the end hub, which has no capacity limit, so nothing is cached for it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Sequence
from typing import TypeVar

from fly_in.model.drone_state import DroneState
from fly_in.model.map_graph import MapGraph
from fly_in.model.movement_rules import (
    connection_used,
    occupied_zone,
    plan_error,
)

ZoneDelta = dict[int, Counter[str]]
ConnectionDelta = dict[int, Counter[tuple[str, str]]]
Key = TypeVar("Key", bound=Hashable)


class Reservation:
    """Validate candidate plans and commit them atomically.

    Invariants: every committed plan is legal for one drone, every capacity
    holds with all committed plans together, and the cache always equals
    what ``_deltas`` would rebuild from the committed plans.
    """

    def __init__(self, graph: MapGraph) -> None:
        """Start with no planned drone; unplanned drones wait at start."""
        self._graph = graph
        self._plans: list[tuple[DroneState, ...]] = []
        self._zone_occupancy: ZoneDelta = {}
        self._connection_usage: ConnectionDelta = {}

    @property
    def graph(self) -> MapGraph:
        """Return the static map whose capacities are enforced."""
        return self._graph

    @property
    def plans(self) -> tuple[tuple[DroneState, ...], ...]:
        """Return the committed plans in commit order (Drone 1, 2, ...)."""
        return tuple(self._plans)

    def zone_occupancy(self, turn: int, zone: str) -> int:
        """Return committed drones in ``zone`` at state ``S_turn``."""
        return self._zone_occupancy.get(turn, Counter())[zone]

    def connection_usage(self, turn: int, key: tuple[str, str]) -> int:
        """Return committed usage of ``key`` during move ``S_turn -> +1``."""
        return self._connection_usage.get(turn, Counter())[key]

    def zone_capacity(self, zone: str) -> int:
        """Return the static capacity of a capacity-limited zone."""
        return self._graph.zone(zone).max_drones

    def connection_capacity(self, key: tuple[str, str]) -> int:
        """Return the static capacity of an undirected connection."""
        return self._graph.connections_by_key[key].max_link_capacity

    def try_add(self, plan: Sequence[DroneState]) -> str | None:
        """Commit ``plan`` if legal; return ``None`` or the rejection reason.

        The plan is copied to a tuple so later changes to the caller's list
        cannot desynchronize the cache. On rejection nothing changes.
        """
        candidate = tuple(plan)
        error = plan_error(self._graph, candidate)
        if error is not None:
            return error
        zone_delta, connection_delta = self._deltas(candidate)
        error = self._capacity_error(zone_delta, connection_delta)
        if error is not None:
            return error
        self._plans.append(candidate)
        _merge(self._zone_occupancy, zone_delta)
        _merge(self._connection_usage, connection_delta)
        return None

    def _deltas(
        self, plan: tuple[DroneState, ...]
    ) -> tuple[ZoneDelta, ConnectionDelta]:
        """Count what one plan adds to the cache, without touching it."""
        zone_delta: ZoneDelta = {}
        connection_delta: ConnectionDelta = {}
        for turn, state in enumerate(plan):
            zone = occupied_zone(self._graph, state)
            if zone is not None:
                zone_delta.setdefault(turn, Counter())[zone] += 1
            if turn + 1 < len(plan):
                key = connection_used(state, plan[turn + 1])
                if key is not None:
                    connection_delta.setdefault(turn, Counter())[key] += 1
        return zone_delta, connection_delta

    def _capacity_error(
        self, zone_delta: ZoneDelta, connection_delta: ConnectionDelta
    ) -> str | None:
        """Check ``committed + delta <= capacity`` for every touched cell."""
        for turn, zones in zone_delta.items():
            for zone, added in zones.items():
                used = self.zone_occupancy(turn, zone) + added
                if used > self.zone_capacity(zone):
                    return f"zone {zone} over capacity at S_{turn}"
        for turn, keys in connection_delta.items():
            for key, added in keys.items():
                used = self.connection_usage(turn, key) + added
                if used > self.connection_capacity(key):
                    return (
                        f"connection {key[0]}-{key[1]} over capacity "
                        f"in turn {turn}"
                    )
        return None


def _merge(
    cache: dict[int, Counter[Key]], delta: dict[int, Counter[Key]]
) -> None:
    """Add ``delta`` into ``cache`` in place."""
    for turn, counts in delta.items():
        cache.setdefault(turn, Counter()).update(counts)
