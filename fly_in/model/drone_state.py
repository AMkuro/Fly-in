"""Physical drone states shared by plans, reservations and history.

A drone is either waiting at a zone or crossing a connection toward a
restricted zone. Locations are zone names; resolve zone attributes with
``MapGraph.zone(name)`` and the connection with
``MapGraph.connection_between(from_zone, to_zone)``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from fly_in.model.zone_model import Zone


class DroneState(ABC):
    """Where one drone is during one turn, as zone names only.

    Each state answers the questions that differ between waiting in a zone
    and crossing a connection, so callers do not branch on the concrete
    class. Answers depend only on the state's own names, never on a map.
    """

    @property
    @abstractmethod
    def destination(self) -> str:
        """Return the zone the drone stands in once any crossing is over."""

    @property
    @abstractmethod
    def settle_turns(self) -> int:
        """Return the turns still needed to stand in ``destination``."""

    @property
    @abstractmethod
    def resident_zone(self) -> str | None:
        """Return the zone the drone stands in now, or ``None`` in transit."""

    @abstractmethod
    def token(self, drone_id: int) -> str:
        """Format this state as one movement token (Subject VII.5)."""


@dataclass(frozen=True)
class AtZone(DroneState):
    """Drone at ``zone``; a delivered drone stays ``AtZone(end)``."""

    zone: str

    @property
    def destination(self) -> str:
        """Return the zone the drone is already standing in."""
        return self.zone

    @property
    def settle_turns(self) -> int:
        """Return 0: the drone already stands in its destination."""
        return 0

    @property
    def resident_zone(self) -> str | None:
        """Return the zone the drone stands in."""
        return self.zone

    def token(self, drone_id: int) -> str:
        """Format the move as ``D<ID>-<zone>``."""
        return f"D{drone_id}-{self.zone}"

    def __post_init__(self) -> None:
        """Reject names that cannot be a zone on any map."""
        Zone.check_name(self.zone, "zone")


@dataclass(frozen=True)
class InTransit(DroneState):
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
        Zone.check_name(self.from_zone, "from_zone")
        Zone.check_name(self.to_zone, "to_zone")
        if self.from_zone == self.to_zone:
            raise ValueError("InTransit endpoints must be different zones.")

    @property
    def destination(self) -> str:
        """Return the zone the drone arrives in next turn."""
        return self.to_zone

    @property
    def settle_turns(self) -> int:
        """Return 1: the forced arrival takes the next turn."""
        return 1

    @property
    def resident_zone(self) -> str | None:
        """Return ``None``: a drone in transit occupies no zone."""
        return None

    def token(self, drone_id: int) -> str:
        """Format the move as ``D<ID>-<from>-<to>`` in travel order."""
        return f"D{drone_id}-{self.from_zone}-{self.to_zone}"
