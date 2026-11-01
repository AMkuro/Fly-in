"""Base for declarations whose optional [...] metadata maps onto fields."""

import re
from abc import ABC, abstractmethod
from typing import NamedTuple

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)


class MetadataSpec(NamedTuple):
    """What a declaration kind accepts inside its [...] block."""

    kind: str
    fields: dict[str, str]
    integer_fields: frozenset[str]


class MetadataModel(BaseModel, ABC):
    """Map declaration metadata onto fields without overwriting any."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    @abstractmethod
    def metadata_spec(cls) -> MetadataSpec:
        """Return the metadata keys, target fields, and integer fields."""

    @staticmethod
    def _validate_integer_text(value: str) -> str:
        """Require signed ASCII decimal text before integer conversion."""
        if re.fullmatch(r"[+-]?[0-9]+", value) is None:
            raise ValueError("must use an ASCII decimal integer.")
        return value

    @model_validator(mode="before")
    @classmethod
    def validate_metadata(cls, value: object) -> object:
        """Validate metadata keys and map them to this model's fields."""
        if not isinstance(value, dict) or "metadata" not in value:
            return value
        values: dict[str, object] = dict(value)
        metadata = values.pop("metadata")
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary.")
        spec = cls.metadata_spec()
        for key, item in metadata.items():
            field = spec.fields.get(key) if isinstance(key, str) else None
            if field is None:
                raise ValueError(
                    f"unsupported {spec.kind} metadata key {key!r}."
                )
            if field in values:
                raise ValueError(
                    f"{spec.kind} metadata key {key!r} duplicates a value "
                    "already set outside the metadata block."
                )
            values[field] = item
        return values

    @field_validator("*", mode="before")
    @classmethod
    def validate_integer_fields(
        cls, value: object, info: ValidationInfo
    ) -> object:
        """Validate integer text, leaving conversion to Pydantic."""
        integer_fields = cls.metadata_spec().integer_fields
        if info.field_name in integer_fields and isinstance(value, str):
            return cls._validate_integer_text(value)
        return value
