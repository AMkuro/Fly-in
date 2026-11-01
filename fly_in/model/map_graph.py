"""Graph view built from validated Fly-in map data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from fly_in.model.connection_model import Connection
from fly_in.model.zone_model import Zone


@dataclass(frozen=True)
class MapGraph:
    """Static zone and connection indexes, independent of execution roles.

    Build from models after whole-map validation. Blocked zones remain in the
    topology; routing must exclude them from paths.
    """

    zones: Mapping[str, Zone]
    connections: tuple[Connection, ...]
    _connections_by_pair: Mapping[tuple[str, str], Connection]
    _zone_adjacency: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_models(
        cls, zones: Mapping[str, Zone], connections: Sequence[Connection]
    ) -> MapGraph:
        """Build topology indexes from already validated map models."""
        zones = dict(zones)
        connections_by_pair: dict[tuple[str, str], Connection] = {}
        zone_adjacency: dict[str, list[str]] = {
            zone_name: [] for zone_name in zones
        }

        for connection in connections:
            key = cls.connection_key(connection.a, connection.b)
            connections_by_pair[key] = connection
            zone_adjacency[connection.a].append(connection.b)
            zone_adjacency[connection.b].append(connection.a)

        return cls(
            zones=MappingProxyType(zones),
            connections=tuple(connections),
            _connections_by_pair=MappingProxyType(connections_by_pair),
            _zone_adjacency=MappingProxyType(
                {
                    zone_name: tuple(neighbors)
                    for zone_name, neighbors in zone_adjacency.items()
                }
            ),
        )

    @staticmethod
    def connection_key(a: str, b: str) -> tuple[str, str]:
        """Return the canonical undirected key for two zone names."""
        return Connection.key(a, b)

    def zone(self, zone_name: str) -> Zone:
        """Return a zone by name."""
        return self.zones[zone_name]

    def neighbors_for(self, zone_name: str) -> tuple[str, ...]:
        """Return every directly adjacent zone name."""
        return self._zone_adjacency[zone_name]

    def link_capacity(self, a: str, b: str) -> int:
        """Return the capacity of the existing connection between two zones."""
        return self._connections_by_pair[
            self.connection_key(a, b)
        ].max_link_capacity

    def connection_between(self, a: str, b: str) -> Connection | None:
        """Return the connection between two zones, if one exists."""
        return self._connections_by_pair.get(self.connection_key(a, b))
