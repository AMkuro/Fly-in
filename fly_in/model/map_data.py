"""Pydantic models for Fly-in map data."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ZoneType(str, Enum):
    """Supported Fly-in zone types."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return all external string values for error messages."""
        return tuple(item.value for item in cls)


def _validate_zone_name(value: str, field_name: str) -> str:
    """Validate a zone name used by zones and connection endpoints."""
    if not value:
        raise ValueError(f"{field_name} must not be empty.")
    if "-" in value:
        raise ValueError(f"{field_name} must not contain dashes.")
    if any(char.isspace() for char in value):
        raise ValueError(f"{field_name} must not contain spaces.")
    return value


class Zone(BaseModel):
    """A zone node in the Fly-in map graph."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    line_number: int = Field(gt=0)
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate subject constraints for zone names."""
        return _validate_zone_name(value, "zone name")

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        """Validate optional color metadata as a single word."""
        if value is None:
            return value
        if not value:
            raise ValueError("color must not be empty.")
        if any(char.isspace() for char in value):
            raise ValueError("color must be a single-word string.")
        return value


class Connection(BaseModel):
    """A bidirectional edge between two Fly-in zones."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    line_number: int = Field(gt=0)
    name: str
    a: str
    b: str
    max_link_capacity: int = Field(default=1, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate generated connection names."""
        if not value:
            raise ValueError("connection name must not be empty.")
        if any(char.isspace() for char in value):
            raise ValueError("connection name must not contain spaces.")
        return value

    @field_validator("a", "b")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        """Validate endpoint names with the same rules as zones."""
        return _validate_zone_name(value, "connection endpoint")

    @model_validator(mode="after")
    def validate_distinct_endpoints(self) -> "Connection":
        """Reject self-loop connections."""
        if self.a == self.b:
            raise ValueError("connection endpoints must be different.")
        return self


