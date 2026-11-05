"""Which drones are on each zone and connection in one confirmed state.

This is a read-only view of one ``TurnState`` ``S_t`` for display. It counts
where drones are *at the end of the turn*; it does not decide whether a move
was legal and must never feed Reservation or Simulation capacity checks.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from fly_in.model.map_graph import MapGraph
from fly_in.simulation.simulation import TurnState


@dataclass(frozen=True)
class TurnOccupancy:
    """Drone ids (1-based, ascending) per zone name and connection name.

    A connection is undirected, so ``InTransit`` drones travelling in both
    directions are listed together under the connection's name.
    """

    zone_drones: Mapping[str, tuple[int, ...]]
    connection_drones: Mapping[str, tuple[int, ...]]

    @classmethod
    def from_state(cls, state: TurnState, graph: MapGraph) -> TurnOccupancy:
        """Group the drones of ``state`` by where they currently are.

        Raises:
            ValueError: If an ``InTransit`` drone is not on any connection of
                ``graph``, which a verified history never contains.
        """
        zones: defaultdict[str, list[int]] = defaultdict(list)
        connections: defaultdict[str, list[int]] = defaultdict(list)
        for index, drone in enumerate(state):
            drone_id = index + 1
            zone = drone.resident_zone
            if zone is not None:
                zones[zone].append(drone_id)
                continue
            from_zone, to_zone = drone.travel_zones
            connection = graph.connection_between(from_zone, to_zone)
            if connection is None:
                raise ValueError(
                    f"drone {drone_id} is in transit on a missing "
                    f"connection {from_zone}-{to_zone}"
                )
            connections[connection.name].append(drone_id)
        return cls(
            {name: tuple(ids) for name, ids in zones.items()},
            {name: tuple(ids) for name, ids in connections.items()},
        )

    def zone_ids(self, zone_name: str) -> tuple[int, ...]:
        """Return the drones at ``zone_name`` (empty if none)."""
        return self.zone_drones.get(zone_name, ())

    def connection_ids(self, connection_name: str) -> tuple[int, ...]:
        """Return the drones in transit on the connection (empty if none)."""
        return self.connection_drones.get(connection_name, ())
