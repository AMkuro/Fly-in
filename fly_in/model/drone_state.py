"""Physical drone states shared by plans, reservations and history.

A drone is either waiting at a zone or crossing a connection toward a
restricted zone. Locations are zone names; resolve zone attributes with
``MapGraph.zone(name)`` and the connection with
``MapGraph.connection_between(from_zone, to_zone)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, Union

from fly_in.model.map_data import _validate_zone_name


@dataclass(frozen=True)
class AtZone:
    """Drone at ``zone``; a delivered drone stays ``AtZone(end)``."""

    zone: str

    def __post_init__(self) -> None:
        """Reject names that cannot be a zone on any map."""
        _validate_zone_name(self.zone, "zone")


@dataclass(frozen=True)
class InTransit:
    """Drone on the connection, moving from ``from_zone`` to ``to_zone``.

    The order keeps the travel direction even though connections are
    undirected.
    """

    from_zone: str
    to_zone: str

    def __post_init__(self) -> None:
        """Reject names and self-loops that no map can contain.

        Whether the zones exist, are adjacent, and whether ``to_zone`` is
        restricted depends on the map and is checked by plan validation.
        """
        _validate_zone_name(self.from_zone, "from_zone")
        _validate_zone_name(self.to_zone, "to_zone")
        if self.from_zone == self.to_zone:
            raise ValueError("InTransit endpoints must be different zones.")


DroneState: TypeAlias = Union[AtZone, InTransit]
