"""Build raw map dictionaries from parsed Fly-in map lines."""

from __future__ import annotations

from fly_in.parse.map_format_def import (
    LineKey,
    MODEL_METADATA_KEYS,
    MapParseError,
    ParsedLine,
    RawConnection,
    RawMap,
    RawZone,
    ZONE_METADATA_KEY,
    ZONE_TYPE_FIELD,
)


def build_raw_map(parsed_lines: list[ParsedLine]) -> RawMap:
    """Build the JSON-like dictionary passed to Pydantic."""
    raw_map: RawMap = {"hubs": [], "connections": []}

    if not parsed_lines:
        raise ValueError(
            "no map declarations; expected nb_drones, start_hub and end_hub."
        )

    first_line, key, value = parsed_lines[0]
    if key is LineKey.NB_DRONES:
        count = _parse_integer(first_line, key.value, value)
        if count <= 0:
            raise MapParseError(first_line, "nb_drones must be positive.")
        raw_map[key.value] = count
    else:
        raise MapParseError(
            first_line, "first meaningful line must be 'nb_drones: <number>'."
        )

    except_first_line = parsed_lines[1:]
    for line_number, key, value in except_first_line:
        if key in {LineKey.START_HUB, LineKey.END_HUB, LineKey.HUB}:
            _append_zone(raw_map, line_number, key, value)
            continue
        if key is LineKey.CONNECTION:
            _append_connection(raw_map, line_number, value)

    for required in (LineKey.START_HUB, LineKey.END_HUB):
        if required.value not in raw_map:
            raise MapParseError(
                parsed_lines[-1][0],
                f"end of input: missing {required.value} declaration.",
            )
    return raw_map


def _append_zone(
    raw_map: RawMap, line_number: int, key: LineKey, value: str
) -> None:
    """Parse and append one zone to the raw map."""
    raw_zone = _parse_zone(line_number, value)

    if key is LineKey.START_HUB:
        raw_map[key.value] = raw_zone
    elif key is LineKey.END_HUB:
        raw_map[key.value] = raw_zone
    else:
        hubs = raw_map["hubs"]
        if not isinstance(hubs, list):
            raise TypeError("internal parser error: hubs is not a list.")
        hubs.append(raw_zone)


def _append_connection(raw_map: RawMap, line_number: int, value: str) -> None:
    """Parse and append one connection to the raw map."""
    raw_connection = _parse_connection(line_number, value)

    connections = raw_map["connections"]
    if not isinstance(connections, list):
        raise TypeError("internal parser error: connections is not a list.")
    connections.append(raw_connection)


def _parse_zone(line_number: int, value: str) -> RawZone:
    """Parse a start, end, or regular hub line into raw zone data."""
    body, metadata = _parse_metadata(line_number, value)
    parts = body.split()
    if len(parts) != 3:
        raise MapParseError(
            line_number, "zone must use '<name> <x> <y> [metadata]' syntax."
        )

    name, x_value, y_value = parts
    raw_zone: RawZone = {
        "line_number": line_number,
        "name": name,
        "x": _parse_integer(line_number, "x", x_value),
        "y": _parse_integer(line_number, "y", y_value),
    }
    for metadata_key, metadata_value in metadata.items():
        field_name = _metadata_field_name(metadata_key)
        raw_zone[field_name] = (
            _parse_integer(line_number, field_name, metadata_value)
            if field_name == "max_drones" else metadata_value
        )
    return raw_zone


def _parse_connection(line_number: int, value: str) -> RawConnection:
    """Parse a connection line into raw connection data."""
    body, metadata = _parse_metadata(line_number, value)
    if "-" not in body:
        raise MapParseError(
            line_number,
            "connection must use '<zone1>-<zone2> [metadata]' syntax.",
        )

    left, right = body.split("-", 1)
    raw_connection: RawConnection = {
        "line_number": line_number,
        "name": f"{left}-{right}",
        "a": left,
        "b": right,
    }
    for metadata_key, metadata_value in metadata.items():
        field_name = _metadata_field_name(metadata_key)
        raw_connection[field_name] = (
            _parse_integer(line_number, field_name, metadata_value)
            if field_name == "max_link_capacity" else metadata_value
        )
    return raw_connection


def _parse_metadata(
    line_number: int, value: str
) -> tuple[str, dict[str, str]]:
    """Split optional bracket metadata from a line payload."""
    if "[" not in value and "]" not in value:
        return value.strip(), {}

    if (
        value.count("[") != 1 or value.count("]") != 1
        or value.index("[") > value.index("]")
    ):
        raise MapParseError(
            line_number, "metadata must use one pair of '[...]' block."
        )

    body, metadata_part = value.split("[", 1)
    metadata_text, trailing = metadata_part.split("]", 1)
    if trailing.strip():
        raise MapParseError(
            line_number, "unexpected content after metadata block."
        )

    metadata: dict[str, str] = {}
    for token in metadata_text.split():
        key_text, separator, metadata_value = token.partition("=")
        if separator != "=" or not key_text or not metadata_value:
            raise MapParseError(
                line_number,
                f"invalid metadata token {token!r}; expected key=value.",
            )
        if key_text in metadata:
            raise MapParseError(
                line_number, f"duplicate metadata key {key_text!r}."
            )
        metadata[key_text] = metadata_value
    return body.strip(), metadata


def _parse_integer(line_number: int, field_name: str, value: str) -> int:
    """Parse integer syntax without Pydantic's decimal-string coercion."""
    try:
        return int(value)
    except ValueError as error:
        raise MapParseError(
            line_number, f"{field_name} must be an integer; got {value!r}."
        ) from error


def _metadata_field_name(metadata_key: str) -> str:
    """Map external metadata keys to safe raw model field names."""
    if metadata_key == ZONE_METADATA_KEY:
        return ZONE_TYPE_FIELD
    if metadata_key in MODEL_METADATA_KEYS:
        return metadata_key
    return f"metadata.{metadata_key}"
