"""Physical drone states shared by plans, reservations and history.

A drone is either waiting at a zone or crossing a connection toward a
restricted zone. Locations are zone names; resolve zone attributes with
``MapGraph.zone(name)`` and the connection with
``MapGraph.connection_between(from_zone, to_zone)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, Union


@dataclass(frozen=True)
class AtZone:
    """Drone at ``zone``; a delivered drone stays ``AtZone(end)``."""

    zone: str


@dataclass(frozen=True)
class InTransit:
    """Drone on the connection, moving from ``from_zone`` to ``to_zone``.

    The order keeps the travel direction even though connections are
    undirected.
    """

    from_zone: str
    to_zone: str


DroneState: TypeAlias = Union[AtZone, InTransit]
