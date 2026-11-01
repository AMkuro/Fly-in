"""Zone settings and their local metadata constraints."""

from enum import Enum

from pydantic import Field, field_validator

from fly_in.model.metadata_model import MetadataModel, MetadataSpec


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
    """Validate a zone name shared by map values and drone states."""
    if not value:
        raise ValueError(f"{field_name} must not be empty.")
    if "-" in value:
        raise ValueError(f"{field_name} must not contain dashes.")
    if any(char.isspace() for char in value):
        raise ValueError(f"{field_name} must not contain spaces.")
    return value


class Zone(MetadataModel):
    """A zone's settings, without parser source information."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, gt=0)

    @classmethod
    def metadata_spec(cls) -> MetadataSpec:
        """Describe the zone metadata block."""
        return MetadataSpec(
            "zone",
            {
                "zone": "zone_type",
                "color": "color",
                "max_drones": "max_drones",
            },
            frozenset({"x", "y", "max_drones"}),
        )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate subject constraints for zone names."""
        return _validate_zone_name(value, "zone name")

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        """Accept an optional single-word color without digits."""
        if value is None:
            return value
        if not value:
            raise ValueError("color must not be empty.")
        if any(char.isspace() for char in value):
            raise ValueError("color must be a single-word string.")
        if any(char.isdigit() for char in value):
            raise ValueError("color must not contain digits.")
        return value
