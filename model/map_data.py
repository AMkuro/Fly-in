"""Pydantic models for Fly-in map data."""

from __future__ import annotations

from enum import Enum

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
    start_hub: Zone
    end_hub: Zone
    hubs: list[Zone] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> "MapData":
        """Validate graph-level constraints from the subject."""
        zone_lines: dict[str, int] = {}
        for zone in self.all_zones():
            previous_line = zone_lines.get(zone.name)
            if previous_line is not None:
                raise ValueError(
                    f"line {zone.line_number}: duplicate zone name "
                    f"{zone.name!r}; first defined on line {previous_line}."
                )
            zone_lines[zone.name] = zone.line_number

        connection_lines: dict[tuple[str, str], int] = {}
        for connection in self.connections:
            self._validate_endpoint_exists(
                connection, connection.a, zone_lines
            )
            self._validate_endpoint_exists(
                connection, connection.b, zone_lines
            )

            key = (
                (connection.a, connection.b)
                if connection.a <= connection.b
                else (connection.b, connection.a)
            )
            previous_line = connection_lines.get(key)
            if previous_line is not None:
                raise ValueError(
                    f"line {connection.line_number}: duplicate connection "
                    f"{connection.a}-{connection.b}; first defined on line "
                    f"{previous_line}."
                )
            connection_lines[key] = connection.line_number
        return self

    def all_zones(self) -> list[Zone]:
        """Return start, end, and regular hubs as a single list."""
        return [self.start_hub, self.end_hub, *self.hubs]

    @staticmethod
    def _validate_endpoint_exists(
        connection: Connection, endpoint: str, zone_lines: dict[str, int]
    ) -> None:
        """Validate that a connection endpoint exists in the zone list."""
        if endpoint not in zone_lines:
            raise ValueError(
                f"line {connection.line_number}: unknown zone "
                f"{endpoint!r} in connection {connection.name!r}."
            )
