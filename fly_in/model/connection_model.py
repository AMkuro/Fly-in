"""Connection settings and their local metadata constraints."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from fly_in.model.metadata_model import MetadataModel, MetadataSpec
from fly_in.model.zone_model import Zone


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
    def validate_endpoint(cls, value: str) -> str:
        """Validate a connection endpoint name."""
        return Zone.check_name(value, "connection endpoint")

    @model_validator(mode="after")
    def reject_self_loop(self) -> Connection:
        """Reject a connection whose endpoints are the same zone."""
        if self.a == self.b:
            raise ValueError(
                "connection endpoints must be different (self-loop)."
            )
        return self