class MapData(BaseModel):
    """Validated Fly-in map data."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    nb_drones: int = Field(gt=0)
    zones: dict[str, Zone]
    start_hub_name: str
    end_hub_name: str
    connections: list[Connection] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_zone_layout(cls, data: object) -> object:
        """Convert raw parser zone fields into the internal zone dict."""
        if not isinstance(data, Mapping):
            return data
        if "zones" in data:
            return data

        normalized: dict[str, Any] = dict(data)
        raw_start = normalized.pop("start_hub", None)
        raw_end = normalized.pop("end_hub", None)
        raw_hubs = normalized.pop("hubs", [])

        raw_zones: list[object] = []
        if raw_start is not None:
            start_name = cls._raw_zone_name(raw_start, "start_hub")
            normalized["start_hub_name"] = start_name
            raw_zones.append(raw_start)
        if raw_end is not None:
            end_name = cls._raw_zone_name(raw_end, "end_hub")
            normalized["end_hub_name"] = end_name
            raw_zones.append(raw_end)
        if not isinstance(raw_hubs, list):
            raise ValueError("hubs must be a list.")
        raw_zones.extend(raw_hubs)

        normalized["zones"] = cls._build_zone_dict(raw_zones)
        return normalized

    @field_validator("start_hub_name", "end_hub_name")
    @classmethod
    def validate_hub_name(cls, value: str) -> str:
        """Validate stored start/end references as zone names."""
        return _validate_zone_name(value, "hub name")

    @model_validator(mode="after")
    def validate_graph(self) -> "MapData":
        """Validate graph-level constraints from the subject."""
        self._validate_zone_keys()
        self._validate_special_hubs()

        connection_lines: dict[tuple[str, str], int] = {}
        zone_lines = {
            zone_name: zone.line_number
            for zone_name, zone in self.zones.items()
        }
        for connection in self.connections:
            self._validate_endpoint_exists(
                connection, connection.a, zone_lines
            )
            self._validate_endpoint_exists(
                connection, connection.b, zone_lines
            )

            key = self.connection_key(connection)
            previous_line = connection_lines.get(key)
            if previous_line is not None:
                raise ValueError(
                    f"line {connection.line_number}: duplicate connection "
                    f"{connection.a}-{connection.b}; first defined on line "
                    f"{previous_line}."
                )
            connection_lines[key] = connection.line_number
        return self

    @staticmethod
    def connection_key(connection: Connection) -> tuple[str, str]:
        """Return the canonical undirected key for a connection."""
        return (
            (connection.a, connection.b)
            if connection.a <= connection.b
            else (connection.b, connection.a)
        )

    @classmethod
    def _build_zone_dict(
        cls, raw_zones: list[object]
    ) -> dict[str, object]:
        """Build a zone dict while preserving duplicate-name errors."""
        zones: dict[str, object] = {}
        zone_lines: dict[str, int] = {}
        for raw_zone in raw_zones:
            zone_name = cls._raw_zone_name(raw_zone, "hub")
            line_number = cls._raw_zone_line(raw_zone)
            previous_line = zone_lines.get(zone_name)
            if previous_line is not None:
                # Raw layout groups special hubs before regular hubs.
                first_line = min(previous_line, line_number or previous_line)
                duplicate_line = max(
                    previous_line, line_number or previous_line
                )
                line_text = cls._line_prefix(duplicate_line)
                raise ValueError(
                    f"{line_text}duplicate zone name {zone_name!r}; "
                    f"first defined on line {first_line}."
                )
            zones[zone_name] = raw_zone
            if line_number is not None:
                zone_lines[zone_name] = line_number
        return zones

    @staticmethod
    def _raw_zone_name(raw_zone: object, label: str) -> str:
        """Read a raw zone name before Pydantic validates the full zone."""
        if not isinstance(raw_zone, Mapping):
            raise ValueError(f"{label} zone data must be a mapping.")
        raw_name = raw_zone.get("name")
        if not isinstance(raw_name, str):
            line_text = MapData._line_prefix(
                MapData._raw_zone_line(raw_zone)
            )
            raise ValueError(
                f"{line_text}{label} zone data must include a string name."
            )
        return raw_name

    @staticmethod
    def _raw_zone_line(raw_zone: object) -> int | None:
        """Read a source line number from raw zone data if present."""
        if not isinstance(raw_zone, Mapping):
            return None
        line_number = raw_zone.get("line_number")
        if isinstance(line_number, int):
            return line_number
        return None

    @staticmethod
    def _line_prefix(line_number: int | None) -> str:
        """Return a human-readable line prefix for model-level errors."""
        if line_number is None:
            return ""
        return f"line {line_number}: "

    def _validate_zone_keys(self) -> None:
        """Validate that dict keys match the contained zone names."""
        for zone_name, zone in self.zones.items():
            _validate_zone_name(zone_name, "zone key")
            if zone_name != zone.name:
                raise ValueError(
                    f"line {zone.line_number}: zone key {zone_name!r} "
                    f"does not match zone name {zone.name!r}."
                )

    def _validate_special_hubs(self) -> None:
        """Validate start/end references against the zone dict."""
        if self.start_hub_name == self.end_hub_name:
            raise ValueError("start and end hubs must be different zones.")
        if self.start_hub_name not in self.zones:
            raise ValueError(
                f"unknown start hub {self.start_hub_name!r}."
            )
        if self.end_hub_name not in self.zones:
            raise ValueError(f"unknown end hub {self.end_hub_name!r}.")

    @staticmethod
    def _validate_endpoint_exists(
        connection: Connection, endpoint: str, zone_lines: dict[str, int]
    ) -> None:
        """Require each endpoint to be declared before its connection."""
        if endpoint not in zone_lines:
            raise ValueError(
                f"line {connection.line_number}: unknown zone "
                f"{endpoint!r} in connection {connection.name!r}."
            )
        if zone_lines[endpoint] >= connection.line_number:
            raise ValueError(
                f"line {connection.line_number}: zone {endpoint!r} must be "
                f"defined before connection {connection.name!r}; "
                f"zone defined on line {zone_lines[endpoint]}."
            )
