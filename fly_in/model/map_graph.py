"""Graph view built from validated Fly-in map data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from fly_in.model.map_data import Connection, MapData, Zone, ZoneType


@dataclass(frozen=True)
class MapGraph:
    """Adjacency-oriented view of a validated map.

    ``MapData`` keeps the parser-facing facts. ``MapGraph`` indexes those facts
    for graph operations such as pathfinding and future simulation.
    """

    nb_drones: int
    start_hub: Zone
    end_hub: Zone
    zones: Mapping[str, Zone]
    connections: tuple[Connection, ...]
    connections_by_name: Mapping[str, Connection]
    connections_by_key: Mapping[tuple[str, str], Connection]
    connections_by_zone: Mapping[str, tuple[Connection, ...]]
    neighbors_by_zone: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_map_data(cls, map_data: MapData) -> "MapGraph":
        """Build adjacency indexes from already-validated ``MapData``."""
        cleaned_zone: dict[str, Zone] = {
            k: v
            for k, v in map_data.zones.items()
            if v.zone_type != ZoneType.BLOCKED
        }
        connections_by_name: dict[str, Connection] = {}
        connections_by_key: dict[tuple[str, str], Connection] = {}
        connections_by_zone: dict[str, list[Connection]] = {
            zone_name: [] for zone_name in cleaned_zone
        }
        neighbors_by_zone: dict[str, list[str]] = {
            zone_name: [] for zone_name in cleaned_zone
        }

        for connection in map_data.connections:
            connections_by_name[connection.name] = connection
            key = cls.connection_key(connection.a, connection.b)
            connections_by_key[key] = connection
            connections_by_zone[connection.a].append(connection)
            connections_by_zone[connection.b].append(connection)
            neighbors_by_zone[connection.a].append(connection.b)
            neighbors_by_zone[connection.b].append(connection.a)

        return cls(
            nb_drones=map_data.nb_drones,
            start_hub=cleaned_zone[map_data.start_hub_name],
            end_hub=cleaned_zone[map_data.end_hub_name],
            zones=MappingProxyType(cleaned_zone),
            connections=tuple(map_data.connections),
            connections_by_name=MappingProxyType(connections_by_name),
            connections_by_key=MappingProxyType(connections_by_key),
            connections_by_zone=MappingProxyType(
                {
                    zone_name: tuple(connections)
                    for zone_name, connections in connections_by_zone.items()
                }
            ),
            neighbors_by_zone=MappingProxyType(
                {
                    zone_name: tuple(neighbors)
                    for zone_name, neighbors in neighbors_by_zone.items()
                }
            ),
        )

    @staticmethod
    def connection_key(a: str, b: str) -> tuple[str, str]:
        """Return the canonical undirected key for two zone names."""
        return (a, b) if a <= b else (b, a)

    def zone(self, zone_name: str) -> Zone:
        """Return a zone by name."""
        return self.zones[zone_name]

    def connection(self, connection_name: str) -> Connection:
        """Return a connection by name."""
        return self.connections_by_name[connection_name]

    def connection_by_name(self, connection_name: str) -> Connection | None:
        """Return a connection by name, if it exists."""
        return self.connections_by_name.get(connection_name)

    def connections_for(self, zone_name: str) -> tuple[Connection, ...]:
        """Return every connection touching ``zone_name``."""
        return self.connections_by_zone[zone_name]

    def neighbors_for(self, zone_name: str) -> tuple[str, ...]:
        """Return every directly adjacent zone name."""
        return self.neighbors_by_zone[zone_name]

    def connection_between(self, a: str, b: str) -> Connection | None:
        """Return the connection between two zones, if one exists."""
        return self.connections_by_key.get(self.connection_key(a, b))

    def other_endpoint(self, connection: Connection, zone_name: str) -> str:
        """Return the endpoint opposite ``zone_name`` on ``connection``."""
        if connection.a == zone_name:
            return connection.b
        if connection.b == zone_name:
            return connection.a
        raise ValueError(
            f"zone {zone_name!r} is not an endpoint of connection "
            f"{connection.name!r}."
        )
