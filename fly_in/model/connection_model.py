"""Connection settings and their local metadata constraints."""

from pydantic import Field, ValidationInfo, field_validator

from fly_in.model.metadata_model import MetadataModel, MetadataSpec
from fly_in.model.zone_model import _validate_zone_name


class Connection(MetadataModel):
    """A bidirectional connection's settings, without source information."""

    name: str
    a: str
    b: str
    max_link_capacity: int = Field(default=1, gt=0)

    @staticmethod
    def key(a: str, b: str) -> tuple[str, str]:
        """Return the shared canonical identity of an undirected connection."""
        return (a, b) if a <= b else (b, a)

    @classmethod
    def metadata_spec(cls) -> MetadataSpec:
        """Describe the connection metadata block."""
        return MetadataSpec(
            "connection",
            {"max_link_capacity": "max_link_capacity"},
            frozenset({"max_link_capacity"}),
        )

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
    def validate_endpoint(cls, value: str, info: ValidationInfo) -> str:
        """Validate endpoint names and reject self-loops before assignment."""
        value = _validate_zone_name(value, "connection endpoint")
        other = "b" if info.field_name == "a" else "a"
        if value == info.data.get(other):
            raise ValueError(
                "connection endpoints must be different (self-loop)."
            )
        return value
