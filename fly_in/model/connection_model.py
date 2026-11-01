"""Connection settings and their local metadata constraints."""

from typing import ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from fly_in.common.validation import unpack_metadata, validate_integer_text
from fly_in.model.zone_model import _validate_zone_name


def connection_key(a: str, b: str) -> tuple[str, str]:
    """Return the shared canonical identity of an undirected connection."""
    return (a, b) if a <= b else (b, a)


class Connection(BaseModel):
    """A bidirectional connection's settings, without source information."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    METADATA_FIELDS: ClassVar[dict[str, str]] = {
        "max_link_capacity": "max_link_capacity"
    }

    name: str
    a: str
    b: str
    max_link_capacity: int = Field(default=1, gt=0)

    @model_validator(mode="before")
    @classmethod
    def validate_metadata(cls, value: object) -> object:
        """Validate metadata keys and map them to this model's fields."""
        return unpack_metadata(value, cls.METADATA_FIELDS, "connection")

    @field_validator("max_link_capacity", mode="before")
    @classmethod
    def validate_integer_text(cls, value: object) -> object:
        """Validate integer text, leaving conversion to Pydantic."""
        if isinstance(value, str):
            return validate_integer_text(value)
        return value

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
