"""Shared scalar, metadata, and error-formatting helpers."""

import re

from pydantic import ValidationError


def validate_integer_text(value: str) -> str:
    """Require signed ASCII decimal text before integer conversion."""
    if re.fullmatch(r"[+-]?[0-9]+", value) is None:
        raise ValueError("must use an ASCII decimal integer.")
    return value


def unpack_metadata(
    value: object, fields: dict[str, str], kind: str
) -> object:
    """Project allowed metadata without overwriting declaration fields."""
    if not isinstance(value, dict) or "metadata" not in value:
        return value
    values: dict[str, object] = dict(value)
    metadata = values.pop("metadata")
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dictionary.")
    for key, item in metadata.items():
        field = fields.get(key) if isinstance(key, str) else None
        if field is None:
            raise ValueError(f"unsupported {kind} metadata key {key!r}.")
        if field in values:
            raise ValueError(
                f"{kind} metadata key {key!r} duplicates a value "
                "already set outside the metadata block."
            )
        values[field] = item
    return values


def validation_message(
    error: ValidationError, metadata_fields: dict[str, str]
) -> str:
    """Describe the first model error using its external metadata names."""
    first = error.errors()[0]
    message = first["msg"].removeprefix("Value error, ")
    names = {field: key for key, field in metadata_fields.items()}
    names.update({"a": "endpoint", "b": "endpoint"})
    fields = [names.get(str(part), str(part)) for part in first["loc"]]
    return f"{'.'.join(fields)}: {message}" if fields else message
