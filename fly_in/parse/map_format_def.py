"""Shared map-format definitions for Fly-in parsing."""

from __future__ import annotations

from enum import Enum


class LineKey(str, Enum):
    """Top-level keys accepted by the Fly-in map format."""

    NB_DRONES = "nb_drones"
    START_HUB = "start_hub"
    END_HUB = "end_hub"
    HUB = "hub"
    CONNECTION = "connection"


class MapParseError(ValueError):
    """A map parsing error with the source line number."""

    def __init__(self, line_number: int, message: str) -> None:
        super().__init__(f"line {line_number}: {message}")
        self.line_number = line_number


ParsedLine = tuple[int, LineKey, str]
RawMap = dict[str, object]
RawZone = dict[str, object]
RawConnection = dict[str, object]

SINGLETON_LINE_KEYS = frozenset(
    {LineKey.NB_DRONES, LineKey.START_HUB, LineKey.END_HUB}
)
ZONE_METADATA_KEY = "zone"
ZONE_TYPE_FIELD = "zone_type"
MODEL_METADATA_KEYS = frozenset({"color", "max_drones", "max_link_capacity"})
